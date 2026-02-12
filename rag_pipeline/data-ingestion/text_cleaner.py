"""
Enterprise Regulatory Text Cleaner
-----------------------------------
Designed for FinCEN / SAR / Advisory Documents

Removes:
- Duplicate full document blocks
- FINCEN ADVISORY footer artifacts
- Footnote references (e.g., "1. See https://...")
- Inline numeric footnote markers
- Page number artifacts
- Excess whitespace
- Table spacing artifacts

Preserves:
- Section headings
- Logical structure
- Core regulatory text

Output:
- cleaned_output.txt
"""

import re
import sys
from collections import Counter


# ==============================
# 1️⃣ REMOVE LARGE DUPLICATION
# ==============================

def remove_large_duplicate_blocks(text):
    midpoint = len(text) // 2
    first_half = text[:midpoint].strip()
    second_half = text[midpoint:].strip()

    if first_half and first_half in second_half:
        return first_half

    return text


# ==============================
# 2️⃣ REMOVE FOOTER ARTIFACTS
# ==============================

def remove_footer_artifacts(text):

    patterns = [
        r"F\s*I\s*N\s*C\s*E\s*N\s*A\s*D\s*V\s*I\s*S\s*O\s*R\s*Y\s*\d*",
        r"\n\d+\s+F\s*I\s*N\s*C\s*E\s*N.*",
        r"Page\s+\d+\s+of\s+\d+",
        r"Page\s+\d+",
    ]

    for p in patterns:
        text = re.sub(p, "", text, flags=re.IGNORECASE)

    return text


# ==============================
# 3️⃣ REMOVE FOOTNOTE REFERENCES
# ==============================

def remove_footnotes(text):

    # Remove numbered URL references
    text = re.sub(r"\d+\.\s*See\s+https?://\S+", "", text)

    # Remove inline numeric references like "...region.1"
    text = re.sub(r"(?<=\w)\d+", "", text)

    return text


# ==============================
# 4️⃣ REMOVE COMMON NOISE
# ==============================

def remove_common_noise(text):

    patterns = [
        r"CONFIDENTIAL",
        r"DRAFT",
        r"SAMPLE",
        r"©\s.*",
    ]

    for p in patterns:
        text = re.sub(p, "", text, flags=re.IGNORECASE)

    return text


# ==============================
# 5️⃣ FIX WORD BREAK ISSUES
# ==============================

def fix_word_breaks(text):

    # Fix common broken words
    replacements = {
        "door-todoor": "door-to-door",
        "wild fires": "wildfires",
    }

    for wrong, correct in replacements.items():
        text = text.replace(wrong, correct)

    return text


# ==============================
# 6️⃣ REMOVE REPEATED PARAGRAPHS
# ==============================

def remove_repeated_paragraphs(text):

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    counts = Counter(paragraphs)

    cleaned = [p for p in paragraphs if counts[p] < 3]

    return "\n\n".join(cleaned)


# ==============================
# 7️⃣ NORMALIZE TABLE SPACING
# ==============================

def fix_table_spacing(text):

    text = re.sub(r"\s{3,}", " | ", text)
    return text


# ==============================
# 8️⃣ NORMALIZE WHITESPACE
# ==============================

def normalize_whitespace(text):

    text = re.sub(r"\r", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()


# ==============================
# 9️⃣ STRUCTURE SECTION HEADINGS
# ==============================

def structure_headings(text):

    headings = [
        "Potential Frauds",
        "Benefits Fraud",
        "Charities Fraud",
        "Cyber-Related Fraud",
        "Suspicious Activity Reporting",
        "For Further Information",
    ]

    for h in headings:
        text = re.sub(
            rf"\b{re.escape(h)}\b",
            f"\n\n## {h}\n",
            text
        )

    return text


# ==============================
# 🔟 FULL CLEANING PIPELINE
# ==============================

def clean_text(text):

    text = remove_large_duplicate_blocks(text)
    text = remove_footer_artifacts(text)
    text = remove_footnotes(text)
    text = remove_common_noise(text)
    text = fix_word_breaks(text)
    text = remove_repeated_paragraphs(text)
    text = fix_table_spacing(text)
    text = normalize_whitespace(text)
    text = structure_headings(text)

    return text


# ==============================
# EXECUTION
# ==============================

if __name__ == "__main__":

    if len(sys.argv) != 2:
        print("Usage: python clean_fincen_guidance.py input.txt")
        sys.exit(1)

    input_file = r"C:\college\Hackathons\BARCLAYS\Hack-o-Hire\rag-pipeline\docs\typologies\Advisory EIP FINAL 508.txt"

    with open(input_file, "r", encoding="utf-8") as f:
        raw_text = f.read()

    cleaned_text = clean_text(raw_text)

    with open("cleaned_output.txt", "w", encoding="utf-8") as f:
        f.write(cleaned_text)

    print("Cleaning complete.")
    print("Saved as cleaned_output.txt")
