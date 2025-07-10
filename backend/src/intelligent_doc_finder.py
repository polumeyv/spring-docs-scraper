#!/usr/bin/env python3
"""
Intelligent documentation finder with AI-powered official site detection,
spell correction, and smart section discovery.
"""
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Tuple
import re
import logging
from urllib.parse import urlparse, quote_plus
from difflib import SequenceMatcher
import json

try:
    from google import genai
    from google.genai import types
    client = genai.Client()
    logger = logging.getLogger(__name__)
    logger.info("Google GenAI client initialized for intelligent doc finder")
except Exception as e:
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to initialize Google GenAI client: {e}")
    client = None

class IntelligentDocFinder:
    def __init__(self):
        self.session = None
        
        # Known framework corrections
        self.known_frameworks = {
            'react': ['reactjs', 'react.js', 'react js', 'reakt', 'raect'],
            'vue': ['vue.js', 'vuejs', 'vue js', 'veu', 'vuje'],
            'angular': ['angularjs', 'angular.js', 'angular js', 'anguar', 'angualr'],
            'svelte': ['sveltejs', 'svelte.js', 'svelet', 'svlte'],
            'spring': ['spring boot', 'springboot', 'spring framework', 'sprng', 'sprin'],
            'docker': ['dokcer', 'doker', 'dockere', 'docket'],
            'kubernetes': ['k8s', 'kube', 'kubernets', 'kuberentes', 'kubernetes.io'],
            'django': ['djago', 'djangoo', 'jango'],
            'flask': ['falsk', 'flsk', 'flask.py'],
            'laravel': ['larave', 'larvel', 'laravell'],
            'nextjs': ['next.js', 'next js', 'nextjs.org'],
            'typescript': ['ts', 'type script', 'typscript'],
            'javascript': ['js', 'java script', 'javscript'],
            'postgresql': ['postgres', 'postgre', 'postgresql.org'],
            'mongodb': ['mongo', 'mongo db', 'mongdb']
        }
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def find_official_documentation(self, user_input: str) -> Dict:
        """
        Find the single official documentation for a framework/tool.
        Returns either the official doc or a spell correction suggestion.
        """
        try:
            # Step 1: Normalize and check for spell corrections
            normalized_input = user_input.lower().strip().replace('-', ' ').replace('_', ' ')
            correction_result = self._check_spelling_correction(normalized_input)
            
            if correction_result['needs_correction']:
                return {
                    'type': 'spelling_suggestion',
                    'original_query': user_input,
                    'suggested_query': correction_result['suggested'],
                    'confidence': correction_result['confidence'],
                    'message': f"Did you mean '{correction_result['suggested']}'?"
                }
            
            # Step 2: Use AI to find the official documentation URL
            official_url = await self._find_official_url_with_ai(correction_result['corrected'])
            
            if not official_url:
                return {
                    'type': 'not_found',
                    'query': user_input,
                    'message': f"Could not find official documentation for '{user_input}'"
                }
            
            # Step 3: Discover sections/products intelligently
            sections = await self._discover_sections_with_ai(official_url, correction_result['corrected'])
            
            return {
                'type': 'official_documentation',
                'framework': correction_result['corrected'],
                'official_url': official_url,
                'sections': sections,
                'description': f"Official {correction_result['corrected']} documentation with {len(sections)} main sections discovered"
            }
            
        except Exception as e:
            logger.error(f"Error in intelligent doc finder: {e}")
            return {
                'type': 'error',
                'query': user_input,
                'message': f"Error finding documentation: {str(e)}"
            }
    
    def _check_spelling_correction(self, user_input: str) -> Dict:
        """Check if user input needs spelling correction"""
        best_match = None
        best_score = 0.0
        
        # Check against known frameworks
        for correct_name, variations in self.known_frameworks.items():
            # Check exact match first
            if user_input == correct_name:
                return {'needs_correction': False, 'corrected': correct_name}
            
            # Check variations
            for variation in variations:
                score = SequenceMatcher(None, user_input, variation).ratio()
                if score > best_score:
                    best_score = score
                    best_match = correct_name
            
            # Check against the correct name itself
            score = SequenceMatcher(None, user_input, correct_name).ratio()
            if score > best_score:
                best_score = score
                best_match = correct_name
        
        # If we found a close match (>70% similarity), suggest correction
        if best_match and best_score > 0.7 and user_input != best_match:
            return {
                'needs_correction': True,
                'corrected': best_match,
                'suggested': best_match,
                'confidence': best_score
            }
        
        return {'needs_correction': False, 'corrected': user_input}
    
    async def _find_official_url_with_ai(self, framework: str) -> Optional[str]:
        """Use AI and search to find the official documentation URL"""
        
        # First, try common patterns
        common_patterns = [
            f"https://{framework}.org/docs",
            f"https://docs.{framework}.org",
            f"https://{framework}.dev",
            f"https://docs.{framework}.com",
            f"https://{framework}.io/docs",
            f"https://docs.{framework}.io"
        ]
        
        # Special cases for known frameworks
        special_cases = {
            'react': 'https://react.dev',
            'vue': 'https://vuejs.org',
            'angular': 'https://angular.io',
            'svelte': 'https://svelte.dev',
            'spring': 'https://spring.io/projects',
            'docker': 'https://docs.docker.com',
            'kubernetes': 'https://kubernetes.io/docs',
            'django': 'https://docs.djangoproject.com',
            'flask': 'https://flask.palletsprojects.com',
            'laravel': 'https://laravel.com/docs',
            'nextjs': 'https://nextjs.org',
            'typescript': 'https://typescriptlang.org',
            'javascript': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript',
            'postgresql': 'https://postgresql.org/docs',
            'mongodb': 'https://docs.mongodb.com'
        }
        
        if framework in special_cases:
            return special_cases[framework]
        
        # Try common patterns
        for pattern in common_patterns:
            try:
                async with self.session.head(pattern, allow_redirects=True, timeout=3) as response:
                    if response.status < 400:
                        return str(response.url)
            except:
                continue
        
        # If AI is available, use it to search
        if client:
            try:
                return await self._ai_search_official_url(framework)
            except Exception as e:
                logger.error(f"AI search failed: {e}")
        
        # Fallback to DuckDuckGo search
        return await self._search_official_url_duckduckgo(framework)
    
    async def _ai_search_official_url(self, framework: str) -> Optional[str]:
        """Use AI to determine the official documentation URL"""
        if not client:
            return None
            
        prompt = f"""Find the official documentation website URL for {framework}.

Return ONLY the URL, nothing else. The URL should be the main official documentation site, not:
- GitHub repositories
- Tutorial sites
- Blog posts
- Third-party documentation

Examples:
- For "react": https://react.dev
- For "vue": https://vuejs.org
- For "django": https://docs.djangoproject.com
- For "docker": https://docs.docker.com

Framework: {framework}
Official documentation URL:"""

        try:
            response = await client.agenerate_content(
                model="gemini-1.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=100
                )
            )
            
            if response and response.text:
                # Extract URL from response
                url_pattern = r'https?://[^\s<>"\'`]+(?:/[^\s<>"\'`]*)?'
                urls = re.findall(url_pattern, response.text.strip())
                if urls:
                    return urls[0]
                    
        except Exception as e:
            logger.error(f"AI URL search error: {e}")
        
        return None
    
    async def _search_official_url_duckduckgo(self, framework: str) -> Optional[str]:
        """Search for official URL using DuckDuckGo"""
        try:
            query = f"{framework} official documentation site"
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            
            async with self.session.get(url, timeout=5) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Look for the first official-looking result
                    for result in soup.find_all('div', class_='result')[:5]:
                        link = result.find('a', class_='result__a')
                        if not link:
                            continue
                        
                        href = link.get('href')
                        title = link.get_text(strip=True).lower()
                        
                        # Check if it looks like official documentation
                        if self._is_official_documentation(href, title, framework):
                            return href
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
        
        return None
    
    def _is_official_documentation(self, url: str, title: str, framework: str) -> bool:
        """Check if a URL looks like official documentation"""
        url_lower = url.lower()
        title_lower = title.lower()
        framework_lower = framework.lower()
        
        # Exclude non-official sites
        exclude_domains = [
            'stackoverflow.com', 'reddit.com', 'medium.com', 'dev.to', 
            'youtube.com', 'github.com', 'tutorial', 'blog'
        ]
        
        if any(domain in url_lower for domain in exclude_domains):
            return False
        
        # Include if it has official indicators
        official_indicators = [
            f'{framework_lower}.org',
            f'{framework_lower}.io',
            f'{framework_lower}.dev',
            f'{framework_lower}.com',
            f'docs.{framework_lower}',
            f'{framework_lower}lang.org',  # For programming languages
        ]
        
        return any(indicator in url_lower for indicator in official_indicators)
    
    async def _discover_sections_with_ai(self, official_url: str, framework: str) -> List[Dict]:
        """Intelligently discover sections/products from the official documentation"""
        
        try:
            # Fetch the official page
            async with self.session.get(official_url, timeout=10) as response:
                if response.status != 200:
                    return self._get_fallback_sections(framework)
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract navigation and content structure
                navigation_data = self._extract_structured_navigation(soup, official_url)
                
                # Use AI to intelligently categorize and organize sections
                if client:
                    return await self._ai_organize_sections(navigation_data, framework, official_url)
                else:
                    return self._heuristic_organize_sections(navigation_data, framework)
                    
        except Exception as e:
            logger.error(f"Error discovering sections: {e}")
            return self._get_fallback_sections(framework)
    
    def _extract_structured_navigation(self, soup: BeautifulSoup, base_url: str) -> Dict:
        """Extract structured navigation from the page"""
        navigation_items = []
        main_sections = []
        
        # Look for navigation menus
        nav_selectors = [
            'nav[role="navigation"]', 'nav.main-nav', 'nav.primary-nav', 
            '.navbar', '.docs-nav', '.documentation-nav', '.sidebar-nav',
            '.nav', '.sidebar', 'aside'
        ]
        
        for selector in nav_selectors:
            elements = soup.select(selector)
            for element in elements:
                links = element.find_all('a', href=True)
                for link in links:
                    text = link.get_text(strip=True)
                    href = link['href']
                    
                    if text and len(text) < 100 and not href.startswith('#'):
                        navigation_items.append({
                            'text': text,
                            'url': href,
                            'level': len(link.find_parents(['ul', 'ol', 'nav']))
                        })
        
        # Look for main content sections
        content_selectors = [
            'main section', '.content section', '.main-content section',
            'article', '.docs-content', '.documentation-content'
        ]
        
        for selector in content_selectors:
            elements = soup.select(selector)
            for element in elements:
                heading = element.find(['h1', 'h2', 'h3'])
                if heading:
                    text = heading.get_text(strip=True)
                    if text and len(text) < 100:
                        main_sections.append({
                            'title': text,
                            'has_links': bool(element.find('a')),
                            'has_code': bool(element.find(['code', 'pre'])),
                            'level': int(heading.name[1]) if heading.name[1:].isdigit() else 2
                        })
        
        return {
            'navigation': navigation_items[:50],  # Limit to 50 items
            'sections': main_sections[:30],       # Limit to 30 sections
            'title': soup.find('title').text.strip() if soup.find('title') else '',
            'description': soup.find('meta', {'name': 'description'})['content'] if soup.find('meta', {'name': 'description'}) else ''
        }
    
    async def _ai_organize_sections(self, navigation_data: Dict, framework: str, base_url: str) -> List[Dict]:
        """Use AI to intelligently organize sections"""
        if not client:
            return self._heuristic_organize_sections(navigation_data, framework)
        
        prompt = f"""Analyze this {framework} documentation structure and organize it into main sections/products.

Framework: {framework}
Page Title: {navigation_data.get('title', '')}
Base URL: {base_url}

Navigation Items: {json.dumps(navigation_data.get('navigation', [])[:20], indent=2)}

Main Sections: {json.dumps(navigation_data.get('sections', [])[:15], indent=2)}

Based on this structure, identify the main sections/products/components of {framework}. 
For example:
- Spring has projects like Spring Boot, Spring Data, Spring Security
- Docker has components like Docker Desktop, Docker Engine, Docker Compose
- React has areas like Components, Hooks, API Reference

Return a JSON array of main sections with this structure:
[
  {{
    "id": "section-id",
    "name": "Section Name", 
    "description": "Brief description of what this section covers",
    "icon": "📚", 
    "category": "core|tools|guides|api",
    "url": "relative or absolute URL",
    "priority": 1
  }}
]

Focus on the most important 6-8 sections that users would typically need. Avoid generic sections like "Home" or "About".

JSON response:"""

        try:
            response = await client.agenerate_content(
                model="gemini-1.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=2000
                )
            )
            
            if response and response.text:
                # Extract JSON from response
                json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
                if json_match:
                    sections = json.loads(json_match.group())
                    return sections[:8]  # Limit to 8 sections
                    
        except Exception as e:
            logger.error(f"AI section organization error: {e}")
        
        return self._heuristic_organize_sections(navigation_data, framework)
    
    def _heuristic_organize_sections(self, navigation_data: Dict, framework: str) -> List[Dict]:
        """Organize sections using heuristic rules when AI is not available"""
        sections = []
        navigation = navigation_data.get('navigation', [])
        
        # Score navigation items based on importance
        scored_items = []
        for item in navigation:
            score = self._score_navigation_item(item['text'], framework)
            if score > 0:
                scored_items.append((item, score))
        
        # Sort by score and take top items
        scored_items.sort(key=lambda x: x[1], reverse=True)
        
        # Convert to structured sections
        for i, (item, score) in enumerate(scored_items[:8]):
            category = self._categorize_section(item['text'])
            sections.append({
                'id': item['text'].lower().replace(' ', '-').replace('/', '-'),
                'name': item['text'],
                'description': f"Documentation for {item['text']}",
                'icon': self._get_section_icon(category),
                'category': category,
                'url': item['url'],
                'priority': i + 1
            })
        
        return sections
    
    def _score_navigation_item(self, text: str, framework: str) -> int:
        """Score a navigation item based on importance"""
        text_lower = text.lower()
        framework_lower = framework.lower()
        
        # Skip generic items
        skip_terms = ['home', 'about', 'contact', 'blog', 'news', 'download']
        if any(term in text_lower for term in skip_terms):
            return 0
        
        score = 5  # Base score
        
        # Boost if contains framework name
        if framework_lower in text_lower:
            score += 10
        
        # Boost for important sections
        important_terms = ['api', 'docs', 'guide', 'tutorial', 'reference', 'getting started']
        for term in important_terms:
            if term in text_lower:
                score += 7
        
        # Boost for product/component names
        product_terms = ['boot', 'data', 'security', 'cloud', 'engine', 'desktop', 'compose']
        for term in product_terms:
            if term in text_lower:
                score += 8
        
        return score
    
    def _categorize_section(self, text: str) -> str:
        """Categorize a section"""
        text_lower = text.lower()
        
        if any(term in text_lower for term in ['api', 'reference']):
            return 'api'
        elif any(term in text_lower for term in ['guide', 'tutorial', 'getting started']):
            return 'guides'  
        elif any(term in text_lower for term in ['tool', 'cli', 'desktop', 'engine']):
            return 'tools'
        else:
            return 'core'
    
    def _get_section_icon(self, category: str) -> str:
        """Get an icon for a section category"""
        icons = {
            'core': '📚',
            'api': '⚙️', 
            'guides': '📖',
            'tools': '🔧'
        }
        return icons.get(category, '📄')
    
    def _get_fallback_sections(self, framework: str) -> List[Dict]:
        """Get fallback sections when discovery fails"""
        fallback_sections = {
            'spring': [
                {'id': 'spring-boot', 'name': 'Spring Boot', 'description': 'Production-ready applications', 'icon': '🚀', 'category': 'core'},
                {'id': 'spring-data', 'name': 'Spring Data', 'description': 'Data access framework', 'icon': '💾', 'category': 'core'},
                {'id': 'spring-security', 'name': 'Spring Security', 'description': 'Authentication and authorization', 'icon': '🔒', 'category': 'core'},
                {'id': 'spring-cloud', 'name': 'Spring Cloud', 'description': 'Distributed systems patterns', 'icon': '☁️', 'category': 'core'}
            ],
            'docker': [
                {'id': 'docker-desktop', 'name': 'Docker Desktop', 'description': 'Local development environment', 'icon': '🖥️', 'category': 'tools'},
                {'id': 'docker-engine', 'name': 'Docker Engine', 'description': 'Core containerization technology', 'icon': '⚙️', 'category': 'core'},
                {'id': 'docker-compose', 'name': 'Docker Compose', 'description': 'Multi-container applications', 'icon': '🔧', 'category': 'tools'},
                {'id': 'docker-hub', 'name': 'Docker Hub', 'description': 'Container registry', 'icon': '🌐', 'category': 'tools'}
            ],
            'react': [
                {'id': 'components', 'name': 'Components', 'description': 'Building UI components', 'icon': '🧩', 'category': 'core'},
                {'id': 'hooks', 'name': 'Hooks', 'description': 'State and lifecycle management', 'icon': '🪝', 'category': 'core'},
                {'id': 'api', 'name': 'API Reference', 'description': 'Complete API documentation', 'icon': '⚙️', 'category': 'api'},
                {'id': 'tutorial', 'name': 'Tutorial', 'description': 'Learn React step by step', 'icon': '📖', 'category': 'guides'}
            ]
        }
        
        framework_lower = framework.lower()
        sections = fallback_sections.get(framework_lower, [
            {'id': 'getting-started', 'name': 'Getting Started', 'description': f'Introduction to {framework}', 'icon': '🚀', 'category': 'guides'},
            {'id': 'documentation', 'name': 'Documentation', 'description': f'Complete {framework} documentation', 'icon': '📚', 'category': 'core'},
            {'id': 'api', 'name': 'API Reference', 'description': f'{framework} API reference', 'icon': '⚙️', 'category': 'api'}
        ])
        
        # Add priority and URL to fallback sections
        for i, section in enumerate(sections):
            section['priority'] = i + 1
            section['url'] = '#'  # Placeholder URL
        
        return sections