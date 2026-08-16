"""TTS provider: Gemini TTS with automatic EdgeTTS fallback.

- Uses Gemini TTS by default (nice voice).
- When Gemini returns a daily-quota error (HTTP 429 / RESOURCE_EXHAUSTED),
  it marks Gemini exhausted FOR TODAY and serves the rest of the day with
  EdgeTTS (free, no daily cap).
- The next calendar day it tries Gemini again automatically (quota resets).

Both engines output WAV so the pipeline decodes them the same way.

Config (data/.config.yaml):
  selected_module:
    TTS: GeminiEdge
  TTS:
    GeminiEdge:
      type: gemini_edge
      api_key: <gemini key>
      model_name: "gemini-2.5-flash-preview-tts"
      voice: Kore                      # Gemini voice
      edge_voice: "vi-VN-HoaiMyNeural" # EdgeTTS fallback voice
      output_dir: tmp/
"""
import base64
import datetime
import os
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


class _QuotaError(Exception):
    pass


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        # Gemini
        self.api_key = config.get("api_key")
        self.model = config.get("model_name", "gemini-2.5-flash-preview-tts")
        self.voice = config.get("private_voice") or config.get("voice", "Kore")
        self.base_url = config.get(
            "base_url", "https://generativelanguage.googleapis.com/v1beta"
        )
        self.default_rate = int(config.get("sample_rate", 24000))
        # EdgeTTS fallback
        self.edge_voice = config.get("edge_voice", "vi-VN-HoaiMyNeural")
        self.audio_file_type = "wav"
        # date on which Gemini quota was found exhausted (None = try Gemini)
        self._exhausted_date = None

    def _gemini_wav(self, text) -> bytes:
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
        if resp.status_code == 429 or "RESOURCE_EXHAUSTED" in resp.text:
            raise _QuotaError(resp.text[:200])
        if resp.status_code != 200:
            raise Exception(f"Gemini TTS {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        b64 = None
        rate = self.default_rate
        parts = data["candidates"][0]["content"]["parts"]
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
            raise Exception(f"Gemini TTS no audio: {data}")
        return _pcm_to_wav(base64.b64decode(b64), sample_rate=rate)

    async def _edge_wav(self, text) -> bytes:
        import edge_tts
        from pydub import AudioSegment

        mp3 = self.generate_filename(".mp3")
        wav = mp3[:-4] + ".wav"
        try:
            await edge_tts.Communicate(text, self.edge_voice).save(mp3)
            AudioSegment.from_file(mp3, format="mp3").export(wav, format="wav")
            with open(wav, "rb") as f:
                return f.read()
        finally:
            for fp in (mp3, wav):
                try:
                    os.remove(fp)
                except OSError:
                    pass

    async def text_to_speak(self, text, output_file):
        today = datetime.date.today()
        wav = None
        if self.api_key and self._exhausted_date != today:
            try:
                wav = self._gemini_wav(text)
            except _QuotaError:
                self._exhausted_date = today
                logger.bind(tag=TAG).warning(
                    "Gemini TTS het quota ngay -> chuyen EdgeTTS den het ngay"
                )
            except Exception as e:
                logger.bind(tag=TAG).warning(f"Gemini TTS loi: {e} -> EdgeTTS")
        if wav is None:
            wav = await self._edge_wav(text)

        if output_file:
            with open(output_file, "wb") as f:
                f.write(wav)
        else:
            return wav
