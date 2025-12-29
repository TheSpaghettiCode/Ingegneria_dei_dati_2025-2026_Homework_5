# Dettagli Implementativi & Code Analysis

Questo documento fornisce una spiegazione approfondita dei moduli principali del codice sorgente.

## 1. Modulo Scraper

### `src/scrapers/pubmed_scraper.py`
Questo script gestisce il download massivo da PubMed Central.

*   **Libreria**: Utilizza `Bio.Entrez` (Biopython).
*   **Gestione Rate Limit**: Include `time.sleep(0.34)` per rispettare le policy NCBI (3 richieste/secondo max senza API Key).
*   **Workflow**:
    1.  `Entrez.esearch`: Cerca gli ID (PMCID) che soddisfano la query (es. "cancer risk...").
    2.  `Entrez.efetch`: Scarica il contenuto XML completo per ogni ID.
    3.  **Salvataggio**: Salva due file per ogni articolo:
        *   `PMCxxxx.xml`: Il contenuto grezzo.
        *   `PMCxxxx_meta.json`: Metadati estratti (titolo, autori, data) per un accesso rapido durante l'indicizzazione.

### `src/scrapers/arxiv_scraper.py`
*   **Libreria**: `arxiv` (wrapper API ufficiale) + `requests`.
*   **Sfida**: ArXiv non fornisce l'HTML via API.
*   **Soluzione**: Lo script costruisce l'URL `https://arxiv.org/html/{paper_id}` e scarica la pagina simulando un browser (`User-Agent` header). Se fallisce, tenta su `ar5iv.org`.

## 2. Modulo Extraction (`src/extraction/extractor.py`)

La classe `Extractor` è il componente più complesso.

### Metodo `process_file(filepath)`
Funge da router:
```python
if filepath.endswith('.xml'):
    return self._process_pubmed(soup, paper_id)
else:
    return self._process_arxiv(soup, paper_id)
```

### Parsing XML (`_process_pubmed`)
Il formato XML di PMC (JATS) è molto strutturato.
*   **Tabelle**: Identificate dal tag `<table-wrap>`.
    *   `id`: Attributo `id` del tag.
    *   `caption`: Tag `<caption>`, spesso contenente `<title>` e `<p>`.
    *   `body`: L'intero sotto-albero `<table>` convertito in stringa per l'indicizzazione.
*   **Figure**: Identificate dal tag `<fig>`.
    *   `url`: Costruito combinando l'ID articolo con il riferimento grafico (`<graphic xlink:href="...">`).

### Parsing HTML ArXiv (`_process_arxiv`)
ArXiv usa *LaTeXML* per convertire i TeX in HTML. La struttura è basata su classi CSS:
*   Tabelle: `div.ltx_table` o `table.ltx_tabular`.
*   Figure: `figure.ltx_figure`.

### Context Extraction Algorithm
Per ogni oggetto (tabella/figura), dobbiamo trovare *dove* viene citato nel testo.
L'algoritmo (`_post_process_context`) funziona in due step:

1.  **Link Detection**: Cerca tag `<a>` nel testo il cui `href` punta all'ID dell'oggetto (es. `#tab1`). Questo è il metodo più preciso.
2.  **Keyword Matching Disambiguato**:
    *   Se non ci sono link espliciti, cerca frasi come "Table 1" o "Figure 2".
    *   Calcola uno "score" di rilevanza basato sull'intersezione di parole significative (rimuovendo le *stop words*) tra la didascalia e il paragrafo.

## 3. Indicizzazione (`src/indexing/`)

### `index_manager.py`
Definisce i *Mappings* di Elasticsearch.
*   **Analizzatori**: Utilizza l'analizzatore `standard` per i campi di testo (`caption`, `body`, `abstract`) per supportare la ricerca full-text.
*   **Keyword**: Campi come `authors`, `source`, `paper_id` sono mappati come `keyword` per permettere filtri esatti e aggregazioni.

### `indexer.py`
Gestisce il caricamento massivo (Batch Processing).
*   Scansiona le cartelle `data/html_arxiv` e `data/html_pubmed`.
*   Usa `elasticsearch.helpers.bulk` per inviare pacchetti di documenti (azioni) in un'unica richiesta HTTP, migliorando drasticamente le performance rispetto all'inserimento singolo.
*   Gestisce la deduplicazione (controlla `es.exists` prima di inserire).

## 4. Web Application (`src/search/app.py` & `src/ui/`)

### Backend (Flask)
*   Endpoint `/api/search`: Riceve i parametri `query`, `index_type` (articles/tables/figures) e `source_type`.
*   Costruisce la query DSL (Domain Specific Language) per Elasticsearch:
    ```json
    {
      "query": {
        "bool": {
          "must": [{"query_string": {"query": "..."}}],
          "filter": [{"term": {"source": "pubmed"}}] 
        }
      }
    }
    ```
*   **Image Proxy** (`/api/image_proxy`): Serve le immagini di ArXiv. Le immagini di ArXiv spesso hanno hotlinking protection; il server Flask le scarica lato server e le serve al client.

### Frontend
*   Layout a griglia CSS con Sidebar fissa.
*   JavaScript vanilla per la gestione asincrona (`fetch`) dei risultati senza ricaricare la pagina.
*   Sistema di template string per generare dinamicamente le "Card" dei risultati.
