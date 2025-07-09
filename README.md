# Spring Docs Scraper

Smart Spring documentation scraper that creates an organized SPA structure.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Download documentation
python spring_docs_scraper.py

# Clean and re-download
python spring_docs_scraper.py --clean

# Serve locally
python serve_docs.py
```

Opens at http://localhost:8081

## Features

- Smart organization - no duplicate HTML files
- Organized static assets (CSS/JS/images in proper folders)
- SPA index page for easy browsing
- Content separated from templates
- Efficient resource caching
- ~5-10 minutes to download

## Structure

```
spring-docs/
├── index.html          # SPA interface
├── static/             # Organized assets
│   ├── css/
│   ├── js/
│   └── img/
├── content/            # JSON content files
├── templates/          # HTML templates
└── metadata.json       # Project metadata
```