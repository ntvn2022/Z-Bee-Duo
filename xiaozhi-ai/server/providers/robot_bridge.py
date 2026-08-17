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
import json
import os
import re
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
        self._registry = None          # cached registry.json
        self._tables = {}              # machine id -> cached rows
        self._mode = set()             # session_ids currently in robot mode

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
            return "Dạ, bạn cần gì ạ?"
        return None

    def _maybe_enter(self, session_id, text):
        n = _norm(text)
        if _EXIT.search(n):
            self._mode.discard(session_id)
            return "exit"
        if session_id not in self._mode and _ENTER.search(n):
            self._mode.add(session_id)
        return "in" if session_id in self._mode else None

    def response(self, session_id, dialogue, **kwargs):
        text = self._last_user(dialogue)
        state = self._maybe_enter(session_id, text)
        if state == "exit":
            yield "Đã thoát chế độ tra cứu lỗi máy."
            return
        if state == "in":
            yield from self._robot_answer(session_id, text)
            return
        w = self._wake_reply(text)
        if w is not None:
            yield w
            return
        yield from super().response(session_id, dialogue, **kwargs)

    def response_with_functions(self, session_id, dialogue, functions=None):
        text = self._last_user(dialogue)
        state = self._maybe_enter(session_id, text)
        if state == "exit":
            yield "Đã thoát chế độ tra cứu lỗi máy.", None
            return
        if state == "in":
            for chunk in self._robot_answer(session_id, text):
                yield chunk, None
            return
        w = self._wake_reply(text)
        if w is not None:
            yield w, None
            return
        yield from super().response_with_functions(session_id, dialogue, functions)
