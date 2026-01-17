import time
import sys
from elasticsearch import Elasticsearch

# CONFIGURAZIONE
ES_HOST = "http://localhost:9200"
INDICES = {
    "articles": ["title", "abstract", "full_text"],
    "tables":   ["caption", "body"],
    "figures":  ["caption", "context_paragraphs"]
}

TEST_QUERIES = [
    "cancer",
    "machine learning",
    "covid AND vaccine",
    "systematic review",
    "protein folding deepmind"
]

def run_quantitative_test():
    # Aumentiamo il timeout perché scaricare tanti documenti è lento
    es = Elasticsearch(ES_HOST, request_timeout=60)
    
    if not es.ping():
        print("❌ Errore: Elasticsearch non è raggiungibile.")
        return

    results = []

    print(f"--- AVVIO BENCHMARK QUANTITATIVO ---")
    
    for query in TEST_QUERIES:
        print(f"\n🔹 Test query: '{query}'...")
        
        query_stats = {
            "query": query,
            "total_hits": 0,
            "unique_ids": 0,
            "latency_es_total": 0,
            "latency_py_total": 0
        }
        
        global_ids = set()
        t_start_global = time.time()

        for index_name, fields in INDICES.items():
            # Feedback visivo: stampiamo cosa sta succedendo
            sys.stdout.write(f"   -> Scanning '{index_name}'... ")
            sys.stdout.flush() # Forza la stampa immediata
            
            try:
                t_start = time.time()
                resp = es.search(
                    index=index_name,
                    body={
                        "query": {"query_string": {"query": query, "fields": fields}},
                        "_source": ["paper_id"], # Scarichiamo solo l'ID
                        "size": 1000, # RIDOTTO A 1000 per velocità (aumentalo se serve)
                        "track_total_hits": True # Importante per avere il conteggio vero > 10000
                    }
                )
                
                # Raccolta metriche
                took = resp['took']
                hits_val = resp['hits']['total']['value']
                query_stats["latency_es_total"] += took
                query_stats["total_hits"] += hits_val
                
                # Raccolta ID
                current_ids = 0
                for hit in resp['hits']['hits']:
                    source = hit.get('_source', {})
                    pid = source.get('paper_id')
                    if not pid:
                        pid = hit['_id']
                    global_ids.add(str(pid))
                    current_ids += 1
                
                print(f"✅ Fatto ({current_ids} docs scaricati in {took}ms)")

            except Exception as e:
                print(f"❌ Errore: {e}")

        t_end_global = time.time()
        
        query_stats["unique_ids"] = len(global_ids)
        query_stats["latency_py_total"] = (t_end_global - t_start_global) * 1000 
        
        results.append(query_stats)

    # OUTPUT CSV
    print("\n\n--- RISULTATI CSV (Da incollare in Excel) ---")
    print("Query,Total Hits,Unique Papers,Latency ES (ms),Latency Total (ms)")
    for r in results:
        print(f"{r['query']},{r['total_hits']},{r['unique_ids']},{r['latency_es_total']},{r['latency_py_total']:.2f}")

if __name__ == "__main__":
    run_quantitative_test()