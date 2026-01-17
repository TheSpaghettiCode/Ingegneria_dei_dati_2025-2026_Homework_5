from flask import Flask, render_template, request, jsonify, Response, stream_with_context
import sys
import os
import requests
from elasticsearch import Elasticsearch
import re
from bs4 import BeautifulSoup



# Ensure internal modules can be imported
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
# Fallback import in case of folder structure issues
try:
    from search.search_engine import SearchEngine
except ImportError:
    from engine import SearchEngine

app = Flask(__name__, template_folder='../ui/templates', static_folder='../ui/static')

# Initialize Search Engine and Elasticsearch client
engine = SearchEngine()
es = Elasticsearch("http://localhost:9200")

@app.route('/')
def index():
    """
    Render availability of the main search dashboard.
    """
    return render_template('index.html')

@app.route('/api/stats')
def stats():
    """
    API Endpoint to get current statistics of the corpus.
    Returns the count of indexed Papers, Tables, and Figures.
    """
    try:
        count_arts = es.count(index="articles")['count']
        count_tabs = es.count(index="tables")['count']
        count_figs = es.count(index="figures")['count']
        return jsonify({
            "papers": count_arts,
            "tables": count_tabs,
            "figures": count_figs
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/search')
def search():
    """
    API Endpoint to perform search operations.
    Accepts 'query' and 'index_type' as query parameters.
    """
    query = request.args.get('query', '')
    index_type = request.args.get('index_type', 'articles')
    source_type = request.args.get('source_type', 'all')
    
    # --- LEGGI PAGINA ---
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1
    # --------------------

    if not query:
        return jsonify({"results": [], "total": 0})
    
    target_index = index_type.lower()
    
    # --- PASSA PAGINA ALL'ENGINE ---
    # Otteniamo un dizionario {'results': [...], 'total': N}
    search_data = engine.search(
        index=target_index, 
        query=query, 
        filters={"source": source_type} if source_type != "all" else None,
        page=page,  
        size=10     
    )
    
    # Estraiamo la lista dei risultati per lavorarci su (es. fix immagini)
    hits = search_data['results']

    # Post-process for Image URLs
    if target_index == 'figures':
        # Iteriamo su 'hits' che è un riferimento alla lista dentro search_data
        for hit in hits:
            src = hit['_source']
            raw_url = src.get('url', '')
            paper_id = src.get('paper_id')
            
            # FIX: Extractor blindly appended .jpg even if present
            if raw_url.endswith('.jpg.jpg'):
                src['url'] = raw_url[:-4]
            elif raw_url.endswith('.png.jpg'): 
                src['url'] = raw_url[:-4]
                
            # ArXiv Handling
            if raw_url and not raw_url.startswith('http') and paper_id and not paper_id.startswith("PMC"):
                 src['url'] = f"https://arxiv.org/html/{paper_id}/{raw_url}"
                
    return jsonify(search_data)

@app.route('/paper/<path:paper_id>')
def paper_detail(paper_id):
    """
    Render a detail page for a specific paper.
    Fetches Paper Metadata, Tables, and Figures associated with the given paper_id.
    """
    # Fetch paper details
    res = es.search(index="articles", body={"query": {"term": {"_id": paper_id}}}, size=1)
    if not res['hits']['hits']:
        return "Paper not found", 404
    
    paper = res['hits']['hits'][0]['_source']
    paper['id'] = paper_id

    # ------ AGGIUNTIVO: FIX URL PAPER --------
    raw_url = paper.get('url', '')
    
    # Se non c'è http, assumiamo sia un link relativo o manchi
    if not raw_url.startswith('http'):
        # Se è un paper ArXiv (spesso l'ID non inizia con PMC), costruiamo il link
        if paper_id and not paper_id.startswith("PMC"):
            paper['url'] = f"https://arxiv.org/abs/{paper_id}"
        # Se è PMC, costruiamo il link per PubMed Central
        elif paper_id and paper_id.startswith("PMC"):
            paper['url'] = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{paper_id}/"
    # --------------------------------------
    
    # Fetch associated tables
    tables_res = es.search(index="tables", body={
        "size": 100,  # <--- Spostato qui dentro
        "query": {
            "term": {"paper_id": paper_id}
        }
    })
    tables = [t['_source'] for t in tables_res['hits']['hits']]
    
    # Fetch associated figures
    figs_res = es.search(index="figures", body={"query": {"term": {"paper_id": paper_id}}}, size=100)
    figures = [f['_source'] for f in figs_res['hits']['hits']]
    
    # Fix figure URLs for proxy use
    for f in figures:
        raw_url = f.get('url', '')
        if raw_url and not raw_url.startswith('http'):
            f['url'] = f"https://arxiv.org/html/{paper_id}/{raw_url}"

    return render_template('paper_detail.html', paper=paper, tables=tables, figures=figures)

# In src/api/app.py

@app.route('/api/image_proxy')
def image_proxy():
    image_url = request.args.get('url')
    if not image_url:
        return "URL mancante", 400

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://www.ncbi.nlm.nih.gov/" 
    }

    # SE È ARXIV: Dobbiamo fingere di essere sulla pagina del paper
    if "arxiv.org" in image_url:
        # Estraiamo l'ID per creare un Referer credibile
        # L'URL è tipo https://arxiv.org/html/2209.15032/...
        match = re.search(r'arxiv.org/html/([^/]+)', image_url)
        if match:
            paper_id = match.group(1)
            headers["Referer"] = f"https://arxiv.org/html/{paper_id}"
        else:
             headers["Referer"] = "https://arxiv.org/"
             
    # SE È PUBMED (Il codice che avevamo già)
    elif "ncbi.nlm.nih.gov" in image_url:
        headers["Referer"] = "https://www.ncbi.nlm.nih.gov/"

    print(f"PROXY REQ: {image_url}")


    try:
        # TENTATIVO 1: URL Diretto (quello che abbiamo costruito noi)
        req = requests.get(image_url, stream=True, headers=headers, timeout=15, allow_redirects=True)
        
        # Se funziona (200), restituiamo l'immagine
        if req.status_code == 200:
            return Response(stream_with_context(req.iter_content(chunk_size=1024)), 
                            content_type=req.headers.get('content-type', 'image/jpeg'))
        
        # TENTATIVO 2: Se riceviamo 404 su PubMed, proviamo a cercare il BLOB reale
        if req.status_code == 404 and "ncbi.nlm.nih.gov" in image_url:
            print("  -> 404 ricevuto. Avvio ricerca 'Blob' intelligente...")
            
            # 1. Estraiamo PMC ID e nome file dall'URL fallito
            # L'URL è tipo: .../articles/PMC8539526/bin/nutrients-13-03303-g001.jpg
            pmc_match = re.search(r'(PMC\d+)', image_url)
            filename_match = re.search(r'\/bin\/([^/]+)$', image_url)
            
            if pmc_match and filename_match:
                pmc_id = pmc_match.group(1)
                full_filename = filename_match.group(1) # es: nutrients-13-03303-g001.jpg
                filename_base = full_filename.split('.')[0] # togliamo .jpg per sicurezza

                # 2. Scarichiamo la pagina HTML dell'articolo (non l'immagine, la pagina web!)
                article_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/"
                print(f"  -> Scansiono pagina articolo: {article_url}")
                
                page_req = requests.get(article_url, headers=headers, timeout=10)
                if page_req.status_code == 200:
                    soup = BeautifulSoup(page_req.content, "html.parser")
                    
                    # 3. Cerchiamo il vero link CDN (Blob)
                    # Cerchiamo un tag <img> che contenga il nostro nome file nel src
                    real_img = soup.find('img', src=re.compile(rf"{filename_base}"))
                    
                    if real_img:
                        real_blob_url = real_img.get('src')
                        # Se il link è relativo (inizia con /), aggiungiamo il dominio
                        if real_blob_url.startswith('/'):
                            real_blob_url = "https://www.ncbi.nlm.nih.gov" + real_blob_url
                            
                        print(f"  -> TROVATO URL BLOB REALE: {real_blob_url}")
                        
                        # 4. Scarichiamo l'immagine dal nuovo URL Blob
                        blob_req = requests.get(real_blob_url, stream=True, headers=headers, timeout=10)
                        if blob_req.status_code == 200:
                            return Response(stream_with_context(blob_req.iter_content(chunk_size=1024)), 
                                            content_type=blob_req.headers.get('content-type', 'image/jpeg'))
            
            print("  -> Fallback fallito. Impossibile trovare immagine alternativa.")
        
        # NUOVO: TENTATIVO 2 per ArXiv (Fallback versione)
        # FALLBACK PER ARXIV (Gestione errori 404)
        if req.status_code == 404 and "arxiv.org" in image_url:
            print(f"  -> ArXiv 404 su: {image_url}")
            
            # Lista di tentativi per riparare l'URL
            alternatives = []
            
            # TENTATIVO A: Manca la versione 'v1'? (es. .../2408.13040/x1.png)
            if "v1" not in image_url and "/html/" in image_url:
                # Cerca un pattern tipo /1234.5678/ e aggiungi v1
                match = re.search(r'/html/(\d+\.\d+)/', image_url)
                if match:
                    paper_id_raw = match.group(1)
                    alternatives.append(image_url.replace(paper_id_raw, f"{paper_id_raw}v1"))

            # TENTATIVO B: C'è '/assets/' di troppo? (es. .../assets/x1.png -> .../x1.png)
            if "/assets/" in image_url:
                alternatives.append(image_url.replace("/assets/", "/"))

            # Eseguiamo i tentativi
            for alt_url in alternatives:
                print(f"  -> Provo variante: {alt_url}")
                try:
                    req_alt = requests.get(alt_url, stream=True, headers=headers, timeout=10)
                    if req_alt.status_code == 200:
                        print("  -> VARIANT FOUND!")
                        return Response(stream_with_context(req_alt.iter_content(chunk_size=1024)), 
                                content_type=req_alt.headers.get('content-type', 'image/jpeg'))
                except:
                    pass

        # Se siamo qui, tutti i tentativi sono falliti
        return f"Errore remoto: {req.status_code}", 404

    except Exception as e:
        print(f"PROXY ERROR: {e}")
        return f"Errore proxy: {e}", 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)