import fitz  # PyMuPDF
import os
import re

# --- CONFIG ---
pdf_folder = "../docs/typologies"   # folder containing your PDFs
output_folder = "typologies_txt" # folder to save cleaned text files

# Create output folder if it doesn't exist
os.makedirs(output_folder, exist_ok=True)

# Function to extract text from a PDF
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

# Function to clean/normalize text
def clean_text(text):
    # Remove page numbers (simple heuristic)
    text = re.sub(r'Page \d+', '', text)
    # Fix hyphenated words across line breaks
    text = re.sub(r'-\n', '', text)
    # Replace multiple newlines with a single space
    text = re.sub(r'\n+', ' ', text)
    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# Process all PDFs
for pdf_file in os.listdir(pdf_folder):
    if pdf_file.endswith(".pdf"):
        pdf_path = os.path.join(pdf_folder, pdf_file)
        print(f"Normalizing {pdf_file}...")

        # Extract text
        raw_text = extract_text_from_pdf(pdf_path)
        # Clean text
        normalized_text = clean_text(raw_text)

        # Save as .txt
        txt_file_path = os.path.join(output_folder, pdf_file.replace(".pdf", ".txt"))
        with open(txt_file_path, "w", encoding="utf-8") as f:
            f.write(normalized_text)

print("All PDFs normalized successfully!")