# chunking_recursive.py
import os
import json
from langchain_text_splitters import RecursiveCharacterTextSplitter

# --- CONFIG ---
normalized_folder = "../docs/historical_sars"   # folder with normalized .txt files
output_folder = "../docs/historical_sars_chunks"  # folder to save JSON chunks
chunk_size = 1000        # max characters per chunk
chunk_overlap = 100      # overlap between chunks

# Create output folder if it doesn't exist
os.makedirs(output_folder, exist_ok=True)

# Initialize recursive text splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=chunk_size,
    chunk_overlap=chunk_overlap
)

# Process each normalized text file
for txt_file in os.listdir(normalized_folder):
    if txt_file.endswith(".txt"):
        txt_path = os.path.join(normalized_folder, txt_file)
        print(f"Chunking (recursive) {txt_file}...")

        # Read file
        with open(txt_path, "r", encoding="utf-8") as f:
            text = f.read()

        # Split into chunks
        chunks = text_splitter.split_text(text)

        # Prepare metadata
        chunked_data = []
        for i, chunk in enumerate(chunks):
            chunked_data.append({
                "content": chunk,
                "metadata": {
                    "source_file": txt_file,
                    "chunk_index": i
                }
            })

        # Save as JSON
        output_path = os.path.join(output_folder, txt_file.replace(".txt", ".json"))
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(chunked_data, f, ensure_ascii=False, indent=2)

print("All files chunked recursively successfully!")