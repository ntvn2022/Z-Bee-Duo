# [custom] Force the process timezone to Vietnam (UTC+7).
#
# Python auto-imports sitecustomize at interpreter startup (via the `site`
# module) when it is found on sys.path (e.g. in site-packages). Setting TZ
# here makes every bare datetime.now() / time.localtime() in the server return
# Vietnam local time, without editing each call site.
#
# "ICT-7" is a POSIX TZ string (the offset sign is inverted in POSIX, so -7
# means UTC+7). Using the POSIX form means no tzdata / zoneinfo files are
# required inside the container. Vietnam has no daylight saving.
import os
import time

os.environ["TZ"] = "ICT-7"
try:
    time.tzset()
except Exception:
    pass
