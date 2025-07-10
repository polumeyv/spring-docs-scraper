"""
Abstract base classes for async scrapers
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import aiohttp
from bs4 import BeautifulSoup
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

from .scraper_models import ScrapedContent, ResourceInfo


class AsyncScraperBase(ABC):
    """Abstract base class for async scrapers"""
    
    def __init__(self, session: aiohttp.ClientSession, logger: Optional[logging.Logger] = None):
        self.session = session
        self.logger = logger or logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def scrape(self, url: str) -> Optional[ScrapedContent]:
        """
        Scrape content from a URL
        
        Args:
            url: URL to scrape
            
        Returns:
            ScrapedContent or None if failed
        """
        pass
    
    @abstractmethod
    async def process_content(self, html: str, url: str) -> Optional[ScrapedContent]:
        """
        Process HTML content and extract relevant data
        
        Args:
            html: Raw HTML content
            url: Source URL
            
        Returns:
            ScrapedContent or None if failed
        """
        pass
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def fetch_content(self, url: str) -> Optional[str]:
        """
        Fetch content from URL with retry logic
        
        Args:
            url: URL to fetch
            
        Returns:
            HTML content or None if failed
        """
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    self.logger.warning(f"Failed to fetch {url}: Status {response.status}")
                    return None
        except Exception as e:
            self.logger.error(f"Error fetching {url}: {e}")
            raise
    
    def parse_html(self, html: str) -> BeautifulSoup:
        """Parse HTML content using BeautifulSoup"""
        return BeautifulSoup(html, 'lxml')
    
    async def extract_resources(self, soup: BeautifulSoup, base_url: str) -> List[ResourceInfo]:
        """
        Extract static resources from HTML
        
        Args:
            soup: BeautifulSoup object
            base_url: Base URL for resolving relative URLs
            
        Returns:
            List of ResourceInfo objects
        """
        resources = []
        
        # Extract CSS
        for link in soup.find_all('link', rel='stylesheet'):
            href = link.get('href')
            if href and not href.startswith(('http://', 'https://', 'data:')):
                from urllib.parse import urljoin
                resources.append(ResourceInfo(
                    url=urljoin(base_url, href),
                    local_path='',  # Will be set by downloader
                    resource_type='css'
                ))
        
        # Extract JS
        for script in soup.find_all('script', src=True):
            src = script.get('src')
            if src and not src.startswith(('http://', 'https://', 'data:')):
                from urllib.parse import urljoin
                resources.append(ResourceInfo(
                    url=urljoin(base_url, src),
                    local_path='',
                    resource_type='js'
                ))
        
        # Extract images
        for img in soup.find_all('img', src=True):
            src = img.get('src')
            if src and not src.startswith(('http://', 'https://', 'data:')):
                from urllib.parse import urljoin
                resources.append(ResourceInfo(
                    url=urljoin(base_url, src),
                    local_path='',
                    resource_type='img'
                ))
        
        return resources


class AsyncResourceDownloader(ABC):
    """Abstract base class for downloading static resources"""
    
    def __init__(self, session: aiohttp.ClientSession, output_dir: str, logger: Optional[logging.Logger] = None):
        self.session = session
        self.output_dir = output_dir
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.cache: Dict[str, str] = {}  # URL to local path mapping
    
    @abstractmethod
    async def download_resource(self, resource: ResourceInfo) -> Optional[str]:
        """
        Download a static resource
        
        Args:
            resource: ResourceInfo object
            
        Returns:
            Local path where resource was saved, or None if failed
        """
        pass
    
    @abstractmethod
    async def process_css_imports(self, css_content: str, base_url: str) -> List[ResourceInfo]:
        """
        Extract and process imports from CSS content
        
        Args:
            css_content: CSS content
            base_url: Base URL for resolving relative URLs
            
        Returns:
            List of additional resources to download
        """
        pass
    
    async def download_batch(self, resources: List[ResourceInfo]) -> Dict[str, str]:
        """
        Download multiple resources concurrently
        
        Args:
            resources: List of resources to download
            
        Returns:
            Mapping of URL to local path for successful downloads
        """
        import asyncio
        
        tasks = [self.download_resource(resource) for resource in resources]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        downloaded = {}
        for resource, result in zip(resources, results):
            if isinstance(result, str):
                downloaded[str(resource.url)] = result
            elif isinstance(result, Exception):
                self.logger.error(f"Failed to download {resource.url}: {result}")
        
        return downloaded