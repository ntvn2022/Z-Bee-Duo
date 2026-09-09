"""Robot-error voice bridge LLM provider for xiaozhi-esp32-server.

Subclasses the Gemini LLM provider so normal chat is unchanged. When the user
enters "robot mode" (says a machine word / code), the error/alarm/symbol/cable
lookup is done LOCALLY (tables cached in memory) and the Vietnamese answer is
produced by streaming Gemini directly - no n8n hop. This removes the slow,
flaky round-trip (registry+tables were re-fetched from GitHub on every query,
and an empty n8n response caused "Expecting value: line 1 column 1"), and the
streamed answer lets the device start speaking almost immediately.

Say "kết thúc robot" to leave the mode.

Config (data/.config.yaml):
  selected_module:
    LLM: RobotBridge
  LLM:
    RobotBridge:
      type: robot_bridge
      api_key: <gemini key>          # reused for normal chat + robot answers
      model_name: "gemini-2.5-flash"
      registry_url: "<optional override>"
"""
import datetime as _dt
import json
import os
import re
import threading
import unicodedata

import requests

from config.logger import setup_logging
from core.providers.llm.gemini.gemini import LLMProvider as GeminiLLM

TAG = __name__
logger = setup_logging()

_REGISTRY_URL = (
    "https://raw.githubusercontent.com/ntvn2022/z-bee-duo/"
    "claude/esp32-s3-touch-screen-wwelt1/xiaozhi-ai/machines/registry.json"
)
# Local data dir (bundled by speedup-robot.sh) is tried FIRST, so the runtime
# never depends on GitHub (which rate-limits this VPS with HTTP 429). URLs are
# only a fallback if the local files are missing.
_ROBOT_DIR = "/opt/xiaozhi-esp32-server/data/robot"

# Enter robot mode on a machine word or a machine symbol/code; leave on an exit
# phrase. Wake word alone gets a short Vietnamese prompt.
_ENTER = re.compile(
    r"\b(robot|tay may|ky hieu|day tin hieu|fc[a-z0-9]{1,5}|ry\d{1,2}"
    r"|[txy]\d{1,3}|sp\d{1,2}|sg\d|al\d|es\d|ej\d)\b"
)
_EXIT = re.compile(r"(ket thuc robot|thoat robot|dung robot|ket thuc may)")
_WAKE = re.compile(r"^(alexa|hi|hey|hello|ok|chao|xin chao|a ?lo)[ !,.?]*$")
# Time / date questions are answered instantly and locally (normal Gemini chat
# takes ~100s here), always in Vietnam time (UTC+7), no dependency on anything.
_TIME_Q = re.compile(
    r"(may gio|gio roi|gio hien tai|thoi gian bay gio|bay gio.*gio"
    r"|what time|time now|几点|现在几点)"
)
_DATE_Q = re.compile(
    r"(hom nay.*(ngay|thu|bao nhieu)|ngay may|ngay bao nhieu|thu may|hom nay la ngay"
    r"|what day|what.{0,3}the date|date today|today.*date|几号|星期几|今天星期)"
)
_VN_TZ = _dt.timezone(_dt.timedelta(hours=7))
# Weather via open-meteo (free, no API key). Answered directly in the bridge.
_WEATHER_Q = re.compile(r"(thoi tiet|weather|天气)")
_WMO = {
    0: "trời quang", 1: "trời quang", 2: "có mây", 3: "nhiều mây",
    45: "sương mù", 48: "sương mù",
    51: "mưa phùn nhẹ", 53: "mưa phùn", 55: "mưa phùn nặng",
    56: "mưa phùn đông đá", 57: "mưa phùn đông đá",
    61: "mưa nhẹ", 63: "mưa", 65: "mưa to",
    66: "mưa đông đá", 67: "mưa đông đá",
    71: "tuyết nhẹ", 73: "tuyết", 75: "tuyết dày", 77: "hạt tuyết",
    80: "mưa rào nhẹ", 81: "mưa rào", 82: "mưa rào lớn",
    85: "mưa tuyết", 86: "mưa tuyết",
    95: "dông", 96: "dông kèm mưa đá", 99: "dông kèm mưa đá",
}
_WEATHER_FILLER = (
    "thoi tiet", "weather", "天气", "bay gio", "the nao", "nhu the nao", "hom nay",
    "ngay mai", "ra sao", "hien tai", "khu vuc", "thanh pho", "cho hoi",
    "cho minh hoi", "?", ".", ",",
)
# Standalone words to drop from a place phrase (word-boundary, so "vinh" is safe).
_PLACE_STOP = re.compile(r"\b(in|at|the|of|today|now|tinh|o|tai)\b")
# Map Vietnamese place names (accent-stripped) to a name the geocoder resolves.
# Provinces are mapped to their main city so weather still works.
_VN_PLACE = {
    "sai gon": "Ho Chi Minh City", "tphcm": "Ho Chi Minh City",
    "tp hcm": "Ho Chi Minh City", "hcm": "Ho Chi Minh City",
    "ho chi minh": "Ho Chi Minh City", "sg": "Ho Chi Minh City",
    "ha noi": "Hanoi", "hn": "Hanoi",
    "da nang": "Da Nang",
    "da lat": "Da Lat", "dalat": "Da Lat",
    "ban me thuot": "Buon Ma Thuot", "buon ma thuot": "Buon Ma Thuot",
    "bmt": "Buon Ma Thuot", "dak lak": "Buon Ma Thuot", "daklak": "Buon Ma Thuot",
    "binh duong": "Thu Dau Mot", "thu dau mot": "Thu Dau Mot",
    "dong nai": "Bien Hoa", "bien hoa": "Bien Hoa",
    "tay ninh": "Tay Ninh",
    "binh phuoc": "Dong Xoai", "dong xoai": "Dong Xoai",
    "ba ria vung tau": "Vung Tau", "vung tau": "Vung Tau", "ba ria": "Ba Ria",
    "can tho": "Can Tho", "hai phong": "Hai Phong", "hue": "Hue",
    "nha trang": "Nha Trang", "khanh hoa": "Nha Trang",
    "bac ninh": "Bac Ninh", "quy nhon": "Quy Nhon", "binh dinh": "Quy Nhon",
    "vinh": "Vinh", "nghe an": "Vinh", "thanh hoa": "Thanh Hoa",
    "long an": "Tan An", "tien giang": "My Tho", "my tho": "My Tho",
    "lam dong": "Da Lat", "gia lai": "Pleiku", "pleiku": "Pleiku",
    "quang ninh": "Ha Long", "ha long": "Ha Long",
}


def _resolve_place(loc):
    """Map a stripped Vietnamese place phrase to a geocoder-friendly name."""
    if loc in _VN_PLACE:
        return _VN_PLACE[loc]
    for k, v in _VN_PLACE.items():
        if k in loc:
            return v
    return loc


# Traffic / travel time: "tu <A> den <B> ..." via Google Directions. Each language
# has its own "from X to Y" pattern; Chinese has no word spaces.
_TRAFFIC_RES = {
    "vi": re.compile(r"\btu\b\s+(.+?)\s+\bden\b\s+(.+)"),
    "en": re.compile(r"\bfrom\b\s+(.+?)\s+\bto\b\s+(.+)"),
    "zh": re.compile(r"从\s*(.+?)\s*到\s*(.+)"),
}
# Trailing question words to strip off the destination, per language.
_DEST_TAILS = {
    "vi": re.compile(
        r"\b(di mat bao lau|di bao lau|mat bao lau|bao lau|bao xa|bao nhieu[a-z ]*"
        r"|may tieng|co ket xe khong|co ket khong|ket xe khong|ket xe|ket khong"
        r"|di duong nao|nhu the nao|the nao|di the nao)\b.*$"
    ),
    "en": re.compile(
        r"\b(how long|how far|take|takes|is it congested|is there traffic"
        r"|any traffic|traffic|by car|to drive|driving)\b.*$"
    ),
    "zh": re.compile(r"(要多久|多久|多远|多长时间|堵车吗|堵不堵|怎么走|开车).*$"),
}


def _dur_lang(sec, lang):
    m = int(round(sec / 60.0))
    tr = _TR[lang]
    if m < 60:
        return f"{m} {tr['min']}"
    h, mm = divmod(m, 60)
    if lang == "zh":
        return f"{h}{tr['hr']}{mm}{tr['min']}" if mm else f"{h}{tr['hr']}"
    return f"{h} {tr['hr']} {mm} {tr['min']}" if mm else f"{h} {tr['hr']}"
_BUOI = (
    (4, "đêm"), (11, "sáng"), (13, "trưa"), (18, "chiều"), (23, "tối"), (24, "đêm"),
)
_WEEKDAY_VI = ["thứ Hai", "thứ Ba", "thứ Tư", "thứ Năm", "thứ Sáu", "thứ Bảy", "Chủ nhật"]

# ---- multi-language support (vi / en / zh) ----------------------------------
_LANG_NAME = {"vi": "Vietnamese", "en": "English", "zh": "Simplified Chinese"}
_LANG_CONFIRM = {
    "vi": "Đã chuyển sang tiếng Việt.",
    "en": "Switched to English.",
    "zh": "已切换到中文。",
}
_SETLANG_RE = re.compile(r"\bsetlang\s+(en|vi|zh)\b")


def _lang_from_text(n):
    # Reliable path: the settings screen sends "setlang en|vi|zh".
    m = _SETLANG_RE.search(n)
    if m:
        return m.group(1)
    # Spoken path: only switch when it's clearly a command (a switch/speak verb),
    # so casual mentions of a language in normal chat don't flip the setting.
    if not re.search(r"(chuyen sang|noi|dung|switch|change|speak|use|说|讲|换成|切换)", n):
        return None
    if re.search(r"(tieng viet|vietnamese|越南语)", n):
        return "vi"
    if re.search(r"(english|tieng anh|英语|英文)", n):
        return "en"
    if re.search(r"(tieng trung|trung quoc|chinese|中文|中国|汉语|普通话)", n):
        return "zh"
    return None


_WD = {
    "vi": ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ nhật"],
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    "zh": ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"],
}
# Weather wrapper words (the sky description comes from the API in-language).
_WX = {
    "vi": {"at": "Thời tiết ở", "temp": "Nhiệt độ", "deg": "độ C",
           "feels": "cảm giác như", "hum": "độ ẩm", "pct": "phần trăm",
           "wind": ["gió nhẹ", "gió vừa", "gió khá mạnh", "gió mạnh"],
           "windu": "km một giờ", "rain_now": "Đang có mưa",
           "rain_hi": "Khả năng mưa cao, khoảng", "rain_md": "Có thể có mưa, khoảng",
           "rain_lo": "Ít khả năng mưa.", "today": "Hôm nay từ", "to": "đến",
           "about": "khoảng",
           "nf": "Xin lỗi, mình không tìm thấy địa điểm", "ask": "Bạn muốn xem thời tiết ở đâu ạ?"},
    "en": {"at": "Weather in", "temp": "Temperature", "deg": "degrees C",
           "feels": "feels like", "hum": "humidity", "pct": "percent",
           "wind": ["light wind", "moderate wind", "fairly strong wind", "strong wind"],
           "windu": "km per hour", "rain_now": "It is raining now",
           "rain_hi": "High chance of rain, about", "rain_md": "Possible rain, about",
           "rain_lo": "Low chance of rain.", "today": "Today between", "to": "and",
           "about": "about",
           "nf": "Sorry, I couldn't find the place", "ask": "Which place's weather would you like?"},
    "zh": {"at": "的天气：", "temp": "气温", "deg": "摄氏度",
           "feels": "体感", "hum": "湿度", "pct": "%",
           "wind": ["微风", "和风", "较强风", "强风"],
           "windu": "公里每小时", "rain_now": "正在下雨",
           "rain_hi": "降雨概率高，约", "rain_md": "可能有雨，约",
           "rain_lo": "降雨概率低。", "today": "今天", "to": "到",
           "nf": "抱歉，找不到这个地点", "ask": "您想查询哪里的天气？"},
}
# Traffic wrapper words (distance/duration text from Google is already localized).
_TR = {
    "vi": {"from": "Từ", "to": "đến", "about": "khoảng", "dur": "đi hết chừng",
           "now": "theo tình hình giao thông hiện tại",
           "cond": ["Đường khá thông thoáng.", "Đường hơi đông xe.", "Đang kẹt xe khá nặng."],
           "min": "phút", "hr": "giờ", "nf": "Xin lỗi, mình không tìm được đường từ",
           "nf2": "đến", "needkey": "Tính năng chỉ đường chưa được bật.",
           "ask": "Bạn muốn đi từ đâu đến đâu ạ?"},
    "en": {"from": "From", "to": "to", "about": "about", "dur": "takes about",
           "now": "with current traffic",
           "cond": ["Traffic is light.", "Traffic is a bit heavy.", "Traffic is quite congested."],
           "min": "min", "hr": "hr", "nf": "Sorry, I couldn't find a route from",
           "nf2": "to", "needkey": "Directions are not enabled yet.",
           "ask": "Where do you want to go from and to?"},
    "zh": {"from": "从", "to": "到", "about": "约", "dur": "大约需要",
           "now": "（按当前路况）",
           "cond": ["道路畅通。", "有点堵车。", "堵车比较严重。"],
           "min": "分钟", "hr": "小时", "nf": "抱歉，找不到从",
           "nf2": "到的路线", "needkey": "尚未启用导航功能。",
           "ask": "您想从哪里到哪里？"},
}


# ---- "Máy 1": voice control of the 3-output ESP32 via MQTT --------------------
# Enter the control loop with "lệnh máy 1"; leave it with "kết thúc máy 1".
_M1_ENTER = re.compile(r"(lenh may 1|dieu khien may 1|vao may 1|control machine 1|机器1|控制机器1|一号机)")
_M1_EXIT = re.compile(r"(ket thuc may 1|thoat may 1|dung may 1|exit machine 1|结束机器1|退出机器1)")
_M1_ON = re.compile(r"\b(bat|mo|on|open|turn on|开|打开|开启)\b")
_M1_OFF = re.compile(r"\b(tat|dong|off|close|turn off|关|关闭)\b")
_M1_ALL = re.compile(r"(tat ca|het|toan bo|all|所有|全部)")
_M1_STATUS = re.compile(r"(trang thai|tinh trang|the nao|bao lau|kiem tra|status|state|how long|状态|多久|情况)")
_M1_SCHED = re.compile(r"(hen gio|dat lich|lich|schedule|定时|计划)")
_M1_CLEAR = re.compile(r"(huy|bo|xoa|clear|cancel|取消|清除)")
# output index from a number word/digit
_NUMWORD = {"mot": 1, "1": 1, "hai": 2, "2": 2, "ba": 3, "3": 3,
            "one": 1, "two": 2, "three": 3, "一": 1, "二": 2, "两": 2, "三": 3}


def _m1_output_index(n):
    """Return 1..3 if the text names an output, else 0."""
    m = re.search(r"(?:dau ra|output|so|kenh|channel|out|号|路)\s*([0-9])", n)
    if m:
        v = int(m.group(1))
        return v if 1 <= v <= 3 else 0
    for w, v in _NUMWORD.items():
        if re.search(r"\b" + re.escape(w) + r"\b", n) or (w in "一二两三" and w in n):
            return v
    return 0


def _m1_time(seg):
    """Parse an 'HH[:.h ]MM' time out of a text fragment -> 'HH:MM' or None."""
    m = re.search(r"(\d{1,2})\s*(?:gio|h|:|点|時|时)\s*(\d{1,2})?", seg)
    if not m:
        m = re.search(r"\b(\d{1,2})\b", seg)
        if not m:
            return None
        h, mn = int(m.group(1)), 0
    else:
        h, mn = int(m.group(1)), int(m.group(2) or 0)
    if 0 <= h <= 23 and 0 <= mn <= 59:
        return f"{h:02d}:{mn:02d}"
    return None


# Localized wording for the máy-1 replies.
_M1 = {
    "vi": {"enter": "Đã vào điều khiển máy 1. Bạn muốn bật, tắt, xem trạng thái hay hẹn giờ đầu ra nào?",
           "exit": "Đã thoát điều khiển máy 1.",
           "on": "Đã bật đầu ra {n}.", "off": "Đã tắt đầu ra {n}.",
           "all_on": "Đã bật tất cả đầu ra.", "all_off": "Đã tắt tất cả đầu ra.",
           "sched": "Đã hẹn đầu ra {n}{on}{off}.",
           "sched_on": " bật lúc {t}", "sched_off": " tắt lúc {t}",
           "cleared": "Đã hủy hẹn giờ đầu ra {n}.",
           "offline": "Máy 1 chưa kết nối. Kiểm tra nguồn và Wi-Fi của máy 1 nhé.",
           "ask": "Bạn muốn thao tác đầu ra nào (1, 2 hay 3)?",
           "st_on": "Đầu ra {n} đang bật, được {d}", "st_off": "Đầu ra {n} đang tắt, được {d}",
           "st_sched": ", hẹn bật {on} tắt {off}", "and": " và ",
           "sec": "{s} giây", "min": "{m} phút", "hour": "{h} giờ {m} phút", "hour0": "{h} giờ"},
    "en": {"enter": "Machine 1 control ready. Turn on, turn off, check status, or schedule which output?",
           "exit": "Exited machine 1 control.",
           "on": "Output {n} turned on.", "off": "Output {n} turned off.",
           "all_on": "All outputs turned on.", "all_off": "All outputs turned off.",
           "sched": "Scheduled output {n}{on}{off}.",
           "sched_on": " on at {t}", "sched_off": " off at {t}",
           "cleared": "Cleared the schedule for output {n}.",
           "offline": "Machine 1 is not connected. Check its power and Wi-Fi.",
           "ask": "Which output (1, 2 or 3)?",
           "st_on": "Output {n} is on, for {d}", "st_off": "Output {n} is off, for {d}",
           "st_sched": ", scheduled on {on} off {off}", "and": " and ",
           "sec": "{s} sec", "min": "{m} min", "hour": "{h} h {m} min", "hour0": "{h} h"},
    "zh": {"enter": "已进入机器1控制。要开、关、查看状态还是定时哪个输出？",
           "exit": "已退出机器1控制。",
           "on": "已打开输出{n}。", "off": "已关闭输出{n}。",
           "all_on": "已打开所有输出。", "all_off": "已关闭所有输出。",
           "sched": "已为输出{n}设定{on}{off}。",
           "sched_on": "{t}开", "sched_off": " {t}关",
           "cleared": "已取消输出{n}的定时。",
           "offline": "机器1未连接，请检查它的电源和Wi-Fi。",
           "ask": "要操作哪个输出（1、2还是3）？",
           "st_on": "输出{n}开启中，已{d}", "st_off": "输出{n}关闭中，已{d}",
           "st_sched": "，定时{on}开{off}关", "and": "；",
           "sec": "{s}秒", "min": "{m}分钟", "hour": "{h}小时{m}分", "hour0": "{h}小时"},
}


def _norm(s):
    s = (s or "").lower()
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _clean(text):
    text = (text or "").replace("*", "").replace("#", "")
    text = re.sub(r"\s*\n\s*", " ", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def _is_digit(s):
    return str(s).isdigit()


class LLMProvider(GeminiLLM):
    def __init__(self, config):
        super().__init__(config)
        self._registry_url = config.get("registry_url", _REGISTRY_URL)
        self._robot_dir = config.get("robot_dir", _ROBOT_DIR)
        self._owm_key = config.get("owm_key", "")  # OpenWeatherMap (accurate)
        self._gmaps_key = config.get("gmaps_key", "")  # Google Directions (traffic)
        self._registry = None          # cached registry.json
        self._tables = {}              # machine id -> cached rows
        self._mode = set()             # session_ids currently in robot mode
        self._lang_file = os.path.join(self._robot_dir, "lang.txt")
        # ---- Máy 1 (MQTT) ----
        self._mqtt_host = config.get("mqtt_host", "")
        self._mqtt_port = int(config.get("mqtt_port", 1883) or 1883)
        self._mqtt_user = config.get("mqtt_user", "")
        self._mqtt_pass = config.get("mqtt_pass", "")
        self._m1 = set()               # session_ids currently in máy-1 control
        self._m1_status = None         # last parsed may1/status payload
        self._m1_online = False        # from may1/online (LWT)
        self._mqtt = None
        self._mqtt_lock = threading.Lock()
        if self._mqtt_host:
            self._mqtt_connect()

    # ---- MQTT (Máy 1) ----
    def _mqtt_connect(self):
        try:
            import paho.mqtt.client as mqtt
        except Exception as e:
            logger.bind(tag=TAG).warning(f"paho-mqtt not installed, máy 1 disabled: {e}")
            return
        try:
            cli = mqtt.Client()
            if self._mqtt_user:
                cli.username_pw_set(self._mqtt_user, self._mqtt_pass)

            def on_connect(c, u, flags, rc):
                c.subscribe("may1/status", 1)
                c.subscribe("may1/online", 1)

            def on_message(c, u, msg):
                try:
                    if msg.topic == "may1/online":
                        self._m1_online = (msg.payload.decode().strip() == "1")
                    elif msg.topic == "may1/status":
                        self._m1_status = json.loads(msg.payload.decode() or "{}")
                except Exception as ex:
                    logger.bind(tag=TAG).error(f"mqtt msg err: {ex}")

            cli.on_connect = on_connect
            cli.on_message = on_message
            cli.connect_async(self._mqtt_host, self._mqtt_port, keepalive=30)
            cli.loop_start()
            self._mqtt = cli
            logger.bind(tag=TAG).info(
                f"máy 1 MQTT connecting to {self._mqtt_host}:{self._mqtt_port}")
        except Exception as e:
            logger.bind(tag=TAG).error(f"mqtt connect failed: {e}")

    def _m1_publish(self, payload):
        if not self._mqtt:
            return False
        try:
            self._mqtt.publish("may1/cmd", json.dumps(payload), qos=1)
            return True
        except Exception as e:
            logger.bind(tag=TAG).error(f"mqtt publish failed: {e}")
            return False

    # ---- language state (shared with the TTS provider via a small file) ----
    def _get_lang(self):
        try:
            with open(self._lang_file, encoding="utf-8") as f:
                c = f.read().strip().lower()
                if c in _LANG_NAME:
                    return c
        except Exception:
            pass
        return "vi"

    def _set_lang(self, code):
        try:
            os.makedirs(self._robot_dir, exist_ok=True)
            with open(self._lang_file, "w", encoding="utf-8") as f:
                f.write(code)
        except Exception as e:
            logger.bind(tag=TAG).error(f"set lang failed: {e}")

    # ---- data: local file first (bundled), URL only as fallback ----
    def _load_local(self, rel):
        p = os.path.join(self._robot_dir, rel)
        try:
            if os.path.exists(p):
                with open(p, encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.bind(tag=TAG).error(f"local {rel} read failed: {e}")
        return None

    def _fetch_json(self, url):
        if not url:
            return None
        try:
            return requests.get(url, timeout=8).json()
        except Exception as e:
            logger.bind(tag=TAG).error(f"fetch {url} failed: {e}")
            return None

    def _get_registry(self):
        if self._registry is None:
            self._registry = (
                self._load_local("registry.json")
                or self._fetch_json(self._registry_url)
                or []
            )
        return self._registry

    def _get_tables(self, machine):
        mid = machine.get("id")
        if mid not in self._tables:
            self._tables[mid] = (
                self._load_local(f"tables/{mid}.json")
                or self._fetch_json(machine.get("tables_url"))
                or []
            )
        return self._tables[mid]

    def _last_user(self, dialogue):
        for m in reversed(dialogue or []):
            if m.get("role") == "user":
                return m.get("content", "") or ""
        return ""

    # ---- lookup: returns ("text", reply) or ("gemini", prompt, fallback) ----
    def _lookup(self, text):
        t = _norm(text)
        reg = self._get_registry()
        machine, best = None, -1
        for m in reg:
            for a in m.get("aliases", []):
                p = t.rfind(_norm(a))
                if p > best:
                    best, machine = p, m
        if machine is None:
            if len(reg) == 1:
                machine = reg[0]
            else:
                names = ", ".join(m.get("name_vi", "") for m in reg)
                return ("text", f"Bạn hỏi về máy nào? Hiện có: {names}.")

        rows = self._get_tables(machine)
        name = machine.get("name_vi", "máy")

        # symbol / signal
        def safe(c):
            return bool(re.search(r"\d", c)) or bool(
                re.match(r"^(FC|SP|SG|AL|ES|EJ|RY)", c, re.I)
            )

        ref, rp = None, -1
        for r in rows:
            if r.get("type") not in ("symbol", "signal"):
                continue
            code = r.get("code", "")
            if not code or not safe(code):
                continue
            mm = re.search(r"\b" + re.escape(code.lower()) + r"\b", t)
            if mm and mm.start() > rp:
                rp, ref = mm.start(), r
        if ref:
            prompt = (
                f'Giải thích ký hiệu "{ref["code"]}" của {name} bằng tiếng Việt, '
                f"rõ ràng dễ hiểu, văn xuôi trơn (không markdown, không * #). "
                f'Dữ liệu: {ref["code"]} = {ref["content"]}\n\nCâu hỏi: {text}'
            )
            return ("gemini", prompt, f'{ref["code"]}: {_clean(ref["content"])}')

        # cable
        if re.search(r"\b(day|cap|cable|chan)\b", t):
            mm = re.search(r"\d{1,2}", t)
            if mm:
                num = int(mm.group())
                cab = next(
                    (
                        r
                        for r in rows
                        if r.get("type") == "cable"
                        and _is_digit(r.get("code", ""))
                        and int(r["code"]) == num
                    ),
                    None,
                )
                if cab:
                    prompt = (
                        f'Giải thích dây tín hiệu (cable) số {cab["code"]} của {name} '
                        f"bằng tiếng Việt, rõ ràng, văn xuôi trơn. "
                        f'Dữ liệu: dây {cab["code"]} = {cab["content"]}\n\nCâu hỏi: {text}'
                    )
                    return (
                        "gemini",
                        prompt,
                        f'Dây tín hiệu số {cab["code"]}: {_clean(cab["content"])}',
                    )

        # error / alarm (mô tả -> nguyên nhân -> khắc phục)
        errT = machine.get("error_types", [])
        almT = machine.get("alarm_types", [])
        nums = re.findall(r"\d{1,3}", t)
        if not nums:
            return (
                "text",
                f"Bạn hỏi mã lỗi/cảnh báo số mấy, hay ký hiệu/chân nào của {name}?",
            )
        num = int(nums[-1])
        ia = max(t.rfind("alarm"), t.rfind("canh bao"))
        ie = max(t.rfind("error"), t.rfind("loi"))
        want_alarm = ia >= 0 and ia > ie
        want_error = ie >= 0 and ie > ia

        def grp(ty):
            return "error" if ty in errT else ("alarm" if ty in almT else "other")

        matches = [
            r
            for r in rows
            if (r.get("type") in errT or r.get("type") in almT)
            and _is_digit(r.get("code", ""))
            and int(r["code"]) == num
        ]
        if not matches:
            return (
                "text",
                f"Không thấy mã {num} cho {name}. Bạn kiểm tra lại số nhé.",
            )
        has_err = any(grp(m["type"]) == "error" for m in matches)
        has_alm = any(grp(m["type"]) == "alarm" for m in matches)
        selected, ask_type = matches, False
        if want_error and not want_alarm:
            selected = [m for m in matches if grp(m["type"]) == "error"]
        elif want_alarm and not want_error:
            selected = [m for m in matches if grp(m["type"]) == "alarm"]
        elif has_err and has_alm:
            ask_type = True
        if not selected:
            selected = matches
        ctx = "\n".join(f'[{m["type"]} {m["code"]}] {m["content"]}' for m in selected)
        s = (
            f"Bạn là trợ lý kỹ thuật cho {name}. Trả lời bằng tiếng Việt, đầy đủ và "
            f"rõ ràng theo thứ tự: 1) Mô tả lỗi 2) Nguyên nhân 3) Cách khắc phục. "
            f"Văn xuôi trơn, KHÔNG markdown, KHÔNG ký hiệu * #. "
        )
        if ask_type:
            s += (
                f"Mã {num} có ở CẢ cảnh báo (alarm) LẪN lỗi (error) — hãy trình bày "
                f"cả hai loại rồi hỏi lại người dùng muốn loại nào. "
            )
        s += (
            "Kết thúc luôn kèm câu nhắc: cần phân biệt cảnh báo (alarm) và lỗi (error) "
            "vì là hai khái niệm khác nhau. CHỈ dùng dữ liệu sau:\n" + ctx
        )
        fallback = (
            "  |  ".join(f'{m["type"]} {m["code"]}: {m["content"]}' for m in selected)
            + "  (Lưu ý: cảnh báo/alarm và lỗi/error là hai loại khác nhau.)"
        )
        return ("gemini", s + f"\n\nCâu hỏi: {text}", fallback)

    # ---- streamed robot answer ----
    def _robot_answer(self, session_id, text):
        result = self._lookup(text)
        if result[0] == "text":
            yield result[1]
            return
        prompt, fallback = result[1], result[2]
        prompt = f"Reply entirely in {_LANG_NAME[self._get_lang()]}. " + prompt
        got = False
        try:
            for chunk in super().response(
                session_id, [{"role": "user", "content": prompt}]
            ):
                if chunk:
                    got = True
                    yield chunk
        except Exception as e:
            logger.bind(tag=TAG).error(f"robot gemini error: {e}")
        if not got:
            yield fallback

    def _wake_reply(self, text):
        if _WAKE.match(_norm(text)):
            return {"vi": "Dạ, bạn cần gì ạ?", "en": "Yes, how can I help?",
                    "zh": "您好，有什么可以帮您？"}[self._get_lang()]
        return None

    def _time_reply(self, text):
        n = _norm(text)
        lang = self._get_lang()
        now = _dt.datetime.now(_VN_TZ)
        if _DATE_Q.search(n):
            wd = _WD[lang][now.weekday()]
            if lang == "en":
                mn = ["January", "February", "March", "April", "May", "June", "July",
                      "August", "September", "October", "November", "December"][now.month - 1]
                return f"Today is {wd}, {mn} {now.day}, {now.year}."
            if lang == "zh":
                return f"今天是{now.year}年{now.month}月{now.day}日，{wd}。"
            return f"Hôm nay là {wd}, ngày {now.day} tháng {now.month} năm {now.year}."
        if _TIME_Q.search(n):
            h, m = now.hour, now.minute
            if lang == "en":
                ampm = "AM" if h < 12 else "PM"
                h12 = h % 12 or 12
                return f"It's {h12}:{m:02d} {ampm}."
            if lang == "zh":
                return f"现在是{h}点{m}分。"
            buoi = next(b for lim, b in _BUOI if h < lim)
            h12 = h % 12 or 12
            phut = f" {m} phút" if m else ""
            return f"Bây giờ là {h12} giờ{phut} {buoi}."
        return None

    def _weather_owm(self, loc):
        """OpenWeatherMap current + short forecast. Returns None on failure so the
        caller can fall back to open-meteo."""
        lang = self._get_lang()
        w = _WX[lang]
        owm_lang = {"vi": "vi", "en": "en", "zh": "zh_cn"}[lang]
        try:
            base = "https://api.openweathermap.org/data/2.5"
            common = {"appid": self._owm_key, "units": "metric", "lang": owm_lang}
            cur = requests.get(
                f"{base}/weather", params={**common, "q": f"{loc},VN"}, timeout=6
            ).json()
            if str(cur.get("cod")) != "200":
                cur = requests.get(
                    f"{base}/weather", params={**common, "q": loc}, timeout=6
                ).json()
            if str(cur.get("cod")) != "200":
                return None
            name = cur.get("name", loc)
            desc = (cur.get("weather") or [{}])[0].get("description", "")
            main = cur.get("main", {})
            temp = round(main.get("temp", 0))
            feels = round(main.get("feels_like", temp))
            hum = main.get("humidity")
            wind_kmh = round((cur.get("wind", {}).get("speed", 0)) * 3.6)
            rain1h = (cur.get("rain") or {}).get("1h")
            tmin = tmax = temp
            pprob = None
            try:
                fc = requests.get(
                    f"{base}/forecast", params={**common, "q": name, "cnt": 8}, timeout=6
                ).json()
                lst = fc.get("list") or []
                temps = [e["main"]["temp"] for e in lst if "main" in e]
                pops = [e.get("pop", 0) for e in lst]
                if temps:
                    tmin, tmax = round(min(temps)), round(max(temps))
                if pops:
                    pprob = round(max(pops) * 100)
            except Exception:
                pass

            if lang == "zh":
                parts = [f"{name}{w['at']}{desc}。"]
                t2 = f"{w['temp']}{temp}{w['deg']}"
                if feels != temp:
                    t2 += f"，{w['feels']}{feels}度"
                parts.append(t2 + "。")
                if hum is not None:
                    parts.append(f"{w['hum']}{hum}%。")
                if wind_kmh:
                    idx = 0 if wind_kmh < 12 else 1 if wind_kmh < 30 else 2 if wind_kmh < 50 else 3
                    parts.append(f"{w['wind'][idx]}，约{wind_kmh}{w['windu']}。")
                if rain1h:
                    parts.append(f"{w['rain_now']}。")
                elif pprob is not None:
                    if pprob >= 60:
                        parts.append(f"{w['rain_hi']}{pprob}%。")
                    elif pprob >= 30:
                        parts.append(f"{w['rain_md']}{pprob}%。")
                    else:
                        parts.append(w["rain_lo"])
                parts.append(f"{w['today']}{tmin}{w['to']}{tmax}{w['deg']}。")
                return "".join(parts)

            parts = [f"{w['at']} {name}: {desc}."]
            t2 = f"{w['temp']} {temp} {w['deg']}"
            if feels != temp:
                t2 += f", {w['feels']} {feels}"
            parts.append(t2 + ".")
            if hum is not None:
                parts.append(f"{w['hum'][0].upper()}{w['hum'][1:]} {hum} {w['pct']}.")
            if wind_kmh:
                idx = 0 if wind_kmh < 12 else 1 if wind_kmh < 30 else 2 if wind_kmh < 50 else 3
                wd = w["wind"][idx]
                parts.append(f"{wd[0].upper()}{wd[1:]}, {w['about'] if 'about' in w else ''} {wind_kmh} {w['windu']}.".replace("  ", " "))
            if rain1h:
                parts.append(f"{w['rain_now']}.")
            elif pprob is not None:
                if pprob >= 60:
                    parts.append(f"{w['rain_hi']} {pprob} {w['pct']}.")
                elif pprob >= 30:
                    parts.append(f"{w['rain_md']} {pprob} {w['pct']}.")
                else:
                    parts.append(w["rain_lo"])
            parts.append(f"{w['today']} {tmin} {w['to']} {tmax} {w['deg']}.")
            return " ".join(parts)
        except Exception as e:
            logger.bind(tag=TAG).error(f"owm weather error: {e}")
            return None

    def _weather_reply(self, text):
        n = _norm(text)
        if not _WEATHER_Q.search(n):
            return None
        loc = n
        for w in _WEATHER_FILLER:
            loc = loc.replace(w, " ")
        loc = _PLACE_STOP.sub(" ", loc)  # drop standalone prepositions/articles
        loc = re.sub(r"\s+", " ", loc).strip()
        if not loc:
            return _WX[self._get_lang()]["ask"]
        loc = _resolve_place(loc)  # provinces / aliases -> geocoder-friendly name
        # Prefer OpenWeatherMap (more accurate, Vietnamese descriptions) if a key
        # is configured; otherwise fall back to the free open-meteo model.
        if self._owm_key:
            r = self._weather_owm(loc)
            if r is not None:
                return r
        try:
            g = requests.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": loc, "count": 1, "language": "vi", "format": "json"},
                timeout=6,
            ).json()
            res = g.get("results") or []
            if not res:
                return f"Xin lỗi, mình không tìm thấy địa điểm {loc}."
            r0 = res[0]
            city = r0.get("name", loc)
            w = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": r0["latitude"],
                    "longitude": r0["longitude"],
                    "current": (
                        "temperature_2m,apparent_temperature,relative_humidity_2m,"
                        "weather_code,cloud_cover,wind_speed_10m,precipitation,is_day"
                    ),
                    "daily": (
                        "temperature_2m_max,temperature_2m_min,"
                        "precipitation_probability_max"
                    ),
                    "timezone": "Asia/Ho_Chi_Minh",
                    "forecast_days": 1,
                },
                timeout=6,
            ).json()
            cur = w.get("current", {})
            daily = w.get("daily", {})
            code = int(cur.get("weather_code", 0))
            temp = round(cur.get("temperature_2m", 0))
            feels = cur.get("apparent_temperature")
            hum = cur.get("relative_humidity_2m")
            cloud = cur.get("cloud_cover")
            wind = cur.get("wind_speed_10m")
            precip = cur.get("precipitation") or 0
            is_day = cur.get("is_day", 1)
            tmin = round((daily.get("temperature_2m_min") or [temp])[0])
            tmax = round((daily.get("temperature_2m_max") or [temp])[0])
            pprob = (daily.get("precipitation_probability_max") or [None])[0]

            # Sky description: rain/fog from the WMO code, otherwise cloud cover.
            if code in _WMO and (code >= 45):
                sky = _WMO[code]
            elif cloud is None:
                sky = _WMO.get(code, "trời quang")
            elif cloud < 20:
                sky = "trời nắng đẹp, quang mây" if is_day else "trời quang, ít mây"
            elif cloud < 60:
                sky = "trời có nắng, ít mây" if is_day else "trời ít mây"
            elif cloud < 85:
                sky = "trời nhiều mây"
            else:
                sky = "trời âm u, nhiều mây"

            parts = [f"Thời tiết ở {city}: {sky}."]
            t2 = f"Nhiệt độ {temp} độ C"
            if feels is not None and round(feels) != temp:
                t2 += f", cảm giác như {round(feels)} độ"
            parts.append(t2 + ".")
            if hum is not None:
                parts.append(f"Độ ẩm {hum} phần trăm.")
            if wind is not None:
                if wind < 12:
                    wd = "gió nhẹ"
                elif wind < 30:
                    wd = "gió vừa"
                elif wind < 50:
                    wd = "gió khá mạnh"
                else:
                    wd = "gió mạnh"
                parts.append(f"{wd[0].upper()}{wd[1:]}, khoảng {round(wind)} km một giờ.")
            if precip > 0:
                parts.append(f"Hiện đang có mưa, lượng mưa {precip} mi li mét.")
            elif pprob is not None:
                if pprob >= 60:
                    parts.append(f"Khả năng mưa cao, khoảng {pprob} phần trăm.")
                elif pprob >= 30:
                    parts.append(f"Có thể có mưa, khoảng {pprob} phần trăm.")
                else:
                    parts.append("Ít khả năng mưa.")
            parts.append(f"Hôm nay dao động từ {tmin} đến {tmax} độ C.")
            return " ".join(parts)
        except Exception as e:
            logger.bind(tag=TAG).error(f"weather error: {e}")
            return "Xin lỗi, hiện chưa lấy được thời tiết. Bạn thử lại sau nhé."

    def _traffic_reply(self, text):
        n = _norm(text)
        lang = self._get_lang()
        tr = _TR[lang]
        m = _TRAFFIC_RES[lang].search(n)
        if not m:  # also accept the other languages' phrasings
            for code, rx in _TRAFFIC_RES.items():
                if code == lang:
                    continue
                m = rx.search(n)
                if m:
                    break
        if not m:
            return None
        if not self._gmaps_key:
            return tr["needkey"]
        origin = re.sub(r"^\s*di\s+", "", m.group(1)).strip()
        dest = _DEST_TAILS[lang].sub("", m.group(2))
        for rx in _DEST_TAILS.values():  # strip any language's trailing question
            dest = rx.sub("", dest)
        dest = dest.strip(" ?.，。")
        if not origin or not dest:
            return tr["ask"]
        o = _resolve_place(origin)
        d = _resolve_place(dest)
        gl = {"vi": "vi", "en": "en", "zh": "zh-CN"}[lang]
        try:
            r = requests.get(
                "https://maps.googleapis.com/maps/api/directions/json",
                params={
                    "origin": o + ", Vietnam",
                    "destination": d + ", Vietnam",
                    "departure_time": "now",
                    "traffic_model": "best_guess",
                    "language": gl,
                    "region": "vn",
                    "key": self._gmaps_key,
                },
                timeout=8,
            ).json()
            st = r.get("status")
            if st != "OK" or not r.get("routes"):
                if st == "REQUEST_DENIED":
                    logger.bind(tag=TAG).error(
                        f"gmaps denied: {r.get('error_message')}"
                    )
                    return tr["needkey"]
                return f"{tr['nf']} {origin} {tr['nf2']} {dest}."
            leg = r["routes"][0]["legs"][0]
            dist = leg["distance"]["text"]
            dur = leg["duration"]["value"]
            durt = leg.get("duration_in_traffic", {}).get("value", dur)
            start = (leg.get("start_address", "") or origin).split(",")[0]
            end = (leg.get("end_address", "") or dest).split(",")[0]
            ratio = (durt / dur) if dur else 1.0
            cond = tr["cond"][2] if ratio >= 1.5 else tr["cond"][1] if ratio >= 1.2 else tr["cond"][0]
            durtxt = _dur_lang(durt, lang)
            if lang == "zh":
                return f"{tr['from']}{start}{tr['to']}{end}{tr['about']}{dist}，{tr['dur']}{durtxt}{tr['now']}。{cond}"
            return (
                f"{tr['from']} {start} {tr['to']} {end} {tr['about']} {dist}, "
                f"{tr['dur']} {durtxt} {tr['now']}. {cond}"
            )
        except Exception as e:
            logger.bind(tag=TAG).error(f"gmaps error: {e}")
            return tr["nf"] + "."

    # ---- Máy 1 control ----
    def _m1_dur(self, sec, lang):
        w = _M1[lang]
        sec = int(sec or 0)
        if sec < 60:
            return w["sec"].format(s=sec)
        m = sec // 60
        if m < 60:
            return w["min"].format(m=m)
        h, mm = divmod(m, 60)
        return w["hour"].format(h=h, m=mm) if mm else w["hour0"].format(h=h)

    def _m1_status_line(self, lang, only=None):
        w = _M1[lang]
        st = self._m1_status or {}
        outs = st.get("outs") or []
        if not outs:
            return w["offline"]
        lines = []
        for i, o in enumerate(outs[:3], start=1):
            if only and i != only:
                continue
            d = self._m1_dur(o.get("since_s", 0), lang)
            base = (w["st_on"] if o.get("on") else w["st_off"]).format(n=i, d=d)
            on_t, off_t = o.get("on_time", ""), o.get("off_time", "")
            if on_t or off_t:
                base += w["st_sched"].format(on=on_t or "--:--", off=off_t or "--:--")
            lines.append(base)
        return (w["and"].join(lines) + ".") if lines else w["ask"]

    def _m1_reply(self, session_id, text):
        """Handle one utterance while in máy-1 control mode."""
        n = _norm(text)
        lang = self._get_lang()
        w = _M1[lang]
        if not self._mqtt:
            return w["offline"]
        idx = _m1_output_index(n)

        # schedule: "hen gio dau ra 1 bat 18 gio tat 22 gio"
        if _M1_SCHED.search(n):
            if _M1_CLEAR.search(n):
                if not idx:
                    return w["ask"]
                self._m1_publish({"cmd": "clear_schedule", "out": idx})
                return w["cleared"].format(n=idx)
            if not idx:
                return w["ask"]
            on_seg = re.split(r"\btat\b|\boff\b|关", n)[0]
            on_part = on_seg.split("bat", 1)[1] if "bat" in on_seg else (
                on_seg.split("on", 1)[1] if "on" in on_seg else "")
            off_part = ""
            m_off = re.split(r"\btat\b|\boff\b|关", n)
            if len(m_off) > 1:
                off_part = m_off[1]
            on_t = _m1_time(on_part) if on_part else None
            off_t = _m1_time(off_part) if off_part else None
            payload = {"cmd": "schedule", "out": idx}
            if on_t:
                payload["on"] = on_t
            if off_t:
                payload["off"] = off_t
            if "on" not in payload and "off" not in payload:
                return w["ask"]
            self._m1_publish(payload)
            return w["sched"].format(
                n=idx,
                on=(w["sched_on"].format(t=on_t) if on_t else ""),
                off=(w["sched_off"].format(t=off_t) if off_t else ""))

        # status query (checked before on/off: a status question like "đang bật
        # bao lâu" contains the word "bật", which must not trigger a switch).
        if _M1_STATUS.search(n):
            if not self._m1_online and not self._m1_status:
                return w["offline"]
            return self._m1_status_line(lang, only=idx or None)

        # on / off (single or all). Remove the "all" phrase first so that
        # "tắt tất cả" (contains "tat" twice) doesn't confuse on/off detection.
        all_flag = bool(_M1_ALL.search(n))
        n2 = _M1_ALL.sub(" ", n)
        want_on = bool(_M1_ON.search(n2))
        want_off = bool(_M1_OFF.search(n2))
        if want_on or want_off:
            on = want_on and not want_off
            if all_flag:
                self._m1_publish({"cmd": "set_all", "on": on})
                return w["all_on"] if on else w["all_off"]
            if not idx:
                return w["ask"]
            self._m1_publish({"cmd": "set", "out": idx, "on": on})
            return (w["on"] if on else w["off"]).format(n=idx)

        return w["ask"]

    def _maybe_setlang(self, text):
        """Return a confirmation string if the user (or the settings screen)
        asked to change language, else None."""
        code = _lang_from_text(_norm(text))
        if code:
            self._set_lang(code)
            return _LANG_CONFIRM[code]
        return None

    def _lang_dialogue(self, dialogue):
        """Return a dialogue that makes normal Gemini chat reply in the selected
        language. The server's persona system prompt is written in Vietnamese and
        keeps answers Vietnamese, so for a non-Vietnamese language we REPLACE the
        system prompt with a clean language-forcing one (keeping the user/assistant
        turns for context) and reinforce the language on the last user turn."""
        lang = self._get_lang()
        if lang == "vi":
            return dialogue  # default persona is already Vietnamese
        name = _LANG_NAME[lang]
        sys_prompt = (
            f"You are a friendly voice assistant. You MUST reply ONLY in {name}. "
            f"Never use Vietnamese. Keep answers short and natural for speech, "
            f"with no markdown or special symbols."
        )
        turns = [m for m in (dialogue or []) if m.get("role") != "system"]
        # reinforce the language on the most recent user turn (recency helps)
        rebuilt = []
        tagged = False
        for m in reversed(turns):
            mm = dict(m)
            if not tagged and mm.get("role") == "user":
                mm["content"] = (mm.get("content", "") or "") + f"\n\n[Answer in {name} only.]"
                tagged = True
            rebuilt.append(mm)
        rebuilt.reverse()
        return [{"role": "system", "content": sys_prompt}] + rebuilt

    def _maybe_enter(self, session_id, text):
        # The robot-error lookup is a Vietnamese-only feature (Vietnamese tables
        # and trigger words). In English/Chinese mode a word like "robot" must go
        # to normal chat and be answered in that language, not enter this mode.
        if self._get_lang() != "vi":
            self._mode.discard(session_id)
            return None
        n = _norm(text)
        if _EXIT.search(n):
            self._mode.discard(session_id)
            return "exit"
        if session_id not in self._mode and _ENTER.search(n):
            self._mode.add(session_id)
        return "in" if session_id in self._mode else None

    def _maybe_enter_m1(self, session_id, text):
        n = _norm(text)
        if _M1_EXIT.search(n):
            self._m1.discard(session_id)
            return "exit"
        if session_id not in self._m1 and _M1_ENTER.search(n):
            self._m1.add(session_id)
            return "enter"
        return "in" if session_id in self._m1 else None

    def response(self, session_id, dialogue, **kwargs):
        text = self._last_user(dialogue)
        sl = self._maybe_setlang(text)
        if sl is not None:
            yield sl
            return
        m1 = self._maybe_enter_m1(session_id, text)
        if m1 == "exit":
            yield _M1[self._get_lang()]["exit"]
            return
        if m1 == "enter":
            yield _M1[self._get_lang()]["enter"]
            return
        if m1 == "in":
            yield self._m1_reply(session_id, text)
            return
        state = self._maybe_enter(session_id, text)
        if state == "exit":
            yield "Đã thoát chế độ tra cứu lỗi máy."
            return
        if state == "in":
            yield from self._robot_answer(session_id, text)
            return
        w = self._wake_reply(text) or self._traffic_reply(text) or self._time_reply(text) or self._weather_reply(text)
        if w is not None:
            yield w
            return
        yield from super().response(session_id, self._lang_dialogue(dialogue), **kwargs)

    def response_with_functions(self, session_id, dialogue, functions=None):
        text = self._last_user(dialogue)
        sl = self._maybe_setlang(text)
        if sl is not None:
            yield sl, None
            return
        m1 = self._maybe_enter_m1(session_id, text)
        if m1 == "exit":
            yield _M1[self._get_lang()]["exit"], None
            return
        if m1 == "enter":
            yield _M1[self._get_lang()]["enter"], None
            return
        if m1 == "in":
            yield self._m1_reply(session_id, text), None
            return
        state = self._maybe_enter(session_id, text)
        if state == "exit":
            yield "Đã thoát chế độ tra cứu lỗi máy.", None
            return
        if state == "in":
            for chunk in self._robot_answer(session_id, text):
                yield chunk, None
            return
        w = self._wake_reply(text) or self._traffic_reply(text) or self._time_reply(text) or self._weather_reply(text)
        if w is not None:
            yield w, None
            return
        yield from super().response_with_functions(
            session_id, self._lang_dialogue(dialogue), functions
        )
