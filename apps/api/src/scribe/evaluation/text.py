"""Text metrics for Uzbek/Russian: normalization, WER/CER, keyword and term matching, script purity."""

import re
import unicodedata

# All the ways Uzbek oʻ / gʻ / tutuq belgisi get typed or transcribed.
_APOSTROPHES = "ʻʼ’‘`´ʹ′"
_APOSTROPHE_RE = re.compile(f"[{_APOSTROPHES}]")
_NON_WORD_RE = re.compile(r"[^\w\s'.,]", re.UNICODE)
_PUNCT_RE = re.compile(r"(?<!\d)[.,]|[.,](?!\d)")  # keep decimal separators inside numbers like 9,8
_SPACE_RE = re.compile(r"\s+")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text).lower().replace("ё", "е")
    text = _APOSTROPHE_RE.sub("'", text)
    text = _NON_WORD_RE.sub(" ", text)
    text = _PUNCT_RE.sub(" ", text)
    return _SPACE_RE.sub(" ", text).strip()


def _edit_distance(ref: list[str], hyp: list[str]) -> int:
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i] + [0] * len(hyp)
        for j, h in enumerate(hyp, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h))
        prev = cur
    return prev[-1]


def wer(reference: str, hypothesis: str) -> float:
    ref, hyp = normalize(reference).split(), normalize(hypothesis).split()
    if not ref:
        return 0.0 if not hyp else 1.0
    return _edit_distance(ref, hyp) / len(ref)


def cer(reference: str, hypothesis: str) -> float:
    ref, hyp = list(normalize(reference).replace(" ", "")), list(normalize(hypothesis).replace(" ", ""))
    if not ref:
        return 0.0 if not hyp else 1.0
    return _edit_distance(ref, hyp) / len(ref)


def keywords_found(groups: list[str], text: str) -> bool:
    """True if every group matches. A group is "a|b|c": any alternative may appear (as a substring)."""
    norm = normalize(text)
    return all(any(normalize(alt) in norm for alt in group.split("|")) for group in groups)


def term_recall(terms: list[str], text: str) -> float | None:
    if not terms:
        return None
    norm = normalize(text)
    return sum(normalize(t) in norm for t in terms) / len(terms)


def _is_cyrillic(ch: str) -> bool:
    return "CYRILLIC" in unicodedata.name(ch, "")


def wrong_script_ratio(text: str, language: str) -> float:
    """Share of letters in the wrong alphabet: Cyrillic in uz-Latn, Latin in uz-Cyrl / ru.

    Latin in Cyrillic notes is partly legitimate (ICD-10 codes, "SpO2", some drug names), so expect a small
    non-zero value there; Cyrillic in uz-Latn should be exactly zero.
    """
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return 0.0
    if language == "uz-Latn":
        wrong = sum(_is_cyrillic(ch) for ch in letters)
    else:
        wrong = sum(not _is_cyrillic(ch) for ch in letters)
    return wrong / len(letters)
