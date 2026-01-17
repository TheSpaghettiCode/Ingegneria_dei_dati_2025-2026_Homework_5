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

        # -------------------- AGGIUNTIVO ----------------------------
        # Caricare metadati extra (abstract) dal JSON


        # ------------------------------------------------------------
        
        if paper_id.startswith("PMC") or filepath.endswith('.xml'):
            return self._process_pubmed(soup, paper_id)
        else:
            return self._process_arxiv(soup, paper_id)

    def _process_arxiv(self, soup, paper_id):

        # ----------- AGGIUNTIVO ---------------------
        # Estrazione Titolo HTML standard
        h1 = soup.find("h1", class_="title")
        title_text = h1.get_text(strip=True).replace("Title:", "").strip() if h1 else soup.title.get_text(strip=True)

        #Estrazione abstract
        abstract_text = ""
        abstract_node = soup.find('div', class_='ltx_abstract') or soup.find(class_='abstract')
        if abstract_node:
            title_node = abstract_node.find(['h6', 'h1', 'h2', 'strong'], string=re.compile(r'Abstract', re.I))
            if title_node: 
                title_node.decompose() # serve a togliere la parola abstract all'inizio
            abstract_text = abstract_node.get_text(separator=' ', strip=True)

        # --------------------------------------------



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
            table_id = f"tab_{i}"
            # Try to find the wrapper figure element which usually contains the caption details
            parent = tbl.find_parent('figure')
            caption_text = ""
            
            # ID di default se non ne troviamo altri
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
            body_text = tbl.get_text(separator=' | ', strip=True) if tbl else ""
            
             
            tables.append({
                "table_id": table_id,
                "caption": caption_text,
                "body": body_text,
                "html": str(tbl),
                "mentions": [], # Filled later
                "context_paragraphs": [] # Filled later
            })

         # --- 3. Extract Figures ---
        # --- Dentro _process_arxiv, sezione Figure ---
        
        html_figures = soup.find_all('figure')
        
        for i, fig in enumerate(html_figures):
            fig_id = fig.get('id', f"fig_{i}")
            caption = fig.find('figcaption')
            caption_text = caption.get_text(strip=True) if caption else ""
            
            img_tag = fig.find('img')
            img_url = ""
            
            if img_tag and img_tag.get('src'):
                src = img_tag.get('src')
                # CORREZIONE: Se l'URL è relativo (non inizia con http), aggiungiamo il dominio
                if src.startswith('http'):
                    img_url = src
                else:
                    # Costruiamo l'URL assoluto basato sull'ID del paper
                    # Nota: Funziona solo se stai usando arxiv.org/html/ID
                    img_url = f"https://arxiv.org/html/{paper_id}/{src}"

            figures.append({
                "figure_id": fig_id,
                "url": img_url,
                "caption": caption_text,
                "mentions": [],
                "context_paragraphs": []
            })

       

        # ------- AGGIUNTIVO ----------
        # ho aggiunto title_text e abstract_text    
        return self._post_process_context(paper_id, title_text, full_text, abstract_text, tables, figures, paragraphs)

    def xml_table_to_html(self, xml_table_soup):
        """
        Converte una tabella XML (stile JATS/PubMed) in HTML standard per il browser.
        Trasforma <row> -> <tr>, <entry> -> <td>, ecc.
        """
        if not xml_table_soup:
            return ""

        # Creiamo una copia per non modificare l'oggetto originale mentre lo leggiamo
        import copy
        new_tbl = copy.copy(xml_table_soup)
        
        # Rinomina i tag XML in tag HTML
        for tag in new_tbl.find_all(True): # Trova tutti i tag ricorsivamente
            if tag.name == 'row':
                tag.name = 'tr'
            elif tag.name == 'entry':
                tag.name = 'td'
                # A volte <entry> ha attributi strani, meglio pulirli se danno fastidio
                # ma per ora manteniamo gli attributi base
            elif tag.name == 'thead':
                tag.name = 'thead' # Spesso uguale
            elif tag.name == 'tbody':
                tag.name = 'tbody' # Spesso uguale
        
        # Rimuove namespace fastidiosi (es: <oasis:table> diventa <table>)
        new_tbl.name = 'table' 
        # Aggiungi classe per stile CSS
        new_tbl['class'] = 'generated-table'
        
        return str(new_tbl)

    def _process_pubmed(self, soup, paper_id):
    
        # ------------ CORREZIONE: ESTRAZIONE ID ----------
        # PubMed memorizza gli ID in <article-id pub-id-type="...">
        # Tipi comuni: 'pmc', 'pmid', 'doi'
        # Cerchiamo di recuperare il vero ID dall'XML se paper_id è vuoto o generico
        
        found_id = None
        article_ids = soup.find_all('article-id')
        
        ids_data = {} # Dizionario per tenere traccia di tutti gli ID trovati
        
        for aid in article_ids:
            id_type = aid.get('pub-id-type')
            id_val = aid.get_text(strip=True)
            ids_data[id_type] = id_val
            
            # Priorità: Se troviamo il PMCID, usiamo quello come paper_id principale
            # (Nota: l'XML di solito contiene solo il numero, es: 12345. 
            # A volte serve il prefisso 'PMC', dipende dalla tua logica di indicizzazione)
            if id_type == 'pmc':
                found_id = id_val

        # Se abbiamo trovato un ID nell'XML, usiamolo. 
        # Altrimenti teniamo quello passato come argomento (se esiste), o mettiamo un fallback.
        if found_id:
            paper_id = found_id
        elif not paper_id or paper_id == "N\\A":
            # Fallback su PMID o DOI se PMC non c'è
            paper_id = ids_data.get('pmid', ids_data.get('doi', "UNKNOWN_ID"))
        
        # -------------------------------------------------
        # Pulizia ID per URL (Rimuove 'PMC' se presente per evitare duplicati dopo)
        # Es: se paper_id è "PMC12345" diventa "12345". Se è "12345" resta "12345".
        clean_pmc_id = paper_id.replace("PMC", "") if paper_id else ""

        # ------------ AGGIUNTIVO ----------
        # Estrazione titolo
        article_title = soup.find("article-title")
        title_text = article_title.get_text(strip=True) if article_title else "No title"

        # Estrazione abstract
        abstract_text = ""
        abstract_node = soup.find('abstract')
        if abstract_node:
            # Rimuoviamo il titolo "Abstract" che a volte è presente nel nodo
            title = abstract_node.find('title')
            if title: title.decompose()
            abstract_text = abstract_node.get_text(separator=' ', strip=True)
        # -----------------------------------

        full_text = soup.get_text(separator=' ', strip=True)
        paragraphs = [p for p in soup.find_all('p')]
        
        tables = []
        figures = []
        
        # 2. Extract Tables (XML: <table-wrap>)
        table_wraps = soup.find_all('table-wrap')
        for i, wrap in enumerate(table_wraps):
            table_id = wrap.get('id', f"tab_{i}")
            
            caption = wrap.find('caption')
            caption_text = caption.get_text(strip=True) if caption else ""
            
            tbl = wrap.find('table')

            if not tbl:
                tbl = wrap.find(lambda tag: tag.name and 'table' in tag.name)

            
            # A. BODY: Testo per la ricerca
            body_text = tbl.get_text(separator=' | ', strip=True)
            
            # B. HTML: CONVERSIONE OBBLIGATORIA
            # Usiamo la funzione helper per trasformare XML -> HTML
            html_content = self.xml_table_to_html(tbl)
            
            # DEBUG PRINT (Fallo apparire nel terminale mentre indicizzi!)
            print(f"DEBUG TABLE {table_id}: Body Len={len(body_text)}, HTML Len={len(html_content)}")
                

            tables.append({
                "table_id": table_id,
                "caption": caption_text,
                "body": body_text,
                "html": str(tbl) if tbl else "",
                "mentions": [],
                "context_paragraphs": []
            })
            
        # 3. Extract Figures (XML: <fig>)
        # --- Dentro _process_pubmed, sezione Figure ---
        fig_wraps = soup.find_all('fig')
        for i, wrap in enumerate(fig_wraps):
            fig_id = wrap.get('id', f"fig_{i}")
            
            caption = wrap.find('caption')
            caption_text = caption.get_text(strip=True) if caption else ""
            
            graphic = wrap.find('graphic')
            img_href = graphic.get('xlink:href') if graphic else ""
            
            img_url = ""
            if img_href and clean_pmc_id and clean_pmc_id != "UNKNOWN_ID":
                # CORREZIONE: A volte l'href contiene già l'estensione, a volte no.
                if ".jpg" in img_href or ".png" in img_href or ".gif" in img_href:
                    base_href = img_href
                else:
                    # Defaultiamo a .jpg che è il più comune su PMC
                    base_href = f"{img_href}.jpg"
                
                img_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{clean_pmc_id}/bin/{base_href}"
            
            figures.append({
                "figure_id": fig_id,
                "url": img_url,
                "caption": caption_text,
                "mentions": [],
                "context_paragraphs": []
            })

        # Passiamo anche ids_data se vuoi salvare DOI/PMID separatamente nel post_process
        return self._post_process_context(paper_id, title_text, full_text, abstract_text, tables, figures, paragraphs)
    
    
    
    # ------- AGGIUNTIVO ----------
    # ho aggiunto title_text e abstract_text 
    def _post_process_context(self, paper_id, title_text, full_text, abstract_text, tables, figures, paragraphs):
        # Common logic for Mentions and Context
        
        # Helper to process list (modify in place)
        for item in tables:
            self._fill_context(item, paragraphs, is_table=True)
            
        for item in figures:
            self._fill_context(item, paragraphs, is_table=False)

        # ------- AGGIUNTIVO ----------
        # ho aggiunto title_text e abstract_text 
        return {
            "paper_id": paper_id,
            "title": title_text,
            "abstract": abstract_text,
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
            is_mentioned = False
            
            # --- 1. Controllo XML (PubMed/PMC) ---
            # PubMed usa <xref ref-type="fig" rid="fig1">
            xrefs = p.find_all('xref')
            for xref in xrefs:
                rid = xref.get('rid')
                if rid == item_id:
                    is_mentioned = True
                    break
            
            # --- 2. Controllo HTML standard (ArXiv) ---
            # Se non trovato come xref, cerchiamo come link standard
            if not is_mentioned:
                links = p.find_all('a', href=True)
                for link in links:
                    href = link['href']
                    # Puliamo l'href da # iniziale (es. "#fig1" -> "fig1")
                    clean_href = href.lstrip('#')
                    if clean_href == item_id:
                        is_mentioned = True
                        break
            
            if is_mentioned:
                mentions.append(p_text)
            
            # B. Semantic Context
            p_keywords = self.extract_keywords(p_text)
            intersection = keywords.intersection(p_keywords)
            
            # Soglia di intersezione (puoi alzarla a 3 se trovi troppi falsi positivi)
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
