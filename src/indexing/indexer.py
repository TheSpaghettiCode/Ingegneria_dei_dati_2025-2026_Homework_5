import os
import json
import sys

# Add key source directories to the system path to ensure modules can be imported
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from extraction.extractor import Extractor
from indexing.index_manager import IndexManager

# Directory containing the downloaded HTML files
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'html_arxiv')

def main():
    """
    Main entry point for the indexing process.
    1. Initializes connection to Elasticsearch.
    2. Ensures necessary indices exist (Articles, Tables, Figures).
    3. Iterates through all HTML files in the data directory.
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
    
    # --- 2. Iterate over HTML files ---
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.html')]
    
    print(f"Found {len(files)} files to process.")
    
    for filename in files:
        filepath = os.path.join(DATA_DIR, filename)
        paper_id = filename.replace('.html', '')
        # Path to the metadata JSON file created by the scraper
        meta_filepath = os.path.join(DATA_DIR, f"{paper_id}_meta.json")
        
        print(f"Processing {paper_id}...")
        
        # --- 3. Load Metadata ---
        metadata = {}
        if os.path.exists(meta_filepath):
            with open(meta_filepath, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        
        # --- 4. Extract Data ---
        try:
            paper_data = extractor.process_file(filepath)
            
            # --- 5. Index Data ---
            indexer.index_data(paper_data, metadata)
            
        except Exception as e:
            print(f"Failed to process {paper_id}: {e}")

if __name__ == "__main__":
    main()
