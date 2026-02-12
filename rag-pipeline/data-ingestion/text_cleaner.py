"""
Text Cleaning Script for Regulatory / SAR Documents
---------------------------------------------------
Input  : Raw extracted text (.txt)
Output : Cleaned structured text (.txt)

Removes:
- Page numbers
- Watermarks
- Common headers/footers
- Repeated disclaimers
- Table spacing artifacts

Preserves:
- Section headings
- Numbered clauses
- Logical structure
"""

import re
import sys
from collections import Counter


# ============================
# CONFIGURATION
# ============================

REPEAT_THRESHOLD = 3

COMMON_NOISE_PATTERNS = [
    r"Page \d+ of \d+",
    r"Page \d+",
    r"CONFIDENTIAL",
    r"For Internal Use Only",
    r"DRAFT",
    r"SAMPLE",
    r"© .*",
]


# ============================
# CLEANING FUNCTIONS
# ============================

def remove_noise_patterns(text):
    for pattern in COMMON_NOISE_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    return text


def remove_repeated_paragraphs(text):
    paragraphs = [p.strip() for p in text.split("\n\n")]
    counts = Counter(paragraphs)

    cleaned = [
        p for p in paragraphs
        if p and counts[p] < REPEAT_THRESHOLD
    ]

    return "\n\n".join(cleaned)


def fix_table_artifacts(text):
    # Replace large spacing with separator
    text = re.sub(r"\s{3,}", " | ", text)
    return text


def normalize_whitespace(text):
    text = re.sub(r"\r", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def preserve_headings(text):
    """
    Preserve numbered clauses like:
    1. Introduction
    1.1 Scope
    2 Filing Requirements
    """

    lines = text.split("\n")
    structured = []

    for line in lines:
        line_strip = line.strip()

        # Detect numbered heading pattern
        if re.match(r"^\d+(\.\d+)*\s+[A-Z]", line_strip):
            structured.append(f"\n## {line_strip}\n")
        else:
            structured.append(line)

    return "\n".join(structured)


# ============================
# MAIN PIPELINE
# ============================

def clean_text(text):

    text = remove_noise_patterns(text)
    text = remove_repeated_paragraphs(text)
    text = fix_table_artifacts(text)
    text = normalize_whitespace(text)
    text = preserve_headings(text)

    return text


# ============================
# EXECUTION
# ============================

if __name__ == "__main__":

    if len(sys.argv) != 2:
        print("Usage: python clean_text_only.py input.txt")
        sys.exit(1)

    input_file = sys.argv[1]

    with open(input_file, "r", encoding="utf-8") as f:
        raw_text = f.read()

    cleaned_text = clean_text(raw_text)

    with open("cleaned_output.txt", "w", encoding="utf-8") as f:
        f.write(cleaned_text)

    print("Cleaning complete.")
    print("Saved as: cleaned_output.txt")
