import os
import json
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from extraction.extractor import Extractor
from indexing.index_manager import IndexManager

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'html_arxiv')

def main():
    # Initialize Manager (Assumes ES is running)
    try:
        indexer = IndexManager()
        indexer.create_indices()
    except Exception as e:
        print(f"Error connecting to Elasticsearch: {e}")
        print("Please ensure Elasticsearch is running.")
        return

    extractor = Extractor()
    
    # Iterate over HTML files
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.html')]
    
    for filename in files:
        filepath = os.path.join(DATA_DIR, filename)
        paper_id = filename.replace('.html', '')
        meta_filepath = os.path.join(DATA_DIR, f"{paper_id}_meta.json")
        
        print(f"Processing {paper_id}...")
        
        # Load Metadata
        metadata = {}
        if os.path.exists(meta_filepath):
            with open(meta_filepath, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        
        # Extract Data
        try:
            paper_data = extractor.process_file(filepath)
            
            # Index Data
            indexer.index_data(paper_data, metadata)
            
        except Exception as e:
            print(f"Failed to process {paper_id}: {e}")

if __name__ == "__main__":
    main()
