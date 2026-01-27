import time
import sys
import pandas as pd
from elasticsearch import Elasticsearch

# --- CONFIGURAZIONE ---
ES_HOST = "http://localhost:9200"

# Pesi dei campi (coerenti con la tua app)
INDEX_CONFIG = {
    "articles": ["title^3", "abstract^2", "full_text"],
    "tables":   ["caption^3", "body", "paper_title^1", "context_paragraphs", "mentions"],
    "figures":  ["caption^3", "mentions", "paper_title^1", "context_paragraphs"]
}

# --- SCENARI DI TEST (I tuoi scenari) ---
TEST_SCENARIOS = [
    # 1. RICERCA BOOLEANA
    { "type": "Boolean", 
     "label": "BOOL: speech AND text", 
     "query": "speech AND text", 
     "indices": ["articles", "tables", "figures"] },

    { "type": "Boolean", 
     "label": "BOOL: food OR risk", 
     "query": "foods OR risk", 
     "indices": ["articles", "tables", "figures"] },

    { "type": "Boolean", 
     "label": "BOOL: NOT foods", 
     "query": "NOT foods", 
     "indices": ["articles", "tables", "figures"] },

    # 3. RICERCA TERMINE SPECIFICO (Phrase Match nel testo)
    { "type": "Specific Term", "label": "TERM: deep learning", "query": "deep learning", "indices": ["articles", "tables", "figures"] },
    { "type": "Specific Term", "label": "TERM: LSTM", "query": "LSTM", "indices": ["articles", "tables", "figures"] },
    { "type": "Specific Term", "label": "TERM: emotion recognition", "query": "emotion recognition", "indices": ["articles", "tables", "figures"] },

    # 4. RICERCA SU INDICE SPECIFICO
    { "type": "Specific Index", "label": "IDX: confidence interval (tables)", "query": "confidence interval", "indices": ["tables"] },
    { "type": "Specific Index", "label": "IDX: plot (figures)", "query": "plot", "indices": ["figures"] },

    # 5. RICERCA SU CAMPO SPECIFICO
    { "type": "Specific Field", "label": "FIELD: transformer (title)", "field": "title", "query": "transformer", "indices": ["articles"] },
    { "type": "Specific Field", "label": "FIELD: error rate (caption)", "field": "caption", "query": "error rate", "indices": ["tables", "figures"] }
]

def print_global_stats(es):
    """
    Stampa le statistiche di volume per la relazione (Sezione 'Dimensione Indice').
    """
    print("\n--- 📊 STATISTICHE DI VOLUME (DA INSERIRE NELLA RELAZIONE) ---")
    
    # 1. Conta documenti per Indice
    indices = ["articles", "tables", "figures"]
    total_docs = 0
    for idx in indices:
        try:
            count = es.count(index=idx)['count']
            print(f"   • Indice '{idx}': {count} documenti")
            total_docs += count
        except:
            print(f"   • Indice '{idx}': 0 (Non trovato)")
    print(f"   ---------------------------")
    print(f"   TOTALE DOCUMENTI: {total_docs}")

    # 2. Conta documenti per Sorgente (solo su Articles per semplicità)
    print("\n--- 📚 DISTRIBUZIONE SORGENTI (SOLO ARTICOLI) ---")
    try:
        arxiv_c = es.count(index="articles", body={"query": {"term": {"source": "arxiv"}}})['count']
        pubmed_c = es.count(index="articles", body={"query": {"term": {"source": "pubmed"}}})['count']
        print(f"   • ArXiv:  {arxiv_c}")
        print(f"   • PubMed: {pubmed_c}")
    except Exception as e:
        print(f"   Errore conteggio sorgenti: {e}")
    print("----------------------------------------------------------\n")

def run_quantitative_test():
    es = Elasticsearch(ES_HOST, request_timeout=60)
    
    if not es.ping():
        print("❌ Errore: Elasticsearch non è raggiungibile.")
        return

    # 1. ESEGUI LA CONTA DEI DATI PER LA RELAZIONE
    print_global_stats(es)

    results = []
    print(f"--- 🚀 AVVIO TEST PRESTAZIONI (LATENZA & RILEVANZA) ---")
    
    for scenario in TEST_SCENARIOS:
        label = scenario['label']
        q_type = scenario['type']
        target_indices = scenario['indices']
        
        # print(f"🔹 Test: {label}")
        
        query_stats = {
            "Label": label,
            "Type": q_type,
            "Total_Hits": 0,       # Rilevanza (Volume di risultati trovati)
            "Lat_Articles": 0,     # Latenza (ms)
            "Lat_Tables": 0,
            "Lat_Figures": 0,
            "Lat_Total_Py": 0      # Tempo totale percepito dallo script Python
        }
        
        t_start_global = time.time()

        for index_name in ["articles", "tables", "figures"]:
            
            # Se lo scenario non prevede questo indice, mettiamo 0 e saltiamo
            if index_name not in target_indices:
                continue

            # --- COSTRUZIONE QUERY ---
            body = {}
            if q_type == "Boolean":
                body = { "query": { "query_string": { "query": scenario['query'], "fields": INDEX_CONFIG.get(index_name, ["*"]), "default_operator": "OR" } } }
            elif q_type == "Source Filter":
                body = { "query": { "term": { scenario['field']: scenario['value'] } } }
            elif q_type == "Specific Term":
                body = { "query": { "multi_match": { "query": scenario['query'], "fields": INDEX_CONFIG.get(index_name, ["*"]), "type": "phrase" } } }
            elif q_type == "Specific Index":
                body = { "query": { "multi_match": { "query": scenario['query'], "fields": INDEX_CONFIG.get(index_name, ["*"]) } } }
            elif q_type == "Specific Field":
                body = { "query": { "match": { scenario['field']: scenario['query'] } } }

            # --- PARAMETRI PER LA RELAZIONE ---
            body["_source"] = ["paper_id"]
            body["size"] = 1000  # LIMITIAMO A 1000 PER MISURARE LA LATENZA REALE UTENTE
            body["track_total_hits"] = True # FONDAMENTALE: Conta TUTTI i risultati anche se ne scarichi 1000

            try:
                # Esecuzione
                resp = es.search(index=index_name, body=body)
                
                # RACCOLTA DATI
                took = resp['took'] # Latenza di Elasticsearch
                real_hits = resp['hits']['total']['value'] # Numero VERO di documenti trovati
                
                query_stats[f"Lat_{index_name.capitalize()}"] = took
                query_stats["Total_Hits"] += real_hits
                
            except Exception as e:
                query_stats[f"Lat_{index_name.capitalize()}"] = -1

        t_end_global = time.time()
        query_stats["Lat_Total_Py"] = round((t_end_global - t_start_global) * 1000, 2)
        
        results.append(query_stats)

    # --- OUTPUT CSV PULITO PER EXCEL ---
    print("\n\n--- 📋 COPIA QUESTO OUTPUT IN EXCEL PER I GRAFICI ---")
    
    # Intestazione CSV
    header = ["Scenario", "Type", "Total Hits (Relevance)", "Lat Articles (ms)", "Lat Tables (ms)", "Lat Figures (ms)", "Total Latency (ms)"]
    print(",".join(header))
    
    for r in results:
        row = [
            f"\"{r['Label']}\"",
            f"\"{r['Type']}\"",
            str(r['Total_Hits']),
            str(r['Lat_Articles']),
            str(r['Lat_Tables']),
            str(r['Lat_Figures']),
            str(r['Lat_Total_Py'])
        ]
        print(",".join(row))

if __name__ == "__main__":
    run_quantitative_test()