from elasticsearch import Elasticsearch

class SearchEngine:
    def __init__(self, host="http://localhost:9200"):
        self.es = Elasticsearch(host)

    # NOTA BENE: Qui abbiamo aggiunto 'page=1' e 'size=10'
    def search(self, index, query, fields=None, filters=None, page=1, size=10):
        """
        Esegue la ricerca su Elasticsearch con supporto alla PAGINAZIONE.
        """
        
        # Base Query
        must_clauses = [
            {
                "query_string": {
                    "query": query,
                    "fields": fields if fields else ["*"],
                    "default_operator": "AND"
                }
            }
        ]
        
        # Apply Filters
        if filters:
            for field, value in filters.items():
                if value:
                     must_clauses.append({"term": {field: value}})
        
        body = {
            "query": {
                "bool": {
                    "must": must_clauses
                }
            },
            "highlight": {
                "fields": {
                    "*": {} 
                }
            }
        }
        
        # --- CALCOLO OFFSET PER PAGINAZIONE ---
        # Questa è la parte nuova che mancava
        start_from = (page - 1) * size
        # --------------------------------------

        try:
            # Passiamo from_ e size a Elasticsearch
            res = self.es.search(index=index, body=body, from_=start_from, size=size)
            
            # Restituiamo il dizionario con total e results
            return {
                "results": res['hits']['hits'],
                "total": res['hits']['total']['value']
            }
        except Exception as e:
            print(f"Search error: {e}")
            return {"results": [], "total": 0}