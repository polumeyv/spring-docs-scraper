# Async Spring Documentation Scraper

High-performance asynchronous implementation of the Spring documentation scraper with connection pooling, concurrent processing, and real-time progress tracking.

## Features

### Performance Improvements
- **3x+ faster** than synchronous implementation
- **Concurrent URL processing** with configurable worker pool
- **Connection pooling** for efficient HTTP resource usage
- **Rate limiting** to respect server limits
- **Async I/O** for non-blocking operations

### Enhanced Functionality
- **Rich console progress tracking** with real-time updates
- **Graceful shutdown** handling (Ctrl+C to save progress)
- **Resume capability** from saved checkpoints
- **Memory-efficient** streaming and processing
- **Comprehensive error handling** with automatic retries

## Architecture

### Core Components

1. **AsyncHTTPClient** (`async_http_client.py`)
   - Connection pooling with configurable limits
   - Token bucket rate limiting
   - Automatic retry with exponential backoff
   - Statistics tracking

2. **URLQueue** (`async_queue.py`)
   - Priority-based URL processing
   - Deduplication and normalization
   - Worker pool pattern
   - State persistence for resume

3. **AsyncSpringDocsScraperEnhanced** (`async_spring_scraper_enhanced.py`)
   - Main scraper with async/await
   - Progress tracking integration
   - Graceful shutdown handling
   - Checkpoint save/resume

4. **ProgressTracker** (`progress_tracker.py`)
   - Rich console UI with live updates
   - Multiple progress bars
   - Real-time statistics
   - Fallback to simple output

### Data Models (Pydantic)

- **ProjectModel**: Spring project information
- **ScrapedContent**: Scraped documentation content
- **RouteModel**: SPA routing information
- **ResourceInfo**: Static resource metadata
- **ScrapeProgress**: Progress tracking data

## Installation

```bash
# Install async dependencies
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
# Run async scraper with default settings
python src/async_spring_scraper_enhanced.py

# Clean existing data before scraping
python src/async_spring_scraper_enhanced.py --clean
```

### Advanced Options

```bash
# Configure performance settings
python src/async_spring_scraper_enhanced.py \
    --max-connections 30 \
    --rate-limit 20.0 \
    --max-workers 15

# Disable rich progress (for CI/CD environments)
python src/async_spring_scraper_enhanced.py --no-rich

# Disable checkpoint saving
python src/async_spring_scraper_enhanced.py --no-checkpoint
```

### Command Line Arguments

- `--clean`: Clean existing documentation before scraping
- `--max-connections`: Maximum concurrent connections (default: 20)
- `--max-per-host`: Maximum connections per host (default: 10)
- `--rate-limit`: Requests per second (default: 10.0)
- `--max-workers`: Maximum concurrent workers (default: 10)
- `--no-rich`: Disable rich console progress display
- `--no-checkpoint`: Disable checkpoint saving

## Performance Benchmarks

Run performance comparison between sync and async implementations:

```bash
# Basic benchmark (5 projects)
python src/benchmark_performance.py

# Extended benchmark with visualization
python src/benchmark_performance.py --projects 10 --visualize

# Custom settings
python src/benchmark_performance.py \
    --projects 20 \
    --max-connections 30 \
    --rate-limit 15.0
```

### Benchmark Results

Typical performance improvements:
- **Speed**: 3-5x faster execution
- **Throughput**: 10-20 URLs/second
- **Memory**: Similar or better memory usage
- **CPU**: Better utilization with async I/O

## Progress Tracking

The async scraper provides real-time progress tracking:

```
Spring Documentation Async Scraper
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Progress
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Overall Progress  ████████████████ 82% │ 00:02:15 │ 00:00:30 ┃
┃ Projects          ████████████████ 10/12 │ 00:02:15         ┃
┃ URLs              ████████████████ 245/300 │ 00:02:15       ┃
┃ Resources         ⠸ Resources (523 files)                    ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Statistics
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Elapsed Time      02:15          ┃
┃ Projects          10 / 12        ┃
┃ URLs Processed    245 / 300      ┃
┃ URLs Failed       5              ┃
┃ Processing Rate   12.5 URLs/sec  ┃
┃ Resources         523            ┃
┃ Data Downloaded   125.3 MB       ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Current Activity
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Project: spring-security         ┃
┃ URL: https://docs.spring.io/...  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

## Graceful Shutdown

The scraper supports graceful shutdown:

1. Press `Ctrl+C` to initiate shutdown
2. Current progress is saved to checkpoint
3. Press `Ctrl+C` again to force immediate exit
4. Resume from checkpoint on next run

## Testing

Run the test suite:

```bash
# Run all tests with coverage
python run_tests.py

# Run specific test file
pytest tests/test_async_http_client.py -v

# Run with coverage report
pytest tests/ --cov=src --cov-report=html
```

### Test Coverage

- `test_async_http_client.py`: HTTP client and rate limiting
- `test_async_queue.py`: URL queue and worker pool
- `test_models.py`: Pydantic model validation

## Project Structure

```
backend/
├── src/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── async_base.py       # Abstract base classes
│   │   └── scraper_models.py   # Pydantic models
│   ├── async_http_client.py    # Async HTTP client
│   ├── async_queue.py          # URL processing queue
│   ├── async_spring_scraper.py # Basic async scraper
│   ├── async_spring_scraper_enhanced.py # Enhanced scraper
│   ├── progress_tracker.py     # Progress tracking
│   └── benchmark_performance.py # Performance benchmarks
├── tests/
│   ├── __init__.py
│   ├── test_async_http_client.py
│   ├── test_async_queue.py
│   └── test_models.py
├── requirements.txt
└── README_ASYNC.md
```

## Implementation Details

### Async/Await Pattern

The scraper uses Python's native async/await for:
- HTTP requests with aiohttp
- Concurrent task processing
- Resource management
- Progress updates

### Connection Pooling

- Reuses TCP connections
- Configurable limits per host
- DNS caching for performance
- Automatic cleanup

### Rate Limiting

- Token bucket algorithm
- Configurable requests/second
- Burst support
- Fair queuing

### Error Handling

- Automatic retry with backoff
- Graceful degradation
- Detailed error logging
- Failed URL tracking

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure you're in the backend directory
2. **Rate limiting**: Reduce `--rate-limit` if getting 429 errors
3. **Memory usage**: Reduce `--max-workers` for less memory
4. **Connection errors**: Check network and reduce `--max-connections`

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

- [ ] Distributed scraping support
- [ ] Database backend for large scrapes
- [ ] API endpoint for scraping status
- [ ] Docker compose for easy deployment
- [ ] Prometheus metrics export

## Contributing

When contributing to the async scraper:

1. Maintain async/await patterns
2. Add tests for new features
3. Update documentation
4. Run benchmarks for performance changes
5. Ensure graceful shutdown works

## License

Same as parent project