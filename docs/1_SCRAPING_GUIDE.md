# Guida allo Scraping - Homework 5

## Introduzione
Questa cartella contiene gli script Python necessari per creare il corpus di documenti per il motore di ricerca. Gli script scaricano articoli scientifici in formato HTML da due fonti principali: **ArXiv** e **PubMed Central (PMC)**.

## Prerequisiti
Assicurati di avere Python installato e di aver installato le librerie necessarie:

```bash
pip install -r requirements.txt
```

Le librerie principali utilizzate sono:
- `requests`: per effettuare le chiamate HTTP ai siti web.
- `beautifulsoup4`: per analizzare (parse) il codice HTML e trovare i link e i titoli.

---

## 1. ArXiv Scraper (`src/scrapers/arxiv_scraper.py`)

Questo script cerca articoli su ArXiv.org basandosi su una keyword specifica.

### Configurazione
Apri il file e modifica la variabile `KEYWORD` all'inizio dello script se vuoi cambiare termine di ricerca (default: "deep learning").

### Come Lanciarlo
Dalla root del progetto, esegui:
```bash
python src/scrapers/arxiv_scraper.py
```

### Logica di Funzionamento
1. **Ricerca**: Effettua una query su `arxiv.org/search`.
2. **Filtro HTML**: Analizza ogni risultato. **CRUCIALE:** Scarica l'articolo *solo se* è disponibile un link "HTML" o "Experimental HTML". Se l'articolo è disponibile solo in PDF, viene ignorato.
3. **Salvataggio**: I file vengono salvati in `data/html_arxiv/` con il titolo dell'articolo come nome file.

---

## 2. PubMed Scraper (`src/scrapers/pubmed_scraper.py`)

Questo script scarica articoli Open Access da PubMed Central.

### Configurazione
Modifica le variabili all'inizio del file:
- `QUERY`: La query di ricerca (default: "cancer risk AND coffee consumption").
- `TARGET_COUNT`: Numero di articoli da scaricare (default: 500).

### Come Lanciarlo
```bash
python src/scrapers/pubmed_scraper.py
```

### Logica di Funzionamento
1. **Filtro Open Access**: La ricerca è limitata automaticamente alla collezione Open Access per garantire che il testo completo sia disponibile legalmente.
2. **Paginazione**: Lo script naviga automaticamente tra le pagine dei risultati finché non raggiunge il numero target di articoli (500).
3. **Rispetto dei Limiti**: Sono inserite delle *pause* (sleep) tra le richieste per evitare di sovraccaricare il server ed essere bloccati (Ban IP).
4. **Salvataggio**: File salvati in `data/html_pubmed/`.

---

## Gestione Errori Comuni

- **Timeout / Connection Error**: Potrebbe cadere la connessione o il sito potrebbe essere momentaneamente irraggiungibile. Riprova più tardi.
- **403 Forbidden**: Significa che il server ti ha bloccato perché hai fatto troppe richieste velocemente.
    - *Soluzione*: Aumenta il tempo di `time.sleep()` negli script o aspetta qualche ora.
- **File non trovati**: Assicurati di lanciare gli script dalla cartella principale del progetto, altrimenti i percorsi relativi (`data/...`) potrebbero non funzionare.
