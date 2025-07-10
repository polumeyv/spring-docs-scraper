#!/usr/bin/env python3
"""
Intelligent Scraper Service with route deduplication and layout detection
"""
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
import re
import hashlib
import logging
from typing import Set, List, Dict, Optional, Callable
from collections import defaultdict

logger = logging.getLogger(__name__)

class IntelligentScraperService:
    def __init__(self, progress_callback: Callable):
        self.progress_callback = progress_callback
        self.session = None
        self.seen_patterns = set()
        self.layout_signatures = defaultdict(int)
        self.common_elements = {}
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def scrape_topic(self, task_id: str, topic_url: str, topic_name: str, framework: str):
        """
        Intelligently scrape a specific documentation topic
        """
        try:
            # Phase 1: Discovery with intelligent deduplication
            await self.progress_callback(task_id, {
                'status': 'discovering',
                'phase': 'route_analysis',
                'progress': 5,
                'message': f'Analyzing {topic_name} documentation structure...'
            })
            
            routes = await self._discover_routes_intelligently(topic_url, task_id)
            total_routes = len(routes)
            
            await self.progress_callback(task_id, {
                'status': 'discovering',
                'phase': 'layout_detection',
                'progress': 15,
                'message': f'Found {total_routes} unique routes. Detecting layout patterns...',
                'total_routes': total_routes
            })
            
            # Phase 2: Layout detection
            layout_info = await self._detect_layout_patterns(routes[:5], task_id)
            
            await self.progress_callback(task_id, {
                'status': 'scraping',
                'phase': 'content_extraction',
                'progress': 20,
                'message': f'Starting intelligent content extraction...',
                'layout_detected': bool(layout_info),
                'total_pages': total_routes,
                'pages_scraped': 0
            })
            
            # Phase 3: Intelligent scraping
            scraped_content = []
            for i, route in enumerate(routes):
                try:
                    content = await self._scrape_page_intelligently(route, layout_info)
                    if content:
                        scraped_content.append(content)
                    
                    # Update progress
                    pages_scraped = i + 1
                    progress = 20 + int((pages_scraped / total_routes) * 70)
                    
                    await self.progress_callback(task_id, {
                        'status': 'scraping',
                        'progress': progress,
                        'message': f'Extracting content from {topic_name} documentation...',
                        'pages_scraped': pages_scraped,
                        'current_page': route['url'],
                        'current_content': content['preview'] if content else None
                    })
                    
                    # Rate limiting
                    await asyncio.sleep(0.2)
                    
                except Exception as e:
                    logger.error(f"Error scraping {route['url']}: {e}")
                    continue
            
            # Phase 4: Post-processing
            await self.progress_callback(task_id, {
                'status': 'processing',
                'progress': 95,
                'message': 'Processing and organizing content...'
            })
            
            # Organize content by sections
            organized_content = self._organize_content(scraped_content, topic_name)
            
            await self.progress_callback(task_id, {
                'status': 'completed',
                'progress': 100,
                'message': f'Successfully scraped {len(scraped_content)} pages from {topic_name}!',
                'total_scraped': len(scraped_content),
                'organized_content': organized_content
            })
            
        except Exception as e:
            logger.error(f"Scraping error: {e}")
            await self.progress_callback(task_id, {
                'status': 'error',
                'message': f'Error: {str(e)}',
                'error': str(e)
            })
    
    async def _discover_routes_intelligently(self, start_url: str, task_id: str) -> List[Dict]:
        """
        Discover routes with intelligent deduplication
        """
        routes = []
        seen_urls = set()
        seen_patterns = set()
        to_visit = {start_url}
        visited = set()
        
        # Parse base URL for scope
        parsed_start = urlparse(start_url)
        base_path = parsed_start.path.rstrip('/')
        
        while to_visit and len(routes) < 200:  # Reasonable limit
            url = to_visit.pop()
            if url in visited:
                continue
                
            visited.add(url)
            
            # Check if this matches a known dynamic pattern
            pattern = self._extract_url_pattern(url)
            if pattern in seen_patterns and self._is_likely_dynamic_route(url):
                continue
            
            try:
                async with self.session.get(url, timeout=5) as response:
                    if response.status != 200:
                        continue
                    
                    content = await response.text()
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Add current page if it's documentation
                    if self._is_documentation_page(soup):
                        routes.append({
                            'url': url,
                            'pattern': pattern,
                            'title': soup.find('title').text if soup.find('title') else '',
                            'type': self._classify_page_type(soup, url)
                        })
                        seen_patterns.add(pattern)
                    
                    # Update discovery progress
                    if len(routes) % 10 == 0:
                        await self.progress_callback(task_id, {
                            'status': 'discovering',
                            'progress': 5 + min(10, len(routes) // 10),
                            'message': f'Discovering routes... Found {len(routes)} unique pages'
                        })
                    
                    # Find links within scope
                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        absolute_url = urljoin(url, href)
                        parsed = urlparse(absolute_url)
                        
                        # Stay within topic scope
                        if (parsed.netloc == parsed_start.netloc and 
                            parsed.path.startswith(base_path) and
                            absolute_url not in visited and
                            not self._should_skip_url(absolute_url)):
                            to_visit.add(absolute_url)
                            
            except Exception as e:
                logger.debug(f"Error discovering {url}: {e}")
                continue
        
        return routes
    
    def _extract_url_pattern(self, url: str) -> str:
        """Extract pattern from URL for deduplication"""
        path = urlparse(url).path
        
        # Replace common dynamic segments
        patterns = [
            (r'/\d+', '/{id}'),  # Numeric IDs
            (r'/[0-9a-f]{8,}', '/{hash}'),  # Hashes
            (r'/v\d+(\.\d+)*', '/v{version}'),  # Versions
            (r'/\d{4}/\d{2}/\d{2}', '/{date}'),  # Dates
            (r'/[a-z]{2}-[A-Z]{2}', '/{locale}'),  # Locales
            (r'/page/\d+', '/page/{n}'),  # Pagination
        ]
        
        pattern = path
        for regex, replacement in patterns:
            pattern = re.sub(regex, replacement, pattern)
        
        return pattern
    
    def _is_likely_dynamic_route(self, url: str) -> bool:
        """Check if URL is likely a dynamic route"""
        path = urlparse(url).path
        
        # Common indicators of dynamic routes
        dynamic_indicators = [
            r'/\d+$',  # Ends with number
            r'/page/\d+',  # Pagination
            r'/[0-9a-f]{24,}',  # MongoDB ObjectId
            r'/\d{4}/\d{2}/\d{2}',  # Date
            r'#',  # Anchor links
        ]
        
        return any(re.search(pattern, path) for pattern in dynamic_indicators)
    
    def _should_skip_url(self, url: str) -> bool:
        """Determine if URL should be skipped"""
        skip_patterns = [
            r'/api/',  # API endpoints
            r'/assets/',  # Static assets
            r'/images/',
            r'/downloads/',
            r'\.(jpg|jpeg|png|gif|svg|pdf|zip)$',  # Binary files
            r'/search\?',  # Search results
            r'/login',  # Auth pages
            r'/register',
            r'/404',  # Error pages
        ]
        
        return any(re.search(pattern, url.lower()) for pattern in skip_patterns)
    
    def _is_documentation_page(self, soup: BeautifulSoup) -> bool:
        """Check if page contains documentation content"""
        # Look for documentation indicators
        indicators = [
            soup.find(['article', 'main']),
            soup.find(class_=re.compile(r'doc|content|prose|markdown')),
            soup.find('pre', class_=re.compile(r'code|language-')),
            len(soup.find_all(['h1', 'h2', 'h3'])) > 2,
            len(soup.find_all('p')) > 5
        ]
        
        return sum(bool(i) for i in indicators) >= 2
    
    def _classify_page_type(self, soup: BeautifulSoup, url: str) -> str:
        """Classify the type of documentation page"""
        title = soup.find('title').text.lower() if soup.find('title') else ''
        path = urlparse(url).path.lower()
        
        if any(term in path or term in title for term in ['api', 'reference']):
            return 'api_reference'
        elif any(term in path or term in title for term in ['guide', 'tutorial', 'getting-started']):
            return 'guide'
        elif any(term in path or term in title for term in ['example', 'sample', 'demo']):
            return 'example'
        elif any(term in path or term in title for term in ['concept', 'overview', 'introduction']):
            return 'concept'
        else:
            return 'general'
    
    async def _detect_layout_patterns(self, sample_routes: List[Dict], task_id: str) -> Dict:
        """Detect common layout patterns from sample pages"""
        layout_elements = defaultdict(list)
        
        for route in sample_routes:
            try:
                async with self.session.get(route['url'], timeout=5) as response:
                    if response.status != 200:
                        continue
                    
                    content = await response.text()
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Extract layout elements
                    for selector in ['header', 'nav', 'aside', 'footer', '.sidebar', '.navigation']:
                        elements = soup.select(selector)
                        for elem in elements:
                            # Create signature of element
                            signature = self._create_element_signature(elem)
                            layout_elements[selector].append(signature)
                    
            except Exception as e:
                logger.debug(f"Error analyzing layout: {e}")
        
        # Find common elements (appear in >60% of pages)
        common_layout = {}
        for selector, signatures in layout_elements.items():
            if signatures:
                # Count occurrences
                sig_counts = defaultdict(int)
                for sig in signatures:
                    sig_counts[sig] += 1
                
                # Find most common
                threshold = len(sample_routes) * 0.6
                for sig, count in sig_counts.items():
                    if count >= threshold:
                        common_layout[selector] = sig
        
        return common_layout
    
    def _create_element_signature(self, element) -> str:
        """Create a signature for an element based on its structure"""
        # Get element structure without text content
        structure = []
        for child in element.find_all(recursive=False):
            structure.append(f"{child.name}:{','.join(child.get('class', []))}")
        
        return hashlib.md5('|'.join(structure).encode()).hexdigest()
    
    async def _scrape_page_intelligently(self, route: Dict, layout_info: Dict) -> Optional[Dict]:
        """Scrape page content while removing common layout elements"""
        try:
            async with self.session.get(route['url'], timeout=5) as response:
                if response.status != 200:
                    return None
                
                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Remove common layout elements
                for selector in layout_info.keys():
                    for elem in soup.select(selector):
                        elem.decompose()
                
                # Remove script and style tags
                for tag in soup(['script', 'style', 'meta', 'link']):
                    tag.decompose()
                
                # Extract main content
                main_content = None
                content_selectors = [
                    'main', 'article', '.content', '#content', 
                    '.documentation', '.docs-content', '.prose'
                ]
                
                for selector in content_selectors:
                    main_content = soup.select_one(selector)
                    if main_content:
                        break
                
                if not main_content:
                    main_content = soup.find('body')
                
                # Extract structured content
                if main_content:
                    # Extract headings and their content
                    sections = []
                    current_section = None
                    
                    for elem in main_content.children:
                        if elem.name in ['h1', 'h2', 'h3']:
                            if current_section:
                                sections.append(current_section)
                            current_section = {
                                'heading': elem.get_text(strip=True),
                                'level': int(elem.name[1]),
                                'content': []
                            }
                        elif current_section and hasattr(elem, 'get_text'):
                            text = elem.get_text(strip=True)
                            if text:
                                current_section['content'].append(text)
                    
                    if current_section:
                        sections.append(current_section)
                    
                    # Extract code examples
                    code_blocks = []
                    for code in main_content.find_all(['pre', 'code']):
                        code_text = code.get_text(strip=True)
                        if len(code_text) > 20:  # Skip tiny snippets
                            code_blocks.append({
                                'code': code_text,
                                'language': code.get('class', [''])[0].replace('language-', '') if code.get('class') else 'text'
                            })
                    
                    # Create preview
                    all_text = main_content.get_text(separator=' ', strip=True)
                    preview = all_text[:300] + '...' if len(all_text) > 300 else all_text
                    
                    return {
                        'url': route['url'],
                        'title': route['title'],
                        'type': route['type'],
                        'sections': sections,
                        'code_examples': code_blocks[:5],  # Limit code examples
                        'preview': preview,
                        'word_count': len(all_text.split())
                    }
                    
        except Exception as e:
            logger.error(f"Error scraping page {route['url']}: {e}")
            return None
    
    def _organize_content(self, scraped_content: List[Dict], topic_name: str) -> Dict:
        """Organize scraped content by type and structure"""
        organized = {
            'topic': topic_name,
            'total_pages': len(scraped_content),
            'total_words': sum(page.get('word_count', 0) for page in scraped_content),
            'content_by_type': defaultdict(list),
            'table_of_contents': []
        }
        
        # Group by type
        for page in scraped_content:
            page_type = page.get('type', 'general')
            organized['content_by_type'][page_type].append({
                'title': page['title'],
                'url': page['url'],
                'sections': len(page.get('sections', [])),
                'code_examples': len(page.get('code_examples', []))
            })
        
        # Create table of contents
        for page_type, pages in organized['content_by_type'].items():
            organized['table_of_contents'].append({
                'type': page_type,
                'count': len(pages),
                'pages': pages[:10]  # Sample of pages
            })
        
        return organized