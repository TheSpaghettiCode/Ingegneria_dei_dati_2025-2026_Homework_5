import arxiv
import os
import time
import json
import argparse
import cloudscraper


# Define the directory where HTML files and metadata will be stored
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'html_arxiv')
os.makedirs(DATA_DIR, exist_ok=True)


def scrape_arxiv(query="speech to text", target_downloads=50):
   client = arxiv.Client()
  
   # Crea uno scraper che simula un browser desktop
   scraper = cloudscraper.create_scraper(browser='chrome')


   # --- MODIFICA CHIAVE: ---
   # Non chiediamo solo 'target_downloads' risultati all'API, perché molti potrebbero fallire (niente HTML).
   # Chiediamo un buffer molto più ampio (es. 10 volte tanto).
   # Il ciclo si interromperà manualmente quando avremo raggiunto il target.
   search_buffer = target_downloads * 10
  
   search = arxiv.Search(
       query=query,
       max_results=search_buffer,
       sort_by=arxiv.SortCriterion.Relevance
   )


   print(f"--- Obiettivo: Scaricare {target_downloads} paper per '{query}' ---")
   print(f"(Scaricamento metadati per max {search_buffer} candidati...)")
  
   count = 0


   # Arxiv Client gestisce la paginazione automaticamente con il generatore
   for result in client.results(search):
      
       # --- CONTROLLO TARGET RAGGIUNTO ---
       if count >= target_downloads:
           print(f"\n✅ Raggiunto target di {target_downloads} paper. Stop.")
           break
       # ----------------------------------


       paper_id = result.get_short_id()
       html_url = f"https://ar5iv.labs.arxiv.org/html/{paper_id}"
      
       try:
           # Usa scraper.get invece di requests.get
           # print(f"Checking HTML for {paper_id}...")
           response = scraper.get(html_url, timeout=20)
          
           if response.status_code == 200:
                # Se la pagina contiene "No HTML available", saltiamo
               if "No HTML available" in response.text:
                   # print(f"   [Skip] {paper_id}: HTML not generated yet.")
                   continue


               filename = f"{paper_id}.html"
               filepath = os.path.join(DATA_DIR, filename)
              
               with open(filepath, "w", encoding="utf-8") as f:
                   f.write(response.text)
              
               # --- Metadata saving ---
               meta_filename = f"{paper_id}_meta.json"
               meta_filepath = os.path.join(DATA_DIR, meta_filename)
               metadata = {
                   "id": paper_id,
                   "title": result.title,
                   "authors": [a.name for a in result.authors],
                   "date": result.published.isoformat(),
                   "abstract": result.summary,
                   "html_url": html_url,
                   "pdf_url": result.pdf_url,
                   "source": "arxiv",
                   "query": query
               }
               with open(meta_filepath, "w", encoding="utf-8") as f:
                   json.dump(metadata, f, indent=4)
              
               count += 1
               print(f"   -> ✅ Downloaded {filename} ({count}/{target_downloads})")
              
               time.sleep(2) # Pausa per non essere bannati
          
           elif response.status_code == 404:
               # print(f"   [Skip] {paper_id}: 404 Not Found on Ar5iv.")
               pass
           elif response.status_code == 403:
               print(f"   ⚠️  403 Forbidden. IP might be temporarily banned. Sleeping 10s...")
               time.sleep(10)
           else:
               print(f"   -> Error code: {response.status_code}")


       except Exception as e:
           print(f"   -> Error processing {paper_id}: {e}")


   if count < target_downloads:
       print(f"\n⚠️  Attenzione: Trovati solo {count} paper con HTML disponibile su {search_buffer} analizzati.")


if __name__ == "__main__":
   # Command Line Interface for the scraper
   parser = argparse.ArgumentParser(description="Download ArXiv papers as HTML.")
   parser.add_argument("--query", type=str, default="speech to text", help="Search query")
   parser.add_argument("--max", type=int, default=50, help="Target number of successful downloads")
   args = parser.parse_args()
  
   scrape_arxiv(query=args.query, target_downloads=args.max)