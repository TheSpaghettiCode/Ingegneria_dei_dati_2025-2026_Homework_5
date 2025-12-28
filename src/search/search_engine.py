from elasticsearch import Elasticsearch

class SearchEngine:
    """
    Wrapper class for Elasticsearch search operations.
    Handles query construction for articles, tables, and figures.
    """
    def __init__(self, es_host="http://localhost:9200"):
        """
        Initialize the SearchEngine.
        
        Args:
            es_host (str): Elasticsearch server URL.
        """
        self.es = Elasticsearch(es_host)
        
    def search(self, index, query, fields=None):
        """
        Perform a search on the specified index using a boolean query string.
        
        Args:
           index (str): The name of the index to search (e.g., 'articles', 'tables', 'figures').
           query (str): The search query string (supports Lucene syntax like 'speech AND text').
           fields (list): Optional list of fields to restrict the search to.
           
        Returns:
            list: A list of search hits (dictionaries) from Elasticsearch.
        """
        
        # We use 'query_string' which allows for complex boolean operations (AND, OR, NOT)
        # This satisfies the requirement for "Boolean Combinations" (e.g., "speech AND text")
        body = {
            "query": {
                "query_string": {
                    "query": query,
                    "fields": fields if fields else ["*"], # Search all fields by default
                    "default_operator": "AND" # Make terms mandatory by default (closer to Google behavior)
                }
            },
            "highlight": {
                "fields": {
                    "*": {} # Highlight matches in all fields
                }
            }
        }
        
        try:
            # Execute search
            res = self.es.search(index=index, body=body)
            # Return the list of hits
            return res['hits']['hits']
        except Exception as e:
            print(f"Search error: {e}")
            return []
