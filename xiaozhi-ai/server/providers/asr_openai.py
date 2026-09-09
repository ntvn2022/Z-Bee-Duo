import time
import os
from config.logger import setup_logging
from typing import Optional, Tuple, List
from core.providers.asr.dto.dto import InterfaceType
from core.providers.asr.base import ASRProviderBase

import requests

TAG = __name__
logger = setup_logging()

# [custom] The settings screen writes the chosen UI language here (vi/en/zh).
# We force Whisper to transcribe in that language so, e.g., Chinese speech is not
# mis-detected as Vietnamese. Same file the LLM bridge and gTTS read.
_LANG_FILE = "/opt/xiaozhi-esp32-server/data/robot/lang.txt"
_WHISPER_LANG = {"vi": "vi", "en": "en", "zh": "zh"}


def _selected_lang(default="vi"):
    try:
        with open(_LANG_FILE, encoding="utf-8") as f:
            c = f.read().strip().lower()
            if c in _WHISPER_LANG:
                return _WHISPER_LANG[c]
    except Exception:
        pass
    return _WHISPER_LANG.get(default, "vi")


class ASRProvider(ASRProviderBase):
    def __init__(self, config: dict, delete_audio_file: bool):
        self.interface_type = InterfaceType.NON_STREAM
        self.api_key = config.get("api_key")
        self.api_url = config.get("base_url")
        self.model = config.get("model_name")
        self.output_dir = config.get("output_dir")
        self.delete_audio_file = delete_audio_file
        # Optional override; if empty we follow the selected UI language.
        self.forced_language = config.get("language", "")

        os.makedirs(self.output_dir, exist_ok=True)

    def requires_file(self) -> bool:
        return True

    async def speech_to_text(self, opus_data: List[bytes], session_id: str, artifacts=None) -> Tuple[Optional[str], Optional[str]]:
        file_path = None
        try:
            if artifacts is None:
                return "", None
            file_path = artifacts.file_path

            logger.bind(tag=TAG).info(f"file path: {file_path}")
            headers = {
                "Authorization": f"Bearer {self.api_key}",
            }

            lang = self.forced_language or _selected_lang()
            # Pass the language so Whisper transcribes in the selected language
            # (auto-detect was mis-hearing Chinese as Vietnamese).
            data = {
                "model": self.model,
                "language": lang,
            }
            logger.bind(tag=TAG).info(f"ASR language: {lang}")

            with open(file_path, "rb") as audio_file:
                files = {
                    "file": audio_file
                }

                start_time = time.time()
                response = requests.post(
                    self.api_url,
                    files=files,
                    data=data,
                    headers=headers
                )
                logger.bind(tag=TAG).debug(
                    f"语音识别耗时: {time.time() - start_time:.3f}s | 结果: {response.text}"
                )

            if response.status_code == 200:
                text = response.json().get("text", "")
                return text, file_path
            else:
                raise Exception(f"API请求失败: {response.status_code} - {response.text}")

        except Exception as e:
            logger.bind(tag=TAG).error(f"语音识别失败: {e}")
            return "", None
