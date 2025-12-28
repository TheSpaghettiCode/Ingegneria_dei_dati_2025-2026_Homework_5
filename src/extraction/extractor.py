import os
from bs4 import BeautifulSoup
import re
import json

class Extractor:
    """
    Class responsible for parsing HTML content of scientific papers to extract:
    1. Full Text and Metadata
    2. Tables (Caption, Body, Mentions, Context)
    3. Figures (URL, Caption, Mentions, Context)
    
    It uses BeautifulSoup for DOM traversal and regular expressions/heuristics 
    for context extraction.
    """
    
    def __init__(self):
        # Basic stop words list (Italian + English common scientific terms) used for keyword extraction
        self.stop_words = set([
            "the", "a", "an", "in", "on", "at", "for", "to", "of", "and", "or", "is", "are", "was", "were", 
            "be", "been", "this", "that", "these", "those", "it", "we", "can", "as", "by", "from", "with",
            "il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "di", "a", "da", "in", "con", "su", "per", "tra", "fra"
        ])
    
    def extract_keywords(self, text):
        """
        Extract meaningful keywords from a given text string.
        Removes punctuation, converts to lowercase, and filters out stop words.
        
        Args:
            text (str): Input text.
            
        Returns:
            set: A set of keywords.
        """
        if not text:
            return set()
        # Clean and tokenize: remove non-alphanumeric char
        text = re.sub(r'[^\w\s]', '', text.lower())
        tokens = text.split()
        keywords = {t for t in tokens if t not in self.stop_words and len(t) > 2}
        return keywords

    def process_file(self, filepath):
        """
        Main method to process a single HTML file.
        
        Args:
            filepath (str): Path to the HTML file.
            
        Returns:
            dict: Structured dictionary containing paper_id, full_text, tables, and figures.
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if filepath.endswith('.xml'):
            soup = BeautifulSoup(content, 'xml')
        else:
            soup = BeautifulSoup(content, 'html.parser')

        paper_id = os.path.basename(filepath).replace('.html', '').replace('.xml', '')
        
        if paper_id.startswith("PMC") or filepath.endswith('.xml'):
            return self._process_pubmed(soup, paper_id)
        else:
            return self._process_arxiv(soup, paper_id)

    def _process_arxiv(self, soup, paper_id):
        # --- 1. Extract Paper Text (Cleaned) ---
        # We target 'ltx_document' which is specific to LaTeXML output (ArXiv HTML format)
        article_body = soup.find('article', class_='ltx_document') or soup.body
        full_text = article_body.get_text(separator=' ', strip=True) if article_body else soup.get_text(separator=' ', strip=True)
        
        # Extract all paragraphs to search for mentions/context later
        paragraphs = [p for p in soup.find_all('p')]
        
        tables = []
        figures = []
        
        # --- 2. Extract Tables ---
        # ArXiv HTML tables are often wrapped in <figure class="ltx_table"> or just <table class="ltx_table">
        html_tables = soup.find_all('table', class_='ltx_table') or soup.find_all('table')
        
        for i, tbl in enumerate(html_tables):
            # Try to find the wrapper figure element which usually contains the caption details
            parent = tbl.find_parent('figure')
            caption_text = ""
            table_id = f"tab_{i}"
            
            # Extract Table ID and Caption from parent figure if available
            if parent:
                if parent.get('id'):
                    table_id = parent.get('id')
                caption = parent.find('figcaption')
                if caption:
                    caption_text = caption.get_text(strip=True)
            
            # Fallback: look for caption inside table tag
            if not caption_text:
                cap = tbl.find('caption')
                if cap:
                    caption_text = cap.get_text(strip=True)
            
            # Extract Table Body Text (cell contents) as a single string
            body_text = tbl.get_text(separator=' ', strip=True)
            
            tables.append({
                "table_id": table_id,
                "caption": caption_text,
                "body": body_text,
                "html": str(tbl),
                "mentions": [], # Filled later
                "context_paragraphs": [] # Filled later
            })

        # --- 3. Extract Figures ---
        # Figures are identified by <figure class="ltx_figure">
        html_figures = soup.find_all('figure', class_='ltx_figure')
        
        for i, fig in enumerate(html_figures):
            fig_id = fig.get('id', f"fig_{i}")
            
            # Extract Image URL (src attribute)
            img = fig.find('img')
            img_url = img.get('src') if img else ""
            
            # Extract Caption
            caption = fig.find('figcaption')
            caption_text = caption.get_text(strip=True) if caption else ""
            
            figures.append({
                "figure_id": fig_id,
                "url": img_url,
                "caption": caption_text,
                "mentions": [],
                "context_paragraphs": []
            })
            
        return self._post_process_context(paper_id, full_text, tables, figures, paragraphs)

    def _process_pubmed(self, soup, paper_id):
        # PubMed Central XML structure
        # If the input was XML, soup should be initialized with 'xml' parser ideally, 
        # but 'html.parser' often handles XML tags okay-ish, or we prefer to be explicit in process_file.
        # However, since process_file uses 'html.parser' by default, we might re-parse if needed
        # or just rely on tag names which works if they are distinct.
        # Better: in process_file check extension.
        
        full_text = soup.get_text(separator=' ', strip=True)
        paragraphs = [p for p in soup.find_all('p')]
        
        tables = []
        figures = []
        
        # 2. Extract Tables (XML: <table-wrap>)
        table_wraps = soup.find_all('table-wrap')
        for i, wrap in enumerate(table_wraps):
            table_id = wrap.get('id', f"tab_{i}")
            
            # Caption
            caption = wrap.find('caption')
            caption_text = caption.get_text(strip=True) if caption else ""
            
            # Body
            tbl = wrap.find('table')
            body_text = tbl.get_text(separator=' ', strip=True) if tbl else ""
            
            tables.append({
                "table_id": table_id,
                "caption": caption_text,
                "body": body_text,
                "html": str(tbl) if tbl else "",
                "mentions": [],
                "context_paragraphs": []
            })
            
        # 3. Extract Figures (XML: <fig>)
        fig_wraps = soup.find_all('fig')
        for i, wrap in enumerate(fig_wraps):
            fig_id = wrap.get('id', f"fig_{i}")
            
            # Caption
            caption = wrap.find('caption')
            caption_text = caption.get_text(strip=True) if caption else ""
            
            # Image URL in XML: <graphic xlink:href="..."/>
            # The href is usually a local filename reference, e.g. "nihms-15000-f0001.jpg"
            # We construct a full URL if possible, or just keep the reference.
            # PMC full text URL: https://www.ncbi.nlm.nih.gov/pmc/articles/{paper_id}/bin/{href}.jpg
            # Note: The extension might vary (.jpg, .gif), but usuall 'jpg' is safe guess for web or we leave as is.
            graphic = wrap.find('graphic')
            img_href = graphic.get('xlink:href') if graphic else ""
            
            if img_href:
                img_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{paper_id}/bin/{img_href}.jpg"
            else:
                img_url = ""
            
            figures.append({
                "figure_id": fig_id,
                "url": img_url,
                "caption": caption_text,
                "mentions": [],
                "context_paragraphs": []
            })
            
        return self._post_process_context(paper_id, full_text, tables, figures, paragraphs)

    def _post_process_context(self, paper_id, full_text, tables, figures, paragraphs):
        # Common logic for Mentions and Context
        
        # Helper to process list (modify in place)
        for item in tables:
            self._fill_context(item, paragraphs, is_table=True)
            
        for item in figures:
            self._fill_context(item, paragraphs, is_table=False)

        return {
            "paper_id": paper_id,
            "full_text": full_text,
            "tables": tables,
            "figures": figures
        }

    def _fill_context(self, item, paragraphs, is_table=True):
        item_id = item.get("table_id") if is_table else item.get("figure_id")
        caption_text = item.get("caption", "")
        
        keywords = self.extract_keywords(caption_text)
        
        mentions = []
        context_paragraphs = []
        
        for p in paragraphs:
            p_text = p.get_text(strip=True)
            
            # A. Explicit Mentions
            # Check for ID in any links within paragraph
            links = p.find_all('a', href=True)
            is_mentioned = False
            for link in links:
                href = link['href']
                # ArXiv uses #id, PMC often uses #id too internally
                if href.endswith(f"#{item_id}") or href == f"#{item_id}":
                    is_mentioned = True
                    break
            
            if is_mentioned:
                mentions.append(p_text)
            
            # B. Semantic Context
            p_keywords = self.extract_keywords(p_text)
            intersection = keywords.intersection(p_keywords)
            
            if len(intersection) >= 2:
                context_paragraphs.append(p_text)
        
        item["mentions"] = mentions
        item["context_paragraphs"] = context_paragraphs

if __name__ == "__main__":
    # Test execution block
    import sys
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'html_arxiv')
    files = [f for f in os.listdir(base_dir) if f.endswith('.html')]
    if files:
        ext = Extractor()
        res = ext.process_file(os.path.join(base_dir, files[0]))
        print(json.dumps(res, indent=2, ensure_ascii=False)[:2000] + "...")
