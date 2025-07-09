# Spring Docs Scraper

Scrapes Spring documentation and serves it locally.

## Usage

### Scrape docs:
```bash
python spring_docs_scraper.py
```

### Serve docs:
```bash
python serve_docs.py
```

Server runs at http://localhost:8081

The server automatically fetches CSS/JS from Spring's servers so docs display properly.

## Files
- `spring_docs_scraper.py` - Downloads Spring documentation HTML
- `serve_docs.py` - Local server with proxy for resources
- `spring-docs/` - Downloaded documentation