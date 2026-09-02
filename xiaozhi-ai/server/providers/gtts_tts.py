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
      gain_db: 0        # them do to sau khi chuan hoa (canh bao: >0 co the re)
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
        # Extra loudness (dB) applied AFTER compression+normalize. 0 is already
        # as loud as possible without clipping; >0 gets louder but may distort.
        try:
            self.gain_db = float(config.get("gain_db", 0) or 0)
        except (TypeError, ValueError):
            self.gain_db = 0.0
        self.audio_file_type = "wav"

    async def text_to_speak(self, text, output_file):
        from gtts import gTTS
        from pydub import AudioSegment

        mp3 = self.generate_filename(".mp3")
        wav = mp3[:-4] + ".wav"
        try:
            gTTS(text=text, lang=self.lang, tld=self.tld).save(mp3)
            seg = AudioSegment.from_file(mp3, format="mp3")
            # Make speech noticeably louder for small speakers: compress the
            # dynamic range (lift quiet parts) then peak-normalize to full scale.
            try:
                from pydub.effects import compress_dynamic_range, normalize

                seg = normalize(compress_dynamic_range(seg))
                if self.gain_db:
                    seg = seg.apply_gain(self.gain_db)
            except Exception as e:
                logger.bind(tag=TAG).warning(f"gtts loudness boost skipped: {e}")
            seg.export(wav, format="wav")
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
