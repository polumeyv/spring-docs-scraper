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
from urllib.parse import urlparse, quote_plus, urljoin
import json

logger = logging.getLogger(__name__)

# Known documentation domains for various frameworks
KNOWN_DOC_DOMAINS = {
    # JavaScript/TypeScript
    'react': ['react.dev', 'legacy.reactjs.org'],
    'vue': ['vuejs.org', 'v3.vuejs.org'],
    'angular': ['angular.io', 'angular.dev'],
    'svelte': ['svelte.dev', 'kit.svelte.dev'],
    'next': ['nextjs.org'],
    'nextjs': ['nextjs.org'],
    'nuxt': ['nuxt.com', 'nuxtjs.org'],
    'node': ['nodejs.org/docs', 'nodejs.org/api'],
    'nodejs': ['nodejs.org/docs', 'nodejs.org/api'],
    'express': ['expressjs.com'],
    'nestjs': ['docs.nestjs.com', 'nestjs.com'],
    'gatsby': ['gatsbyjs.com'],
    'remix': ['remix.run/docs'],
    'typescript': ['typescriptlang.org/docs'],
    'javascript': ['developer.mozilla.org/en-US/docs/Web/JavaScript'],
    
    # Python
    'django': ['docs.djangoproject.com', 'djangoproject.com'],
    'flask': ['flask.palletsprojects.com'],
    'fastapi': ['fastapi.tiangolo.com'],
    'python': ['docs.python.org'],
    'pytest': ['docs.pytest.org', 'pytest.org'],
    'numpy': ['numpy.org/doc'],
    'pandas': ['pandas.pydata.org/docs'],
    'scipy': ['docs.scipy.org', 'scipy.org'],
    'tensorflow': ['tensorflow.org/api_docs'],
    'pytorch': ['pytorch.org/docs'],
    'scikit-learn': ['scikit-learn.org'],
    'sklearn': ['scikit-learn.org'],
    
    # Java/Spring
    'spring': ['docs.spring.io', 'spring.io'],
    'springboot': ['docs.spring.io/spring-boot', 'spring.io/projects/spring-boot'],
    'hibernate': ['hibernate.org/documentation'],
    'maven': ['maven.apache.org/guides'],
    'gradle': ['docs.gradle.org'],
    'java': ['docs.oracle.com/javase', 'dev.java/learn'],
    
    # PHP
    'laravel': ['laravel.com/docs'],
    'symfony': ['symfony.com/doc'],
    'wordpress': ['developer.wordpress.org'],
    'php': ['php.net/docs.php'],
    
    # Ruby
    'rails': ['guides.rubyonrails.org', 'api.rubyonrails.org'],
    'ruby': ['ruby-doc.org', 'docs.ruby-lang.org'],
    
    # Go
    'go': ['go.dev/doc', 'pkg.go.dev'],
    'golang': ['go.dev/doc', 'pkg.go.dev'],
    'gin': ['gin-gonic.com/docs'],
    'echo': ['echo.labstack.com/docs'],
    
    # Rust
    'rust': ['doc.rust-lang.org', 'rust-lang.org'],
    'tokio': ['tokio.rs'],
    'actix': ['actix.rs/docs'],
    
    # Database
    'postgresql': ['postgresql.org/docs'],
    'postgres': ['postgresql.org/docs'],
    'mysql': ['dev.mysql.com/doc'],
    'mongodb': ['docs.mongodb.com', 'mongodb.com/docs'],
    'redis': ['redis.io/docs'],
    'elasticsearch': ['elastic.co/guide/en/elasticsearch'],
    
    # Mobile
    'flutter': ['docs.flutter.dev', 'api.flutter.dev'],
    'react-native': ['reactnative.dev/docs'],
    'reactnative': ['reactnative.dev/docs'],
    'kotlin': ['kotlinlang.org/docs'],
    'swift': ['docs.swift.org', 'developer.apple.com/documentation/swift'],
    
    # Cloud/DevOps
    'docker': ['docs.docker.com'],
    'kubernetes': ['kubernetes.io/docs'],
    'k8s': ['kubernetes.io/docs'],
    'aws': ['docs.aws.amazon.com'],
    'azure': ['learn.microsoft.com/en-us/azure'],
    'gcp': ['cloud.google.com/docs'],
    'terraform': ['developer.hashicorp.com/terraform/docs'],
    'ansible': ['docs.ansible.com'],
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
        framework_lower = framework.lower().replace(' ', '').replace('-', '').replace('.', '')
        
        # Run multiple search strategies in parallel
        tasks = [
            self._search_known_domains(framework, framework_lower),
            self._search_duckduckgo(framework),
            self._search_github(framework, framework_lower),
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
        
        # If we don't have enough results, add some helpful links
        if len(combined_results) < 5:
            combined_results.extend(self._get_additional_links(framework, seen_domains))
        
        return combined_results[:5]
    
    async def _search_known_domains(self, framework: str, framework_lower: str) -> List[Dict]:
        """Check known documentation domains"""
        results = []
        
        # Check direct matches and common variations
        keys_to_check = [
            framework_lower,
            framework_lower.replace('js', ''),  # e.g., "nextjs" -> "next"
            framework_lower + 'js',  # e.g., "next" -> "nextjs"
        ]
        
        for key in keys_to_check:
            if key in KNOWN_DOC_DOMAINS:
                domains = KNOWN_DOC_DOMAINS[key]
                
                for domain in domains[:2]:  # Check first 2 known domains
                    # Handle different URL patterns
                    if domain.startswith('http'):
                        url = domain
                    else:
                        url = f"https://{domain}"
                    
                    try:
                        async with self.session.head(url, allow_redirects=True, timeout=3) as response:
                            if response.status < 400:
                                doc_type = self._categorize_url(str(response.url), domain)
                                results.append({
                                    'title': f"{framework} Documentation",
                                    'url': str(response.url),
                                    'type': doc_type,
                                    'description': f"Official {framework} documentation"
                                })
                                if doc_type == 'official':  # Found official docs, that's enough
                                    break
                    except Exception as e:
                        logger.debug(f"Failed to check {url}: {e}")
                        continue
                
                if results:  # Found something, stop checking variations
                    break
        
        return results
    
    async def _search_duckduckgo(self, framework: str) -> List[Dict]:
        """Search using DuckDuckGo HTML version"""
        results = []
        query = f"{framework} documentation official docs site"
        
        try:
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            
            async with self.session.get(url, timeout=5) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # DuckDuckGo HTML results are in <div class="result">
                    for result in soup.find_all('div', class_='result')[:10]:
                        link = result.find('a', class_='result__a')
                        if not link:
                            continue
                        
                        href = link.get('href')
                        title = link.get_text(strip=True)
                        
                        # Get snippet
                        snippet = result.find('a', class_='result__snippet')
                        description = snippet.get_text(strip=True) if snippet else ''
                        
                        # Filter for documentation-related results
                        if self._is_documentation_url(href, title):
                            doc_type = self._categorize_url(href, title)
                            
                            results.append({
                                'title': title,
                                'url': href,
                                'type': doc_type,
                                'description': description[:200] + '...' if len(description) > 200 else description
                            })
                            
                            if len(results) >= 3:  # Get top 3 from search
                                break
        
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
        
        return results
    
    async def _search_github(self, framework: str, framework_lower: str) -> List[Dict]:
        """Search GitHub for the framework repository"""
        results = []
        
        try:
            # Common GitHub organizations/users for frameworks
            common_orgs = {
                'react': 'facebook/react',
                'vue': 'vuejs/vue',
                'angular': 'angular/angular',
                'svelte': 'sveltejs/svelte',
                'django': 'django/django',
                'flask': 'pallets/flask',
                'rails': 'rails/rails',
                'laravel': 'laravel/laravel',
                'spring': 'spring-projects/spring-framework',
                'express': 'expressjs/express',
            }
            
            # Check if we have a known repo
            repo = common_orgs.get(framework_lower)
            if repo:
                url = f"https://github.com/{repo}"
                results.append({
                    'title': f"{framework} - GitHub",
                    'url': url,
                    'type': 'github',
                    'description': f"Source code repository for {framework}"
                })
            else:
                # Try common patterns
                patterns = [
                    f"https://github.com/{framework_lower}/{framework_lower}",
                    f"https://github.com/{framework_lower}js/{framework_lower}",
                    f"https://github.com/{framework_lower}",
                ]
                
                for pattern in patterns:
                    try:
                        async with self.session.head(pattern, allow_redirects=True, timeout=2) as response:
                            if response.status == 200:
                                results.append({
                                    'title': f"{framework} - GitHub",
                                    'url': str(response.url),
                                    'type': 'github',
                                    'description': f"Source code repository for {framework}"
                                })
                                break
                    except:
                        continue
        
        except Exception as e:
            logger.error(f"GitHub search error: {e}")
        
        return results
    
    def _is_documentation_url(self, url: str, title: str) -> bool:
        """Check if a URL is likely to be documentation"""
        url_lower = url.lower()
        title_lower = title.lower()
        
        # Exclude non-documentation sites
        exclude_domains = ['stackoverflow.com', 'reddit.com', 'medium.com', 'dev.to', 'youtube.com']
        if any(domain in url_lower for domain in exclude_domains):
            return False
        
        # Include if it has documentation keywords
        doc_keywords = ['docs', 'documentation', 'api', 'guide', 'reference', 'manual', 'tutorial']
        return any(keyword in url_lower or keyword in title_lower for keyword in doc_keywords)
    
    def _categorize_url(self, url: str, title: str) -> str:
        """Categorize a URL based on its content"""
        url_lower = url.lower()
        title_lower = title.lower()
        
        if 'github.com' in url_lower:
            return 'github'
        elif any(term in url_lower for term in ['/api', '/javadoc', '/apidoc', '/reference/api']):
            return 'api'
        elif any(term in title_lower for term in ['getting started', 'tutorial', 'guide', 'quickstart', 'learn']):
            return 'tutorial'
        elif any(term in url_lower for term in ['/docs', '/documentation', '/doc/']):
            return 'official'
        elif 'reference' in url_lower or 'manual' in url_lower:
            return 'reference'
        else:
            return 'official'  # Default to official
    
    def _get_additional_links(self, framework: str, seen_domains: Set[str]) -> List[Dict]:
        """Get additional helpful links when not enough results are found"""
        additional = []
        
        # MDN for web technologies
        if framework.lower() in ['javascript', 'js', 'css', 'html', 'web']:
            mdn_url = f"https://developer.mozilla.org/en-US/search?q={quote_plus(framework)}"
            if 'developer.mozilla.org' not in seen_domains:
                additional.append({
                    'title': f"{framework} - MDN Web Docs",
                    'url': mdn_url,
                    'type': 'tutorial',
                    'description': 'Comprehensive web technology documentation'
                })
        
        # DevDocs.io
        devdocs_url = f"https://devdocs.io/{framework.lower().replace(' ', '_')}"
        if 'devdocs.io' not in seen_domains:
            additional.append({
                'title': f"{framework} - DevDocs",
                'url': devdocs_url,
                'type': 'reference',
                'description': 'Fast, offline API documentation browser'
            })
        
        # Package managers
        framework_lower = framework.lower()
        
        # NPM for JavaScript packages
        if not any(lang in framework_lower for lang in ['python', 'java', 'ruby', 'php', 'go', 'rust']):
            npm_url = f"https://www.npmjs.com/package/{framework_lower}"
            if 'npmjs.com' not in seen_domains:
                additional.append({
                    'title': f"{framework} - npm",
                    'url': npm_url,
                    'type': 'reference',
                    'description': 'Package information and documentation'
                })
        
        # PyPI for Python packages
        if 'python' in framework_lower or framework_lower in ['django', 'flask', 'pytest', 'numpy', 'pandas']:
            pypi_url = f"https://pypi.org/project/{framework_lower}/"
            if 'pypi.org' not in seen_domains:
                additional.append({
                    'title': f"{framework} - PyPI",
                    'url': pypi_url,
                    'type': 'reference',
                    'description': 'Python package index'
                })
        
        return additional