"""Robot-error voice bridge LLM provider for xiaozhi-esp32-server.

Subclasses the Gemini LLM provider so normal chat is unchanged. When the user
enters "robot mode" (says a machine word like "robot", or is already in mode),
the utterance is forwarded to the n8n leader/branch bot which looks up the
error/alarm code and returns a spoken-friendly answer. Say "kết thúc robot"
to leave the mode.

Config (data/.config.yaml):
  selected_module:
    LLM: RobotBridge
  LLM:
    RobotBridge:
      type: robot_bridge
      api_key: <gemini key>              # reused for normal chat + passed to n8n
      model_name: "gemini-2.5-flash"
      n8n_url: "http://42.112.26.67:5678/webhook/jarvis-bot"
"""
import re
import unicodedata
import requests

from config.logger import setup_logging
from core.providers.llm.gemini.gemini import LLMProvider as GeminiLLM

TAG = __name__
logger = setup_logging()


def _norm(s):
    s = (s or "").lower()
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


# Enter robot mode when a machine word appears; leave on an exit phrase.
_ENTER = re.compile(r"\b(robot|tay may)\b")
_EXIT = re.compile(r"(ket thuc robot|thoat robot|dung robot|ket thuc may)")


def _clean(text):
    text = (text or "").replace("*", "").replace("#", "")
    text = re.sub(r"\s*\n\s*", " ", text)
    return re.sub(r"\s{2,}", " ", text).strip()


class LLMProvider(GeminiLLM):
    def __init__(self, config):
        super().__init__(config)
        self.n8n_url = config.get(
            "n8n_url", "http://42.112.26.67:5678/webhook/jarvis-bot"
        )
        self._gemini_key = config.get("api_key", "")
        # session_id -> list of user utterances since entering robot mode
        self._ctx = {}

    def _last_user(self, dialogue):
        for m in reversed(dialogue or []):
            if m.get("role") == "user":
                return m.get("content", "") or ""
        return ""

    def _ask_n8n(self, query):
        try:
            r = requests.post(
                self.n8n_url,
                json={"text": query, "gemini_key": self._gemini_key},
                timeout=30,
            )
            return _clean((r.json() or {}).get("reply", ""))
        except Exception as e:
            logger.bind(tag=TAG).error(f"n8n bridge error: {e}")
            return ""

    def _robot_reply(self, session_id, text):
        """Return a reply string if this turn is handled by robot mode, else None."""
        t = _norm(text)
        if _EXIT.search(t):
            self._ctx.pop(session_id, None)
            return "Đã thoát chế độ tra cứu lỗi máy."
        in_mode = session_id in self._ctx
        if not in_mode and _ENTER.search(t):
            self._ctx[session_id] = []
            in_mode = True
        if not in_mode:
            return None
        # accumulate recent turns so follow-ups ("cảnh báo", a new code...) keep context
        self._ctx[session_id].append(text)
        self._ctx[session_id] = self._ctx[session_id][-4:]
        query = " ".join(self._ctx[session_id])
        reply = self._ask_n8n(query)
        return reply or None  # fall through to normal chat if n8n failed

    def response(self, session_id, dialogue, **kwargs):
        reply = self._robot_reply(session_id, self._last_user(dialogue))
        if reply is not None:
            yield reply
            return
        yield from super().response(session_id, dialogue, **kwargs)

    def response_with_functions(self, session_id, dialogue, functions=None):
        reply = self._robot_reply(session_id, self._last_user(dialogue))
        if reply is not None:
            yield reply, None
            return
        yield from super().response_with_functions(session_id, dialogue, functions)
