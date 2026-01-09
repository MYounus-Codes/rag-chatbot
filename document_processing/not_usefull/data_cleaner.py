import json
import os
import re
from typing import Any

INPUT_FILES = [
    "products/3,4 mm Orange Standard Cable/catalogues/Catalogue_Danish.json",
    "products/3,4 mm Orange Standard Cable/catalogues/Catalogue_English.json",
    "products/3,4 mm Orange Standard Cable/catalogues/Catalogue_French.json",
    "products/3,4 mm Orange Standard Cable/catalogues/Catalogue_German.json",
    "products/3,4 mm Orange Standard Cable/catalogues/Catalogue_Italian.json",
    "products/3,4 mm Orange Standard Cable/catalogues/Catalogue_Spanish.json",
]

OUTPUT_DIR = "cleaned"

# ----------------------------
# Regex patterns for cleaning
# ----------------------------

IMAGE_PATTERN = re.compile(r"!\[.*?\]\(.*?\)", re.IGNORECASE)

HEADER_FOOTER_PATTERN = re.compile(
    r"""
    ^\s*ROBOTS\s*\d*|
    ^\s*MOBOTS\s*\d*|
    ^\s*ROBOTS\s+ROBOTS\s*|
    ^\s*\d+\s*$               # standalone page numbers
    """,
    re.IGNORECASE | re.MULTILINE | re.VERBOSE,
)

URL_EMAIL_PATTERN = re.compile(
    r"(https?://\S+|www\.\S+|\S+@\S+)", re.IGNORECASE
)

MULTI_WHITESPACE_PATTERN = re.compile(r"\n{3,}")
EXTRA_SPACES_PATTERN = re.compile(r"[ \t]{2,}")


# ----------------------------
# Core cleaning function
# ----------------------------

def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return text

    # Remove images
    text = IMAGE_PATTERN.sub("", text)

    # Remove headers / footers / page numbers
    text = HEADER_FOOTER_PATTERN.sub("", text)

    # Remove URLs and emails
    text = URL_EMAIL_PATTERN.sub("", text)

    # Normalize whitespace
    text = EXTRA_SPACES_PATTERN.sub(" ", text)
    text = MULTI_WHITESPACE_PATTERN.sub("\n\n", text)

    return text.strip()


# ----------------------------
# Recursive JSON cleaner
# ----------------------------

def clean_json(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: clean_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_json(item) for item in obj]
    elif isinstance(obj, str):
        return clean_text(obj)
    else:
        return obj


# ----------------------------
# Main processing loop
# ----------------------------

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for file_path in INPUT_FILES:
        if not os.path.exists(file_path):
            print(f"[SKIP] File not found: {file_path}")
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        cleaned_data = clean_json(data)

        output_path = os.path.join(
            OUTPUT_DIR,
            os.path.basename(file_path).replace(".json", ".json"),
        )

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

        print(f"[OK] Cleaned file written to: {output_path}")


if __name__ == "__main__":
    main()
