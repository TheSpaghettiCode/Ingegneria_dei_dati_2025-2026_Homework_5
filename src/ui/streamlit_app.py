import streamlit as st
from elasticsearch import Elasticsearch
import pandas as pd
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
# Attempt to import search engine, but we might just use ES directly for some tailored queries
from search.search_engine import SearchEngine

# Page Config
st.set_page_config(
    page_title="SciSearch Dashboard",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize ES
@st.cache_resource
def get_es():
    try:
        return Elasticsearch("http://localhost:9200")
    except:
        return None

es = get_es()

# Initialize Search Engine Wrapper
engine = SearchEngine()

# Custom CSS
st.markdown("""
<style>
    .result-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        border: 1px solid #f0f2f6;
    }
    .result-title {
        color: #2563eb;
        font-weight: bold;
        font-size: 1.2rem;
        text-decoration: none;
        display: block;
        margin-bottom: 5px;
    }
    .result-meta {
        color: #64748b;
        font-size: 0.9rem;
        margin-bottom: 10px;
    }
    .caption-highlight {
        background-color: #f0fdf4;
        border-left: 4px solid #22c55e;
        padding: 10px;
        font-style: italic;
        margin-bottom: 10px;
        color: #1a202c;
    }
    .highlight-em {
        background-color: #fef08a;
        font-weight: bold;
    }
    /* Dark mode adjustments would be handled by Streamlit's native theme generally */
</style>
""", unsafe_allow_html=True)


# --- SIDEBAR ---
with st.sidebar:
    st.title("🔬 SciSearch")
    st.markdown("Scientific Knowledge Graph Search")
    
    st.divider()
    
    # Metriche
    if es and es.ping():
        c1, c2, c3 = st.columns(3)
        try:
            count_arts = es.count(index="articles")['count']
            count_tabs = es.count(index="tables")['count']
            count_figs = es.count(index="figures")['count']
        except:
            count_arts = count_tabs = count_figs = "-"
            
        st.metric("Papers", count_arts)
        st.metric("Tables", count_tabs)
        st.metric("Figures", count_figs)
    else:
        st.error("Elasticsearch non connesso!")
    
    st.divider()
    
    # Search Target
    search_target = st.radio(
        "Search Target",
        ["Papers", "Tables", "Figures"],
        index=0
    )
    
    st.markdown("---")
    st.info("💡 **Tip**: Use boolean operators like `speech AND text`.")

# --- MAIN AREA ---

st.title("Scientific Knowledge Graph Search")

# Search Bar
col_search, col_btn = st.columns([4, 1])
with col_search:
    query = st.text_input("Enter your query...", placeholder="e.g., 'Entity resolution', 'Transformer architecture'...", label_visibility="collapsed")
with col_btn:
    search_clicked = st.button("Search", type="primary", use_container_width=True)

# Logic
target_index_map = {
    "Papers": "articles",
    "Tables": "tables",
    "Figures": "figures"
}

if search_clicked or query:
    if not query:
        st.warning("Please enter a query.")
    else:
        index_name = target_index_map[search_target]
        results = engine.search(index=index_name, query=query)
        
        st.markdown(f"### Found {len(results)} results for *'{query}'* in **{search_target}**")
        
        for hit in results:
            source = hit['_source']
            score = hit['_score']
            
            with st.container():
                st.markdown('<div class="result-card">', unsafe_allow_html=True)
                
                # --- VISTA PAPERS ---
                if search_target == "Papers":
                    st.markdown(f"[{source.get('title')}]({source.get('html_url', '#')})", unsafe_allow_html=True) # Fake link or real if available
                    st.markdown(f"<div class='result-meta'>Authors: {', '.join(source.get('authors', []))} • Date: {source.get('date', '')[:10]}</div>", unsafe_allow_html=True)
                    
                    abstract = source.get('abstract', '')
                    # Show first 3 lines approx (slice)
                    preview_len = 300
                    st.markdown(f"{abstract[:preview_len]}...")
                    
                    with st.expander("Leggi Abstract Completo"):
                        st.write(abstract)

                # --- VISTA TABLES ---
                elif search_target == "Tables":
                    st.markdown(f"#### Tabella trovata in: *{source.get('paper_id')}*")
                    
                    # Caption
                    caption = source.get('caption', 'No caption')
                    st.markdown(f"<div class='caption-highlight'>{caption}</div>", unsafe_allow_html=True)
                    
                    # Body
                    body_content = source.get('body', '')
                    # Try to see if it looks like a CSV or simple text. 
                    # Often it's unstructured text from scraping <table> text.
                    # If we had structured CSV, we'd use pd.DataFrame. 
                    # For now, scraping usually gives text.
                    with st.expander("Visualizza Contenuto Tabella", expanded=True):
                        st.code(body_content, language="text")
                    
                    # Context & Mentions
                    c_ment, c_cont = st.columns(2)
                    with c_ment:
                        with st.expander(f"Citations ({len(source.get('mentions', []))})"):
                            for m in source.get('mentions', []):
                                st.markdown(f"- {m}")
                    with c_cont:
                        with st.expander(f"Semantic Context ({len(source.get('context_paragraphs', []))})"):
                            for c in source.get('context_paragraphs', []):
                                st.markdown(f"> {c}")

                # --- VISTA FIGURES ---
                elif search_target == "Figures":
                    fc1, fc2 = st.columns([1, 2])
                    
                    with fc1:
                        url = source.get("url")
                        if url:
                            # If local path or relative, might need fix. ArXiv scraper puts absolute URL?
                            # Scraper put "https://arxiv.org/html/..." images usually are relative "../image.png" or full.
                            # Scraper logic: img.get('src').
                            # If it's relative, we need base URL.
                            # Let's try to display it. If it fails, st.image handles it gracefully usually.
                            
                            # Fix relative URLs from scraper if needed (heuristic)
                            # If src starts with x, and html_url is .../paper_id
                            # But we don't have base url easily here.
                            # Assuming scraper got full src or it works.
                            try:
                                st.image(url, caption="Figure Preview", use_container_width=True)
                            except:
                                st.warning("Image could not be loaded")
                        else:
                            st.text("No Image URL")

                    with fc2:
                        st.subheader(f"Figure ID: {source.get('figure_id')}")
                        st.markdown(f"**Source Paper:** {source.get('paper_id')}")
                        st.markdown(f"<div class='caption-highlight'>{source.get('caption', '')}</div>", unsafe_allow_html=True)
                        
                        with st.expander("Dove viene citata?"):
                            if source.get('mentions'):
                                for m in source.get('mentions'):
                                    st.markdown(f"- {m}")
                            else:
                                st.info("Nessuna citazione esplicita trovata nel testo.")

                st.markdown('</div>', unsafe_allow_html=True)


# --- FOOTER ---
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #94a3b8; font-size: 0.8rem;'>
        Engineered for <strong>Data Engineering HW5</strong> | Powered by Elasticsearch & Streamlit
    </div>
    """,
    unsafe_allow_html=True
)
