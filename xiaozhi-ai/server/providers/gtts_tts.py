"""TTS provider using gTTS (Google Translate TTS).

Free, no API key, no daily quota, reliable from most servers. Good Vietnamese
voice. Outputs WAV (converted from gTTS mp3 via pydub/ffmpeg).

Config (data/.config.yaml):
  selected_module:
    TTS: GTTS
  TTS:
    GTTS:
      type: gtts
      lang: vi
      output_dir: tmp/
"""
import os

from config.logger import setup_logging
from core.providers.tts.base import TTSProviderBase

TAG = __name__
logger = setup_logging()


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.lang = config.get("lang", "vi")
        self.tld = config.get("tld", "com")
        self.audio_file_type = "wav"

    async def text_to_speak(self, text, output_file):
        from gtts import gTTS
        from pydub import AudioSegment

        mp3 = self.generate_filename(".mp3")
        wav = mp3[:-4] + ".wav"
        try:
            gTTS(text=text, lang=self.lang, tld=self.tld).save(mp3)
            AudioSegment.from_file(mp3, format="mp3").export(wav, format="wav")
            with open(wav, "rb") as f:
                data = f.read()
        finally:
            for fp in (mp3, wav):
                try:
                    os.remove(fp)
                except OSError:
                    pass

        if output_file:
            with open(output_file, "wb") as f:
                f.write(data)
        else:
            return data
