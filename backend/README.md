# Spring Documentation Scraper Backend

Backend service for scraping and serving Spring documentation.

## Components

### 1. Synchronous Scraper (Original)
- `spring_docs_scraper.py` - Original synchronous implementation
- Simple, straightforward scraping logic
- Sequential processing of projects and URLs

### 2. Asynchronous Scraper (High Performance)
- `async_spring_scraper_enhanced.py` - Enhanced async implementation  
- **3x+ faster** than synchronous version
- Concurrent processing with connection pooling
- Real-time progress tracking
- See [README_ASYNC.md](README_ASYNC.md) for full details

### 3. Documentation Server
- `serve_docs.py` - Simple HTTP server for scraped documentation
- Serves the SPA interface and scraped content

## Quick Start

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Run Scraper

**Synchronous (Original)**:
```bash
python src/spring_docs_scraper.py
```

**Asynchronous (Recommended)**:
```bash
python src/async_spring_scraper_enhanced.py
```

### Serve Documentation
```bash
python src/serve_docs.py
# Open http://localhost:8082
```

## Performance Comparison

Run benchmarks to compare sync vs async performance:
```bash
python src/benchmark_performance.py --projects 10 --visualize
```

Typical results:
- Async is 3-5x faster
- Better resource utilization
- Handles concurrent requests efficiently

## Testing

```bash
# Run all tests
python run_tests.py

# Run specific tests
pytest tests/test_async_http_client.py -v
```

## Docker Support

Build and run with Docker:
```bash
docker build -t spring-docs-scraper .
docker run -p 8082:8082 spring-docs-scraper
```

## Project Structure

```
backend/
├── src/
│   ├── models/           # Pydantic data models
│   ├── spring_docs_scraper.py       # Sync scraper
│   ├── async_spring_scraper_enhanced.py  # Async scraper
│   ├── async_http_client.py         # HTTP client with pooling
│   ├── async_queue.py               # URL processing queue
│   ├── progress_tracker.py          # Progress UI
│   ├── benchmark_performance.py     # Performance tests
│   └── serve_docs.py               # Documentation server
├── tests/               # Test suite
├── requirements.txt     # Python dependencies
├── Dockerfile          # Container configuration
└── README.md           # This file
```

## Requirements

- Python 3.8+
- See requirements.txt for Python packages

## License

[License details here]