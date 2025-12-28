# Sviluppo di un Sistema Avanzato di Ricerca su Articoli Scientifici

## Descrizione del Progetto
Questo progetto implementa un motore di ricerca avanzato per articoli scientifici (nello specifico da [arXiv](https://arxiv.org)), trattando non solo il testo degli articoli, ma anche **Tabelle** e **Figure** come oggetti di "prima classe". Questo significa che è possibile cercare specificamente all'interno delle tabelle (didascalie, contenuto) e delle figure (didascalie), oltre alla classica ricerca full-text sugli articoli.

Il sistema è stato progettato per il corso di Ingegneria dei Dati 2025-2026 (Homework 5).

## Funzionalità Principali
1.  **Corpus Creation (Multi-Source)**:
    *   **ArXiv**: Script per scaricare articoli HTML/XML (query: "speech to text").
    *   **PubMed Central (PMC)**: Script per scaricare articoli Open Access (XML) (query: "cancer risk AND coffee consumption").
2.  **Estrazione Dati**: Parsing avanzato di HTML e XML per estrarre:
    *   **Articoli**: Metadati (titolo, autori, data, abstract) e testo completo.
    *   **Tabelle**: Didascalia, contenuto (body), ID, paragrafi che citano la tabella, e paragrafi di contesto.
    *   **Figure**: Didascalia, URL immagine, ID, menzioni e contesto.
3.  **Indicizzazione**: Utilizzo di **Elasticsearch** per indicizzare tre tipologie di documenti (`articles`, `tables`, `figures`) con campo `source` (arxiv o pubmed).
4.  **Interfaccia di Ricerca**:
    *   **Web UI**: Dashboard avanzata con filtri per collezione (Paper, Table, Figure) e **Sorgente** (All, ArXiv, PubMed).

## Struttura del Progetto

```text
Ingegneria_dei_dati_2025-2026_Homework_5/
├── data/                       # Dati scaricati e processati
│   ├── html_arxiv/             # Corpus ArXiv
│   └── html_pubmed/            # Corpus PubMed (XML)
├── src/                        # Codice sorgente
│   ├── scrapers/
│   │   ├── arxiv_scraper.py    # Scraper ArXiv
│   │   └── pubmed_scraper.py   # Scraper PubMed (BioPython)
│   ├── extraction/
│   │   └── extractor.py        # Logica di estrazione (HTML + XML)
│   ├── indexing/
│   │   ├── index_manager.py    # Mappings Elasticsearch
│   │   └── indexer.py          # Script di indicizzazione massiva
│   ├── search/
│   │   ├── search_engine.py    # Wrapper Elasticsearch
│   │   └── app.py              # Backend applicazione Web (Flask)
│   └── ui/
│       ├── templates/          # Template HTML
│       └── static/             # File statici
├── docker-compose.yml          # Configurazione Elasticsearch
├── requirements.txt            # Dipendenze Python
├── .gitignore                  # File ignorati
└── README.md                   # Documentazione
```

## Requisiti e Installazione

### Prerequisiti
*   Python 3.8 o superiore
*   Docker (opzionale) o Elasticsearch locale.

### Setup
1.  **Installazione Dipendenze**:
    ```bash
    pip install -r requirements.txt
    ```
    *Include `biopython`, `arxiv`, `elasticsearch`, `flask`, `beautifulsoup4`, ecc.*

2.  **Avvia Elasticsearch**:
    ```bash
    docker-compose up -d
    ```
    *Oppure avvia l'istanza locale su `localhost:9200`.*

## Come Eseguire il Sistema

### 1. Creazione del Corpus
**ArXiv**:
```bash
python src/scrapers/arxiv_scraper.py
```
**PubMed**:
```bash
python src/scrapers/pubmed_scraper.py --max 500
```
*I file verranno salvati rispettivamente in `data/html_arxiv` e `data/html_pubmed`.*

### 2. Indicizzazione
Processa entrambi i corpus ed inviali a Elasticsearch.
```bash
python src/indexing/indexer.py
```

### 3. Ricerca (Web UI)
Avvia la dashboard Flask:
```bash
python src/search/app.py
```
Apri il browser all'indirizzo: **http://127.0.0.1:5000**

*   Potrai filtrare i risultati per **Source** (ArXiv/PubMed) e tipo di oggetto (Paper, Table, Figure).

### Dettagli Implementativi
*   **PubMed Integration**: Utilizza `Bio.Entrez` per scaricare XML full-text. L'`extractor.py` seleziona automaticamente il parser (`xml` vs `html.parser`) in base all'estensione del file.
*   **Context Extraction**: Algoritmo ibrido basato su link espliciti (`<a href...`) e keyword matching nei paragrafi adiacenti.

