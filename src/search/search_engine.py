from elasticsearch import Elasticsearch

class SearchEngine:
    def __init__(self, es_host="http://localhost:9200"):
        self.es = Elasticsearch(es_host)
        
    def search(self, index, query, fields=None):
        """
        Perform a search on the specified index.
        :param index: 'articles', 'tables', or 'figures' (or comma separated)
        :param query: Query string (Lucene syntax supported)
        :param fields: List of fields to search (optional)
        """
        body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": fields if fields else ["*"]
                }
            },
             "highlight": {
                "fields": {
                    "*": {}
                }
            }
        }
        
        # If user wants robust boolean, simple_query_string or query_string is better
        # User asked for "Combinazioni di query (es. ricerca booleana)".
        # query_string is best for "speech AND text"
        body = {
            "query": {
                "query_string": {
                    "query": query,
                    "fields": fields if fields else ["*"],
                    "default_operator": "AND"
                }
            },
            "highlight": {
                "fields": {
                    "*": {}
                }
            }
        }
        
        try:
            res = self.es.search(index=index, body=body)
            return res['hits']['hits']
        except Exception as e:
            print(f"Search error: {e}")
            return []
