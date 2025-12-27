import requests
from bs4 import BeautifulSoup
import os
import time
import urllib.parse

# --- CONFIGURAZIONE ---
# Inserisci qui la keyword specifica per il filtro (modificabile)
KEYWORD = "deep learning"
OUTPUT_DIR = os.path.join("data", "html_arxiv")
BASE_URL = "https://arxiv.org/search/?"
# ----------------------

def setup_directories():
    """
    Crea la directory di output se non esiste.
    Input: Nessuno (usa variabile globale OUTPUT_DIR)
    Output: Nessuno (crea side-effect su filesystem)
    """
    if not os.path.exists(OUTPUT_DIR):
        # Creo la cartella, inclusi i genitori se necessario
        os.makedirs(OUTPUT_DIR)
        print(f"[INFO] Creata directory: {OUTPUT_DIR}")

def get_arxiv_html(keyword):
    """
    Cerca su ArXiv e scarica gli articoli che hanno una versione HTML disponibile.
    
    Input:
        keyword (str): La parola chiave da cercare su ArXiv.
    
    Output:
        Nessuno diretto, ma salva i file .html su disco.
    
    Logica:
        1. Costruisce l'URL di ricerca.
        2. Itera sui risultati della pagina.
        3. Controlla se l'articolo ha un link "HTML" o "Experimental HTML".
        4. Se presente, scarica il contenuto e lo salva.
        5. Se assente, salta l'articolo.
    """
    
    # Costruzione della query string sicura
    # query: stringa di ricerca
    # searchtype: all (cerca ovunque)
    # source: header (filtro)
    params = {
        "query": keyword,
        "searchtype": "all",
        "source": "header"
    }
    query_string = urllib.parse.urlencode(params)
    search_url = BASE_URL + query_string
    
    print(f"[INFO] Inizio ricerca su ArXiv per: '{keyword}'")
    print(f"[INFO] URL Ricerca: {search_url}")

    try:
        # Effettuo la richiesta HTTP alla pagina di ricerca
        response = requests.get(search_url)
        response.raise_for_status() # Lancia eccezione per codici 4xx/5xx
    except requests.exceptions.RequestException as e:
        print(f"[ERRORE] Impossibile contattare ArXiv: {e}")
        return

    # Parsing dell'HTML della pagina dei risultati
    soup = BeautifulSoup(response.content, "html.parser")
    
    # Trovo tutti i blocchi relativi agli articoli (tag 'li' con classe 'arxiv-result')
    results = soup.find_all("li", class_="arxiv-result")
    
    print(f"[INFO] Trovati {len(results)} risultati nella prima pagina.")

    count = 0
    for result in results:
        # Estraggo il titolo per il nome del file (pulendolo da caratteri non validi)
        title_tag = result.find("p", class_="title")
        if not title_tag:
            continue
        
        # Rimuovo spazi extra e caratteri che danno noia al filesystem
        title_text = title_tag.text.strip().replace("Title:", "").strip()
        safe_title = "".join([c for c in title_text if c.isalnum() or c in (' ', '-', '_')]).strip()
        safe_title = safe_title.replace(" ", "_")[:100] # Limito lunghezza filename

        # --- LOGICA DI FILTRO HTML ---
        # Cerco i link disponibili per questo articolo.
        # ArXiv mostra link come: [PDF] [HTML] [Other]
        # Devo verificare esplicitamente la presenza di 'HTML' o 'Experimental HTML'.
        links_paragraph = result.find("p", class_="list-title is-inline-block")
        if not links_paragraph:
            continue
            
        html_link = None
        # Itero su tutti i tag 'a' dentro il blocco dei link
        for link in links_paragraph.find_all("a"):
            link_text = link.text.strip().lower()
            if "html" in link_text:
                html_link = link.get("href")
                break
        
        # Se non ho trovato il link HTML, salto l'articolo
        if not html_link:
            print(f"[SKIP] Nessun HTML per: {title_text[:50]}...")
            continue
            
        # Gestione URL relativo vs assoluto
        if html_link and not html_link.startswith("http"):
            html_link = "https://arxiv.org" + html_link

        # --- DOWNLOAD ---
        try:
            print(f"[DOWNLOAD] Scaricando HTML: {title_text[:50]}...")
            # Pausa tattica per non essere bloccati (rate limiting manuale)
            time.sleep(2) 
            
            # Richiedo la pagina HTML dell'articolo (spesso è su ar5iv)
            article_response = requests.get(html_link)
            article_response.raise_for_status()
            
            # Salvo il file
            filename = f"{safe_title}.html"
            file_path = os.path.join(OUTPUT_DIR, filename)
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(article_response.text)
                
            count += 1
            print(f"[OK] Salvato: {filename}")
            
        except Exception as e:
            print(f"[ERRORE] Fallito download di {html_link}: {e}")

    print(f"\n[FINE] Totale articoli HTML scaricati: {count}")

if __name__ == "__main__":
    setup_directories()
    get_arxiv_html(KEYWORD)
