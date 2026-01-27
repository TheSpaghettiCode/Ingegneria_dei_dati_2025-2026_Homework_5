import os
import time
import json
import requests
import argparse
from Bio import Entrez
from bs4 import BeautifulSoup

# Define Directories
DATA_DIR_PM = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'html_pubmed')
os.makedirs(DATA_DIR_PM, exist_ok=True)

# Respectful Identify
Entrez.email = "student@university.edu" 
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.ncbi.nlm.nih.gov/",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}
# Mappa per convertire mesi testuali in numeri (comune nell'XML)
MONTH_MAP = {
    "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04", "May": "05", "Jun": "06",
    "Jul": "07", "Aug": "08", "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12",
    "January": "01", "February": "02", "March": "03", "April": "04", "June": "06",
    "July": "07", "August": "08", "September": "09", "October": "10", "November": "11", "December": "12"
}





def scrape_pubmed(query="ultra-processed foods AND cardiovascular risk", max_results=500):
    print(f"Searching PubMed (PMC) for: '{query}'...")
    
    # 1. Search in PMC (PubMed Central) for Open Access articles
    # Filter: "open access"[filter] ensures we can likely get the full text
    full_query = f"{query} AND open access[filter]"
    
    try:
        handle = Entrez.esearch(db="pmc", term=full_query, retmax=max_results, sort="relevance")
        record = Entrez.read(handle)
        handle.close()
    except Exception as e:
        print(f"Error during Entrez Search: {e}")
        return

    id_list = record["IdList"]
    print(f"Found {len(id_list)} articles.")

    count = 0
    for pmc_id_raw in id_list:
        # PMC IDs in search result usually are just numbers "12345", but URLs need "PMC12345"
        pmc_id = f"PMC{pmc_id_raw}" if not pmc_id_raw.startswith("PMC") else pmc_id_raw
        
        # Check if already exists (XML or HTML)
        filename = f"{pmc_id}.xml"
        filepath = os.path.join(DATA_DIR_PM, filename)
        if os.path.exists(filepath):
            print(f"  -> Already exists. Skipping.")
            count += 1
            continue

        try:
            # 2. Download XML using Entrez API
            # This is the official way and avoids 403 on HTML pages
            handle = Entrez.efetch(db="pmc", id=pmc_id, rettype="full", retmode="xml")
            xml_content = handle.read()
            handle.close()
            
            # Save XML
            with open(filepath, "wb") as f: # efetch returns bytes sometimes or string
                if isinstance(xml_content, str):
                    f.write(xml_content.encode('utf-8'))
                else:
                    f.write(xml_content)
            
            # 3. Extract Basic Metadata
            # We parse the XML to get metadata
            soup = BeautifulSoup(xml_content, "xml")
            
            # Title
            title_tag = soup.find("article-title")
            title = title_tag.get_text(strip=True) if title_tag else f"Unknown Title ({pmc_id})"
            
                       
            # 2. AUTORI
            # Cerca nel gruppo dei contributori, filtrando solo gli autori
            authors = []
            contrib_group = soup.find("contrib-group")
            if contrib_group:
                for contrib in contrib_group.find_all("contrib", {"contrib-type": "author"}):
                    name_tag = contrib.find("name")
                    if name_tag:
                        surname = name_tag.find("surname")
                        given = name_tag.find("given-names")
                        
                        s_txt = surname.get_text(strip=True) if surname else ""
                        g_txt = given.get_text(strip=True) if given else ""
                        
                        full_name = f"{g_txt} {s_txt}".strip()
                        if full_name:
                            authors.append(full_name)
            
            # Abstract
            abstract_tag = soup.find("abstract")
            abstract = abstract_tag.get_text(separator=' ', strip=True) if abstract_tag else ""
            
            # 3. DATA (Logica avanzata)
            # PubMed XML ha vari tipi di date. Le proviamo in ordine di preferenza.
            # epub = data pubblicazione online (solitamente la più precisa)
            # ppub = data pubblicazione cartacea
            # pmc-release = data ingresso in archivio
            pub_date = soup.find("pub-date", {"pub-type": "epub"}) or \
                    soup.find("pub-date", {"pub-type": "ppub"}) or \
                    soup.find("pub-date", {"pub-type": "pmc-release"})
            date_str = ""
            if pub_date:
                year_tag = pub_date.find("year")
                if year_tag:
                    year = year_tag.get_text(strip=True)
                    
                    # Gestione Mese (Numero o Testo)
                    month_tag = pub_date.find("month")
                    month = "01" # Default Gennaio
                    if month_tag:
                        m_text = month_tag.get_text(strip=True)
                        # Se è numero ("10") lo usa, se è testo ("Oct") usa la mappa
                        if m_text.isdigit():
                            month = m_text.zfill(2)
                        else:
                            month = MONTH_MAP.get(m_text, "01")
                    
                    # Gestione Giorno
                    day_tag = pub_date.find("day")
                    day = day_tag.get_text(strip=True).zfill(2) if day_tag else "01"
                    
                    # Costruiamo la data ISO 8601
                    date_str = f"{year}-{month}-{day}"



            metadata = {
                "id": pmc_id,
                "title": title,
                "authors": authors,
                "date": date_str,
                "abstract": abstract,
                "html_url": f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/",
                "source": "pubmed"
            }
            
            meta_filepath = os.path.join(DATA_DIR_PM, f"{pmc_id}_meta.json")
            with open(meta_filepath, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=4)
            
            d_print = date_str if date_str else "NO DATE"
            print(f"  -> Downloaded XML. Date: {d_print}")
            count += 1
            
            # Politeness sleep
            time.sleep(0.34) 
                
        except Exception as e:
            print(f"  -> Error: {e}")
            
    print(f"Total downloaded: {count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", type=str, default="ultra-processed foods AND cardiovascular risk", help="Query")
    parser.add_argument("--max", type=int, default=500, help="Max results")
    args = parser.parse_args()
    
    scrape_pubmed(query=args.query, max_results=args.max)
