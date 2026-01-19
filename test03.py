import time
import sys
import pandas as pd
from elasticsearch import Elasticsearch

# --- CONFIGURAZIONE ---
ES_HOST = "http://localhost:9200"

# Configurazione standard per le query generiche (pesi)
INDEX_CONFIG = {
    "articles": ["title^3", "abstract^2", "full_text"],
    "tables":   ["caption^3", "body", "paper_title^1", "context_paragraphs", "mentions"],
    "figures":  ["caption^3", "mentions", "paper_title^1", "context_paragraphs"]
}

# --- DEFINIZIONE SCENARI DI TEST ---
TEST_SCENARIOS = [
    # 1. RICERCA BOOLEANA (AND, OR, NOT)
    {
        "type": "boolean",
        "label": "BOOL: speech AND text",
        "query": "speech AND text",
        "indices": ["articles", "tables", "figures"] 
    },
    {
        "type": "boolean",
        "label": "BOOL: food OR risk",
        "query": "foods OR risk",
        "indices": ["articles", "tables", "figures"]
    },

    {
        "type": "boolean",
        "label": "BOOL: -foods",
        "query": "NOT foods",
        "indices": ["articles", "tables", "figures"]
    },

    # 5. RICERCA SORGENTE SPECIFICA
    {
        "type": "term",
        "label": "SOURCE: Arxiv",
        "field": "source",
        "value": "arxiv",
        "indices": ["articles", "tables", "figures"]
    },
    {
        "type": "term",
        "label": "SOURCE: Pubmed",
        "field": "source",
        "value": "pubmed",
        "indices": ["articles", "tables", "figures"]
    },
    # 2. RICERCA TERMINE SPECIFICO (Phrase Match) [MODIFICATO]
    # Cerca una frase esatta o un termine tecnico nel testo
    {
        "type": "specific_term",
        "label": "TERM: deep learning",
        "query": "deep learning",
        "indices": ["articles", "tables", "figures"]
    },
    {
        "type": "specific_term",
        "label": "TERM: LSTM",
        "query": "LSTM",
        "indices": ["articles", "tables", "figures"]
    },

    {
        "type": "specific_term",
        "label": "TERM: emotion recognition",
        "query": "emotion recognition ",
        "indices": ["articles", "tables", "figures"]
    },

    # 3. RICERCA RELATIVA A UN INDICE SPECIFICO
    {
        "type": "specific_index",
        "label": "IDX: confidence interval (tables)",
        "query": "confidence interval",
        "indices": ["tables"] 
    },
    {
        "type": "specific_index",
        "label": "IDX: plot (figures)",
        "query": "plot",
        "indices": ["figures"] 
    },

    # 4. RICERCA RELATIVA A UN CAMPO SPECIFICO
    {
        "type": "specific_field",
        "label": "FIELD: transformer (title)",
        "field": "title",
        "query": "transformer",
        "indices": ["articles"] 
    },
    {
        "type": "specific_field",
        "label": "FIELD: error rate (caption)",
        "field": "caption",
        "query": "error rate",
        "indices": ["tables", "figures"] 
    }
]

def run_quantitative_test():
    es = Elasticsearch(ES_HOST, request_timeout=60)
    
    if not es.ping():
        print("❌ Errore: Elasticsearch non è raggiungibile.")
        return

    results = []
    print(f"--- AVVIO BENCHMARK QUANTITATIVO AVANZATO ---")
    print(f"Target Host: {ES_HOST}")
    
    for scenario in TEST_SCENARIOS:
        label = scenario['label']
        q_type = scenario['type']
        target_indices = scenario['indices']
        
        print(f"\n🔹 Test Scenario: '{label}' ({q_type})")
        
        query_stats = {
            "query_label": label,
            "query_type": q_type,
            "total_hits": 0,
            "unique_papers": 0,
            "lat_articles": 0,
            "lat_tables": 0,
            "lat_figures": 0,
            "total_time_py": 0
        }
        
        global_paper_ids = set()
        t_start_global = time.time()

        for index_name in ["articles", "tables", "figures"]:
            
            if index_name not in target_indices:
                continue

            sys.stdout.write(f"   -> Scanning '{index_name}'... ")
            sys.stdout.flush()
            
            # --- COSTRUZIONE DINAMICA DELLA QUERY ---
            body = {}
            
            if q_type == "boolean":
                # Ricerca con operatori logici
                body = {
                    "query": {
                        "query_string": {
                            "query": scenario['query'],
                            "fields": INDEX_CONFIG.get(index_name, ["*"]),
                            "default_operator": "OR"
                        }
                    }
                }
            
            elif q_type == "specific_term":
                # [MODIFICATO] Ricerca frase esatta nel testo
                body = {
                    "query": {
                        "multi_match": {
                            "query": scenario['query'],
                            "fields": INDEX_CONFIG.get(index_name, ["*"]),
                            "type": "phrase" # <--- Importante: cerca la sequenza esatta
                        }
                    }
                }

            elif q_type == "specific_index":
                # Ricerca limitata all'indice corrente
                body = {
                    "query": {
                        "multi_match": {
                            "query": scenario['query'],
                            "fields": INDEX_CONFIG.get(index_name, ["*"])
                        }
                    }
                }

            elif q_type == "specific_field":
                # Ricerca limitata a un campo specifico
                body = {
                    "query": {
                        "match": {
                            scenario['field']: scenario['query']
                        }
                    }
                }

            # Parametri standard
            body["_source"] = ["paper_id"]
            body["size"] = 1000
            body["track_total_hits"] = True

            try:
                resp = es.search(index=index_name, body=body)
                
                took = resp['took']
                hits_val = resp['hits']['total']['value']
                
                query_stats[f"lat_{index_name}"] = took
                query_stats["total_hits"] += hits_val
                
                for hit in resp['hits']['hits']:
                    source = hit.get('_source', {})
                    pid = source.get('paper_id')
                    if not pid:
                        raw_id = hit['_id']
                        pid = raw_id.split('_')[0] if '_' in raw_id else raw_id
                    
                    if pid:
                        global_paper_ids.add(str(pid))
                
                print(f"✅ {hits_val} hits ({took}ms)")

            except Exception as e:
                print(f"❌ Errore: {e}")
                query_stats[f"lat_{index_name}"] = -1

        t_end_global = time.time()
        
        query_stats["unique_papers"] = len(global_paper_ids)
        query_stats["total_time_py"] = round((t_end_global - t_start_global) * 1000, 2)
        
        results.append(query_stats)

    # --- OUTPUT CSV ---
    print("\n\n--- RISULTATI CSV ---")
    header = ["Scenario Label", "Type", "Total Hits", "Unique Papers", "Lat. Art (ms)", "Lat. Tab (ms)", "Lat. Fig (ms)", "Total Time (ms)"]
    print(",".join(header))
    
    for r in results:
        row = [
            f"\"{r['query_label']}\"",
            r['query_type'],
            str(r['total_hits']),
            str(r['unique_papers']),
            str(r['lat_articles']),
            str(r['lat_tables']),
            str(r['lat_figures']),
            str(r['total_time_py'])
        ]
        print(",".join(row))

if __name__ == "__main__":
    run_quantitative_test()