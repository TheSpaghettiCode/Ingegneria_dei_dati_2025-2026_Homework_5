from elasticsearch import Elasticsearch, helpers

class IndexManager:
    """
    Manages Elasticsearch indices and handles the bulk indexing of data.
    """
    def __init__(self, es_host="http://localhost:9200"):
        """
        Initialize the IndexManager.
        
        Args:
            es_host (str): Elasticsearch server URL.
        """
        self.es = Elasticsearch(es_host)
        
        # Define index schemas (mappings) for articles, tables, and figures
        self.indices = {
            "articles": {
                "mappings": {
                    "properties": {
                        "title": {"type": "text"},
                        "authors": {"type": "keyword"},
                        "date": {"type": "date"},
                        "abstract": {"type": "text"},
                        "abstract": {"type": "text"},
                        "full_text": {"type": "text"},
                        "source": {"type": "keyword"} # 'arxiv' or 'pubmed'
                    }
                }
            },
            "tables": {
                "mappings": {
                    "properties": {
                        "paper_id": {"type": "keyword"},
                        "table_id": {"type": "keyword"},
                        "caption": {"type": "text"},
                        "body": {"type": "text"},
                        "mentions": {"type": "text"},
                        "context_paragraphs": {"type": "text"},
                         "source": {"type": "keyword"}
                    }
                }
            },
            "figures": {
                "mappings": {
                    "properties": {
                        "paper_id": {"type": "keyword"},
                        "figure_id": {"type": "keyword"},
                        "url": {"type": "keyword"},
                        "caption": {"type": "text"},
                        "mentions": {"type": "text"},
                        "context_paragraphs": {"type": "text"},
                        "source": {"type": "keyword"} 
                    }
                }
            }
        }

    def create_indices(self):
        """
        Create indices in Elasticsearch if they do not exist.
        """
        for index_name, config in self.indices.items():
            if not self.es.indices.exists(index=index_name):
                self.es.indices.create(index=index_name, body=config)
                print(f"Created index: {index_name}")
            else:
                print(f"Index {index_name} already exists.")

    def index_data(self, data):
        """
        Prepare and bulk index data for a single paper (Article + Tables + Figures).
        
        Args:
            data (dict): Unified dictionary containing paper content and metadata.
        """
        actions = []
        
        # 1. Prepare Article Document
        article_doc = {
            "_index": "articles",
            "_id": data["paper_id"],
            "_source": {
                "title": data.get("title", ""),
                "authors": data.get("authors", []),
                "date": data.get("date", ""),
                "abstract": data.get("abstract", ""),
                "full_text": data.get("full_text", ""),
                "source": data.get("source", "arxiv")
            }
        }
        actions.append(article_doc)
        
        # 2. Prepare Table Documents
        for tbl in data.get("tables", []):
            table_doc = {
                "_index": "tables",
                "_source": {
                    "paper_id": data["paper_id"],
                    "table_id": tbl["table_id"],
                    "caption": tbl["caption"],
                    "body": tbl["body"],
                    "mentions": tbl["mentions"],
                    "context_paragraphs": tbl["context_paragraphs"],
                    "source": data.get("source", "arxiv")
                }
            }
            actions.append(table_doc)
            
        # 3. Prepare Figure Documents
        for fig in data.get("figures", []):
            fig_doc = {
                "_index": "figures",
                "_source": {
                    "paper_id": data["paper_id"],
                    "figure_id": fig["figure_id"],
                    "url": fig["url"],
                    "caption": fig["caption"],
                    "mentions": fig["mentions"],
                    "context_paragraphs": fig["context_paragraphs"],
                    "source": data.get("source", "arxiv")
                }
            }
            actions.append(fig_doc)
            
        # Execute Bulk Indexing
        if actions:
            helpers.bulk(self.es, actions)
            # print(f"Indexed {len(actions)} documents for paper {data['paper_id']}")
