#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


SOURCE_URL = "https://www.bishwagurunepal.com/"
TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"
BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_PATH = BASE_DIR / "data" / "rashifal.json"

SIGN_NAME_MAP = {
    "मेष": "Aries",
    "वृष": "Taurus",
    "मिथुन": "Gemini",
    "कर्क": "Cancer",
    "कर्कट": "Cancer",
    "सिंह": "Leo",
    "कन्या": "Virgo",
    "तुला": "Libra",
    "वृश्चिक": "Scorpio",
    "धनु": "Sagittarius",
    "मकर": "Capricorn",
    "कुम्भ": "Aquarius",
    "मीन": "Pisces",
}

SIGN_SLUG_MAP = {
    "मेष": "aries",
    "वृष": "taurus",
    "मिथुन": "gemini",
    "कर्क": "cancer",
    "कर्कट": "cancer",
    "सिंह": "leo",
    "कन्या": "virgo",
    "तुला": "libra",
    "वृश्चिक": "scorpio",
    "धनु": "sagittarius",
    "मकर": "capricorn",
    "कुम्भ": "aquarius",
    "मीन": "pisces",
}


def fetch_text(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; ShivaWebsiteRashifalBot/1.0; +https://github.com/creatorbgrn/Shiva-Website)"
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="ignore")


def clean_text(value: str) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", value))
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_section(page_html: str) -> str:
    match = re.search(
        r"<!-- Rashifal Section Start -->(.*?)</section>",
        page_html,
        flags=re.S,
    )
    if not match:
        raise RuntimeError("Could not find Bishwaguru rashifal section.")
    return match.group(1)


def extract_date(section_html: str) -> tuple[str, str]:
    date_match = re.search(
        r'<div class="date-display[^"]*">\s*(.*?)\s*</div>',
        section_html,
        flags=re.S,
    )
    if not date_match:
        raise RuntimeError("Could not find Bishwaguru rashifal date block.")

    raw_date = clean_text(date_match.group(1))
    english_match = re.search(r"\((?:तदनुसार\s*)?([^)]+)\)", raw_date)
    english_date = english_match.group(1).strip() if english_match else translate_text(raw_date)
    return raw_date, english_date


def normalize_sign_name(name_np: str) -> str:
    normalized = clean_text(name_np)
    if normalized == "कर्कट":
        return "कर्क"
    return normalized


def extract_cards(section_html: str) -> list[dict[str, str]]:
    pattern = re.compile(
        r'<div class="rashifal-card[^>]*style="background-color:\s*([^;"]+);?"[^>]*>\s*'
        r'<div class="zodiac-icon[^>]*>(.*?)</div>\s*'
        r'<h5[^>]*>(.*?)</h5>\s*'
        r'<div class="rashi-letters[^>]*>(.*?)</div>\s*'
        r'<p class="card-text">(.*?)</p>',
        flags=re.S,
    )
    cards: list[dict[str, str]] = []
    for color, symbol, sign_np, letters_np, content_np in pattern.findall(section_html):
        title_np = normalize_sign_name(sign_np)
        cards.append(
            {
                "slug": SIGN_SLUG_MAP.get(title_np, title_np),
                "sign_np": title_np,
                "sign_en": SIGN_NAME_MAP.get(title_np, title_np),
                "symbol": clean_text(symbol),
                "letters_np": clean_text(letters_np),
                "content_np": clean_text(content_np),
                "color": clean_text(color),
            }
        )

    if len(cards) != 12:
        raise RuntimeError(f"Expected 12 rashifal cards, found {len(cards)}.")

    return cards


def translate_text(text: str) -> str:
    params = urllib.parse.urlencode(
        {
            "client": "gtx",
            "sl": "ne",
            "tl": "en",
            "dt": "t",
            "q": text,
        }
    )
    request = urllib.request.Request(
        f"{TRANSLATE_URL}?{params}",
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    translated_chunks: list[str] = []
    for chunk in payload[0]:
        if chunk and chunk[0]:
            translated_chunks.append(chunk[0])
    return "".join(translated_chunks).strip()


def build_payload(page_html: str) -> dict[str, object]:
    section_html = extract_section(page_html)
    date_np, date_en = extract_date(section_html)
    cards = extract_cards(section_html)

    for index, card in enumerate(cards):
        try:
            card["content_en"] = translate_text(card["content_np"])
            time.sleep(0.25)
        except Exception:
            card["content_en"] = card["content_np"]
        cards[index] = card

    return {
        "source": {
            "name": "Bishwaguru Nepal",
            "url": SOURCE_URL,
            "reference_np": "स्रोत: Bishwaguru Nepal",
            "reference_en": "Source: Bishwaguru Nepal",
            "translation_note_np": "अंग्रेजी सामग्री सुविधा लागि देखाइएको अनुवाद हो।",
            "translation_note_en": "English text is shown as a convenience translation of the sourced Nepali rashifal.",
        },
        "title_np": "आजको राशिफल",
        "title_en": "Today's Rashifal",
        "date_np": date_np,
        "date_en": date_en,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "signs": cards,
    }


def main() -> int:
    page_html = fetch_text(SOURCE_URL)
    payload = build_payload(page_html)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote rashifal data to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
