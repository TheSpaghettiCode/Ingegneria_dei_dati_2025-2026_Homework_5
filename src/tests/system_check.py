import requests
import sys
import os
from elasticsearch import Elasticsearch

def check_elasticsearch_connection(url="http://localhost:9200"):
    print(f"--- Checking Elasticsearch Connection ({url}) ---")
    try:
        resp = requests.get(url, timeout=2)
        if resp.status_code == 200:
            print("[\u2705] Elasticsearch is reachable.")
            info = resp.json()
            print(f"    Name: {info.get('name')}")
            print(f"    Version: {info.get('version', {}).get('number')}")
            return True
        else:
            print(f"[\u274C] Elasticsearch returned status code {resp.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("[\u274C] Connection failed. Is it running?")
        return False
    except Exception as e:
        print(f"[\u274C] Error: {e}")
        return False

def check_indices(es):
    print("\n--- Checking Indices Counts ---")
    indices = ["articles", "tables", "figures"]
    all_ok = True
    for idx in indices:
        try:
            if es.indices.exists(index=idx):
                count = es.count(index=idx)['count']
                emoji = "\u2705" if count > 0 else "\u26A0\uFE0F"
                print(f"[{emoji}] Index '{idx}': {count} documents")
            else:
                print(f"[\u274C] Index '{idx}' DOES NOT EXIST.")
                all_ok = False
        except Exception as e:
            print(f"[\u274C] Error checking '{idx}': {e}")
            all_ok = False
    return all_ok

def check_image_access(paper_id="2306.12020v1", image_name="x1.png"):
    print("\n--- Checking External Image Access (ArXiv) ---")
    url = f"https://arxiv.org/html/{paper_id}/{image_name}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    print(f"Testing URL: {url}")
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            print(f"[\u2705] Image fetched successfully ({len(r.content)} bytes).")
            print("    ArXiv access is working.")
        elif r.status_code == 403:
            print("[\u26A0\uFE0F] 403 Forbidden. Note: The Dashboard uses 'referrerpolicy' to bypass this in browsers, so it might still work in UI.")
        else:
            print(f"[\u274C] Failed with status: {r.status_code}")
    except Exception as e:
        print(f"[\u274C] Exception: {e}")

def main():
    print("=== SYSTEM HEALTH CHECK ===\n")
    
    es_alive = check_elasticsearch_connection()
    
    if es_alive:
        es = Elasticsearch("http://localhost:9200")
        check_indices(es)
        
    check_image_access()
    
    print("\n=== CHECK COMPLETE ===")

if __name__ == "__main__":
    main()
