import os
import json
import sys

# Add key source directories to the system path to ensure modules can be imported
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from extraction.extractor import Extractor
from indexing.index_manager import IndexManager

# Directory containing the downloaded HTML files

DATA_DIR_ARXIV = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'html_arxiv')
DATA_DIR_PUBMED = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'html_pubmed')

DATA_DIRS = [DATA_DIR_ARXIV, DATA_DIR_PUBMED]

def main():
    """
    Main entry point for the indexing process.
    1. Initializes connection to Elasticsearch.
    2. Ensures necessary indices exist (Articles, Tables, Figures).
    3. Iterates through all HTML files in the data directories.
    4. Extracts structured data using Extractor.
    5. Indexes the extracted data using IndexManager.
    """
    # --- 1. Initialize Manager (Assumes ES is running) ---
    try:
        indexer = IndexManager()
        indexer.create_indices()
    except Exception as e:
        print(f"Error connecting to Elasticsearch: {e}")
        print("Please ensure Elasticsearch is running.")
        return

    extractor = Extractor()
    
    # --- 2. Iterate over Data Directories ---
    for data_dir in DATA_DIRS:
        if not os.path.exists(data_dir):
            print(f"Directory {data_dir} does not exist. Skipping.")
            continue
            
        print(f"--- Indexing directory: {data_dir} ---")
        files = [f for f in os.listdir(data_dir) if f.endswith('.html') or f.endswith('.xml')]
        
        print(f"Found {len(files)} files to process in {os.path.basename(data_dir)}.")
        
        for filename in files:
            filepath = os.path.join(data_dir, filename)
            paper_id = filename.replace('.html', '').replace('.xml', '')
            # Path to the metadata JSON file created by the scraper
            meta_filepath = os.path.join(data_dir, f"{paper_id}_meta.json")
            
            print(f"Processing {paper_id}...")

            # Check if already indexed
            if indexer.es.exists(index="articles", id=paper_id):
                 print(f"  -> Article {paper_id} already indexed. Skipping.")
                 continue
            
            # --- 4. Extract Data ---
            try:
                data = extractor.process_file(filepath)
            except Exception as e:
                print(f"  -> Extraction Failed for {filename}: {e}")
                continue
                
            # --- 3. Load and Merge Metadata ---
            if os.path.exists(meta_filepath):
                with open(meta_filepath, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                    # Update fields in 'data' with metadata, preferring metadata if available
                    data['title'] = meta.get('title', data.get('title'))
                    data['authors'] = meta.get('authors', [])
                    data['date'] = meta.get('published', '')
                    data['source'] = meta.get('source', data.get('source'))
            
            # Ensure separate identification if missing
            if "source" not in data or not data['source']:
                data["source"] = "arxiv" if "html_arxiv" in data_dir else "pubmed"
                
            # --- 5. Index Data ---
            try:
                indexer.index_data(data)
                print(f"  -> Successfully indexed {paper_id} ({data['source']})")
            except Exception as e:
                print(f"Failed to index {paper_id}: {e}")

if __name__ == "__main__":
    main()
