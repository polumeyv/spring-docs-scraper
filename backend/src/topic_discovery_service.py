#!/usr/bin/env python3
import os
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from google import genai
from google.genai import types
import json
import logging
from typing import List, Dict, Optional
try:
    from prompts import (create_product_discovery_prompt, create_documentation_discovery_prompt, 
                        create_grounded_prompt, create_code_execution_prompt, create_chain_discovery_prompt,
                        get_strategy_config)
except ImportError:
    # Define minimal fallback functions
    def create_product_discovery_prompt(*args, **kwargs):
        return "Analyze this content and extract topics."
    def create_documentation_discovery_prompt(*args, **kwargs):
        return "Analyze this content and extract topics."
    def create_grounded_prompt(*args, **kwargs):
        return "Analyze this content and extract topics."
    def create_code_execution_prompt(*args, **kwargs):
        return "Analyze this content and extract topics."
    def create_chain_discovery_prompt(*args, **kwargs):
        return "Analyze this content and extract topics."
    def get_strategy_config(*args, **kwargs):
        return {"strategy": "standard"}

logger = logging.getLogger(__name__)

try:
    client = genai.Client()
    logger.info("Google GenAI client initialized")
except Exception as e:
    logger.error(f"Failed to initialize Google GenAI client: {e}")
    client = None

class TopicDiscoveryService:
    def __init__(self, progress_callback=None):
        self.session = None
        self.progress_callback = progress_callback
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def discover_topics(self, url: str, framework: str, task_id: str = None) -> Dict:
        try:
            await self._emit_progress(task_id, {
                'stage': 'url_analysis',
                'message': f'Analyzing URL for {framework}',
                'progress': 10,
                'details': {'input_url': url, 'framework': framework}
            })
            
            discovery_url = self._get_discovery_url(url, framework)
            logger.info(f"Using discovery URL: {discovery_url}")
            
            await self._emit_progress(task_id, {
                'stage': 'page_fetch',
                'message': f'Fetching documentation page: {discovery_url}',
                'progress': 20,
                'details': {'discovery_url': discovery_url}
            })
            
            html_content = await self._fetch_page(discovery_url)
            if not html_content:
                await self._emit_progress(task_id, {
                    'stage': 'error',
                    'message': 'Failed to fetch documentation page',
                    'progress': 0,
                    'error': 'Page fetch failed'
                })
                return {'error': 'Failed to fetch documentation page'}
            
            await self._emit_progress(task_id, {
                'stage': 'navigation_extraction',
                'message': 'Extracting navigation structure',
                'progress': 40,
                'details': {'content_size': len(html_content)}
            })
            
            navigation_data = self._extract_navigation(html_content, discovery_url)
            
            await self._emit_progress(task_id, {
                'stage': 'ai_analysis',
                'message': 'Analyzing with AI to discover topics',
                'progress': 60,
                'details': {
                    'navigation_items': len(navigation_data.get('navigation', [])),
                    'sections_found': len(navigation_data.get('sections', []))
                }
            })
            
            topics = await self._analyze_with_gemini(navigation_data, framework, discovery_url, task_id)
            
            await self._emit_progress(task_id, {
                'stage': 'complete',
                'message': f'Successfully discovered {len(topics)} topics',
                'progress': 100,
                'details': {'topics_found': len(topics)}
            })
            
            return {
                'framework': framework,
                'base_url': discovery_url,
                'topics': topics
            }
            
        except Exception as e:
            logger.error(f"Error discovering topics: {e}")
            await self._emit_progress(task_id, {
                'stage': 'error',
                'message': f'Error discovering topics: {str(e)}',
                'progress': 0,
                'error': str(e)
            })
            return {'error': str(e)}
    
    def _get_discovery_url(self, url: str, framework: str) -> str:
        framework_lower = framework.lower()
        parsed = urlparse(url)
        
        redirect_patterns = {
            'spring.io': {'patterns': ['/projects/', '/project/'], 'redirect': 'https://spring.io/projects'},
            'docs.spring.io': {'patterns': ['*'], 'redirect': 'https://spring.io/projects'},
            'react.dev': {'patterns': ['/learn/', '/reference/', '/blog/'], 'redirect': 'https://react.dev'},
            'reactjs.org': {'patterns': ['*'], 'redirect': 'https://react.dev'},
            'vuejs.org': {'patterns': ['/guide/', '/api/', '/tutorial/'], 'redirect': 'https://vuejs.org'},
            'angular.io': {'patterns': ['/guide/', '/api/', '/tutorial/'], 'redirect': 'https://angular.io'},
            'docs.aws.amazon.com': {'patterns': ['*'], 'redirect': 'https://aws.amazon.com/products/'},
            'docs.djangoproject.com': {'patterns': ['*'], 'redirect': 'https://djangoproject.com'},
            'kubernetes.io': {'patterns': ['/docs/', '/reference/'], 'redirect': 'https://kubernetes.io/docs'},
            'docs.docker.com': {'patterns': ['*'], 'redirect': 'https://docs.docker.com'},
            'laravel.com': {'patterns': ['/docs/'], 'redirect': 'https://laravel.com/docs'},
            'guides.rubyonrails.org': {'patterns': ['*'], 'redirect': 'https://guides.rubyonrails.org'},
            'nodejs.org': {'patterns': ['/docs/', '/api/'], 'redirect': 'https://nodejs.org/en/docs'},
        }
        
        domain = parsed.netloc.lower()
        if domain in redirect_patterns:
            rule = redirect_patterns[domain]
            if '*' in rule['patterns'] or any(pattern in url for pattern in rule['patterns']):
                return rule['redirect']
        
        framework_mappings = {
            'spring': 'https://spring.io/projects', 'spring boot': 'https://spring.io/projects',
            'spring framework': 'https://spring.io/projects', 'stripe': 'https://stripe.com/docs',
            'aws': 'https://aws.amazon.com/products/', 'amazon web services': 'https://aws.amazon.com/products/',
            'gcp': 'https://cloud.google.com/products', 'google cloud': 'https://cloud.google.com/products',
            'azure': 'https://azure.microsoft.com/en-us/products/', 'microsoft azure': 'https://azure.microsoft.com/en-us/products/',
            'django': 'https://djangoproject.com', 'flask': 'https://flask.palletsprojects.com',
            'fastapi': 'https://fastapi.tiangolo.com', 'express': 'https://expressjs.com',
            'laravel': 'https://laravel.com/docs', 'rails': 'https://guides.rubyonrails.org',
            'ruby on rails': 'https://guides.rubyonrails.org', 'react': 'https://react.dev',
            'vue': 'https://vuejs.org', 'angular': 'https://angular.io', 'svelte': 'https://svelte.dev',
            'kubernetes': 'https://kubernetes.io/docs', 'docker': 'https://docs.docker.com',
            'terraform': 'https://terraform.io/docs', 'mongodb': 'https://docs.mongodb.com',
            'postgresql': 'https://postgresql.org/docs', 'redis': 'https://redis.io/documentation',
            'elasticsearch': 'https://www.elastic.co/guide'
        }
        
        for key, mapped_url in framework_mappings.items():
            if key in framework_lower:
                return mapped_url
        
        url_path = parsed.path.lower()
        good_discovery_paths = ['/projects', '/products', '/docs', '/documentation', '/guide']
        if any(path in url_path for path in good_discovery_paths):
            return url
        
        if url_path.count('/') > 2:
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            doc_roots = ['/docs', '/documentation', '/guide', '/api']
            for root in doc_roots:
                if root in url_path:
                    return f"{base_url}{root}"
            return base_url
        
        return url
    
    async def _fetch_page(self, url: str) -> Optional[str]:
        try:
            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.error(f"Failed to fetch {url}: Status {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def _extract_navigation(self, html: str, base_url: str) -> Dict:
        soup = BeautifulSoup(html, 'html.parser')
        
        nav_selectors = [
            ('nav[role="navigation"]', 10), ('nav.main-nav', 9), ('nav.primary-nav', 9), ('.navbar', 8),
            ('.docs-nav', 7), ('.documentation-nav', 7), ('.sidebar-nav', 6), ('.toc', 6),
            ('nav', 5), ('.nav', 4), ('.sidebar', 3), ('aside', 2),
        ]
        
        navigation_items = []
        seen_urls = set()
        
        for selector, priority in nav_selectors:
            elements = soup.select(selector)
            for element in elements:
                links = element.find_all('a', href=True)
                for link in links:
                    href = link['href']
                    text = link.get_text(strip=True)
                    
                    if not text or href in seen_urls or len(text) > 100:
                        continue
                    
                    absolute_url = urljoin(base_url, href)
                    
                    if not self._is_same_domain(absolute_url, base_url) or (href.startswith('#') and len(href) > 1):
                        continue
                    
                    semantic_score = self._calculate_semantic_score(text, link, element)
                    
                    seen_urls.add(href)
                    navigation_items.append({
                        'text': text,
                        'url': absolute_url,
                        'relative_url': href,
                        'level': len(link.find_parents(['ul', 'ol', 'nav'])),
                        'priority_score': priority,
                        'semantic_score': semantic_score,
                        'context': self._get_link_context(link)
                    })
        
        navigation_items = sorted(navigation_items, key=lambda x: (x['priority_score'] + x['semantic_score']), reverse=True)
        navigation_items = self._deduplicate_navigation(navigation_items)
        
        main_sections = self._extract_structured_sections(soup)
        metadata = self._extract_page_metadata(soup)
        
        return {
            'navigation': navigation_items[:100],
            'sections': main_sections[:50],
            'metadata': metadata,
            'title': soup.find('title').text.strip() if soup.find('title') else '',
            'description': soup.find('meta', {'name': 'description'})['content'] if soup.find('meta', {'name': 'description'}) else ''
        }
    
    def _calculate_semantic_score(self, text: str, link, element) -> int:
        score = 0
        text_lower = text.lower()
        
        high_value_keywords = [
            'spring boot', 'spring data', 'spring cloud', 'spring security',
            'react router', 'next.js', 'gatsby', 'vue router', 'nuxt',
            'angular material', 'angular cli', 'sveltekit',
            'payments', 'connect', 'terminal', 'radar', 'billing'
        ]
        
        medium_value_keywords = ['api', 'sdk', 'library', 'framework', 'tool', 'service']
        low_value_keywords = ['getting started', 'tutorial', 'guide', 'examples', 'quickstart']
        
        if any(keyword in text_lower for keyword in high_value_keywords):
            score += 10
        elif any(keyword in text_lower for keyword in medium_value_keywords):
            score += 5
        elif any(keyword in text_lower for keyword in low_value_keywords):
            score -= 5
        
        if any(char.isdigit() for char in text) and ('v' in text_lower or '.' in text):
            score += 3
        
        parent_text = element.get_text(strip=True) if element else ''
        if 'products' in parent_text.lower() or 'projects' in parent_text.lower():
            score += 5
        
        return score
    
    def _get_link_context(self, link) -> Dict:
        context = {}
        parent = link.find_parent(['section', 'div', 'article'])
        if parent:
            parent_text = parent.get_text(strip=True).lower()[:200]
            context['in_products_section'] = 'products' in parent_text or 'projects' in parent_text
            context['in_docs_section'] = 'documentation' in parent_text or 'guides' in parent_text
        sibling_img = link.find_next_sibling('img') or link.find_previous_sibling('img')
        context['has_icon'] = bool(sibling_img)
        return context
    
    def _deduplicate_navigation(self, items: List[Dict]) -> List[Dict]:
        seen_texts = set()
        deduplicated = []
        for item in items:
            text_key = item['text'].lower().strip()
            if text_key not in seen_texts:
                seen_texts.add(text_key)
                deduplicated.append(item)
        return deduplicated
    
    def _extract_structured_sections(self, soup) -> List[Dict]:
        sections = []
        content_selectors = ['main section', '.content section', '.main-content section', 'article']
        for selector in content_selectors:
            elements = soup.select(selector)
            for element in elements:
                heading = element.find(['h1', 'h2', 'h3'])
                if heading:
                    text = heading.get_text(strip=True)
                    if text and len(text) < 100:
                        sections.append({
                            'text': text,
                            'level': int(heading.name[1]),
                            'has_code': bool(element.find('code') or element.find('pre')),
                            'has_links': bool(element.find('a'))
                        })
        return sections
    
    def _extract_page_metadata(self, soup) -> Dict:
        metadata = {}
        meta_keywords = soup.find('meta', {'name': 'keywords'})
        if meta_keywords:
            metadata['keywords'] = meta_keywords.get('content', '')
        og_type = soup.find('meta', {'property': 'og:type'})
        if og_type:
            metadata['og_type'] = og_type.get('content', '')
        schema_script = soup.find('script', {'type': 'application/ld+json'})
        if schema_script:
            try:
                schema_data = json.loads(schema_script.string)
                metadata['schema_type'] = schema_data.get('@type', '')
            except:
                pass
        return metadata
    
    def _is_same_domain(self, url1: str, url2: str) -> bool:
        domain1 = urlparse(url1).netloc.lower()
        domain2 = urlparse(url2).netloc.lower()
        return domain1 == domain2 or domain1.endswith(f'.{domain2}') or domain2.endswith(f'.{domain1}')
    
    async def _analyze_with_gemini(self, navigation_data: Dict, framework: str, base_url: str) -> List[Dict]:
        intelligent_fallback = self._try_intelligent_fallback(framework, base_url, navigation_data)
        if intelligent_fallback:
            logger.info(f"Using intelligent fallback for {framework} at {base_url}")
            return intelligent_fallback
        
        # For now, use fallback topic extraction when AI is not available
        return self._fallback_topic_extraction(navigation_data, base_url)
    
    def _fallback_topic_extraction(self, navigation_data: Dict, base_url: str) -> List[Dict]:
        """Extract topics from navigation data when AI is not available"""
        topics = []
        navigation = navigation_data.get('navigation', [])
        
        # Group similar navigation items
        grouped_items = {}
        for item in navigation[:20]:  # Limit to top 20 items
            text = item['text'].strip()
            if len(text) > 2 and not any(skip in text.lower() for skip in ['home', 'about', 'contact', 'search']):
                key = text.lower().replace(' ', '_').replace('-', '_')
                if key not in grouped_items:
                    grouped_items[key] = {
                        'id': key,
                        'name': text,
                        'description': f"Documentation for {text}",
                        'url': item['url'],
                        'priority': item.get('priority_score', 1),
                        'subtopics': []
                    }
        
        # Convert to list and sort by priority
        topics = list(grouped_items.values())
        topics.sort(key=lambda x: x['priority'], reverse=True)
        
        return topics[:10]  # Return top 10 topics
    
    def _try_intelligent_fallback(self, framework: str, base_url: str, navigation_data: Dict) -> List[Dict]:
        """Try intelligent fallback for known frameworks"""
        framework_lower = framework.lower()
        domain = base_url.lower()
        
        # Check for pattern matches
        pattern_name = None
        if 'spring' in framework_lower or 'spring.io' in domain:
            pattern_name = 'spring'
        elif 'docker' in framework_lower or 'docs.docker.com' in domain:
            pattern_name = 'docker'
        elif 'kubernetes' in framework_lower or 'kubernetes.io' in domain:
            pattern_name = 'kubernetes'
        
        if pattern_name:
            return self._get_framework_specific_topics(pattern_name)
        
        return None
    
    def _get_framework_specific_topics(self, pattern_name: str) -> List[Dict]:
        """Get predefined topics for specific frameworks"""
        if pattern_name == 'spring':
            return [
                {
                    'id': 'spring-boot',
                    'name': 'Spring Boot',
                    'description': 'Create stand-alone, production-grade Spring based Applications',
                    'url': 'https://spring.io/projects/spring-boot',
                    'priority': 1,
                    'subtopics': ['Auto Configuration', 'Starters', 'Actuator', 'DevTools']
                },
                {
                    'id': 'spring-framework',
                    'name': 'Spring Framework',
                    'description': 'Core support for dependency injection, transaction management, web apps',
                    'url': 'https://spring.io/projects/spring-framework',
                    'priority': 2,
                    'subtopics': ['Core Container', 'Data Access', 'Web', 'AOP']
                },
                {
                    'id': 'spring-data',
                    'name': 'Spring Data',
                    'description': 'Consistent, Spring-based programming model for data access',
                    'url': 'https://spring.io/projects/spring-data',
                    'priority': 3,
                    'subtopics': ['JPA', 'MongoDB', 'Redis', 'Elasticsearch']
                },
                {
                    'id': 'spring-security',
                    'name': 'Spring Security',
                    'description': 'Comprehensive security framework for Java applications',
                    'url': 'https://spring.io/projects/spring-security',
                    'priority': 4,
                    'subtopics': ['Authentication', 'Authorization', 'OAuth2', 'JWT']
                },
                {
                    'id': 'spring-cloud',
                    'name': 'Spring Cloud',
                    'description': 'Tools for developers to quickly build common patterns in distributed systems',
                    'url': 'https://spring.io/projects/spring-cloud',
                    'priority': 5,
                    'subtopics': ['Service Discovery', 'Circuit Breaker', 'Gateway', 'Config Server']
                }
            ]
        elif pattern_name == 'docker':
            return [
                {
                    'id': 'docker-desktop',
                    'name': 'Docker Desktop',
                    'description': 'Local development environment for building and sharing containerized applications',
                    'url': 'https://docs.docker.com/desktop/',
                    'priority': 1,
                    'subtopics': ['Installation', 'Settings', 'Extensions', 'Dev Environments']
                },
                {
                    'id': 'docker-engine',
                    'name': 'Docker Engine',
                    'description': 'Open source containerization technology for building and containerizing applications',
                    'url': 'https://docs.docker.com/engine/',
                    'priority': 2,
                    'subtopics': ['Installation', 'CLI Reference', 'API Reference', 'Daemon']
                },
                {
                    'id': 'docker-compose',
                    'name': 'Docker Compose',
                    'description': 'Tool for defining and running multi-container Docker applications',
                    'url': 'https://docs.docker.com/compose/',
                    'priority': 3,
                    'subtopics': ['Compose File', 'CLI Reference', 'Environment Variables', 'Networking']
                },
                {
                    'id': 'docker-build',
                    'name': 'Docker Build',
                    'description': 'Advanced build features with BuildKit',
                    'url': 'https://docs.docker.com/build/',
                    'priority': 4,
                    'subtopics': ['Dockerfile', 'BuildKit', 'Multi-stage Builds', 'Build Cache']
                },
                {
                    'id': 'docker-hub',
                    'name': 'Docker Hub',
                    'description': 'Cloud-based registry service for sharing container images',
                    'url': 'https://docs.docker.com/docker-hub/',
                    'priority': 5,
                    'subtopics': ['Repositories', 'Organizations', 'Webhooks', 'API']
                },
                {
                    'id': 'docker-scout',
                    'name': 'Docker Scout',
                    'description': 'Software supply chain security for container images and registries',
                    'url': 'https://docs.docker.com/scout/',
                    'priority': 6,
                    'subtopics': ['Vulnerability Analysis', 'Image Analysis', 'Policy', 'Integration']
                }
            ]
        elif pattern_name == 'kubernetes':
            return [
                {
                    'id': 'kubectl',
                    'name': 'kubectl',
                    'description': 'Command line tool for communicating with a Kubernetes cluster',
                    'url': 'https://kubernetes.io/docs/reference/kubectl/',
                    'priority': 1,
                    'subtopics': ['Installation', 'Commands', 'Config', 'Cheat Sheet']
                },
                {
                    'id': 'workloads',
                    'name': 'Workloads',
                    'description': 'Objects you use to manage and run your containers on the cluster',
                    'url': 'https://kubernetes.io/docs/concepts/workloads/',
                    'priority': 2,
                    'subtopics': ['Pods', 'Deployments', 'ReplicaSets', 'StatefulSets', 'Jobs']
                },
                {
                    'id': 'services-networking',
                    'name': 'Services and Networking',
                    'description': 'Concepts and resources behind networking in Kubernetes',
                    'url': 'https://kubernetes.io/docs/concepts/services-networking/',
                    'priority': 3,
                    'subtopics': ['Services', 'Ingress', 'NetworkPolicies', 'DNS']
                },
                {
                    'id': 'helm',
                    'name': 'Helm',
                    'description': 'Package manager for Kubernetes applications',
                    'url': 'https://helm.sh/docs/',
                    'priority': 4,
                    'subtopics': ['Charts', 'Templates', 'Values', 'Hooks']
                },
                {
                    'id': 'kustomize',
                    'name': 'Kustomize',
                    'description': 'Kubernetes native configuration management',
                    'url': 'https://kustomize.io/',
                    'priority': 5,
                    'subtopics': ['Overlays', 'Patches', 'Resources', 'Generators']
                }
            ]
        
        return []
    
    def _validate_and_enhance_topics(self, topics: List[Dict], base_url: str, navigation_data: Dict) -> List[Dict]:
        """Validate and enhance discovered topics"""
        if not isinstance(topics, list):
            return []
        
        enhanced_topics = []
        for topic in topics:
            if isinstance(topic, dict) and 'name' in topic:
                enhanced_topic = {
                    'id': topic.get('id', topic['name'].lower().replace(' ', '-')),
                    'name': topic['name'],
                    'description': topic.get('description', f"Documentation for {topic['name']}"),
                    'url': topic.get('url', base_url),
                    'priority': topic.get('priority', 1),
                    'subtopics': topic.get('subtopics', [])
                }
                enhanced_topics.append(enhanced_topic)
        
        return enhanced_topics
    

    async def _process_chain_discovery(self, framework: str, base_url: str, navigation_data: Dict, context_analysis: Dict) -> List[Dict]:
        """Process chain discovery: discovery -> validation -> enhancement"""
        try:
            logger.info(f"Starting chain discovery for {framework} at {base_url}")
            # For now, use fallback as chain prompting is complex to implement
            return self._fallback_topic_extraction(navigation_data, base_url)
        except Exception as e:
            logger.error(f"Error in chain discovery: {e}")
            return self._fallback_topic_extraction(navigation_data, base_url)
    
    async def _emit_progress(self, task_id: str, progress_data: dict):
        """Emit progress updates via callback if available"""
        if self.progress_callback and task_id:
            try:
                await self.progress_callback(task_id, progress_data)
            except Exception as e:
                logger.error(f"Error emitting progress: {e}")
