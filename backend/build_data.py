"""Build pages.json: page -> lines -> words from raw mushaf line data.

Sources:
  - pages_raw.json : 604 pages x 15 lines, exact Madani 15-line Mushaf layout
                     (scraped from quran.com, github.com/blueheron786/line-by-line-quran)
  - quran_full.json : 114 surahs Uthmani text (risan/quran-json, from tanzil.net)

Output:
  data/pages.json
  {
    "pages": {
      "1": [
        {"n": 9, "text": "...", "words": [{"t": "بِسْمِ", "m": null}, {"t": "١", "m": 1}]},
        ...
      ]
    },
    "meta": {...}
  }
"""

import json
import re
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

AR_DIGITS = "٠١٢٣٤٥٦٧٨٩"
DIGIT_RE = re.compile(rf"^[\u06DD۝]*[{AR_DIGITS}][{AR_DIGITS}]?[\u06DD۝]*$")


def is_verse_marker(token: str) -> int | None:
    """Return the Arabic-Indic number if token is a verse-end marker, else None."""
    if DIGIT_RE.match(token.strip()):
        digits = "".join(c for c in token if c in AR_DIGITS)
        return AR_DIGITS.index(digits[0]) * 10 + (AR_DIGITS.index(digits[1]) if len(digits) > 1 else 0)
    return None


def build() -> dict:
    pages_raw = json.loads((DATA / "pages_raw.json").read_text(encoding="utf-8"))
    quran = json.loads((DATA / "quran_full.json").read_text(encoding="utf-8"))

    surah_meta = [
        {"id": ch["id"], "name": ch["name"], "total_verses": ch["total_verses"]}
        for ch in quran
    ]

    pages = {}
    for page_idx, raw_lines in enumerate(pages_raw, start=1):
        line_data = []
        for line_idx, raw in enumerate(raw_lines, start=1):
            tokens = raw.split()
            words = []
            for token in tokens:
                marker = is_verse_marker(token)
                if marker is not None:
                    words.append({"t": token.strip(), "m": marker})
                elif token.strip():
                    words.append({"t": token.strip(), "m": None})
            text = " ".join(w["t"] for w in words)
            if not text.strip():
                continue
            line_data.append({"n": line_idx, "text": text, "words": words})
        pages[str(page_idx)] = line_data

    return {
        "pages": pages,
        "meta": {
            "total_pages": len(pages_raw),
            "lines_per_page": 15,
            "surahs": surah_meta,
            "source": "Tanzil Uthmani (tanzil.net) via risan/quran-json; "
                      "15-line Madani layout via blueheron786/line-by-line-quran",
        },
    }


if __name__ == "__main__":
    out = build()
    (DATA / "pages.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"pages.json written: {len(out['pages'])} pages, "
          f"sample page1 lines: {len(out['pages']['1'])}")
    for ln in out["pages"]["1"][:3]:
        print("  ", ln["n"], [w["t"] for w in ln["words"][:4]])
