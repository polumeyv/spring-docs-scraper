#!/usr/bin/env python3
"""
Smart Spring Documentation Scraper
Creates an organized SPA structure instead of duplicating HTML
"""

import requests
import json
import time
import re
import shutil
from datetime import datetime
from typing import Dict, List, Set
from urllib.parse import urljoin, urlparse, unquote
from bs4 import BeautifulSoup
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class SmartSpringDocsScraper:
    def __init__(self, output_dir='spring-docs', clean=False):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Compatible; Spring Docs Scraper)'
        })
        self.output_dir = output_dir
        self.projects = {}
        self.routes = {}
        self.static_cache = {}  # Cache for static assets
        self.templates = {}  # Store templates for each doc type
        self.rate_limit = 0.3
        self.clean = clean
        
    def scrape_all(self):
        """Main method to scrape all Spring documentation"""
        logging.info("Starting smart Spring documentation scrape...")
        
        # Clean existing directory if requested
        if self.clean and os.path.exists(self.output_dir):
            logging.info(f"Cleaning existing directory: {self.output_dir}")
            shutil.rmtree(self.output_dir)
        
        # Create directory structure
        self.create_directory_structure()
        
        # 1. Get all projects
        self.get_projects()
        
        # 2. For each project, get versions
        self.get_all_versions()
        
        # 3. Scrape documentation in smart way
        self.scrape_current_docs()
        
        # 4. Create SPA index
        self.create_spa_index()
        
        # 5. Save metadata
        self.save_metadata()
        
        logging.info("Smart scraping complete!")
        
    def create_directory_structure(self):
        """Create organized directory structure"""
        dirs = [
            f"{self.output_dir}/static/css",
            f"{self.output_dir}/static/js",
            f"{self.output_dir}/static/img",
            f"{self.output_dir}/static/fonts",
            f"{self.output_dir}/content",
            f"{self.output_dir}/templates"
        ]
        for dir_path in dirs:
            os.makedirs(dir_path, exist_ok=True)
    
    def get_projects(self):
        """Get all Spring projects from the main projects page"""
        url = "https://spring.io/projects"
        response = self.session.get(url)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a', href=re.compile(r'/projects/spring-[\w-]+'))
            
            for link in links:
                project_url = urljoin(url, link.get('href'))
                project_name = project_url.split('/')[-1]
                
                project_response = self.session.get(project_url)
                if project_response.status_code == 200:
                    project_soup = BeautifulSoup(project_response.text, 'html.parser')
                    desc_elem = project_soup.find('p', class_='project-description')
                    description = desc_elem.text.strip() if desc_elem else None
                    
                    self.projects[project_name] = {
                        'name': project_name,
                        'url': project_url,
                        'description': description,
                        'versions': [],
                        'docs': {}
                    }
                    
                time.sleep(self.rate_limit)
                
        logging.info(f"Found {len(self.projects)} projects")
    
    def get_all_versions(self):
        """Get versions for all projects"""
        for project_name in self.projects:
            self.get_project_versions(project_name)
    
    def get_project_versions(self, project_name):
        """Get available versions for a project"""
        urls = [
            f"https://docs.spring.io/{project_name}/docs/",
            f"https://docs.spring.io/{project_name}/site/docs/"
        ]
        
        for url in urls:
            try:
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    if soup.find('pre') or 'Index of' in soup.text:
                        versions = []
                        
                        for link in soup.find_all('a'):
                            href = link.get('href', '')
                            if href and href != '../':
                                version = href.rstrip('/')
                                if (re.match(r'^\d+\.\d+', version) or 
                                    version in ['current', 'current-SNAPSHOT']):
                                    versions.append(version)
                        
                        self.projects[project_name]['versions'] = sorted(versions, reverse=True)
                        logging.info(f"{project_name}: Found {len(versions)} versions")
                        break
                        
                time.sleep(self.rate_limit)
            except:
                pass
    
    def scrape_current_docs(self):
        """Scrape documentation for current version of each project"""
        for project_name, project in self.projects.items():
            if 'current' in project['versions']:
                self.scrape_project_docs(project_name, 'current')
            elif project['versions']:
                self.scrape_project_docs(project_name, project['versions'][0])
    
    def scrape_project_docs(self, project_name, version):
        """Scrape documentation for a specific project version"""
        logging.info(f"Smart scraping {project_name} {version}")
        
        # Documentation URLs to try
        doc_urls = {
            'reference': [
                f"https://docs.spring.io/{project_name}/docs/{version}/reference/html/",
                f"https://docs.spring.io/{project_name}/reference/index.html",
                f"https://docs.spring.io/{project_name}/reference/"
            ],
            'api': [
                f"https://docs.spring.io/{project_name}/docs/{version}/api/",
                f"https://docs.spring.io/{project_name}/api/java/index.html",
                f"https://docs.spring.io/{project_name}/docs/{version}/javadoc-api/"
            ]
        }
        
        for doc_type, urls in doc_urls.items():
            for url in urls:
                try:
                    response = self.session.get(url, timeout=10)
                    if response.status_code == 200:
                        self.projects[project_name]['docs'][doc_type] = url
                        
                        # Process the documentation smartly
                        if doc_type == 'reference':
                            self.process_reference_doc(project_name, version, url, response.text)
                        else:
                            self.process_api_doc(project_name, version, url, response.text)
                        break
                        
                    time.sleep(self.rate_limit)
                except:
                    pass
    
    def process_reference_doc(self, project_name, version, base_url, html_content):
        """Process reference documentation (Antora-based)"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract and save template if not already saved
        if 'reference' not in self.templates:
            self.extract_reference_template(soup)
        
        # Extract navigation structure
        nav_data = self.extract_navigation(soup)
        
        # Extract main content
        article = soup.find('article', class_='doc')
        if article:
            content_data = {
                'title': soup.find('h1', class_='page').text if soup.find('h1', class_='page') else 'Overview',
                'content': str(article),
                'nav': nav_data,
                'type': 'reference',
                'project': project_name
            }
            
            # Save content
            content_path = f"{self.output_dir}/content/{project_name}-reference-index.json"
            with open(content_path, 'w', encoding='utf-8') as f:
                json.dump(content_data, f)
            
            # Add route
            self.routes[f"/{project_name}/reference"] = {
                'content': f"/content/{project_name}-reference-index.json",
                'title': content_data['title'],
                'project': project_name,
                'type': 'reference'
            }
        
        # Extract and download static resources
        self.extract_and_download_resources(soup, base_url)
        
        # Process other pages from navigation
        self.process_reference_pages(project_name, version, base_url, nav_data)
    
    def extract_reference_template(self, soup):
        """Extract the common template from reference docs"""
        # Clone the soup to work with
        template_soup = BeautifulSoup(str(soup), 'html.parser')
        
        # Remove the unique content
        article = template_soup.find('article', class_='doc')
        if article:
            article.clear()
            article.append(BeautifulSoup('<div id="content-placeholder"></div>', 'html.parser'))
        
        # Save template
        self.templates['reference'] = str(template_soup)
        
        with open(f"{self.output_dir}/templates/reference.html", 'w', encoding='utf-8') as f:
            f.write(self.templates['reference'])
    
    def extract_navigation(self, soup):
        """Extract navigation structure from the page"""
        nav_data = []
        nav_menu = soup.find('nav', class_='nav-menu')
        
        if nav_menu:
            for item in nav_menu.find_all('li', class_='nav-item'):
                link = item.find('a')
                if link:
                    nav_entry = {
                        'text': link.text.strip(),
                        'href': link.get('href', ''),
                        'children': []
                    }
                    
                    # Check for sub-items
                    sub_list = item.find('ul', class_='nav-list')
                    if sub_list:
                        for sub_item in sub_list.find_all('li', class_='nav-item', recursive=False):
                            sub_link = sub_item.find('a')
                            if sub_link:
                                nav_entry['children'].append({
                                    'text': sub_link.text.strip(),
                                    'href': sub_link.get('href', '')
                                })
                    
                    nav_data.append(nav_entry)
        
        return nav_data
    
    def process_reference_pages(self, project_name, version, base_url, nav_data):
        """Process additional reference pages from navigation"""
        # Extract URLs from navigation
        urls_to_process = []
        
        def extract_urls(items):
            for item in items:
                if item['href'] and not item['href'].startswith(('#', 'http://', 'https://')):
                    urls_to_process.append(item['href'])
                if item.get('children'):
                    extract_urls(item['children'])
        
        extract_urls(nav_data)
        
        # Process each URL
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for relative_url in urls_to_process[:20]:  # Limit for now
                url = urljoin(base_url, relative_url)
                future = executor.submit(self.fetch_and_process_page, project_name, url, 'reference')
                futures.append(future)
            
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logging.warning(f"Failed to process page: {e}")
    
    def fetch_and_process_page(self, project_name, url, doc_type):
        """Fetch and process a single documentation page"""
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                return
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract content based on type
            if doc_type == 'reference':
                article = soup.find('article', class_='doc')
                title_elem = soup.find('h1', class_='page')
            else:  # API
                article = soup.find('main') or soup.find('div', class_='contentContainer')
                title_elem = soup.find('title')
            
            if not article:
                return
            
            title = title_elem.text.strip() if title_elem else 'Untitled'
            
            # Create route path
            parsed_url = urlparse(url)
            path_parts = parsed_url.path.strip('/').split('/')
            route_path = f"/{project_name}/{doc_type}/{'/'.join(path_parts[-2:])}"
            
            # Save content
            content_data = {
                'title': title,
                'content': str(article),
                'type': doc_type,
                'project': project_name
            }
            
            # Generate content filename
            content_hash = hashlib.md5(route_path.encode()).hexdigest()[:8]
            content_path = f"{self.output_dir}/content/{project_name}-{doc_type}-{content_hash}.json"
            
            with open(content_path, 'w', encoding='utf-8') as f:
                json.dump(content_data, f)
            
            # Add route
            self.routes[route_path] = {
                'content': f"/content/{project_name}-{doc_type}-{content_hash}.json",
                'title': title,
                'project': project_name,
                'type': doc_type
            }
            
            # Extract resources
            self.extract_and_download_resources(soup, url)
            
            time.sleep(self.rate_limit)
            
        except Exception as e:
            logging.debug(f"Error processing {url}: {e}")
    
    def extract_and_download_resources(self, soup, base_url):
        """Extract and download static resources"""
        resources = set()
        
        # CSS
        for link in soup.find_all('link', rel='stylesheet'):
            href = link.get('href')
            if href and not href.startswith(('http://', 'https://', 'data:')):
                resources.add(('css', urljoin(base_url, href)))
        
        # JS
        for script in soup.find_all('script', src=True):
            src = script.get('src')
            if src and not src.startswith(('http://', 'https://', 'data:')):
                resources.add(('js', urljoin(base_url, src)))
        
        # Images
        for img in soup.find_all('img', src=True):
            src = img.get('src')
            if src and not src.startswith(('http://', 'https://', 'data:')):
                resources.add(('img', urljoin(base_url, src)))
        
        # Download resources
        for resource_type, resource_url in resources:
            self.download_static_resource(resource_type, resource_url)
    
    def download_static_resource(self, resource_type, url):
        """Download a static resource if not already cached"""
        # Check cache
        if url in self.static_cache:
            return self.static_cache[url]
        
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                return None
            
            # Generate filename
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)
            if not filename:
                filename = hashlib.md5(url.encode()).hexdigest()[:8]
            
            # Determine path
            if resource_type == 'css':
                local_path = f"static/css/{filename}"
            elif resource_type == 'js':
                local_path = f"static/js/{filename}"
            elif resource_type == 'img':
                local_path = f"static/img/{filename}"
            else:
                local_path = f"static/{filename}"
            
            # Save file
            full_path = os.path.join(self.output_dir, local_path)
            content_type = response.headers.get('Content-Type', '')
            
            if 'text' in content_type or local_path.endswith(('.css', '.js', '.svg')):
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(response.text)
            else:
                with open(full_path, 'wb') as f:
                    f.write(response.content)
            
            # Cache the path
            self.static_cache[url] = local_path
            
            # Process CSS for nested resources
            if resource_type == 'css':
                self.process_css_resources(response.text, url)
            
            return local_path
            
        except Exception as e:
            logging.debug(f"Failed to download {url}: {e}")
            return None
    
    def process_css_resources(self, css_content, base_url):
        """Extract and download resources referenced in CSS"""
        url_pattern = re.compile(r'url\(["\']?([^"\'()]+)["\']?\)')
        
        for match in url_pattern.finditer(css_content):
            resource_url = match.group(1)
            if not resource_url.startswith(('data:', 'http://', 'https://')):
                full_url = urljoin(base_url, resource_url)
                # Determine type based on extension
                if resource_url.endswith(('.woff', '.woff2', '.ttf', '.eot')):
                    self.download_static_resource('fonts', full_url)
                elif resource_url.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg')):
                    self.download_static_resource('img', full_url)
    
    def process_api_doc(self, project_name, version, base_url, html_content):
        """Process API documentation (Javadoc)"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract and save template if not already saved
        if 'api' not in self.templates:
            self.extract_api_template(soup)
        
        # Extract main content
        main = soup.find('main') or soup.find('body')
        if main:
            title_elem = soup.find('title')
            title = title_elem.text if title_elem else 'API Documentation'
            
            content_data = {
                'title': title,
                'content': str(main),
                'type': 'api',
                'project': project_name
            }
            
            # Save content
            content_path = f"{self.output_dir}/content/{project_name}-api-index.json"
            with open(content_path, 'w', encoding='utf-8') as f:
                json.dump(content_data, f)
            
            # Add route
            self.routes[f"/{project_name}/api"] = {
                'content': f"/content/{project_name}-api-index.json",
                'title': title,
                'project': project_name,
                'type': 'api'
            }
        
        # Extract and download static resources
        self.extract_and_download_resources(soup, base_url)
    
    def extract_api_template(self, soup):
        """Extract the common template from API docs"""
        # Clone the soup
        template_soup = BeautifulSoup(str(soup), 'html.parser')
        
        # Remove unique content
        main = template_soup.find('main')
        if main:
            main.clear()
            main.append(BeautifulSoup('<div id="content-placeholder"></div>', 'html.parser'))
        
        # Save template
        self.templates['api'] = str(template_soup)
        
        with open(f"{self.output_dir}/templates/api.html", 'w', encoding='utf-8') as f:
            f.write(self.templates['api'])
    
    def create_spa_index(self):
        """Create the main SPA index.html"""
        spa_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Spring Documentation</title>
    <style>
        :root {
            --spring-green: #6db33f;
            --text-color: #333;
            --bg-color: #f5f5f5;
            --white: #fff;
            --border-color: #e0e0e0;
        }
        
        * {
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: var(--bg-color);
            color: var(--text-color);
        }
        
        .header {
            background-color: var(--spring-green);
            color: var(--white);
            padding: 1rem 2rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            margin: 0;
            font-size: 1.5rem;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        .projects-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-top: 2rem;
        }
        
        .project-card {
            background: var(--white);
            border-radius: 8px;
            padding: 1.5rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .project-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        
        .project-name {
            font-size: 1.2rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
            color: var(--text-color);
        }
        
        .project-description {
            font-size: 0.9rem;
            color: #666;
            margin-bottom: 1rem;
            line-height: 1.4;
        }
        
        .doc-links {
            display: flex;
            gap: 1rem;
        }
        
        .doc-link {
            display: inline-block;
            padding: 0.5rem 1rem;
            background-color: var(--spring-green);
            color: var(--white);
            text-decoration: none;
            border-radius: 4px;
            font-size: 0.9rem;
            transition: background-color 0.2s;
        }
        
        .doc-link:hover {
            background-color: #5da030;
        }
        
        .search-box {
            margin-bottom: 2rem;
        }
        
        .search-input {
            width: 100%;
            max-width: 500px;
            padding: 0.75rem 1rem;
            font-size: 1rem;
            border: 1px solid var(--border-color);
            border-radius: 4px;
        }
        
        .stats {
            background: var(--white);
            padding: 1rem;
            border-radius: 4px;
            margin-bottom: 2rem;
            display: flex;
            gap: 2rem;
            flex-wrap: wrap;
        }
        
        .stat-item {
            display: flex;
            flex-direction: column;
        }
        
        .stat-label {
            font-size: 0.9rem;
            color: #666;
        }
        
        .stat-value {
            font-size: 1.5rem;
            font-weight: 600;
            color: var(--spring-green);
        }
        
        #doc-viewer {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: var(--white);
            z-index: 1000;
        }
        
        #doc-viewer.active {
            display: block;
        }
        
        .viewer-header {
            background: var(--spring-green);
            color: var(--white);
            padding: 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .close-viewer {
            background: none;
            border: none;
            color: var(--white);
            font-size: 1.5rem;
            cursor: pointer;
            padding: 0.5rem;
        }
        
        .viewer-content {
            height: calc(100vh - 60px);
            overflow-y: auto;
        }
        
        .viewer-iframe {
            width: 100%;
            height: 100%;
            border: none;
        }
    </style>
</head>
<body>
    <header class="header">
        <h1>🌱 Spring Documentation Browser</h1>
    </header>
    
    <div class="container">
        <div class="search-box">
            <input type="text" class="search-input" id="searchInput" placeholder="Search projects...">
        </div>
        
        <div class="stats" id="stats"></div>
        
        <div class="projects-grid" id="projectsGrid"></div>
    </div>
    
    <div id="doc-viewer">
        <div class="viewer-header">
            <h2 id="viewer-title">Documentation</h2>
            <button class="close-viewer" onclick="closeViewer()">✕</button>
        </div>
        <div class="viewer-content">
            <iframe class="viewer-iframe" id="viewer-frame"></iframe>
        </div>
    </div>
    
    <script>
        let projects = {};
        let routes = {};
        
        // Load metadata
        async function loadMetadata() {
            try {
                const response = await fetch('/metadata.json');
                const data = await response.json();
                projects = data.projects || {};
                
                const routesResponse = await fetch('/routes.json');
                routes = await routesResponse.json();
                
                renderStats(data);
                renderProjects();
            } catch (error) {
                console.error('Failed to load metadata:', error);
            }
        }
        
        function renderStats(data) {
            const statsHtml = `
                <div class="stat-item">
                    <span class="stat-label">Total Projects</span>
                    <span class="stat-value">${data.total_projects || 0}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Last Updated</span>
                    <span class="stat-value">${new Date(data.scrape_date).toLocaleDateString()}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Total Routes</span>
                    <span class="stat-value">${Object.keys(routes).length}</span>
                </div>
            `;
            document.getElementById('stats').innerHTML = statsHtml;
        }
        
        function renderProjects() {
            const grid = document.getElementById('projectsGrid');
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            
            const projectsHtml = Object.entries(projects)
                .filter(([name]) => name.toLowerCase().includes(searchTerm))
                .map(([name, project]) => {
                    if (typeof project !== 'object') return '';
                    
                    const hasApi = routes[`/${name}/api`];
                    const hasReference = routes[`/${name}/reference`];
                    
                    return `
                        <div class="project-card">
                            <div class="project-name">${name}</div>
                            <div class="project-description">${project.description || 'Spring project documentation'}</div>
                            <div class="doc-links">
                                ${hasApi ? `<a href="#" class="doc-link" onclick="openDoc('/${name}/api', '${name} API')">API Docs</a>` : ''}
                                ${hasReference ? `<a href="#" class="doc-link" onclick="openDoc('/${name}/reference', '${name} Reference')">Reference</a>` : ''}
                            </div>
                        </div>
                    `;
                })
                .join('');
            
            grid.innerHTML = projectsHtml || '<p>No projects found</p>';
        }
        
        function openDoc(routePath, title) {
            const route = routes[routePath];
            if (!route) {
                alert('Documentation not found');
                return;
            }
            
            // For now, create a simple viewer
            // In a real implementation, this would load the content dynamically
            const viewer = document.getElementById('doc-viewer');
            const frame = document.getElementById('viewer-frame');
            const titleElem = document.getElementById('viewer-title');
            
            titleElem.textContent = title;
            
            // Load the original scraped HTML for now
            // This could be enhanced to load the JSON content and render it
            const project = route.project;
            const type = route.type;
            frame.src = `/${project}/current/${type}/index.html`;
            
            viewer.classList.add('active');
        }
        
        function closeViewer() {
            document.getElementById('doc-viewer').classList.remove('active');
        }
        
        // Search functionality
        document.getElementById('searchInput').addEventListener('input', renderProjects);
        
        // Load data on startup
        loadMetadata();
    </script>
</body>
</html>"""
        
        with open(f"{self.output_dir}/index.html", 'w') as f:
            f.write(spa_html)
    
    def save_metadata(self):
        """Save project metadata and routes"""
        # Save main metadata
        metadata = {
            'scrape_date': datetime.now().isoformat(),
            'total_projects': len(self.projects),
            'projects': self.projects
        }
        
        with open(os.path.join(self.output_dir, 'metadata.json'), 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Save routes
        with open(os.path.join(self.output_dir, 'routes.json'), 'w') as f:
            json.dump(self.routes, f, indent=2)
        
        logging.info(f"Saved metadata for {len(self.projects)} projects")
        logging.info(f"Created {len(self.routes)} routes")
        
        # Create summary
        summary = f"""Spring Documentation Smart Scrape Summary
Date: {metadata['scrape_date']}
Total Projects: {metadata['total_projects']}
Total Routes: {len(self.routes)}
Static Resources: {len(self.static_cache)}

Projects with documentation:
"""
        for name, project in self.projects.items():
            if project['docs']:
                summary += f"\n{name}:"
                summary += f"\n  Versions: {len(project['versions'])}"
                summary += f"\n  Docs: {', '.join(project['docs'].keys())}"
        
        with open(os.path.join(self.output_dir, 'summary.txt'), 'w') as f:
            f.write(summary)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Smart Spring documentation scraper')
    parser.add_argument('--clean', action='store_true', 
                        help='Clean existing documentation before scraping')
    args = parser.parse_args()
    
    scraper = SmartSpringDocsScraper(clean=args.clean)
    scraper.scrape_all()
    print("\nSmart scraping complete! Check 'spring-docs' directory for results.")
    print("Run 'python serve_docs.py' to browse the documentation.")


if __name__ == "__main__":
    main()