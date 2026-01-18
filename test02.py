import time
import sys
import pandas as pd # Se non hai pandas, usa il print csv standard alla fine
from elasticsearch import Elasticsearch

# --- CONFIGURAZIONE (ALLINEATA AD APP.PY) ---
ES_HOST = "http://localhost:9200"

# Mappatura esatta dei campi e dei pesi usati nell'applicazione
INDEX_CONFIG = {
    "articles": ["title^3", "abstract^2", "full_text"],
    "tables":   ["caption^3", "body", "paper_title^1", "context_paragraphs","mentions"],
    "figures":  ["caption^3", "mentions", "paper_title^1", "context_paragraphs"]
}


# Query miste per testare ArXiv (Speech) e PubMed (Food/Health)
TEST_QUERIES = [
    # --- DOMINIO ARXIV (Speech) ---
    "Word Error Rate",          # Metrica tecnica (Tabelle)
    "Spectrogram",              # Visualizzazione (Figure)
    "Transformer architecture", # Concetto generale
    "End-to-end ASR",           # Specifico
    
    # --- DOMINIO PUBMED (Health) ---
    "Hazard Ratio",             # Metrica statistica (Tabelle)
    "Kaplan-Meier",             # Grafico sopravvivenza (Figure)
    "ultra-processed foods",    # Keyword homework
    "cardiovascular risk"       # Keyword homework
]

def run_quantitative_test():
    es = Elasticsearch(ES_HOST, request_timeout=60)
    
    if not es.ping():
        print("❌ Errore: Elasticsearch non è raggiungibile.")
        return

    results = []
    print(f"--- AVVIO BENCHMARK QUANTITATIVO (Performance & Volume) ---")
    print(f"Target Host: {ES_HOST}")
    
    for query in TEST_QUERIES:
        print(f"\n🔹 Test query: '{query}'")
        
        query_stats = {
            "query": query,
            "total_hits_all_indices": 0,
            "unique_papers_found": 0,
            "latency_articles": 0,
            "latency_tables": 0,
            "latency_figures": 0,
            "total_latency_py": 0
        }
        
        global_paper_ids = set()
        t_start_global = time.time()

        for index_name, fields in INDEX_CONFIG.items():
            sys.stdout.write(f"   -> Scanning '{index_name}'... ")
            sys.stdout.flush()
            
            try:
                # Esecuzione Query
                # Nota: Usiamo simple_query_string o query_string con i campi pesati
                resp = es.search(
                    index=index_name,
                    body={
                        "query": {
                            "query_string": {
                                "query": query,
                                "fields": fields, # <--- QUI USIAMO I PESI (es. caption^3)
                                "default_operator": "AND" # Più restrittivo e preciso
                            }
                        },
                        "_source": ["paper_id"], 
                        "size": 1000, 
                        "track_total_hits": True 
                    }
                )
                
                # Metriche Elasticsearch
                took = resp['took']
                hits_val = resp['hits']['total']['value']
                
                # Salvataggio metriche specifiche per indice
                query_stats[f"latency_{index_name}"] = took
                query_stats["total_hits_all_indices"] += hits_val
                
                # Raccolta ID per contare i Paper unici coinvolti
                current_ids = 0
                for hit in resp['hits']['hits']:
                    source = hit.get('_source', {})
                    pid = source.get('paper_id')
                    # Fallback se paper_id non è nel source (es. vecchio indice)
                    if not pid: 
                         # Prova a estrarre dal formato ID composto (es. 2209.1234_tab_1)
                         raw_id = hit['_id']
                         pid = raw_id.split('_')[0] if '_' in raw_id else raw_id
                         
                    if pid:
                        global_paper_ids.add(str(pid))
                    current_ids += 1
                
                print(f"✅ {hits_val} hits ({took}ms)")

            except Exception as e:
                print(f"❌ Errore: {e}")
                query_stats[f"latency_{index_name}"] = -1 # Indica errore

        t_end_global = time.time()
        
        query_stats["unique_papers_found"] = len(global_paper_ids)
        query_stats["total_latency_py"] = round((t_end_global - t_start_global) * 1000, 2)
        
        results.append(query_stats)

    # --- OUTPUT FINALE CSV ---
    print("\n\n--- RISULTATI CSV (Copia in Excel per i grafici) ---")
    
    # Intestazione
    header = ["Query", "Unique Papers", "Total Hits", "Lat. Articles (ms)", "Lat. Tables (ms)", "Lat. Figures (ms)", "Total Time (ms)"]
    print(",".join(header))
    
    for r in results:
        row = [
            f"\"{r['query']}\"", # Virgolette per sicurezza se la query ha spazi
            str(r['unique_papers_found']),
            str(r['total_hits_all_indices']),
            str(r['latency_articles']),
            str(r['latency_tables']),
            str(r['latency_figures']),
            str(r['total_latency_py'])
        ]
        print(",".join(row))

if __name__ == "__main__":
    run_quantitative_test()