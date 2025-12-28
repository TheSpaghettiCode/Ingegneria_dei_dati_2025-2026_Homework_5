import arxiv
import requests
import os
import time
import json
import argparse
from bs4 import BeautifulSoup

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'html_arxiv')
os.makedirs(DATA_DIR, exist_ok=True)

def scrape_arxiv(query="speech to text", max_results=50):
    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance
    )

    print(f"Searching for '{query}'...")
    
    count = 0
    for result in client.results(search):
        paper_id = result.get_short_id()
        # Clean title for filename
        safe_title = "".join([c if c.isalnum() else "_" for c in result.title])[:150]
        
        html_url = f"https://arxiv.org/html/{paper_id}"
        
        try:
            print(f"Checking HTML for {paper_id}: {result.title[:50]}...")
            response = requests.get(html_url, timeout=10)
            
            if response.status_code == 200 and "text/html" in response.headers.get("Content-Type", ""):
                if "abs/" in response.url:
                    print(f"  -> HTML not found (redirected to abstract). Skipping.")
                    continue
                
                # Save HTML
                filename = f"{paper_id}.html"
                filepath = os.path.join(DATA_DIR, filename)
                
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(response.text)
                
                # Save Metadata
                meta_filename = f"{paper_id}_meta.json"
                meta_filepath = os.path.join(DATA_DIR, meta_filename)
                
                metadata = {
                    "id": paper_id,
                    "title": result.title,
                    "authors": [a.name for a in result.authors],
                    "published": result.published.isoformat(),
                    "abstract": result.summary,
                    "html_url": html_url,
                    "pdf_url": result.pdf_url
                }
                
                with open(meta_filepath, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=4)
                
                print(f"  -> Downloaded {filename}")
                count += 1
                
                time.sleep(1)
            else:
                print(f"  -> HTML not found or error ({response.status_code}).")
        
        except Exception as e:
            print(f"  -> Error downloading {paper_id}: {e}")

    print(f"\nTotal downloaded for '{query}': {count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", type=str, default="speech to text", help="Search query")
    parser.add_argument("--max", type=int, default=50, help="Max results")
    args = parser.parse_args()
    
    scrape_arxiv(query=args.query, max_results=args.max)
