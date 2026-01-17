import time
import sys
import statistics
from elasticsearch import Elasticsearch

# Configurazione
ES_HOST = "http://localhost:9200"
INDICES = {
    "articles": ["title^3", "abstract^2", "full_text"],
    "tables":   ["caption^3", "body", "mentions"],
    "figures":  ["caption^3", "context_paragraphs", "mentions"]
}

# Colori per il terminale
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def evaluate_index(es, index_name, search_fields, query_string, top_k=5):
    """
    Esegue una valutazione su un singolo indice.
    """
    print(f"\n{Colors.HEADER}{'='*60}")
    print(f"  VALUTAZIONE INDICE: {index_name.upper()}")
    print(f"{'='*60}{Colors.ENDC}")

    # 1. Costruzione Query
    body = {
        "query": {
            # MODIFICA: Usiamo "query_string" invece di "simple_query_string"
            "query_string": {
                "query": query_string,
                "fields": search_fields,
                # Se l'utente scrive parole a caso senza operatori (es. "cancer coffee"), 
                # default_operator="AND" implica che devono esserci ENTRAMBE.
                "default_operator": "AND" 
            }
        },
        "highlight": {
            # ... (il resto rimane uguale)
            "fields": { field.split('^')[0]: {} for field in search_fields },
            "pre_tags": [f"{Colors.RED}"],
            "post_tags": [f"{Colors.ENDC}"]
        },
        "_source": ["title", "caption", "paper_id", "source", "score", "date", "table_id", "figure_id"]
    }

    # 2. Misurazione Performance (Quantitativa)
    start_time = time.time()
    try:
        response = es.search(index=index_name, body=body, size=top_k)
    except Exception as e:
        print(f"{Colors.RED}Errore durante la ricerca: {e}{Colors.ENDC}")
        return

    end_time = time.time()
    latency_ms = (end_time - start_time) * 1000

    # 3. Estrazione Metriche
    hits = response['hits']['hits']
    total_hits = response['hits']['total']['value']
    max_score = response['hits']['max_score'] or 0
    
    scores = [h['_score'] for h in hits]
    avg_score = statistics.mean(scores) if scores else 0

    # --- REPORT QUANTITATIVO ---
    print(f"{Colors.BLUE}[METRICHE QUANTITATIVE]{Colors.ENDC}")
    print(f"Latenza:        {latency_ms:.2f} ms")
    print(f"Totale Trovati: {total_hits}")
    print(f"Max Score:      {max_score:.4f}")
    print(f"Avg Score (top {top_k}): {avg_score:.4f}")
    
    if total_hits == 0:
        print(f"\n{Colors.YELLOW}Nessun risultato trovato per questo indice.{Colors.ENDC}")
        return

    # --- REPORT QUALITATIVO ---
    print(f"\n{Colors.BLUE}[ANALISI QUALITATIVA - TOP {len(hits)}]{Colors.ENDC}")
    
    for i, hit in enumerate(hits):
        score = hit['_score']
        source = hit['_source']
        
        # --- MODIFICA QUI ---
        # Prova a prenderlo dal source (tabelle/figure), 
        # altrimenti prendi l'ID univoco del documento (articoli)
        paper_id = source.get('paper_id') 
        # --------------------
        
        origin = source.get('source', 'Unknown')

        
        # Determina cosa mostrare in base all'indice
        title_or_caption = ""
        if index_name == "articles":
            title_or_caption = source.get('title', 'No Title')
            sub_info = source.get('date', 'No Date')
        elif index_name == "tables":
            title_or_caption = source.get('caption', 'No Caption')[:100] + "..."
            sub_info = source.get('table_id', 'N/A')
        elif index_name == "figures":
            title_or_caption = source.get('caption', 'No Caption')[:100] + "..."
            sub_info = source.get('figure_id', 'N/A')

        print(f"\n{i+1}. {Colors.BOLD}[{score:.2f}] {title_or_caption}{Colors.ENDC}")
        print(f"ID: {paper_id} | {sub_info} | Fonte: {origin}")

        # Mostra snippet evidenziati (Highlighting)
        if 'highlight' in hit:
            print(f"{Colors.YELLOW}Match context:{Colors.ENDC}")
            for field, snippets in hit['highlight'].items():
                for snippet in snippets[:1]: # Mostra solo il primo snippet per pulizia
                    print(f" - {field}: ...{snippet}...")

def main():
    # Connessione
    es = Elasticsearch(ES_HOST)
    if not es.ping():
        print("Impossibile connettersi a Elasticsearch.")
        return

    # Input Query
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        # Default query di test
        query = "cancer coffee"

    print(f"Avvio Test Performance per la query: '{Colors.GREEN}{query}{Colors.ENDC}'")
    
    # Loop su tutti gli indici
    for index, fields in INDICES.items():
        evaluate_index(es, index, fields, query)

if __name__ == "__main__":
    main()