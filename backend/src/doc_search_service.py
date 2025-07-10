#!/usr/bin/env python3
"""
Documentation search service that finds official documentation links for frameworks and tools.
"""
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Set
import re
import logging
from urllib.parse import urlparse, quote_plus

logger = logging.getLogger(__name__)

# Known documentation domains for various frameworks
KNOWN_DOC_DOMAINS = {
    # JavaScript/TypeScript
    'react': ['react.dev', 'legacy.reactjs.org'],
    'vue': ['vuejs.org', 'v3.vuejs.org'],
    'angular': ['angular.io', 'angular.dev'],
    'svelte': ['svelte.dev', 'kit.svelte.dev'],
    'next': ['nextjs.org'],
    'nuxt': ['nuxtjs.org', 'nuxt.com'],
    'nodejs': ['nodejs.org'],
    'express': ['expressjs.com'],
    'nestjs': ['nestjs.com', 'docs.nestjs.com'],
    'gatsby': ['gatsbyjs.com'],
    'remix': ['remix.run'],
    
    # Python
    'django': ['djangoproject.com', 'docs.djangoproject.com'],
    'flask': ['flask.palletsprojects.com'],
    'fastapi': ['fastapi.tiangolo.com'],
    'pytest': ['pytest.org', 'docs.pytest.org'],
    'numpy': ['numpy.org'],
    'pandas': ['pandas.pydata.org'],
    'scipy': ['scipy.org', 'docs.scipy.org'],
    'tensorflow': ['tensorflow.org'],
    'pytorch': ['pytorch.org'],
    'scikit-learn': ['scikit-learn.org'],
    
    # Java/Spring
    'spring': ['spring.io', 'docs.spring.io'],
    'springboot': ['spring.io', 'docs.spring.io'],
    'hibernate': ['hibernate.org'],
    'maven': ['maven.apache.org'],
    'gradle': ['gradle.org', 'docs.gradle.org'],
    
    # PHP
    'laravel': ['laravel.com'],
    'symfony': ['symfony.com'],
    'wordpress': ['developer.wordpress.org', 'codex.wordpress.org'],
    
    # Ruby
    'rails': ['rubyonrails.org', 'guides.rubyonrails.org', 'api.rubyonrails.org'],
    'ruby': ['ruby-lang.org', 'ruby-doc.org'],
    
    # Go
    'go': ['golang.org', 'go.dev', 'pkg.go.dev'],
    'gin': ['gin-gonic.com'],
    'echo': ['echo.labstack.com'],
    
    # Rust
    'rust': ['rust-lang.org', 'doc.rust-lang.org'],
    'tokio': ['tokio.rs'],
    'actix': ['actix.rs'],
    
    # Database
    'postgresql': ['postgresql.org'],
    'mysql': ['dev.mysql.com'],
    'mongodb': ['mongodb.com', 'docs.mongodb.com'],
    'redis': ['redis.io'],
    'elasticsearch': ['elastic.co'],
    
    # Mobile
    'flutter': ['flutter.dev', 'docs.flutter.dev', 'api.flutter.dev'],
    'reactnative': ['reactnative.dev'],
    'kotlin': ['kotlinlang.org'],
    'swift': ['swift.org', 'developer.apple.com/swift'],
    
    # Cloud/DevOps
    'docker': ['docs.docker.com'],
    'kubernetes': ['kubernetes.io'],
    'aws': ['docs.aws.amazon.com'],
    'azure': ['docs.microsoft.com/azure', 'azure.microsoft.com'],
    'gcp': ['cloud.google.com'],
    'terraform': ['terraform.io', 'registry.terraform.io'],
    'ansible': ['ansible.com', 'docs.ansible.com'],
}

# Documentation URL patterns
DOC_PATTERNS = {
    'official': [
        r'(?:docs?|documentation|guide|manual|reference)\.{framework}\.(?:org|io|com|dev)',
        r'{framework}\.(?:org|io|com|dev)/(?:docs?|documentation|guide|manual|reference)',
        r'{framework}\.readthedocs\.io',
        r'(?:learn|tutorial)\.{framework}\.(?:org|io|com|dev)',
    ],
    'api': [
        r'api\.{framework}\.(?:org|io|com|dev)',
        r'{framework}\.(?:org|io|com|dev)/api',
        r'(?:javadoc|apidoc|reference)\.{framework}\.(?:org|io|com|dev)',
    ],
    'github': [
        r'github\.com/{framework}(?:/{framework})?',
        r'github\.com/(?:[\w-]+)/{framework}',
    ]
}


class DocSearchService:
    def __init__(self):
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def search_documentation(self, framework: str) -> List[Dict]:
        """Search for documentation links for a given framework/tool"""
        framework_lower = framework.lower().replace(' ', '').replace('-', '')
        
        # Run multiple search strategies in parallel
        tasks = [
            self._search_known_domains(framework, framework_lower),
            self._search_google(framework),
            self._search_github(framework, framework_lower),
            self._search_devdocs(framework),
        ]
        
        all_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine and deduplicate results
        combined_results = []
        seen_domains = set()
        
        for results in all_results:
            if isinstance(results, Exception):
                logger.error(f"Search error: {results}")
                continue
                
            for result in results:
                domain = urlparse(result['url']).netloc
                if domain not in seen_domains:
                    seen_domains.add(domain)
                    combined_results.append(result)
        
        # Sort by relevance (official docs first, then by type)
        type_priority = {'official': 0, 'api': 1, 'tutorial': 2, 'reference': 3, 'github': 4}
        combined_results.sort(key=lambda x: type_priority.get(x['type'], 5))
        
        # Ensure we have at least 5 results
        if len(combined_results) < 5:
            combined_results.extend(self._get_fallback_links(framework))
        
        return combined_results[:5]
    
    async def _search_known_domains(self, framework: str, framework_lower: str) -> List[Dict]:
        """Check known documentation domains"""
        results = []
        
        if framework_lower in KNOWN_DOC_DOMAINS:
            domains = KNOWN_DOC_DOMAINS[framework_lower]
            
            for domain in domains[:3]:  # Check top 3 known domains
                url = f"https://{domain}"
                try:
                    async with self.session.head(url, allow_redirects=True, timeout=3) as response:
                        if response.status == 200:
                            doc_type = 'api' if 'api' in domain else 'official'
                            results.append({
                                'title': f"{framework} Official Documentation",
                                'url': str(response.url),
                                'type': doc_type,
                                'description': f"Official {framework} documentation and guides"
                            })
                            break
                except:
                    continue
        
        return results
    
    async def _search_google(self, framework: str) -> List[Dict]:
        """Search Google for documentation links"""
        results = []
        query = f"{framework} official documentation site:*.org OR site:*.io OR site:*.com OR site:*.dev"
        
        try:
            # Using Google's JSON API (limited but free)
            search_url = f"https://www.googleapis.com/customsearch/v1?q={quote_plus(query)}&num=10"
            
            # Fallback to scraping Google search results
            search_url = f"https://www.google.com/search?q={quote_plus(query)}"
            
            async with self.session.get(search_url, timeout=5) as response:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Parse Google search results
                for g in soup.find_all('div', class_='g')[:5]:
                    link = g.find('a', href=True)
                    title_elem = g.find('h3')
                    
                    if link and title_elem:
                        url = link['href']
                        title = title_elem.get_text(strip=True)
                        
                        # Skip Google's own URLs
                        if 'google.com' in url:
                            continue
                        
                        doc_type = self._categorize_url(url, title)
                        if doc_type:
                            snippet = g.find('span', class_='aCOpRe')
                            description = snippet.get_text(strip=True) if snippet else ''
                            
                            results.append({
                                'title': title,
                                'url': url,
                                'type': doc_type,
                                'description': description[:200] + '...' if len(description) > 200 else description
                            })
        except Exception as e:
            logger.error(f"Google search error: {e}")
        
        return results
    
    async def _search_github(self, framework: str, framework_lower: str) -> List[Dict]:
        """Search GitHub for the framework repository"""
        results = []
        
        try:
            # Search GitHub API
            search_url = f"https://api.github.com/search/repositories?q={framework_lower}+in:name&sort=stars&order=desc"
            
            async with self.session.get(search_url, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for repo in data.get('items', [])[:3]:
                        # Check if repo name matches framework
                        if framework_lower in repo['name'].lower():
                            results.append({
                                'title': f"{repo['full_name']} - GitHub",
                                'url': repo['html_url'],
                                'type': 'github',
                                'description': repo.get('description', 'Source code and examples')[:200]
                            })
                            break
        except Exception as e:
            logger.error(f"GitHub search error: {e}")
        
        return results
    
    async def _search_devdocs(self, framework: str) -> List[Dict]:
        """Check if framework is available on DevDocs"""
        results = []
        
        try:
            # DevDocs has a predictable URL pattern
            devdocs_url = f"https://devdocs.io/{framework.lower().replace(' ', '_')}"
            
            async with self.session.head(devdocs_url, allow_redirects=False, timeout=3) as response:
                if response.status in [200, 301, 302]:
                    results.append({
                        'title': f"{framework} - DevDocs",
                        'url': devdocs_url,
                        'type': 'reference',
                        'description': f"API documentation for {framework} on DevDocs"
                    })
        except:
            pass
        
        return results
    
    def _categorize_url(self, url: str, title: str) -> Optional[str]:
        """Categorize a URL based on its content"""
        url_lower = url.lower()
        title_lower = title.lower()
        
        if 'github.com' in url_lower:
            return 'github'
        elif any(term in url_lower for term in ['api', 'javadoc', 'apidoc', 'reference/api']):
            return 'api'
        elif any(term in title_lower for term in ['getting started', 'tutorial', 'guide', 'quickstart', 'learn']):
            return 'tutorial'
        elif any(term in url_lower for term in ['/docs', '/documentation', '/reference', '/manual']):
            return 'official'
        elif 'reference' in url_lower or 'manual' in url_lower:
            return 'reference'
        
        return None
    
    def _get_fallback_links(self, framework: str) -> List[Dict]:
        """Get fallback links when not enough results are found"""
        return [
            {
                'title': f"Search {framework} on DevDocs",
                'url': f"https://devdocs.io/search?q={quote_plus(framework)}",
                'type': 'reference',
                'description': 'Search DevDocs for API documentation'
            },
            {
                'title': f"Search {framework} on MDN",
                'url': f"https://developer.mozilla.org/en-US/search?q={quote_plus(framework)}",
                'type': 'tutorial',
                'description': 'Search MDN Web Docs for tutorials and guides'
            },
            {
                'title': f"Search {framework} on Stack Overflow",
                'url': f"https://stackoverflow.com/questions/tagged/{quote_plus(framework.lower())}",
                'type': 'reference',
                'description': 'Browse questions and answers about ' + framework
            }
        ]