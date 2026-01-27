import pandas as pd
from elasticsearch import Elasticsearch

# --- CONFIGURAZIONE ---
ES_HOST = "http://localhost:9200"
es = Elasticsearch(ES_HOST)

# 1. I TUOI PESI REALI (Copiati dalla tua app)
# Questo assicura che il test rifletta il comportamento reale del sistema
INDEX_CONFIG = {
    "articles": ["title^3", "abstract^2", "full_text"],
    "tables":   ["caption^3", "body", "paper_title^1", "context_paragraphs", "mentions"],
    "figures":  ["caption^3", "mentions", "paper_title^1", "context_paragraphs"]
}

# 2. LISTA QUERY DA VALUTARE
# Scegli 3-4 casi d'uso significativi per la tua tesi
# 2. SCENARI DA VALUTARE
QUALITATIVE_SCENARIOS = [
    # A. UTENTE MEDICO (Ricerca generica - AND implicito)
    {
        "query": "cardiovascular risk AND ultra-processed foods", 
        "index": "articles", 
        "desc": "Ricerca Medica Generica",
        "use_quotes": False # <--- NO virgolette, usa logica booleana
    },
    
    # B. UTENTE TECNICO (Ricerca esatta - Phrase)
    {
        "query": "attention mechanism", 
        "index": "articles", 
        "desc": "Ricerca Concetto NLP Esatto",
        "use_quotes": True  # <--- SÌ virgolette, cerca la frase esatta
    },
    
    # C. RICERCA DATI (Tabelle - Phrase)
    {
        "query": "confidence interval", 
        "index": "tables", 
        "desc": "Ricerca Statistica in Tabelle",
        "use_quotes": True
    },
    # D. RICERCA VISUALE (Figure - Phrase)
    {
        "query": "learning curve", 
        "index": "figures", 
        "desc": "Ricerca Visuale (Grafici)",
        "use_quotes": True
    }
]

def run_manual_evaluation():
    results = []
    print("--- 🕵️ AVVIO VALUTAZIONE QUALITATIVA ---")
    print("Il sistema userà i pesi reali della tua app (es. title^3).")
    print("Per ogni risultato, digita 'y' (Sì/Rilevante) o 'n' (No/Rumore).\n")

    for scenario in QUALITATIVE_SCENARIOS:
        q_text = scenario["query"]
        idx = scenario["index"]
        use_quotes = scenario.get("use_quotes", False) # Legge il flag

        # --- LOGICA FONDAMENTALE: AGGIUNTA VIRGOLETTE ---
        # Se use_quotes è True, avvolgiamo la stringa tra virgolette escaped.
        # Es: 'attention mechanism' diventa '"attention mechanism"'
        if use_quotes:
            final_query_string = f'"{q_text}"'
            mode_label = "PHRASE (Esatta)"
        else:
            final_query_string = q_text
            mode_label = "BOOLEAN/AND (Generica)"
        # -----------------------------------------------

        # Recupera i campi pesati corretti per questo indice
        target_fields = INDEX_CONFIG.get(idx, ["*"])
        
        print(f"\n🔹 SCENARIO: {scenario['desc']}")
        print(f"   Query: '{q_text}' | Indice: {idx} | Tipo: {mode_label}")
        print("-" * 60)

        # Se la query ha le virgolette, Elasticsearch farà Phrase Search automaticamente.
        # Se non le ha, userà il tuo "default_operator": "AND".
        
        try:
            resp = es.search(
                index=idx,
                body={
                    "query": {
                        "query_string": {
                            "query": final_query_string,           # Passi la stringa (con o senza virgolette)
                            "fields": target_fields,   # I tuoi pesi (title^3 ecc)
                            "default_operator": "AND"  # La logica base della tua app
                        }
                    },
                    "size": 5
                }
            )
        except Exception as e:
            print(f"❌ Errore query: {e}")
            continue

        hits = resp['hits']['hits']
        
        if not hits:
            print("   ⚠️ Nessun risultato trovato.")
        
        for rank, hit in enumerate(hits, 1):
            score = hit['_score']
            source = hit['_source']
            paper_id = source.get('paper_id', hit['_id'])
            
            # Creiamo un'anteprima intelligente in base all'indice
            if idx == "articles":
                title = source.get('title', 'No Title')
                preview = f"TITOLO: {title}"
            elif idx == "tables" or idx == "figures":
                caption = source.get('caption', 'No Caption')
                preview = f"DIDASCALIA: {caption[:150]}..." # Tagliamo se troppo lunga
            
            print(f"\n   #{rank} [Score: {score:.2f}] ID: {paper_id}")
            print(f"   {preview}")
            
            # Input Manuale
            while True:
                vote = input("   👉 Rilevante? (y/n): ").strip().lower()
                if vote in ['y', 'n']:
                    break
            
            is_relevant = 1 if vote == 'y' else 0
            
            # Salvataggio dati per il report
            results.append({
                "Scenario": scenario['desc'],
                "Query": q_text,
                "Index": idx,
                "Rank": rank,
                "Score": score,
                "Paper_ID": paper_id,
                "Preview": preview,
                "Relevant": is_relevant
            })

    # --- OUTPUT FINALE ---
    if results:
        df = pd.DataFrame(results)
        filename = "valutazione_qualitativa.csv"
        df.to_csv(filename, index=False)
        
        print("\n\n--- 📊 RISULTATI (P@5) ---")
        # Calcola la precisione media per scenario
        precision = df.groupby("Scenario")["Relevant"].mean() * 100
        print(precision)
        print(f"\nDati salvati in '{filename}'. Usa questo CSV per la tabella nella relazione!")
    else:
        print("\nNessun dato raccolto.")

if __name__ == "__main__":
    run_manual_evaluation()