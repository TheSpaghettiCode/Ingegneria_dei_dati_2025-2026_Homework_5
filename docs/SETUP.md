# Guida all'Installazione e Setup

Questa guida spiega come configurare l'ambiente di sviluppo per eseguire il motore di ricerca SciSearch in locale.

## Prerequisiti

*   **Python 3.8+**
*   **Elasticsearch 8.x** (Eseguibile via Docker o installazione nativa)
*   **Git**

## 1. Setup dell'Ambiente Python

È raccomandato l'uso di un ambiente virtuale per isolare le dipendenze.

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

Installare le dipendenze:
```bash
pip install -r requirements.txt
```

Il file `requirements.txt` dovrebbe includere:
```text
flask
elasticsearch
beautifulsoup4
requests
lxml
biopython
arxiv
```

## 2. Configurazione Elasticsearch

Il sistema richiede un'istanza Elasticsearch attiva su `http://localhost:9200`.

### Opzione A: Docker (Consigliata)
Se hai Docker Desktop installato, puoi avviare un nodo singolo in modalità sviluppo (senza sicurezza per semplicità locale):

```bash
docker run -d --name scisearch-es -p 9200:9200 -e "discovery.type=single-node" -e "xpack.security.enabled=false" elasticsearch:8.11.1
```

### Opzione B: Installazione Locale (Windows)
1.  Scarica lo ZIP da [elastic.co](https://www.elastic.co/downloads/elasticsearch).
2.  Estrai lo ZIP.
3.  Modifica `config/elasticsearch.yml` aggiungendo:
    ```yaml
    xpack.security.enabled: false
    ```
4.  Esegui `bin/elasticsearch.bat`.

Verifica che sia attivo visitando `http://localhost:9200` nel browser. Dovresti vedere un JSON di risposta.

## 3. Popolamento Dati (Pipeline)

Una volta attivo l'ambiente, esegui i comandi in ordine sequenziale:

### Passo 1: Download Corpus
Scarica gli articoli. Nota: i comandi di scraping possono richiedere tempo.

```bash
# Scarica ~20 paper da ArXiv
python src/scrapers/arxiv_scraper.py --query "speech to text" --max 20

# Scarica ~500 paper da PubMed
python src/scrapers/pubmed_scraper.py --query "cancer risk AND coffee consumption" --max 500
```

### Passo 2: Indicizzazione
Processa i file scaricati e popola Elasticsearch.

```bash
python src/indexing/indexer.py
```
*Output atteso*: Log che mostrano "Successfully indexed..." per ogni paper.

## 4. Avvio Applicazione Web

Lancia il server Flask di sviluppo:

```bash
python src/search/app.py
```

L'applicazione sarà accessibile a: **http://127.0.0.1:5000**

## Troubleshooting Comune

| Problema | Causa Possibile | Soluzione |
| :--- | :--- | :--- |
| **ConnectionError** (ES) | Elasticsearch non è attivo | Controlla Docker o il servizio Windows. Verifica `curl localhost:9200`. |
| **Missing Source Filter** | Browser cache o JS vecchio | Ricarica la pagina con `Ctrl+F5`. |
| **0 Results** | Indice vuoto | Riesegui `indexer.py`. Controlla se la cartella `data/` ha file. |
| **Image not loading** | Anti-bot ArXiv | L'app usa un proxy interno, verifica i log Flask per errori 403/404. |
