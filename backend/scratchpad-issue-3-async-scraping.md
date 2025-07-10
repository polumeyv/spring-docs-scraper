# Async Scraping Implementation Plan

Issue: https://github.com/polumeyv/docs-scraper/issues/3

## Overview
Convert the synchronous Spring documentation scraper to use async/await for improved performance and resource utilization.

## Current State Analysis
The current implementation (`spring_docs_scraper.py`) uses:
- `requests` library for synchronous HTTP calls
- `ThreadPoolExecutor` for limited concurrency
- Sequential processing of projects and versions
- Rate limiting with `time.sleep()`

## Async Architecture Design

### 1. Core Components

#### AsyncScraperBase (Abstract Base Class)
```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import aiohttp
from pydantic import BaseModel

class AsyncScraperBase(ABC):
    @abstractmethod
    async def scrape(self, url: str) -> Dict:
        pass
    
    @abstractmethod
    async def process_content(self, content: str, url: str) -> Dict:
        pass
```

#### Data Models (Pydantic)
```python
from pydantic import BaseModel, HttpUrl
from typing import List, Dict, Optional
from datetime import datetime

class ProjectModel(BaseModel):
    name: str
    url: HttpUrl
    description: Optional[str]
    versions: List[str] = []
    docs: Dict[str, HttpUrl] = {}

class RouteModel(BaseModel):
    content: str
    title: str
    project: str
    type: str

class ScrapedContent(BaseModel):
    title: str
    content: str
    nav: Optional[List[Dict]]
    type: str
    project: str
```

### 2. Async HTTP Client with Connection Pooling

#### Features:
- Connection pooling with configurable limits
- Rate limiting using `asyncio.Semaphore`
- Retry logic with exponential backoff
- Proper timeout handling

```python
class AsyncHTTPClient:
    def __init__(self, 
                 max_connections: int = 10,
                 max_per_host: int = 5,
                 rate_limit: float = 0.3,
                 timeout: int = 30):
        self.rate_limit = rate_limit
        self.semaphore = asyncio.Semaphore(max_connections)
        self.connector = aiohttp.TCPConnector(
            limit=max_connections,
            limit_per_host=max_per_host
        )
        self.timeout = aiohttp.ClientTimeout(total=timeout)
```

### 3. Async Queue System

#### URLQueue for processing:
```python
class URLQueue:
    def __init__(self, max_workers: int = 10):
        self.queue = asyncio.Queue()
        self.max_workers = max_workers
        self.processed = set()
        self.failed = set()
        
    async def process_urls(self, processor_func):
        workers = [
            asyncio.create_task(self.worker(processor_func))
            for _ in range(self.max_workers)
        ]
        await self.queue.join()
        for worker in workers:
            worker.cancel()
```

### 4. Progress Tracking with Rich

```python
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

class ProgressTracker:
    def __init__(self):
        self.console = Console()
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self.console
        )
```

### 5. Main Async Scraper Implementation

Key changes:
- Convert all HTTP calls to use `aiohttp`
- Replace `time.sleep()` with `asyncio.sleep()`
- Use `asyncio.gather()` for concurrent operations
- Implement producer-consumer pattern for URL processing

## Implementation Steps

1. **Create base infrastructure**
   - Abstract base classes
   - Pydantic models
   - Async HTTP client

2. **Convert scraping logic**
   - Replace `requests` with `aiohttp`
   - Convert methods to async/await
   - Implement concurrent processing

3. **Add queue system**
   - URL queue for processing
   - Worker pool pattern
   - Error handling and retries

4. **Progress tracking**
   - Rich console integration
   - Real-time progress updates
   - Statistics display

5. **Graceful shutdown**
   - Signal handlers
   - Cleanup resources
   - Save partial results

## Performance Goals
- 3x improvement in scraping speed
- Stable memory usage during large scrapes
- Better CPU utilization through async I/O

## Testing Strategy
- Unit tests for async components
- Integration tests for full scraping flow
- Performance benchmarks comparing sync vs async
- Memory usage profiling

## Dependencies Required
- aiohttp (already in requirements.txt)
- httpx (already in requirements.txt)
- rich (already in requirements.txt)
- pydantic (already in requirements.txt)

## Risks and Mitigations
- **Risk**: Rate limiting from target servers
  - **Mitigation**: Configurable rate limits, exponential backoff
- **Risk**: Memory usage with many concurrent requests
  - **Mitigation**: Connection pooling, queue size limits
- **Risk**: Partial failures during scraping
  - **Mitigation**: Checkpoint system, resume capability