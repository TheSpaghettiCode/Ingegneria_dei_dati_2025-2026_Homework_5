from flask import Flask, render_template, request, jsonify
import sys
import os
import requests
from elasticsearch import Elasticsearch

# Add src to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from search.search_engine import SearchEngine

app = Flask(__name__, template_folder='../ui/templates', static_folder='../ui/static')
engine = SearchEngine()
es = Elasticsearch("http://localhost:9200")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stats')
def stats():
    try:
        count_arts = es.count(index="articles")['count']
        count_tabs = es.count(index="tables")['count']
        count_figs = es.count(index="figures")['count']
        return jsonify({
            "papers": count_arts,
            "tables": count_tabs,
            "figures": count_figs
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/search')
def search():
    query = request.args.get('query', '')
    index_type = request.args.get('index_type', 'articles')
    
    if not query:
        return jsonify([])
    
    # Map friendly name to index name if needed, but we use strict names in UI
    target_index = index_type.lower()
    
    results = engine.search(index=target_index, query=query)
    
    # Post-process for Image URLs
    if target_index == 'figures':
        for hit in results:
            src = hit['_source']
            raw_url = src.get('url', '')
            paper_id = src.get('paper_id')
            # If relative URL (doesn't start with http), prepend arxiv base
            if raw_url and not raw_url.startswith('http') and paper_id:
                # ArXiv HTML convention
                src['url'] = f"https://arxiv.org/html/{paper_id}/{raw_url}"
                
    return jsonify(results)

@app.route('/paper/<path:paper_id>')
def paper_detail(paper_id):
    # Fetch paper details
    res = es.search(index="articles", body={"query": {"term": {"_id": paper_id}}}, size=1)
    if not res['hits']['hits']:
        return "Paper not found", 404
    
    paper = res['hits']['hits'][0]['_source']
    paper['id'] = paper_id
    
    # Fetch tables
    tables_res = es.search(index="tables", body={"query": {"term": {"paper_id": paper_id}}}, size=100)
    tables = [t['_source'] for t in tables_res['hits']['hits']]
    
    # Fetch figures
    figs_res = es.search(index="figures", body={"query": {"term": {"paper_id": paper_id}}}, size=100)
    figures = [f['_source'] for f in figs_res['hits']['hits']]
    
    # Fix figure URLs for proxy
    for f in figures:
        raw_url = f.get('url', '')
        if raw_url and not raw_url.startswith('http'):
            f['url'] = f"https://arxiv.org/html/{paper_id}/{raw_url}"

    return render_template('paper_detail.html', paper=paper, tables=tables, figures=figures)

@app.route('/api/image_proxy')
def image_proxy():
    url = request.args.get('url')
    if not url:
        return "Missing URL", 400
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        resp = requests.get(url, headers=headers, stream=True, timeout=10)
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items()
                   if name.lower() not in excluded_headers]
        
        from flask import Response
        return Response(resp.content, resp.status_code, headers)
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
