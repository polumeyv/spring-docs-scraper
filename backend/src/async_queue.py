"""
Async queue system for URL processing
"""
import asyncio
from typing import Callable, Set, Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import logging
from enum import Enum
from urllib.parse import urlparse
import hashlib


class Priority(Enum):
    """Priority levels for queue items"""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass
class QueueItem:
    """Item to be processed in the queue"""
    url: str
    priority: Priority = Priority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    
    def __lt__(self, other):
        """Compare items by priority for heap queue"""
        return self.priority.value < other.priority.value


class URLQueue:
    """Async queue for processing URLs with deduplication and priority"""
    
    def __init__(self, 
                 max_workers: int = 10,
                 max_queue_size: int = 10000,
                 max_retries: int = 3,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize URL queue
        
        Args:
            max_workers: Maximum concurrent workers
            max_queue_size: Maximum queue size
            max_retries: Maximum retries per URL
            logger: Logger instance
        """
        self.queue = asyncio.PriorityQueue(maxsize=max_queue_size)
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        
        # Tracking sets
        self.seen_urls: Set[str] = set()
        self.processing: Set[str] = set()
        self.processed: Set[str] = set()
        self.failed: Dict[str, str] = {}  # URL -> error message
        
        # Workers
        self.workers: List[asyncio.Task] = []
        self.running = False
        
        # Statistics
        self.stats = {
            'total_queued': 0,
            'total_processed': 0,
            'total_failed': 0,
            'total_retried': 0,
            'start_time': None
        }
        
        # Callbacks
        self.on_success: Optional[Callable] = None
        self.on_failure: Optional[Callable] = None
        self.on_complete: Optional[Callable] = None
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for deduplication"""
        # Remove fragment and trailing slash
        parsed = urlparse(url)
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if parsed.query:
            normalized += f"?{parsed.query}"
        return normalized.rstrip('/')
    
    async def add_url(self, url: str, priority: Priority = Priority.NORMAL, metadata: Optional[Dict] = None):
        """
        Add URL to queue if not already seen
        
        Args:
            url: URL to add
            priority: Processing priority
            metadata: Additional metadata
        """
        normalized_url = self._normalize_url(url)
        
        if normalized_url in self.seen_urls:
            self.logger.debug(f"URL already seen, skipping: {url}")
            return
        
        self.seen_urls.add(normalized_url)
        item = QueueItem(url=normalized_url, priority=priority, metadata=metadata or {})
        
        try:
            await self.queue.put((item.priority.value, item))
            self.stats['total_queued'] += 1
            self.logger.debug(f"Added to queue: {url} (priority: {priority.name})")
        except asyncio.QueueFull:
            self.logger.warning(f"Queue full, dropping URL: {url}")
            self.seen_urls.remove(normalized_url)
    
    async def add_urls(self, urls: List[str], priority: Priority = Priority.NORMAL):
        """Add multiple URLs to queue"""
        for url in urls:
            await self.add_url(url, priority)
    
    async def worker(self, worker_id: int, processor: Callable):
        """
        Worker coroutine that processes items from queue
        
        Args:
            worker_id: Worker ID for logging
            processor: Async function to process each URL
        """
        self.logger.info(f"Worker {worker_id} started")
        
        while self.running:
            try:
                # Get item from queue with timeout
                priority, item = await asyncio.wait_for(
                    self.queue.get(), 
                    timeout=1.0
                )
                
                # Mark as processing
                self.processing.add(item.url)
                self.logger.debug(f"Worker {worker_id} processing: {item.url}")
                
                try:
                    # Process the URL
                    result = await processor(item.url, item.metadata)
                    
                    # Success
                    self.processed.add(item.url)
                    self.stats['total_processed'] += 1
                    
                    if self.on_success:
                        await self.on_success(item.url, result)
                    
                    self.logger.info(f"Successfully processed: {item.url}")
                    
                except Exception as e:
                    # Failure
                    error_msg = str(e)
                    self.logger.error(f"Failed to process {item.url}: {error_msg}")
                    
                    # Retry logic
                    if item.retry_count < self.max_retries:
                        item.retry_count += 1
                        self.stats['total_retried'] += 1
                        self.logger.info(f"Retrying {item.url} (attempt {item.retry_count + 1}/{self.max_retries + 1})")
                        
                        # Re-add to queue with lower priority
                        item.priority = Priority.LOW
                        await self.queue.put((item.priority.value, item))
                    else:
                        # Max retries exceeded
                        self.failed[item.url] = error_msg
                        self.stats['total_failed'] += 1
                        
                        if self.on_failure:
                            await self.on_failure(item.url, error_msg)
                
                finally:
                    # Remove from processing
                    self.processing.discard(item.url)
                    self.queue.task_done()
                    
            except asyncio.TimeoutError:
                # No items in queue, continue
                continue
            except asyncio.CancelledError:
                # Worker cancelled
                break
            except Exception as e:
                self.logger.error(f"Worker {worker_id} error: {e}")
        
        self.logger.info(f"Worker {worker_id} stopped")
    
    async def start(self, processor: Callable):
        """
        Start processing queue with specified processor function
        
        Args:
            processor: Async function that takes (url, metadata) and processes it
        """
        if self.running:
            raise RuntimeError("Queue is already running")
        
        self.running = True
        self.stats['start_time'] = datetime.now()
        
        # Start workers
        for i in range(self.max_workers):
            worker = asyncio.create_task(self.worker(i, processor))
            self.workers.append(worker)
        
        self.logger.info(f"Started {self.max_workers} workers")
    
    async def wait_complete(self):
        """Wait for all queued items to be processed"""
        await self.queue.join()
        self.logger.info("All items processed")
        
        if self.on_complete:
            await self.on_complete(self.get_stats())
    
    async def stop(self):
        """Stop all workers gracefully"""
        self.running = False
        
        # Cancel all workers
        for worker in self.workers:
            worker.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
        
        self.logger.info("Queue stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        stats = self.stats.copy()
        stats.update({
            'queue_size': self.queue.qsize(),
            'processing': len(self.processing),
            'processed': len(self.processed),
            'failed': len(self.failed),
            'seen_urls': len(self.seen_urls)
        })
        
        if stats['start_time']:
            duration = (datetime.now() - stats['start_time']).total_seconds()
            stats['duration'] = duration
            if duration > 0:
                stats['avg_rate'] = stats['total_processed'] / duration
        
        return stats
    
    def get_failed_urls(self) -> Dict[str, str]:
        """Get dictionary of failed URLs and their error messages"""
        return self.failed.copy()
    
    async def save_state(self, filepath: str):
        """Save queue state to file for resuming later"""
        import json
        
        state = {
            'seen_urls': list(self.seen_urls),
            'processed': list(self.processed),
            'failed': self.failed,
            'stats': self.stats,
            'timestamp': datetime.now().isoformat()
        }
        
        # Get pending items from queue
        pending_items = []
        temp_items = []
        
        # Temporarily drain queue to get items
        while not self.queue.empty():
            try:
                priority, item = self.queue.get_nowait()
                temp_items.append((priority, item))
                pending_items.append({
                    'url': item.url,
                    'priority': item.priority.name,
                    'metadata': item.metadata,
                    'retry_count': item.retry_count
                })
            except asyncio.QueueEmpty:
                break
        
        # Put items back
        for priority, item in temp_items:
            await self.queue.put((priority, item))
        
        state['pending'] = pending_items
        
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2, default=str)
        
        self.logger.info(f"Saved queue state to {filepath}")
    
    async def load_state(self, filepath: str):
        """Load queue state from file"""
        import json
        
        with open(filepath, 'r') as f:
            state = json.load(f)
        
        # Restore sets
        self.seen_urls = set(state.get('seen_urls', []))
        self.processed = set(state.get('processed', []))
        self.failed = state.get('failed', {})
        
        # Restore stats
        self.stats.update(state.get('stats', {}))
        
        # Restore pending items
        for item_data in state.get('pending', []):
            item = QueueItem(
                url=item_data['url'],
                priority=Priority[item_data['priority']],
                metadata=item_data.get('metadata', {}),
                retry_count=item_data.get('retry_count', 0)
            )
            await self.queue.put((item.priority.value, item))
        
        self.logger.info(f"Loaded queue state from {filepath}: "
                        f"{len(self.seen_urls)} seen, "
                        f"{len(self.processed)} processed, "
                        f"{self.queue.qsize()} pending")