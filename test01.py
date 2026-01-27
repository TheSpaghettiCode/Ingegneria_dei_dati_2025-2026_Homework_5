import sys
from elasticsearch import Elasticsearch

# Configurazione
ES_HOST = "http://localhost:9200"
INDICES = {
    "articles": ["title^3", "abstract^2", "full_text"],
    "tables":   ["caption^3", "body", "paper_title^1", "context_paragraphs","mentions"],
    "figures":  ["caption^3", "mentions", "paper_title^1", "context_paragraphs"]
}

class Colors:
    HEADER = '\033[95m'
    BOLD = '\033[1m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'

def run_qualitative_test(query):
    es = Elasticsearch(ES_HOST)
    print(f"\n{Colors.HEADER}{'='*60}")
    print(f"  ANALISI QUALITATIVA (Deduplicata in Python): '{query}'")
    print(f"{'='*60}{Colors.ENDC}")

    for index_name, fields in INDICES.items():
        try:
            # 1. Chiediamo PIÙ risultati (size=15) per avere margine di manovra sui duplicati
            resp = es.search(
                index=index_name,
                body={
                    "query": {"query_string": {"query": query, "fields": fields, "default_operator": "AND"}},
                    "highlight": {
                        "fields": { f.split('^')[0]: {} for f in fields },
                        "pre_tags": [f"{Colors.RED}"],
                        "post_tags": [f"{Colors.ENDC}"]
                    },
                    "_source": ["title", "caption", "paper_id"],
                    "size": 15  # Scarichiamo un buffer di risultati
                }
            )
        except Exception as e:
            print(f"\n{Colors.RED}Errore su indice {index_name}: {e}{Colors.ENDC}")
            continue

        raw_hits = resp['hits']['hits']
        if not raw_hits:
            continue

        # 2. DEDUPLICAZIONE LATO CLIENT (Python)
        seen_ids = set()
        unique_hits = []
        
        for hit in raw_hits:
            # Recupera ID (o usa l'ID interno se manca paper_id)
            p_id = hit['_source'].get('paper_id')
            if not p_id:
                p_id = hit['_id']
            
            # Se non l'abbiamo ancora visto, lo aggiungiamo alla lista dei "buoni"
            if p_id not in seen_ids:
                seen_ids.add(p_id)
                unique_hits.append(hit)
            
            # Ci fermiamo quando ne abbiamo trovati 2 o 3 puliti
            if len(unique_hits) >= 3:
                break

        # Ora lavoriamo solo su unique_hits
        if not unique_hits:
            continue

        # Analisi dello Score
        scores = [h['_score'] for h in unique_hits]
        max_score = scores[0]
        
        drop_msg = "N/A"
        is_tie = False

        if len(scores) > 1:
            first = scores[0]
            second = scores[1]
            
            if abs(first - second) < 0.0001:
                is_tie = True
                drop_msg = f"{Colors.RED}0.0% (TIE){Colors.ENDC}"
            else:
                drop_pct = ((first - second) / first) * 100
                drop_msg = f"{drop_pct:.1f}%"

        print(f"\nINDICE: {Colors.BOLD}{index_name.upper()}{Colors.ENDC}")
        print(f"Max Score: {max_score:.2f} | Confidence Drop (deduplicato): {drop_msg}")
        
        if is_tie:
            print(f"{Colors.YELLOW}⚠️  NOTA: Score identico tra due paper DIVERSI.{Colors.ENDC}")

        # Mostra il VINCITORE
        winner = unique_hits[0]
        source = winner['_source']
        content = source.get('title') if index_name == "articles" else source.get('caption')
        if not content: content = "No Title/Caption"
            
        print(f"🏆 {Colors.GREEN}VINCITORE:{Colors.ENDC} {content[:100]}...")
        print(f"   ID: {source.get('paper_id', 'N/A')}")
        
        if 'highlight' in winner:
            print(f"   MATCH (Context):")
            first_field = list(winner['highlight'].keys())[0]
            snippet = winner['highlight'][first_field][0]
            print(f"   -> {first_field}: ...{snippet}...")
        print("-" * 40)

if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "ultra-processed foods AND cardiovascular risk"
    run_qualitative_test(q)