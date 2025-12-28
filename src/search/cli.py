import argparse
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from search.search_engine import SearchEngine

def main():
    parser = argparse.ArgumentParser(description="Scientific Article Search Engine CLI")
    parser.add_argument("query", help="Search query (e.g., 'speech to text' or 'caption:result')")
    parser.add_argument("--index", help="Index to search: articles, tables, figures (default: all)", default="_all")
    parser.add_argument("--fields", help="Fields to search (comma separated)", default=None)
    
    args = parser.parse_args()
    
    engine = SearchEngine()
    fields = args.fields.split(",") if args.fields else None
    
    print(f"Searching for '{args.query}' in '{args.index}'...")
    results = engine.search(index=args.index, query=args.query, fields=fields)
    
    print(f"Found {len(results)} results.\n")
    
    for hit in results:
        source = hit['_source']
        score = hit['_score']
        index = hit['_index']
        
        print(f"[{index.upper()}] (Score: {score})")
        
        if index == "articles":
            print(f"Title: {source.get('title')}")
            print(f"Authors: {source.get('authors')}")
            print(f"Date: {source.get('date')}")
        elif index == "tables":
            print(f"Table ID: {source.get('table_id')} (Paper: {source.get('paper_id')})")
            print(f"Caption: {source.get('caption')}")
        elif index == "figures":
            print(f"Figure ID: {source.get('figure_id')} (Paper: {source.get('paper_id')})")
            print(f"Caption: {source.get('caption')}")
            print(f"URL: {source.get('url')}")
            
        # Show highlights if any
        if 'highlight' in hit:
            print("Highlights:")
            for field, fragments in hit['highlight'].items():
                for frag in fragments:
                    print(f"  - {field}: {frag}")
        
        print("-" * 40)

if __name__ == "__main__":
    main()
