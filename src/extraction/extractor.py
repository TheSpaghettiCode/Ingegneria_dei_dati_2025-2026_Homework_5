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
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        paper_id = os.path.basename(filepath).replace('.html', '')
        
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
            
            # --- Extract Mentions and Context ---
            mentions = []
            context_paragraphs = []
            
            # Get keywords from caption to find semantic context
            keywords = self.extract_keywords(caption_text)
            
            for p in paragraphs:
                p_text = p.get_text(strip=True)
                
                # A. Explicit Mentions: Check for <a href="#table_id"> links
                links = p.find_all('a', href=True)
                is_mentioned = False
                for link in links:
                    if link['href'].endswith(f"#{table_id}"):
                        is_mentioned = True
                        break
                
                if is_mentioned:
                    mentions.append(p_text)
                
                # B. Semantic Context: Check for keyword intersection
                # If paragraph contains significant number of keywords from caption (>= 2)
                p_keywords = self.extract_keywords(p_text)
                intersection = keywords.intersection(p_keywords)
                
                if len(intersection) >= 2:
                    context_paragraphs.append(p_text)
            
            tables.append({
                "table_id": table_id,
                "caption": caption_text,
                "body": body_text,
                "html": str(tbl),
                "mentions": mentions,
                "context_paragraphs": context_paragraphs
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
            
            mentions = []
            context_paragraphs = []
            
            keywords = self.extract_keywords(caption_text)
            
            for p in paragraphs:
                p_text = p.get_text(strip=True)
                
                # A. Explicit Mentions by ID
                links = p.find_all('a', href=True)
                is_mentioned = False
                for link in links:
                    if link['href'].endswith(f"#{fig_id}"):
                        is_mentioned = True
                        break
                
                if is_mentioned:
                    mentions.append(p_text)
                    
                # B. Semantic Context (Terms from Caption)
                p_keywords = self.extract_keywords(p_text)
                intersection = keywords.intersection(p_keywords)
                
                if len(intersection) >= 2:
                    context_paragraphs.append(p_text)
            
            figures.append({
                "figure_id": fig_id,
                "url": img_url,
                "caption": caption_text,
                "mentions": mentions,
                "context_paragraphs": context_paragraphs
            })

        return {
            "paper_id": paper_id,
            "full_text": full_text,
            "tables": tables,
            "figures": figures
        }

if __name__ == "__main__":
    # Test execution block
    import sys
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'html_arxiv')
    files = [f for f in os.listdir(base_dir) if f.endswith('.html')]
    if files:
        ext = Extractor()
        res = ext.process_file(os.path.join(base_dir, files[0]))
        print(json.dumps(res, indent=2, ensure_ascii=False)[:2000] + "...")
