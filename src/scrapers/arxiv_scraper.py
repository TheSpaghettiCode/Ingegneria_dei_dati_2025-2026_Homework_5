import arxiv
import requests
import os
import time
import json
import argparse
from bs4 import BeautifulSoup

# Define the directory where HTML files and metadata will be stored
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'html_arxiv')
os.makedirs(DATA_DIR, exist_ok=True)

def scrape_arxiv(query="speech to text", max_results=50):
    """
    Search ArXiv for papers matching the query, download their HTML content, 
    and save their metadata.
    
    Args:
        query (str): The search query string.
        max_results (int): Maximum number of results to fetch.
    """
    client = arxiv.Client()
    
    # Configure the search (sort by relevance to get best matches first)
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance
    )

    print(f"Searching for '{query}'...")
    
    count = 0
    # Iterate through search results
    for result in client.results(search):
        paper_id = result.get_short_id()
        
        # Construct the URL for the HTML version of the paper (ArXiv vanity URL)
        html_url = f"https://arxiv.org/html/{paper_id}"
        
        try:
            print(f"Checking HTML for {paper_id}: {result.title[:50]}...")
            
            # Request the HTML content
            response = requests.get(html_url, timeout=10)
            
            # Check if request was successful and returned HTML content
            if response.status_code == 200 and "text/html" in response.headers.get("Content-Type", ""):
                # ArXiv often redirects '/html/paper_id' to '/abs/paper_id' if HTML is not available
                if "abs/" in response.url:
                    print(f"  -> HTML not found (redirected to abstract). Skipping.")
                    continue
                
                # --- Save HTML Content ---
                filename = f"{paper_id}.html"
                filepath = os.path.join(DATA_DIR, filename)
                
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(response.text)
                
                # --- Save Metadata (JSON) ---
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
                
                # Respectful delay to avoid IP ban
                time.sleep(1)
            else:
                print(f"  -> HTML not found or error ({response.status_code}).")
        
        except Exception as e:
            print(f"  -> Error downloading {paper_id}: {e}")

    print(f"\nTotal downloaded for '{query}': {count}")

if __name__ == "__main__":
    # Command Line Interface for the scraper
    parser = argparse.ArgumentParser(description="Download ArXiv papers as HTML.")
    parser.add_argument("--query", type=str, default="speech to text", help="Search query")
    parser.add_argument("--max", type=int, default=50, help="Max results")
    args = parser.parse_args()
    
    scrape_arxiv(query=args.query, max_results=args.max)
