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
        
    def search(self, index, query, fields=None, filters=None):
        """
        Perform a search on the specified index using a boolean query string.
        
        Args:
           index (str): The name of the index to search (e.g., 'articles', 'tables', 'figures').
           query (str): The search query string (supports Lucene syntax like 'speech AND text').
           fields (list): Optional list of fields to restrict the search to.
           filters (dict): Optional dictionary of exact match filters (e.g., {"source": "pubmed"}).
           
        Returns:
            list: A list of search hits (dictionaries) from Elasticsearch.
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
        
        try:
            # Execute search
            res = self.es.search(index=index, body=body)
            # Return the list of hits
            return res['hits']['hits']
        except Exception as e:
            print(f"Search error: {e}")
            return []
