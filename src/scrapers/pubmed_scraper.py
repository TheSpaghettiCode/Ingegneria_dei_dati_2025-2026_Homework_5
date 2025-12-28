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

def scrape_pubmed(query="cancer risk AND coffee consumption", max_results=500):
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
            
            # Authors
            authors = []
            contrib_group = soup.find("contrib-group")
            if contrib_group:
                for contrib in contrib_group.find_all("contrib", {"contrib-type": "author"}):
                    name = contrib.find("name")
                    if name:
                        surname = name.find("surname")
                        given = name.find("given-names")
                        full_name = f"{given.get_text(strip=True) if given else ''} {surname.get_text(strip=True) if surname else ''}".strip()
                        if full_name:
                            authors.append(full_name)
            
            # Abstract
            abstract_tag = soup.find("abstract")
            abstract = abstract_tag.get_text(separator=' ', strip=True) if abstract_tag else ""
            
            # Pub Date
            pub_date = soup.find("pub-date", {"pub-type": "epub"}) or soup.find("pub-date", {"pub-type": "pmc-release"})
            date_str = ""
            if pub_date:
                year = pub_date.find("year")
                year_str = year.get_text(strip=True) if year else ""
                month = pub_date.find("month")
                month_str = month.get_text(strip=True) if month else "01"
                day = pub_date.find("day")
                day_str = day.get_text(strip=True) if day else "01"
                if year_str:
                    date_str = f"{year_str}-{month_str.zfill(2)}-{day_str.zfill(2)}"

            metadata = {
                "id": pmc_id,
                "title": title,
                "authors": authors,
                "published": date_str,
                "abstract": abstract,
                "html_url": f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/",
                "source": "pubmed"
            }
            
            meta_filepath = os.path.join(DATA_DIR_PM, f"{pmc_id}_meta.json")
            with open(meta_filepath, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=4)
            
            print(f"  -> Downloaded XML.")
            count += 1
            
            # Politeness sleep
            time.sleep(0.34) 
                
        except Exception as e:
            print(f"  -> Error: {e}")
            
    print(f"Total downloaded: {count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", type=str, default="cancer risk AND coffee consumption", help="Query")
    parser.add_argument("--max", type=int, default=500, help="Max results")
    args = parser.parse_args()
    
    scrape_pubmed(query=args.query, max_results=args.max)
