from dataclasses import dataclass

from scribe.providers import STTSpec
from scribe.stt.base import STTResult
from scribe.transcript import Segment, Transcript

# A short synthetic Uzbek consultation with Russian medical words, returned for any audio in demo mode.
DEMO_SEGMENTS = [
    ("doctor", "Assalomu alaykum, o'tiring. Nima bezovta qilyapti?"),
    ("patient", "Ikki haftadan beri boshim og'riyapti, ayniqsa ertalab, ensa qismida."),
    ("doctor", "Davleniyani uyda o'lchayapsizmi?"),
    ("patient", "Ha, ertalab 160 ga 100 gacha chiqyapti. Amlodipin 5 milligramm ichyapman."),
    ("doctor", "Hozir bosim 165 ga 100, puls 82. Amlodipinni 10 milligrammga oshiramiz, kuniga bir marta."),
    ("doctor", "Ikki haftadan keyin qayta keling."),
]


@dataclass
class FakeSTT:
    spec: STTSpec

    def transcribe(self, audio: bytes, filename: str, mime_type: str, language_hint: str | None = None) -> STTResult:
        segments = [Segment(id=i, speaker=spk, text=text) for i, (spk, text) in enumerate(DEMO_SEGMENTS)]
        return STTResult(
            transcript=Transcript(segments=segments, language="uz", provider=self.spec.id),
            latency_s=0.0,
            cost_usd=0.0,
        )
