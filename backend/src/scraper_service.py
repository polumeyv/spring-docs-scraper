#!/usr/bin/env python3
"""
Simplified scraping service with real-time progress updates
"""
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
import logging
from typing import Callable, Set

logger = logging.getLogger(__name__)

class ScraperService:
    def __init__(self, progress_callback: Callable):
        self.progress_callback = progress_callback
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def scrape_documentation(self, task_id: str, url: str, framework: str):
        """Scrape documentation with real-time progress updates"""
        try:
            # Update status to starting
            await self.progress_callback(task_id, {
                'status': 'starting',
                'progress': 0,
                'message': f'Starting to scrape {framework} documentation...'
            })
            
            # Parse the base URL
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # Create output directory
            output_dir = f"/tmp/docs/{framework}"
            os.makedirs(output_dir, exist_ok=True)
            
            # Phase 1: Discover pages
            await self.progress_callback(task_id, {
                'status': 'discovering',
                'progress': 10,
                'message': 'Discovering documentation pages...'
            })
            
            pages = await self._discover_pages(url, base_url, task_id)
            total_pages = len(pages)
            
            await self.progress_callback(task_id, {
                'status': 'scraping',
                'progress': 20,
                'message': f'Found {total_pages} pages to scrape',
                'total_pages': total_pages,
                'pages_scraped': 0
            })
            
            # Phase 2: Scrape pages
            scraped_content = []
            for i, page_url in enumerate(pages):
                try:
                    content = await self._scrape_page(page_url)
                    if content:
                        scraped_content.append({
                            'url': page_url,
                            'title': content.get('title', 'Untitled'),
                            'content': content.get('text', '')[:500] + '...'  # Preview
                        })
                    
                    # Update progress
                    pages_scraped = i + 1
                    progress = 20 + int((pages_scraped / total_pages) * 70)
                    
                    await self.progress_callback(task_id, {
                        'status': 'scraping',
                        'progress': progress,
                        'message': f'Scraped {pages_scraped} of {total_pages} pages',
                        'pages_scraped': pages_scraped,
                        'current_page': page_url,
                        'scraped_content': scraped_content[-5:]  # Last 5 pages
                    })
                    
                    # Small delay to avoid overwhelming
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Error scraping {page_url}: {e}")
                    continue
            
            # Phase 3: Complete
            await self.progress_callback(task_id, {
                'status': 'completed',
                'progress': 100,
                'message': f'Successfully scraped {len(scraped_content)} pages!',
                'total_scraped': len(scraped_content),
                'scraped_content': scraped_content[-10:]  # Last 10 pages
            })
            
        except Exception as e:
            logger.error(f"Scraping error: {e}")
            await self.progress_callback(task_id, {
                'status': 'error',
                'progress': 0,
                'message': f'Error: {str(e)}',
                'error': str(e)
            })
    
    async def _discover_pages(self, start_url: str, base_url: str, task_id: str) -> list:
        """Discover documentation pages"""
        pages = set()
        to_visit = {start_url}
        visited = set()
        
        while to_visit and len(pages) < 50:  # Limit for demo
            url = to_visit.pop()
            if url in visited:
                continue
                
            visited.add(url)
            
            try:
                async with self.session.get(url, timeout=5) as response:
                    if response.status != 200:
                        continue
                        
                    content = await response.text()
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Add current page
                    pages.add(url)
                    
                    # Update discovery progress
                    if len(pages) % 5 == 0:
                        await self.progress_callback(task_id, {
                            'status': 'discovering',
                            'progress': 10 + min(10, len(pages) // 5),
                            'message': f'Discovering pages... Found {len(pages)} so far'
                        })
                    
                    # Find documentation links
                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        
                        # Skip non-documentation links
                        if href.startswith('#') or href.startswith('mailto:'):
                            continue
                            
                        # Convert to absolute URL
                        absolute_url = urljoin(url, href)
                        
                        # Only follow same domain and documentation-like URLs
                        if (absolute_url.startswith(base_url) and 
                            any(keyword in absolute_url.lower() for keyword in ['docs', 'guide', 'api', 'reference']) and
                            absolute_url not in visited):
                            to_visit.add(absolute_url)
                            
            except Exception as e:
                logger.debug(f"Error discovering {url}: {e}")
                continue
        
        return list(pages)
    
    async def _scrape_page(self, url: str) -> dict:
        """Scrape a single page and extract content"""
        try:
            async with self.session.get(url, timeout=5) as response:
                if response.status != 200:
                    return None
                    
                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Extract title
                title = soup.find('title')
                title_text = title.text.strip() if title else urlparse(url).path
                
                # Extract main content
                # Try common content containers
                main_content = None
                for selector in ['main', 'article', '.content', '#content', '.documentation', '.doc-content']:
                    main_content = soup.select_one(selector)
                    if main_content:
                        break
                
                if not main_content:
                    main_content = soup.find('body')
                
                # Extract text
                if main_content:
                    # Remove script and style elements
                    for script in main_content(['script', 'style']):
                        script.decompose()
                    
                    text = main_content.get_text(separator=' ', strip=True)
                else:
                    text = ''
                
                return {
                    'title': title_text,
                    'text': text,
                    'url': url
                }
                    
        except Exception as e:
            logger.error(f"Error scraping page {url}: {e}")
            return None