import os
from bs4 import BeautifulSoup
import re
import json

class Extractor:
    def __init__(self):
        # Basic stop words list (Italian + English common scientific terms)
        self.stop_words = set([
            "the", "a", "an", "in", "on", "at", "for", "to", "of", "and", "or", "is", "are", "was", "were", 
            "be", "been", "this", "that", "these", "those", "it", "we", "can", "as", "by", "from", "with",
            "il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "di", "a", "da", "in", "con", "su", "per", "tra", "fra"
        ])
    
    def extract_keywords(self, text):
        if not text:
            return set()
        # Clean and tokenize
        text = re.sub(r'[^\w\s]', '', text.lower())
        tokens = text.split()
        keywords = {t for t in tokens if t not in self.stop_words and len(t) > 2}
        return keywords

    def process_file(self, filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        paper_id = os.path.basename(filepath).replace('.html', '')
        
        # 1. Extract Paper Text (Cleaned)
        # We try to remove navs, footers, etc if possible, but simplest is get text from 'ltx_document' or body
        article_body = soup.find('article', class_='ltx_document') or soup.body
        full_text = article_body.get_text(separator=' ', strip=True) if article_body else soup.get_text(separator=' ', strip=True)
        
        # Paragraphs for context search
        paragraphs = [p for p in soup.find_all('p')]
        
        tables = []
        figures = []
        
        # 2. Extract Tables
        # LaTeXML usually uses look for table/figure wrappers
        # Use find_all recursive=True
        
        # Tables
        html_tables = soup.find_all('table', class_='ltx_table') or soup.find_all('table')
        
        for i, tbl in enumerate(html_tables):
            # Try to find the wrapper figure/table element if exists to get caption
            # Often <figure class="ltx_table"><table>...</table><figcaption>...</figcaption></figure>
            parent = tbl.find_parent('figure')
            caption_text = ""
            table_id = f"tab_{i}"
            
            if parent:
                if parent.get('id'):
                    table_id = parent.get('id')
                caption = parent.find('figcaption')
                if caption:
                    caption_text = caption.get_text(strip=True)
            
            # If no parent figure, look for caption inside
            if not caption_text:
                cap = tbl.find('caption')
                if cap:
                    caption_text = cap.get_text(strip=True)
            
            # Table Body
            body_text = tbl.get_text(separator=' ', strip=True)
            
            # Mentions (look for links href="#table_id" or text "Table X")
            mentions = []
            context_paragraphs = []
            
            keywords = self.extract_keywords(caption_text)
            
            for p in paragraphs:
                p_text = p.get_text(strip=True)
                
                # Check for explicit mentions via ID
                # check if p contains <a href="#table_id">
                links = p.find_all('a', href=True)
                is_mentioned = False
                for link in links:
                    if link['href'].endswith(f"#{table_id}"):
                        is_mentioned = True
                        break
                
                # Check for textual mentions (heuristic)
                # e.g. "Table 1" if table_id is S1.T1 or similar often displayed as Table 1
                # This is tricky without knowing the exact display number.
                # However, LaTeXML usually puts the number in the caption.
                # Let's rely on ID link first.
                
                # Textual match of caption keywords
                p_keywords = self.extract_keywords(p_text)
                intersection = keywords.intersection(p_keywords)
                
                if is_mentioned:
                    mentions.append(p_text)
                
                # Context: containing frequent terms from table/caption
                # Heuristic: if intersection is significant (e.g. > 2 words or > 20% of keywords)
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

        # 3. Extract Figures
        html_figures = soup.find_all('figure', class_='ltx_figure')
        
        for i, fig in enumerate(html_figures):
            fig_id = fig.get('id', f"fig_{i}")
            
            # Image URL
            img = fig.find('img')
            img_url = img.get('src') if img else ""
            
            # Caption
            caption = fig.find('figcaption')
            caption_text = caption.get_text(strip=True) if caption else ""
            
            mentions = []
            context_paragraphs = [] # Figure context is "paragrafi che la citano" and "paragrafi che citano termini nella caption"
            
            keywords = self.extract_keywords(caption_text)
            
            for p in paragraphs:
                p_text = p.get_text(strip=True)
                
                # Mentions
                links = p.find_all('a', href=True)
                is_mentioned = False
                for link in links:
                    if link['href'].endswith(f"#{fig_id}"):
                        is_mentioned = True
                        break
                
                if is_mentioned:
                    mentions.append(p_text)
                    
                # Context (terms from caption)
                p_keywords = self.extract_keywords(p_text)
                intersection = keywords.intersection(p_keywords)
                
                if len(intersection) >= 2:
                    # User said "paragrafi che la citano" AND "paragrafi che citano termini..."
                    # I will put both in context list or separates?
                    # User Requirement 5: "estrarre ... i paragrafi che la citano, i paragrafi che citano termini..."
                    # I'll store them. The user wants "Context Data".
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
    # Test on a file
    import sys
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'html_arxiv')
    files = [f for f in os.listdir(base_dir) if f.endswith('.html')]
    if files:
        ext = Extractor()
        res = ext.process_file(os.path.join(base_dir, files[0]))
        print(json.dumps(res, indent=2, ensure_ascii=False)[:2000] + "...")
