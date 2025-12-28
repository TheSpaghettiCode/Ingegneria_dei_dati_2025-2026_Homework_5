# Sviluppo di un Sistema Avanzato di Ricerca su Articoli Scientifici

## Descrizione del Progetto
Questo progetto implementa un motore di ricerca avanzato per articoli scientifici (nello specifico da [arXiv](https://arxiv.org)), trattando non solo il testo degli articoli, ma anche **Tabelle** e **Figure** come oggetti di "prima classe". Questo significa che è possibile cercare specificamente all'interno delle tabelle (didascalie, contenuto) e delle figure (didascalie), oltre alla classica ricerca full-text sugli articoli.

Il sistema è stato progettato per il corso di Ingegneria dei Dati 2025-2026 (Homework 5).

## Funzionalità Principali
1.  **Corpus Creation**: Script automatico per scaricare articoli in formato HTML da arXiv basati su query specifiche (es. "speech to text").
2.  **Estrazione Dati**: Parsing avanzato dell'HTML per estrarre:
    *   **Articoli**: Metadati (titolo, autori, data, abstract) e testo completo.
    *   **Tabelle**: Didascalia, contenuto (body), ID, paragrafi che citano la tabella, e paragrafi di contesto (keyword matching).
    *   **Figure**: Didascalia, URL immagine, ID, menzioni e contesto.
3.  **Indicizzazione**: Utilizzo di **Elasticsearch** per indicizzare tre tipologie di documenti distinti (`articles`, `tables`, `figures`).
4.  **Interfaccia di Ricerca**:
    *   **CLI (Command Line Interface)**: Per ricerche rapide da terminale.
    *   **Web UI**: Interfaccia web user-friendly basata su Flask per esplorare i risultati.

## Struttura del Progetto

```text
Ingegneria_dei_dati_2025-2026_Homework_5/
├── data/                       # Dati scaricati e processati
│   └── html_arxiv/             # File HTML grezzi e metadati JSON
├── src/                        # Codice sorgente
│   ├── scrapers/
│   │   └── arxiv_scraper.py    # Script per il download da arXiv
│   ├── extraction/
│   │   └── extractor.py        # Logica di estrazione (BeautifulSoup)
│   ├── indexing/
│   │   ├── index_manager.py    # Gestione schemi Elasticsearch
│   │   └── indexer.py          # Script di indicizzazione massiva
│   ├── search/
│   │   ├── search_engine.py    # Wrapper per query Elasticsearch
│   │   ├── cli.py              # Interfaccia a riga di comando
│   │   └── app.py              # Backend applicazione Web (Flask)
│   └── ui/
│       ├── templates/          # Template HTML per la Web UI
│       └── static/             # File statici (CSS, JS)
├── docker-compose.yml          # Configurazione per avviare Elasticsearch/Kibana
├── requirements.txt            # Dipendenze Python
├── .gitignore                  # File ignorati da Git
└── README.md                   # Documentazione
```

## Requisiti e Installazione

### Prerequisiti
*   Python 3.8 o superiore
*   Docker (opzionale, raccomandato per Elasticsearch) o un'istanza Elasticsearch locale.

### Setup
1.  **Clona il repository** (o scarica i file):
    ```bash
    git clone <repository-url>
    cd Ingegneria_dei_dati_2025-2026_Homework_5
    ```

2.  **Crea un Virtual Environment (opzionale ma consigliato)**:
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # Mac/Linux
    source venv/bin/activate
    ```

3.  **Installa le dipendenze**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Avvia Elasticsearch**:
    
    ### Opzione A: Con Docker (Consigliato)
    Se hai Docker installato, usa il file `docker-compose.yml` incluso:
    ```bash
    docker-compose up -d
    ```

    ### Opzione B: Installazione Locale (No Docker)
    Se non puoi usare Docker:
    1.  Scarica Elasticsearch (ZIP per Windows) dal sito ufficiale: [Download Elasticsearch](https://www.elastic.co/downloads/elasticsearch)
    2.  Estrai lo ZIP in una cartella (es. `C:\elasticsearch`).
    3.  Apri il terminale, vai nella cartella estratta ed esegui:
        ```cmd
        bin\elasticsearch.bat
        ```
    4.  **Nota Importante**: Dalla versione 8.0, la sicurezza è abilitata per default. Per questo progetto (sviluppo locale), potresti voler disabilitare la sicurezza per semplicità (o configurare `verify_certs=False` nel codice Python).
        *   Per disabilitare la sicurezza (SOLO LOCALE/DEV): Apri `config/elasticsearch.yml` e imposta `xpack.security.enabled: false`.

    Attendi che Elasticsearch sia attivo su `http://localhost:9200`.

## Come Eseguire il Sistema

### 1. Creazione del Corpus (Download)
Scarica gli articoli da arXiv. Di default cerca "speech to text".
```bash
python src/scrapers/arxiv_scraper.py
```
*I file verranno salvati in `data/html_arxiv`.*

### 2. Indicizzazione
Processa i file HTML scaricati ed inviali a Elasticsearch.
```bash
python src/indexing/indexer.py
```
*Questo script creerà gli indici `articles`, `tables` e `figures` se non esistono.*

### 3. Ricerca
Puoi cercare utilizzando due modalità:

**A. Riga di Comando (CLI)**
```bash
# Cerca negli articoli
python src/search/cli.py "deep learning" --index articles

# Cerca nelle tabelle (es. didascalie o contenuto)
python src/search/cli.py "accuracy result" --index tables

# Cerca figure
python src/search/cli.py "architecture" --index figures
```

**B. Interfaccia Web (Dashboard Avanzata)**
Avvia la nuova dashboard (Custom Flask):
```bash
python src/search/app.py
```
Apri il browser all'indirizzo: **http://127.0.0.1:5000**


## Dettagli Implementativi

### Estrazione (`extractor.py`)
Utilizza `BeautifulSoup` per analizzare il DOM HTML generato da ArXiv (spesso convertito via LaTeXML).
*   **Contesto**: Per associare il contesto a tabelle e figure, lo script cerca nei paragrafi del testo:
    1.  Link espliciti all'ID dell'oggetto (es. `<a href="#tab1">`).
    2.  Intersezione di keyword (escludendo stop words) tra la didascalia e il paragrafo.

### Schema Elasticsearch (`index_manager.py`)
*   **Articles**: `title`, `authors`, `date`, `abstract`, `full_text`.
*   **Tables**: `paper_id`, `table_id`, `caption`, `body` (contenuto celle), `mentions` (paragrafi citanti), `context_paragraphs`.
*   **Figures**: `paper_id`, `figure_id`, `url`, `caption`, `mentions`, `context_paragraphs`.

