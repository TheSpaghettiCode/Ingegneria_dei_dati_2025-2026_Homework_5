import requests
from bs4 import BeautifulSoup
import os
import time

# --- CONFIGURAZIONE ---
# Query di ricerca configurabile come richiesto
QUERY = "cancer risk AND coffee consumption"
TARGET_COUNT = 500  # Obiettivo di download
OUTPUT_DIR = os.path.join("data", "html_pubmed")
BASE_URL = "https://pmc.ncbi.nlm.nih.gov"
SEARCH_URL = "https://pmc.ncbi.nlm.nih.gov/search/"
# ----------------------

def setup_directories():
    """
    Crea la directory di output se non esiste.
    Input: Nessuno
    Output: Nessuno
    """
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"[INFO] Creata directory: {OUTPUT_DIR}")

def get_pubmed_html(query, target_count):
    """
    Scarica articoli Open Access da PubMed Central (PMC).
    
    Input:
        query (str): La stringa di ricerca.
        target_count (int): Numero di articoli da scaricare.
    
    Output:
        Nessuno diretto, salva i file .html.
        
    Logica:
        1. Esegue la ricerca con filtro Open Access.
        2. Gestisce la PAGINAZIONE navigando tra le pagine dei risultati.
        3. Estrae i link agli articoli full-text.
        4. Scarica fino al raggiungimento del target.
    """
    
    # Header User-Agent per identificarsi ed evitare blocchi immediati
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    # Parametri della query iniziale
    # filter=collections.open_access : Filtro fondamentale richiesto
    params = {
        "term": query,
        "filter": "collections.open_access",
        "page": 1
    }

    downloaded_count = 0
    current_page = 1
    
    print(f"[INFO] Inizio ricerca PMC per: '{query}'")
    print(f"[INFO] Target: {target_count} articoli.")

    # --- LOOP PAGINAZIONE ---
    # Continua finché non raggiungiamo il numero target di articoli
    while downloaded_count < target_count:
        print(f"\n[INFO] Elaborazione pagina {current_page}...")
        params["page"] = current_page
        
        try:
            # Richiesta alla pagina di ricerca
            response = requests.get(SEARCH_URL, params=params, headers=headers)
            response.raise_for_status()
        except Exception as e:
            print(f"[ERRORE] Impossibile caricare pagina ricerca {current_page}: {e}")
            break

        soup = BeautifulSoup(response.content, "html.parser")
        
        # PMC usa div con class 'rprt' per ogni risultato
        results = soup.find_all("div", class_="rprt")
        
        if not results:
            print("[INFO] Nessun altro risultato trovato. Stop.")
            break
            
        print(f"[INFO] Trovati {len(results)} articoli nella pagina corrente.")

        # Itero sui risultati della singola pagina
        for res in results:
            if downloaded_count >= target_count:
                break
            
            # Estraggo il titolo
            title_tag = res.find("div", class_="title")
            if not title_tag:
                continue
            
            # Il link all'articolo è dentro un tag 'a' nel titolo o vicino
            link_tag = title_tag.find("a")
            if not link_tag:
                continue
                
            article_url_rel = link_tag.get("href")
            full_article_url = BASE_URL + article_url_rel
            
            # Pulizia titolo per filename
            title_text = link_tag.text.strip()
            safe_title = "".join([c for c in title_text if c.isalnum() or c in (' ', '-', '_')]).strip()
            safe_title = safe_title.replace(" ", "_")[:100]
            
            filename = f"{safe_title}.html"
            file_path = os.path.join(OUTPUT_DIR, filename)
            
            # Evito di scaricare se esiste già
            if os.path.exists(file_path):
                print(f"[SKIP] File esistente: {filename}")
                continue

            # --- DOWNLOAD ARTICOLO ---
            try:
                # Rispetto delle buone maniere: pausa tra le richieste
                time.sleep(0.5) 
                
                art_resp = requests.get(full_article_url, headers=headers)
                art_resp.raise_for_status()
                
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(art_resp.text)
                
                downloaded_count += 1
                if downloaded_count % 10 == 0:
                     print(f"[PROGRESSO] Scaricati {downloaded_count}/{target_count} articoli.")
                
            except Exception as e:
                print(f"[ERRORE] Fallito download {full_article_url}: {e}")

        # Passo alla pagina successiva
        current_page += 1
        # Pausa più lunga tra le pagine di ricerca
        time.sleep(1)

    print(f"\n[FINE] Operazione completata. Scaricati {downloaded_count} articoli in {OUTPUT_DIR}")

if __name__ == "__main__":
    setup_directories()
    get_pubmed_html(QUERY, TARGET_COUNT)
