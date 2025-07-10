"""
Async HTTP client with connection pooling and rate limiting
"""
import asyncio
import aiohttp
from typing import Optional, Dict, Any
import logging
from datetime import datetime, timedelta
from collections import deque
import time


class RateLimiter:
    """Token bucket rate limiter for async requests"""
    
    def __init__(self, rate: float, burst: int = 1):
        """
        Initialize rate limiter
        
        Args:
            rate: Requests per second
            burst: Maximum burst size
        """
        self.rate = rate
        self.burst = burst
        self.tokens = burst
        self.last_update = time.monotonic()
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire a token, waiting if necessary"""
        async with self.lock:
            while self.tokens <= 0:
                now = time.monotonic()
                elapsed = now - self.last_update
                self.tokens += elapsed * self.rate
                self.tokens = min(self.tokens, self.burst)
                self.last_update = now
                
                if self.tokens <= 0:
                    sleep_time = (1 - self.tokens) / self.rate
                    await asyncio.sleep(sleep_time)
            
            self.tokens -= 1


class AsyncHTTPClient:
    """Async HTTP client with connection pooling and rate limiting"""
    
    def __init__(self,
                 max_connections: int = 10,
                 max_per_host: int = 5,
                 rate_limit: float = 3.0,  # requests per second
                 timeout: int = 30,
                 retry_attempts: int = 3,
                 retry_delay: float = 1.0,
                 headers: Optional[Dict[str, str]] = None):
        """
        Initialize async HTTP client
        
        Args:
            max_connections: Maximum total connections
            max_per_host: Maximum connections per host
            rate_limit: Requests per second
            timeout: Request timeout in seconds
            retry_attempts: Number of retry attempts
            retry_delay: Base delay between retries (exponential backoff)
            headers: Default headers for all requests
        """
        self.connector = aiohttp.TCPConnector(
            limit=max_connections,
            limit_per_host=max_per_host,
            ttl_dns_cache=300,  # DNS cache for 5 minutes
            enable_cleanup_closed=True
        )
        
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.rate_limiter = RateLimiter(rate_limit, burst=int(rate_limit * 2))
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        
        self.default_headers = {
            'User-Agent': 'Mozilla/5.0 (Compatible; Spring Docs Async Scraper)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        if headers:
            self.default_headers.update(headers)
        
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_bytes': 0,
            'start_time': None
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def start(self):
        """Start the HTTP client session"""
        if self.session is None:
            self.session = aiohttp.ClientSession(
                connector=self.connector,
                timeout=self.timeout,
                headers=self.default_headers
            )
            self.stats['start_time'] = datetime.now()
            self.logger.info("HTTP client session started")
    
    async def close(self):
        """Close the HTTP client session"""
        if self.session:
            await self.session.close()
            await self.connector.close()
            self.session = None
            
            # Log statistics
            if self.stats['total_requests'] > 0:
                duration = (datetime.now() - self.stats['start_time']).total_seconds()
                self.logger.info(
                    f"HTTP client closed. Stats: "
                    f"Total requests: {self.stats['total_requests']}, "
                    f"Success: {self.stats['successful_requests']}, "
                    f"Failed: {self.stats['failed_requests']}, "
                    f"Total bytes: {self.stats['total_bytes']:,}, "
                    f"Duration: {duration:.2f}s, "
                    f"Avg rate: {self.stats['total_requests'] / duration:.2f} req/s"
                )
    
    async def fetch(self, 
                   url: str, 
                   method: str = 'GET',
                   headers: Optional[Dict[str, str]] = None,
                   data: Any = None,
                   json: Any = None,
                   **kwargs) -> Optional[aiohttp.ClientResponse]:
        """
        Fetch a URL with rate limiting and retry logic
        
        Args:
            url: URL to fetch
            method: HTTP method
            headers: Additional headers
            data: Form data
            json: JSON data
            **kwargs: Additional arguments for aiohttp request
            
        Returns:
            ClientResponse or None if all retries failed
        """
        if not self.session:
            raise RuntimeError("HTTP client not started. Use 'await client.start()' or context manager.")
        
        # Merge headers
        request_headers = self.default_headers.copy()
        if headers:
            request_headers.update(headers)
        
        attempt = 0
        last_error = None
        
        while attempt < self.retry_attempts:
            try:
                # Rate limiting
                await self.rate_limiter.acquire()
                
                # Update statistics
                self.stats['total_requests'] += 1
                
                # Make request
                async with self.session.request(
                    method,
                    url,
                    headers=request_headers,
                    data=data,
                    json=json,
                    **kwargs
                ) as response:
                    # Read content to ensure connection can be reused
                    content = await response.read()
                    
                    # Update statistics
                    self.stats['successful_requests'] += 1
                    self.stats['total_bytes'] += len(content)
                    
                    # Store content in response object for later use
                    response._content = content
                    
                    if response.status < 400:
                        return response
                    elif response.status == 429:  # Too Many Requests
                        retry_after = response.headers.get('Retry-After', '60')
                        wait_time = int(retry_after)
                        self.logger.warning(f"Rate limited on {url}. Waiting {wait_time}s")
                        await asyncio.sleep(wait_time)
                        attempt += 1
                        continue
                    elif response.status >= 500:  # Server error, retry
                        self.logger.warning(f"Server error {response.status} for {url}. Retrying...")
                        last_error = f"HTTP {response.status}"
                    else:  # Client error, don't retry
                        self.logger.error(f"Client error {response.status} for {url}")
                        self.stats['failed_requests'] += 1
                        return None
                        
            except asyncio.TimeoutError:
                last_error = "Timeout"
                self.logger.warning(f"Timeout fetching {url} (attempt {attempt + 1}/{self.retry_attempts})")
            except aiohttp.ClientError as e:
                last_error = str(e)
                self.logger.warning(f"Client error fetching {url}: {e} (attempt {attempt + 1}/{self.retry_attempts})")
            except Exception as e:
                last_error = str(e)
                self.logger.error(f"Unexpected error fetching {url}: {e}")
                self.stats['failed_requests'] += 1
                raise
            
            # Exponential backoff
            if attempt < self.retry_attempts - 1:
                wait_time = self.retry_delay * (2 ** attempt)
                await asyncio.sleep(wait_time)
            
            attempt += 1
        
        # All retries failed
        self.stats['failed_requests'] += 1
        self.logger.error(f"Failed to fetch {url} after {self.retry_attempts} attempts. Last error: {last_error}")
        return None
    
    async def fetch_text(self, url: str, encoding: Optional[str] = None, **kwargs) -> Optional[str]:
        """Fetch URL and return text content"""
        response = await self.fetch(url, **kwargs)
        if response:
            try:
                # Use stored content
                content = response._content
                if encoding:
                    return content.decode(encoding)
                else:
                    return content.decode('utf-8', errors='replace')
            except Exception as e:
                self.logger.error(f"Error decoding text from {url}: {e}")
        return None
    
    async def fetch_json(self, url: str, **kwargs) -> Optional[Dict]:
        """Fetch URL and return JSON content"""
        response = await self.fetch(url, **kwargs)
        if response:
            try:
                import json
                content = response._content
                return json.loads(content)
            except Exception as e:
                self.logger.error(f"Error parsing JSON from {url}: {e}")
        return None
    
    async def fetch_bytes(self, url: str, **kwargs) -> Optional[bytes]:
        """Fetch URL and return binary content"""
        response = await self.fetch(url, **kwargs)
        if response:
            return response._content
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics"""
        stats = self.stats.copy()
        if stats['start_time']:
            stats['duration'] = (datetime.now() - stats['start_time']).total_seconds()
            if stats['duration'] > 0:
                stats['avg_rate'] = stats['total_requests'] / stats['duration']
        return stats