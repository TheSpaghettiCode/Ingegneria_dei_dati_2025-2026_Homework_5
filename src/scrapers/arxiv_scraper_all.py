import arxiv
import requests
import os
import time
import json
import argparse
# from bs4 import BeautifulSoup # Non usata nel codice attuale, si può rimuovere se non serve dopo

# Define the directory where HTML files and metadata will be stored
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'html_arxiv')
os.makedirs(DATA_DIR, exist_ok=True)

def scrape_arxiv(query="text to speech", max_results=None):
    """
    Search ArXiv for papers matching the query.
    
    Args:
        query (str): The search query string.
        max_results (int or None): Maximum number of results to fetch. 
                                   Set to None to fetch ALL matching results.
    """
    client = arxiv.Client(
        page_size=100, # Ottimizzazione: richiede 100 metadati per pagina API
        delay_seconds=3.0, # Ritardo tra le richieste API di ArXiv per evitare il rate limit
        num_retries=3
    )
    
    # Configure the search
    # Impostando max_results=None, la libreria scaricherà tutto finché non finiscono i risultati
    search = arxiv.Search(
        query=query,
        max_results=max_results, 
        sort_by=arxiv.SortCriterion.Relevance
    )

    limit_str = "ALL" if max_results is None else str(max_results)
    print(f"Searching for '{query}' (Limit: {limit_str})...")
    
    count_downloaded = 0
    count_processed = 0

    try:
        # Iterate through search results (questo loop può durare molto a lungo se max_results è None)
        for result in client.results(search):
            count_processed += 1
            paper_id = result.get_short_id()
            filename = f"{paper_id}.html"
            filepath = os.path.join(DATA_DIR, filename)
            
            # --- Check if already exists (Resumability) ---
            # Molto importante se scarichi migliaia di paper: evita di riscaricare se crasha
            if os.path.exists(filepath):
                print(f"[{count_processed}] {paper_id} already exists. Skipping download.")
                continue

            # Construct the URL for the HTML version
            html_url = f"https://arxiv.org/html/{paper_id}"
            
            try:
                print(f"[{count_processed}] Checking HTML for {paper_id}: {result.title[:50]}...")
                
                # Request the HTML content
                # User-Agent è spesso richiesto per evitare blocchi su grandi volumi
                headers = {'User-Agent': 'Mozilla/5.0 (Scientific Research Scraper)'}
                response = requests.get(html_url, headers=headers, timeout=15)
                
                # Check status and content type
                if response.status_code == 200 and "text/html" in response.headers.get("Content-Type", ""):
                    
                    # Check redirect to abstract (significa che non c'è l'HTML sperimentale)
                    if "abs/" in response.url:
                        print(f"  -> HTML not found (redirected to abstract). Skipping.")
                        # Non salvare nulla se non c'è l'HTML
                        continue
                    
                    # --- Save HTML Content ---
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(response.text)
                    
                    # --- Save Metadata (JSON) ---
                    meta_filename = f"{paper_id}_meta.json"
                    meta_filepath = os.path.join(DATA_DIR, meta_filename)
                    
                    metadata = {
                        "id": paper_id,
                        "title": result.title,
                        "authors": [a.name for a in result.authors],
                        "date": result.published.isoformat(),
                        "abstract": result.summary,
                        "html_url": html_url,
                        "pdf_url": result.pdf_url
                    }
                    
                    with open(meta_filepath, "w", encoding="utf-8") as f:
                        json.dump(metadata, f, indent=4)
                    
                    print(f"  -> DOWNLOADED: {filename}")
                    count_downloaded += 1
                    
                    # Respectful delay
                    # ArXiv banna aggressivamente se scarichi HTML in massa.
                    # 2 secondi è il minimo sindacale, 3-5 è più sicuro per grandi volumi.
                    time.sleep(2) 
                else:
                    print(f"  -> HTML not found or error ({response.status_code}).")
            
            except Exception as e:
                print(f"  -> Error downloading {paper_id}: {e}")
                time.sleep(5) # Pause longer on error

    # --- NUOVA GESTIONE ERRORI DEL CICLO PRINCIPALE ---
    except arxiv.HTTPError as e:
        print(f"\n[STOP] Limite API ArXiv raggiunto o errore server (spesso accade a 10.000 risultati): {e}")
    except KeyboardInterrupt:
        print("\nScraper interrotto dall'utente.")
    except Exception as e:
        print(f"\n[ERRORE CRITICO] Errore imprevisto nel loop principale: {e}")
    
    print(f"\n--- Riepilogo ---")
    print(f"Processati (scansionati): {count_processed}")
    print(f"Scaricati con successo: {count_downloaded}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download ArXiv papers as HTML.")
    parser.add_argument("--query", type=str, default="text to speech", help="Search query")
    # Imposta il default a None (o un numero molto alto) se non specificato
    parser.add_argument("--max", type=int, default=None, help="Max results (leave empty for ALL)")
    args = parser.parse_args()
    
    scrape_arxiv(query=args.query, max_results=args.max)