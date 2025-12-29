# Sviluppo di un Sistema Avanzato di Ricerca su Articoli Scientifici

## Descrizione del Progetto
Questo progetto implementa un motore di ricerca avanzato per articoli scientifici (nello specifico da [arXiv](https://arxiv.org)), trattando non solo il testo degli articoli, ma anche **Tabelle** e **Figure** come oggetti di "prima classe". Questo significa che è possibile cercare specificamente all'interno delle tabelle (didascalie, contenuto) e delle figure (didascalie), oltre alla classica ricerca full-text sugli articoli.

Il sistema è stato progettato per il corso di Ingegneria dei Dati 2025-2026 (Homework 5).

## Funzionalità Principali
1.  **Corpus Creation (Multi-Source)**:
# SciSearch: Ricerca Semantica per Articoli Scientifici

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Elasticsearch](https://img.shields.io/badge/Elasticsearch-8.x-yellow)
![Flask](https://img.shields.io/badge/Backend-Flask-green)
![Status](https://img.shields.io/badge/Status-Complete-success)

**SciSearch** è un motore di ricerca avanzato progettato per indicizzare e interrogare corpus scientifici eterogenei (ArXiv e PubMed). A differenza dei motori tradizionali, SciSearch tratta **Tabelle** e **Figure** come "cittadini di prima classe", permettendo agli utenti di cercare specificamente all'interno dei dati tabulari o delle didascalie grafiche, mantenendo il contesto semantico (ovvero, *dove* e *come* l'oggetto è citato nel testo).

---

## Documentazione

La documentazione completa del progetto è disponibile nella cartella [`docs/`](./docs):

*   **[Architettura del Sistema](./docs/ARCHITECTURE.md)**: Diagrammi Mermaid e spiegazione dei flussi ETL e della logica di indicizzazione.
*   **[Dettagli Implementativi](./docs/IMPLEMENTATION.md)**: Analisi approfondita del codice (Scrapers, Extractor, Indexer) e delle scelte algoritmiche.
*   **[Guida all'Installazione](./docs/SETUP.md)**: Istruzioni passo-passo per setup, Docker, e avvio rapido.

## Funzionalità Chiave

1.  **Multi-Source Ingestion**:
    *   **ArXiv**: Scraping di HTML (via LaTeXML/ar5iv).
    *   **PubMed Central**: Ingestione di XML Open Access tramite API Entrez.
2.  **Object-Level Indexing**:
    *   Le tabelle non sono solo blocchi di testo: le celle, le didascalie e i paragrafi di citazione sono indicizzati strutturalmente.
    *   Le figure sono ricercabili tramite didascalia e contesto.
3.  **Context Awareness**:
    *   Ogni risultato (Tabella/Figura) mostra i "Context Paragraphs": ovvero i brani esatti del paper che discutono quell'elemento.
4.  **Interfaccia Avanzata**:
    *   Filtri laterali persistenti (Source: ArXiv/PubMed).
    *   Switch dinamico del target di ricerca (Paper, Table, Figure).
    *   Proxy immagini integrato per visualizzare figure protette.

## Quick Start

Per i più impazienti, ecco come avviare tutto in pochi secondi (assumendo Elasticsearch attivo su localhost:9200):

```bash
# 1. Installa dipendenze
pip install -r requirements.txt

# 2. Popola il DB (se vuoto)
python src/indexing/indexer.py

# 3. Avvia la Web App
python src/search/app.py
```
Visita **http://127.0.0.1:5000** per iniziare a cercare.

---
*Progetto sviluppato per il corso di Ingegneria dei Dati, A.A. 2025-2026. Autore: Andrea.*
