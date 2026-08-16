"""Gemini TTS provider for xiaozhi-esp32-server.

Uses Google Gemini's native TTS (generateContent with AUDIO modality).
Gemini returns raw PCM (16-bit mono, usually 24kHz); we wrap it in a WAV
container so the server's audio pipeline can decode + opus-encode it.

Config (data/.config.yaml):
  selected_module:
    TTS: GeminiTTS
  TTS:
    GeminiTTS:
      type: gemini
      api_key: <your gemini key>
      model_name: "gemini-2.5-flash-preview-tts"
      voice: Kore          # Kore, Puck, Charon, Aoede, Leda, Orus, Zephyr...
      output_dir: tmp/
"""
import base64
import struct
import requests

from config.logger import setup_logging
from core.providers.tts.base import TTSProviderBase

TAG = __name__
logger = setup_logging()


def _pcm_to_wav(pcm: bytes, sample_rate: int = 24000, channels: int = 1,
                bits: int = 16) -> bytes:
    byte_rate = sample_rate * channels * bits // 8
    block_align = channels * bits // 8
    data_len = len(pcm)
    header = b"RIFF" + struct.pack("<I", 36 + data_len) + b"WAVE"
    header += b"fmt " + struct.pack("<IHHIIHH", 16, 1, channels,
                                    sample_rate, byte_rate, block_align, bits)
    header += b"data" + struct.pack("<I", data_len)
    return header + pcm


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.api_key = config.get("api_key")
        self.model = config.get("model_name", "gemini-2.5-flash-preview-tts")
        self.voice = config.get("private_voice") or config.get("voice", "Kore")
        self.base_url = config.get(
            "base_url", "https://generativelanguage.googleapis.com/v1beta"
        )
        self.default_rate = int(config.get("sample_rate", 24000))
        self.audio_file_type = "wav"

    async def text_to_speak(self, text, output_file):
        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": text}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {"voiceName": self.voice}
                    }
                },
            },
        }
        resp = requests.post(url, json=payload, timeout=30)
        if resp.status_code != 200:
            raise Exception(f"Gemini TTS请求失败: {resp.status_code} - {resp.text}")

        data = resp.json()
        b64 = None
        rate = self.default_rate
        try:
            parts = data["candidates"][0]["content"]["parts"]
        except (KeyError, IndexError):
            raise Exception(f"Gemini TTS phản hồi không hợp lệ: {data}")
        for p in parts:
            inline = p.get("inlineData") or p.get("inline_data")
            if inline and inline.get("data"):
                b64 = inline["data"]
                mt = inline.get("mimeType") or inline.get("mime_type") or ""
                if "rate=" in mt:
                    try:
                        rate = int(mt.split("rate=")[1].split(";")[0])
                    except Exception:
                        pass
                break
        if not b64:
            raise Exception(f"Gemini TTS không trả về audio: {data}")

        wav = _pcm_to_wav(base64.b64decode(b64), sample_rate=rate)
        if output_file:
            with open(output_file, "wb") as f:
                f.write(wav)
        else:
            return wav
