from elasticsearch import Elasticsearch, helpers

class IndexManager:
    def __init__(self, es_host="http://localhost:9200"):
        self.es = Elasticsearch(es_host)
        self.indices = {
            "articles": {
                "mappings": {
                    "properties": {
                        "title": {"type": "text"},
                        "authors": {"type": "keyword"},
                        "date": {"type": "date"},
                        "abstract": {"type": "text"},
                        "full_text": {"type": "text"}
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
                        "context_paragraphs": {"type": "text"}
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
                        # context_paragraphs mentioned in point 5 for extraction, but not explicitly in point 7 for indexing?
                        # Point 7: "url, paper_id, table_id (ID della figura...), caption, mentions".
                        # Wait, point 5 says extract context. Point 7 says index Url, paper_id, ID, caption, mentions.
                        # I will add context_paragraphs anyway as it's useful for search.
                        "context_paragraphs": {"type": "text"} 
                    }
                }
            }
        }

    def create_indices(self):
        for index_name, config in self.indices.items():
            if not self.es.indices.exists(index=index_name):
                self.es.indices.create(index=index_name, body=config)
                print(f"Created index: {index_name}")
            else:
                print(f"Index {index_name} already exists.")

    def index_data(self, paper_data, metadata):
        actions = []
        
        # 1. Article Document
        article_doc = {
            "_index": "articles",
            "_id": paper_data["paper_id"],
            "_source": {
                "title": metadata.get("title", ""),
                "authors": metadata.get("authors", []),
                "date": metadata.get("published", ""),
                "abstract": metadata.get("abstract", ""),
                "full_text": paper_data.get("full_text", "")
            }
        }
        actions.append(article_doc)
        
        # 2. Tables
        for tbl in paper_data["tables"]:
            table_doc = {
                "_index": "tables",
                "_source": {
                    "paper_id": paper_data["paper_id"],
                    "table_id": tbl["table_id"],
                    "caption": tbl["caption"],
                    "body": tbl["body"],
                    "mentions": tbl["mentions"],
                    "context_paragraphs": tbl["context_paragraphs"]
                }
            }
            actions.append(table_doc)
            
        # 3. Figures
        for fig in paper_data["figures"]:
            fig_doc = {
                "_index": "figures",
                "_source": {
                    "paper_id": paper_data["paper_id"],
                    "figure_id": fig["figure_id"],
                    "url": fig["url"],
                    "caption": fig["caption"],
                    "mentions": fig["mentions"],
                     # Adding context if available, though strict requirement didn't list it for indexing, extraction asked for it.
                    "context_paragraphs": fig["context_paragraphs"]
                }
            }
            actions.append(fig_doc)
            
        # Bulk Index
        if actions:
            helpers.bulk(self.es, actions)
            print(f"Indexed {len(actions)} documents for paper {paper_data['paper_id']}")
