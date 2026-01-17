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

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def get_performance_and_ids(es, index_name, search_fields, query_string):
    """
    Fase Quantitativa:
    - Conta i risultati totali
    - Estrae gli ID unici
    - Misura il tempo di risposta (Latenza)
    """
    body = {
        "query": {
            "query_string": {
                "query": query_string,
                "fields": search_fields,
                "default_operator": "AND"
            }
        },
        "size": 0,  # Non ci serve scaricare i documenti qui, vogliamo solo i numeri
        "track_total_hits": True,
        "aggs": {
            "unique_papers": {
                "cardinality": {
                    "field": "paper_id.keyword" # Assicurati che paper_id sia keyword, altrimenti usa paper_id
                }
            }
        }
    }
    
    start_time = time.time()
    try:
        resp = es.search(index=index_name, body=body)
        end_time = time.time()
        
        # Latenza Totale (Python) vs Latenza Motore (ES)
        latency_total = (end_time - start_time) * 1000
        latency_es = resp['took'] 
        
        total_hits = resp['hits']['total']['value']
        unique_count = resp['aggregations']['unique_papers']['value']
        
        # Nota: Con size=0 non recuperiamo gli ID come lista, ma solo il conteggio. 
        # Se ti servono tassativamente gli ID nel set globale, devi usare il metodo precedente
        # o una "Composite Aggregation", ma per le statistiche questo è 100x più veloce.
        
        return unique_count, total_hits, latency_total, latency_es
        
    except Exception as e:
        print(f"{Colors.RED}Errore indice {index_name}: {e}{Colors.ENDC}")
        return 0, 0, 0.0, 0.0

def evaluate_quality_metrics(es, index_name, search_fields, query_string, top_k=5):
    """
    Fase Qualitativa:
    - Calcola statistiche di Rilevanza (Max Score, Avg Score)
    - Mostra snippet di testo
    """
    print(f"\n{Colors.HEADER}{'='*60}")
    print(f"  ANALISI QUALITATIVA: {index_name.upper()}")
    print(f"{'='*60}{Colors.ENDC}")

    body = {
        "query": {
            "query_string": {
                "query": query_string,
                "fields": search_fields,
                "default_operator": "AND"
            }
        },
        "highlight": {
            "fields": { field.split('^')[0]: {} for field in search_fields },
            "pre_tags": [f"{Colors.RED}"],
            "post_tags": [f"{Colors.ENDC}"]
        },
        "_source": ["title", "caption", "paper_id", "score"],
        "size": top_k
    }

    try:
        response = es.search(index=index_name, body=body)
    except Exception as e:
        return 0, 0

    hits = response['hits']['hits']
    max_score = response['hits']['max_score'] or 0
    scores = [h['_score'] for h in hits]
    max_score = scores[0] if scores else 0
    avg_score = statistics.mean(scores) if scores else 0

    # CALCOLO DEL DROP (Confidenza)
    score_drop = 0
    if len(scores) > 1:
        first = scores[0]
        second = scores[1]
        # Percentuale di differenza tra il 1° e il 2° risultato
        score_drop = ((first - second) / first) * 100

    print(f"Max Score: {max_score:.2f} | Drop al 2° risultato: {Colors.BOLD}{score_drop:.1f}%{Colors.ENDC}")

    # Stampa esempi
    print(f"{Colors.BLUE}[TOP {len(hits)} RISULTATI]{Colors.ENDC}")

    for i, hit in enumerate(hits):
        score = hit['_score']
        source = hit['_source']
        paper_id = source.get('paper_id', 'N/A')
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

        print(f"\n{i+1}. {Colors.BOLD}[Score: {score:.2f}] {title_or_caption}{Colors.ENDC}")
        print(f"ID: {paper_id} | Fonte: {origin}")

        # Mostra snippet evidenziati (Highlighting)
        if 'highlight' in hit:
            print(f"{Colors.YELLOW}Match context:{Colors.ENDC}")
            for field, snippets in hit['highlight'].items():
                for snippet in snippets[:1]: # Mostra solo il primo snippet per pulizia
                    print(f" - {field}: ...{snippet}...")

    '''
    for i, hit in enumerate(hits):
        score = hit['_score']
        source = hit['_source']
        content = source.get('title') or source.get('caption') or "No Title"
        content = content[:80] + "..." if len(content) > 80 else content
        
        print(f"{i+1}. {Colors.BOLD}[Score: {score:.2f}] {content}{Colors.ENDC}")
        if 'highlight' in hit:
            print(f"   Match: ...{list(hit['highlight'].values())[0][0]}...")
    '''
            
    return max_score, avg_score

def main():
    es = Elasticsearch(ES_HOST, request_timeout=30)
    if not es.ping():
        print("Impossibile connettersi a Elasticsearch.")
        return

    # Query Input
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "cancer AND coffee"

    print(f" \n \n Avvio Benchmark Completo per: '{Colors.GREEN}{query}{Colors.ENDC}'")
    
    global_unique_papers = set()
    stats_table = {}

    # --- FASE 1: QUANTITATIVA & PRESTAZIONI ---
    print(f"\n{Colors.CYAN}--- FASE 1: Raccolta Metriche (Scanning) ---{Colors.ENDC}")
    for index, fields in INDICES.items():
        # CORREZIONE QUI: Riceviamo 4 valori invece di 3
        unique_count, total_hits, lat_total, lat_es = get_performance_and_ids(es, index, fields, query)
        
        stats_table[index] = {
            "total_hits": total_hits,
            "unique_ids": unique_count, # Usiamo direttamente il conteggio
            "latency": lat_total,       # Tempo totale Python
            "latency_es": lat_es,       # Tempo interno Elasticsearch (nuovo!)
            "max_score": 0, 
            "avg_score": 0 
        }
        
        # NOTA IMPORTANTE: Con l'ottimizzazione "cardinality", NON abbiamo più gli ID singoli.
        # Quindi non possiamo aggiornare global_unique_papers con precisione.
        # Se ti serve tassativamente il totale globale unificato, devi tornare al metodo lento.
        # Per ora commentiamo questa riga per evitare errori:
        # global_unique_papers.update(ids) 
        
        print(f"   {index.ljust(10)}: {unique_count} ID stimati | Tot: {lat_total:.2f}ms (ES: {lat_es}ms)")
    # --- FASE 2: QUALITATIVA & RILEVANZA ---
    print(f"\n{Colors.CYAN}--- FASE 2: Analisi Rilevanza (Quality Check) ---{Colors.ENDC}")
    for index, fields in INDICES.items():
        if stats_table[index]["total_hits"] > 0:
            mx, avg = evaluate_quality_metrics(es, index, fields, query, top_k=5)
            stats_table[index]["max_score"] = mx
            stats_table[index]["avg_score"] = avg
        else:
            print(f"\n⚠️  Indice {index} vuoto per questa query.")

    # --- REPORT FINALE ---
    print(f"\n\n{Colors.CYAN}{'-'*80}")
    print(f"  REPORT PRESTAZIONI SISTEMA")
    print(f"{'-'*80}{Colors.ENDC}")
    
    print(f"Query: {Colors.BOLD}{query}{Colors.ENDC}")
    print(f"Paper Unici Totali: {Colors.GREEN}{len(global_unique_papers)}{Colors.ENDC}")
    print("-" * 80)
    
    # Intestazione Tabella
    row_fmt = "{:<10} | {:<10} | {:<12} | {:<12} | {:<10} | {:<10}"
    print(row_fmt.format("INDICE", "LATENZA", "HITS TOT", "PAPER UNICI", "MAX SCORE", "AVG SCORE"))
    print("-" * 80)
    
    for idx, stat in stats_table.items():
        # Coloriamo la latenza: Verde se <100ms, Rosso se >500ms
        lat_val = stat['latency']
        lat_str = f"{lat_val:.1f}  ms"
        if lat_val < 100: lat_str = f"{Colors.GREEN}{lat_str}{Colors.ENDC}"
        elif lat_val > 500: lat_str = f"{Colors.RED}{lat_str}{Colors.ENDC}"
        
        print(row_fmt.format(
            idx, 
            lat_str,
            str(stat['total_hits']), 
            str(stat['unique_ids']), 
            f"{stat['max_score']:.2f}",
            f"{stat['avg_score']:.2f}"
        ))
    print("-" * 80)

if __name__ == "__main__":
    main()