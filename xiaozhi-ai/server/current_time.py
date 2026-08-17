"""
时间工具模块 (Vietnam timezone patch)
提供统一的时间获取功能。

Drop-in replacement for core/utils/current_time.py that returns the current
time in Vietnam time (UTC+7) instead of the container's UTC clock. Without
this, the assistant answers "what time is it?" 7 hours behind (e.g. 2:21
instead of 9:21). Vietnam has no daylight saving, so a fixed +7 offset is
always correct; we still prefer the real IANA zone when tzdata is present.
"""

import cnlunar
from datetime import datetime, timezone, timedelta

# Prefer the real IANA zone; fall back to a fixed +7 offset if tzdata is
# unavailable inside the container (both give the same result for Vietnam).
try:
    from zoneinfo import ZoneInfo

    _TZ = ZoneInfo("Asia/Ho_Chi_Minh")
except Exception:  # pragma: no cover - depends on container tzdata
    _TZ = timezone(timedelta(hours=7))


def _now() -> datetime:
    return datetime.now(_TZ)


WEEKDAY_MAP = {
    "Monday": "星期一",
    "Tuesday": "星期二",
    "Wednesday": "星期三",
    "Thursday": "星期四",
    "Friday": "星期五",
    "Saturday": "星期六",
    "Sunday": "星期日",
}


def get_current_time() -> str:
    """
    获取当前时间字符串 (格式: HH:MM)
    """
    return _now().strftime("%H:%M")


def get_current_date() -> str:
    """
    获取今天日期字符串 (格式: YYYY-MM-DD)
    """
    return _now().strftime("%Y-%m-%d")


def get_current_weekday() -> str:
    """
    获取今天星期几
    """
    now = _now()
    return WEEKDAY_MAP[now.strftime("%A")]


def get_current_lunar_date() -> str:
    """
    获取农历日期字符串
    """
    try:
        # cnlunar expects a naive datetime; drop the tzinfo but keep the
        # Vietnam-local calendar date.
        now = _now().replace(tzinfo=None)
        today_lunar = cnlunar.Lunar(now, godType="8char")
        return "%s年%s%s" % (
            today_lunar.lunarYearCn,
            today_lunar.lunarMonthCn[:-1],
            today_lunar.lunarDayCn,
        )
    except Exception:
        return "农历获取失败"


def get_current_time_info() -> tuple:
    """
    获取当前时间信息
    返回: (当前时间字符串, 今天日期, 今天星期, 农历日期)
    """
    current_time = get_current_time()
    today_date = get_current_date()
    today_weekday = get_current_weekday()
    lunar_date = get_current_lunar_date()

    return current_time, today_date, today_weekday, lunar_date
