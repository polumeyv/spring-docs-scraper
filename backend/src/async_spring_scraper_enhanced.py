#!/usr/bin/env python3
"""
Enhanced Async Spring Documentation Scraper with Progress Tracking and Graceful Shutdown
"""

import asyncio
import json
import re
import os
import hashlib
import signal
import sys
from datetime import datetime
from typing import Dict, List, Set, Optional, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import logging
from pathlib import Path

from models import (
    ProjectModel, DocType, ScrapedContent, RouteModel, 
    ScrapeMetadata, NavigationItem, ResourceInfo
)
from async_http_client import AsyncHTTPClient
from async_queue import URLQueue, Priority
from progress_tracker import create_progress_tracker


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class GracefulShutdown:
    """Handle graceful shutdown on signals"""
    
    def __init__(self):
        self.shutdown_event = asyncio.Event()
        self.force_shutdown = False
        
    def handle_signal(self, signum, frame):
        """Handle shutdown signals"""
        if self.force_shutdown:
            print("\nForce shutdown requested. Exiting immediately...")
            sys.exit(1)
        
        print(f"\nReceived signal {signum}. Starting graceful shutdown...")
        print("Press Ctrl+C again to force shutdown.")
        self.shutdown_event.set()
        self.force_shutdown = True
    
    def install_handlers(self):
        """Install signal handlers"""
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)
    
    async def wait_for_shutdown(self):
        """Wait for shutdown signal"""
        await self.shutdown_event.wait()


class AsyncSpringDocsScraperEnhanced:
    """Enhanced async Spring documentation scraper with progress and shutdown handling"""
    
    def __init__(self, 
                 output_dir: str = 'spring-docs',
                 clean: bool = False,
                 max_connections: int = 20,
                 max_per_host: int = 10,
                 rate_limit: float = 10.0,
                 max_workers: int = 10,
                 use_rich_progress: bool = True,
                 save_checkpoint: bool = True):
        """
        Initialize enhanced async scraper
        
        Args:
            output_dir: Output directory for scraped content
            clean: Whether to clean existing directory
            max_connections: Maximum total connections
            max_per_host: Maximum connections per host
            rate_limit: Requests per second
            max_workers: Maximum concurrent workers
            use_rich_progress: Use rich console for progress
            save_checkpoint: Save progress for resuming
        """
        self.output_dir = Path(output_dir)
        self.clean = clean
        self.logger = logging.getLogger(self.__class__.__name__)
        self.use_rich_progress = use_rich_progress
        self.save_checkpoint = save_checkpoint
        
        # HTTP client
        self.http_client = AsyncHTTPClient(
            max_connections=max_connections,
            max_per_host=max_per_host,
            rate_limit=rate_limit
        )
        
        # URL queue
        self.url_queue = URLQueue(
            max_workers=max_workers,
            max_queue_size=50000
        )
        
        # Data storage
        self.projects: Dict[str, ProjectModel] = {}
        self.routes: Dict[str, RouteModel] = {}
        self.static_cache: Dict[str, str] = {}  # URL -> local path
        self.templates: Dict[str, str] = {}
        
        # Tracking
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        
        # Graceful shutdown
        self.shutdown_handler = GracefulShutdown()
        self.shutdown_task: Optional[asyncio.Task] = None
        
        # Progress tracker
        self.progress_tracker = None
        
        # Checkpoint file
        self.checkpoint_file = self.output_dir / ".scraper_checkpoint.json"
    
    async def scrape_all(self):
        """Main method to scrape all Spring documentation with enhanced features"""
        self.start_time = datetime.now()
        self.shutdown_handler.install_handlers()
        
        try:
            async with create_progress_tracker(self.use_rich_progress) as tracker:
                self.progress_tracker = tracker
                
                # Create shutdown monitoring task
                self.shutdown_task = asyncio.create_task(self.monitor_shutdown())
                
                # Clean or prepare directory
                if self.clean and self.output_dir.exists():
                    self.logger.info(f"Cleaning existing directory: {self.output_dir}")
                    import shutil
                    shutil.rmtree(self.output_dir)
                
                # Create directory structure
                self.create_directory_structure()
                
                # Check for checkpoint
                if self.checkpoint_file.exists() and not self.clean:
                    await self.resume_from_checkpoint()
                else:
                    # Start fresh
                    await self.http_client.start()
                    
                    # 1. Get all projects
                    await self.get_projects()
                    
                    # 2. Get versions for all projects concurrently
                    await self.get_all_versions()
                
                # 3. Scrape documentation concurrently
                await self.scrape_current_docs()
                
                # 4. Create SPA index
                await self.create_spa_index()
                
                # 5. Save metadata
                await self.save_metadata()
                
                self.end_time = datetime.now()
                duration = (self.end_time - self.start_time).total_seconds()
                
                self.logger.info(f"Async scraping complete in {duration:.2f} seconds!")
                self.logger.info(f"Projects: {len(self.projects)}, Routes: {len(self.routes)}")
                
        except asyncio.CancelledError:
            self.logger.info("Scraping cancelled")
            raise
        finally:
            # Cleanup
            await self.cleanup()
    
    async def monitor_shutdown(self):
        """Monitor for shutdown signals"""
        await self.shutdown_handler.wait_for_shutdown()
        
        self.logger.info("Shutdown requested. Saving progress...")
        
        # Save checkpoint
        if self.save_checkpoint:
            await self.save_checkpoint_data()
        
        # Stop queue processing
        self.url_queue.running = False
        
        # Cancel ongoing operations
        tasks = [t for t in asyncio.all_tasks() if t != asyncio.current_task()]
        for task in tasks:
            task.cancel()
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            # Close HTTP client
            if self.http_client.session:
                await self.http_client.close()
            
            # Stop URL queue
            if self.url_queue.running:
                await self.url_queue.stop()
            
            # Cancel shutdown task
            if self.shutdown_task and not self.shutdown_task.done():
                self.shutdown_task.cancel()
                try:
                    await self.shutdown_task
                except asyncio.CancelledError:
                    pass
            
            # Remove checkpoint if completed successfully
            if self.end_time and self.checkpoint_file.exists():
                self.checkpoint_file.unlink()
                
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    async def save_checkpoint_data(self):
        """Save current progress to checkpoint file"""
        checkpoint_data = {
            'timestamp': datetime.now().isoformat(),
            'projects': {name: proj.dict() for name, proj in self.projects.items()},
            'routes': {path: route.dict() for path, route in self.routes.items()},
            'static_cache': self.static_cache,
            'templates': self.templates,
            'queue_state': None  # Will be saved by queue
        }
        
        # Save queue state
        queue_state_file = self.output_dir / ".queue_state.json"
        await self.url_queue.save_state(str(queue_state_file))
        checkpoint_data['queue_state'] = str(queue_state_file)
        
        # Write checkpoint
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
        
        self.logger.info(f"Checkpoint saved to {self.checkpoint_file}")
    
    async def resume_from_checkpoint(self):
        """Resume from saved checkpoint"""
        self.logger.info("Resuming from checkpoint...")
        
        with open(self.checkpoint_file, 'r') as f:
            checkpoint_data = json.load(f)
        
        # Restore data
        for name, proj_data in checkpoint_data.get('projects', {}).items():
            self.projects[name] = ProjectModel(**proj_data)
        
        for path, route_data in checkpoint_data.get('routes', {}).items():
            self.routes[path] = RouteModel(**route_data)
        
        self.static_cache = checkpoint_data.get('static_cache', {})
        self.templates = checkpoint_data.get('templates', {})
        
        # Start HTTP client
        await self.http_client.start()
        
        # Restore queue state
        if checkpoint_data.get('queue_state'):
            queue_state_file = checkpoint_data['queue_state']
            if os.path.exists(queue_state_file):
                await self.url_queue.load_state(queue_state_file)
        
        self.logger.info(f"Resumed with {len(self.projects)} projects, "
                        f"{len(self.routes)} routes, "
                        f"{self.url_queue.queue.qsize()} pending URLs")
    
    def create_directory_structure(self):
        """Create organized directory structure"""
        dirs = [
            self.output_dir / "static" / "css",
            self.output_dir / "static" / "js",
            self.output_dir / "static" / "img",
            self.output_dir / "static" / "fonts",
            self.output_dir / "content",
            self.output_dir / "templates"
        ]
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    async def get_projects(self):
        """Get all Spring projects from the main projects page"""
        url = "https://spring.io/projects"
        html = await self.http_client.fetch_text(url)
        
        if html:
            soup = BeautifulSoup(html, 'lxml')
            links = soup.find_all('a', href=re.compile(r'/projects/spring-[\w-]+'))
            
            # Update progress
            if self.progress_tracker:
                self.progress_tracker.set_projects_total(len(links))
            
            # Process projects concurrently
            tasks = []
            for link in links:
                project_url = urljoin(url, link.get('href'))
                project_name = project_url.split('/')[-1]
                tasks.append(self.get_project_info(project_name, project_url))
            
            # Wait for all project info to be fetched
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Store successful results
            for result in results:
                if isinstance(result, ProjectModel):
                    self.projects[result.name] = result
                    if self.progress_tracker:
                        self.progress_tracker.update_project(result.name)
                elif isinstance(result, Exception):
                    self.logger.error(f"Failed to get project info: {result}")
        
        self.logger.info(f"Found {len(self.projects)} projects")
    
    async def get_project_info(self, project_name: str, project_url: str) -> Optional[ProjectModel]:
        """Get project information"""
        html = await self.http_client.fetch_text(project_url)
        
        if html:
            soup = BeautifulSoup(html, 'lxml')
            desc_elem = soup.find('p', class_='project-description')
            description = desc_elem.text.strip() if desc_elem else None
            
            return ProjectModel(
                name=project_name,
                url=project_url,
                description=description
            )
        return None
    
    async def get_all_versions(self):
        """Get versions for all projects concurrently"""
        tasks = []
        for project_name in self.projects:
            tasks.append(self.get_project_versions(project_name))
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def get_project_versions(self, project_name: str):
        """Get available versions for a project"""
        urls = [
            f"https://docs.spring.io/{project_name}/docs/",
            f"https://docs.spring.io/{project_name}/site/docs/"
        ]
        
        for url in urls:
            html = await self.http_client.fetch_text(url)
            if html:
                soup = BeautifulSoup(html, 'lxml')
                
                if soup.find('pre') or 'Index of' in soup.text:
                    versions = []
                    
                    for link in soup.find_all('a'):
                        href = link.get('href', '')
                        if href and href != '../':
                            version = href.rstrip('/')
                            if (re.match(r'^\d+\.\d+', version) or 
                                version in ['current', 'current-SNAPSHOT']):
                                versions.append(version)
                    
                    self.projects[project_name].versions = sorted(versions, reverse=True)
                    self.logger.info(f"{project_name}: Found {len(versions)} versions")
                    break
    
    async def scrape_current_docs(self):
        """Scrape documentation for current version of each project"""
        # Set up queue callbacks
        self.url_queue.on_success = self.on_url_success
        self.url_queue.on_failure = self.on_url_failure
        
        # Periodic stats update
        async def update_stats():
            while self.url_queue.running:
                if self.progress_tracker:
                    self.progress_tracker.update_queue_stats(self.url_queue.get_stats())
                await asyncio.sleep(1)
        
        stats_task = asyncio.create_task(update_stats())
        
        try:
            # Start the queue processor
            await self.url_queue.start(self.process_doc_url)
            
            # Add initial URLs to queue if not resuming
            if self.url_queue.queue.qsize() == 0:
                for project_name, project in self.projects.items():
                    version = 'current' if 'current' in project.versions else (project.versions[0] if project.versions else None)
                    
                    if version:
                        # Add reference and API doc URLs
                        doc_urls = {
                            DocType.REFERENCE: [
                                f"https://docs.spring.io/{project_name}/docs/{version}/reference/html/",
                                f"https://docs.spring.io/{project_name}/reference/index.html",
                                f"https://docs.spring.io/{project_name}/reference/"
                            ],
                            DocType.API: [
                                f"https://docs.spring.io/{project_name}/docs/{version}/api/",
                                f"https://docs.spring.io/{project_name}/api/java/index.html",
                                f"https://docs.spring.io/{project_name}/docs/{version}/javadoc-api/"
                            ]
                        }
                        
                        for doc_type, urls in doc_urls.items():
                            for url in urls:
                                await self.url_queue.add_url(
                                    url,
                                    Priority.HIGH,
                                    {
                                        'project': project_name,
                                        'version': version,
                                        'doc_type': doc_type,
                                        'is_index': True
                                    }
                                )
            
            # Wait for processing to complete or shutdown
            await self.url_queue.wait_complete()
            
        finally:
            stats_task.cancel()
            await self.url_queue.stop()
    
    async def process_doc_url(self, url: str, metadata: Dict) -> Optional[ScrapedContent]:
        """Process a documentation URL"""
        # Update progress
        if self.progress_tracker:
            self.progress_tracker.update_url(url, success=False)  # Will update to success if completed
        
        html = await self.http_client.fetch_text(url)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'lxml')
        project_name = metadata['project']
        doc_type = metadata['doc_type']
        
        # Process based on doc type
        result = None
        if doc_type == DocType.REFERENCE:
            result = await self.process_reference_doc(project_name, url, soup, metadata)
        elif doc_type == DocType.API:
            result = await self.process_api_doc(project_name, url, soup, metadata)
        
        # Update progress on success
        if result and self.progress_tracker:
            self.progress_tracker.update_url(url, success=True)
        
        return result
    
    async def process_reference_doc(self, project_name: str, url: str, soup: BeautifulSoup, metadata: Dict) -> Optional[ScrapedContent]:
        """Process reference documentation"""
        # Extract and save template if not already saved
        if DocType.REFERENCE not in self.templates:
            self.extract_reference_template(soup)
        
        # Extract navigation structure
        nav_data = self.extract_navigation(soup)
        
        # Extract main content
        article = soup.find('article', class_='doc')
        if article:
            title_elem = soup.find('h1', class_='page')
            title = title_elem.text if title_elem else 'Overview'
            
            content = ScrapedContent(
                title=title,
                content=str(article),
                nav=nav_data,
                type=DocType.REFERENCE,
                project=project_name
            )
            
            # Save content
            content_path = self.output_dir / "content" / f"{project_name}-reference-{hashlib.md5(url.encode()).hexdigest()[:8]}.json"
            with open(content_path, 'w', encoding='utf-8') as f:
                f.write(content.json())
            
            # Create route
            route_path = self.create_route_path(project_name, DocType.REFERENCE, url)
            self.routes[route_path] = RouteModel(
                content=f"/content/{content_path.name}",
                title=title,
                project=project_name,
                type=DocType.REFERENCE
            )
            
            # Extract and queue additional pages if this is the index
            if metadata.get('is_index'):
                await self.queue_reference_pages(project_name, url, nav_data, metadata['version'])
            
            # Extract resources
            resources = await self.extract_resources(soup, url)
            await self.download_resources(resources)
            
            return content
        
        return None
    
    async def process_api_doc(self, project_name: str, url: str, soup: BeautifulSoup, metadata: Dict) -> Optional[ScrapedContent]:
        """Process API documentation"""
        # Extract and save template if not already saved
        if DocType.API not in self.templates:
            self.extract_api_template(soup)
        
        # Extract main content
        main = soup.find('main') or soup.find('body')
        if main:
            title_elem = soup.find('title')
            title = title_elem.text if title_elem else 'API Documentation'
            
            content = ScrapedContent(
                title=title,
                content=str(main),
                type=DocType.API,
                project=project_name
            )
            
            # Save content
            content_path = self.output_dir / "content" / f"{project_name}-api-{hashlib.md5(url.encode()).hexdigest()[:8]}.json"
            with open(content_path, 'w', encoding='utf-8') as f:
                f.write(content.json())
            
            # Create route
            route_path = self.create_route_path(project_name, DocType.API, url)
            self.routes[route_path] = RouteModel(
                content=f"/content/{content_path.name}",
                title=title,
                project=project_name,
                type=DocType.API
            )
            
            # Extract resources
            resources = await self.extract_resources(soup, url)
            await self.download_resources(resources)
            
            return content
        
        return None
    
    def extract_reference_template(self, soup: BeautifulSoup):
        """Extract the common template from reference docs"""
        template_soup = BeautifulSoup(str(soup), 'lxml')
        
        # Remove the unique content
        article = template_soup.find('article', class_='doc')
        if article:
            article.clear()
            article.append(BeautifulSoup('<div id="content-placeholder"></div>', 'html.parser'))
        
        # Save template
        self.templates[DocType.REFERENCE] = str(template_soup)
        
        template_path = self.output_dir / "templates" / "reference.html"
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(self.templates[DocType.REFERENCE])
    
    def extract_api_template(self, soup: BeautifulSoup):
        """Extract the common template from API docs"""
        template_soup = BeautifulSoup(str(soup), 'lxml')
        
        # Remove unique content
        main = template_soup.find('main')
        if main:
            main.clear()
            main.append(BeautifulSoup('<div id="content-placeholder"></div>', 'html.parser'))
        
        # Save template
        self.templates[DocType.API] = str(template_soup)
        
        template_path = self.output_dir / "templates" / "api.html"
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(self.templates[DocType.API])
    
    def extract_navigation(self, soup: BeautifulSoup) -> List[NavigationItem]:
        """Extract navigation structure from the page"""
        nav_data = []
        nav_menu = soup.find('nav', class_='nav-menu')
        
        if nav_menu:
            for item in nav_menu.find_all('li', class_='nav-item'):
                link = item.find('a')
                if link:
                    nav_entry = NavigationItem(
                        text=link.text.strip(),
                        href=link.get('href', ''),
                        children=[]
                    )
                    
                    # Check for sub-items
                    sub_list = item.find('ul', class_='nav-list')
                    if sub_list:
                        for sub_item in sub_list.find_all('li', class_='nav-item', recursive=False):
                            sub_link = sub_item.find('a')
                            if sub_link:
                                nav_entry.children.append(NavigationItem(
                                    text=sub_link.text.strip(),
                                    href=sub_link.get('href', '')
                                ))
                    
                    nav_data.append(nav_entry)
        
        return nav_data
    
    async def queue_reference_pages(self, project_name: str, base_url: str, nav_data: List[NavigationItem], version: str):
        """Queue additional reference pages for processing"""
        def extract_urls(items: List[NavigationItem], urls: Set[str]):
            for item in items:
                if item.href and not item.href.startswith(('#', 'http://', 'https://')):
                    urls.add(urljoin(base_url, item.href))
                if item.children:
                    extract_urls(item.children, urls)
        
        urls_to_process = set()
        extract_urls(nav_data, urls_to_process)
        
        # Add URLs to queue with normal priority
        for url in urls_to_process:
            await self.url_queue.add_url(
                url,
                Priority.NORMAL,
                {
                    'project': project_name,
                    'version': version,
                    'doc_type': DocType.REFERENCE,
                    'is_index': False
                }
            )
    
    async def extract_resources(self, soup: BeautifulSoup, base_url: str) -> List[ResourceInfo]:
        """Extract static resources from HTML"""
        resources = []
        
        # CSS
        for link in soup.find_all('link', rel='stylesheet'):
            href = link.get('href')
            if href and not href.startswith(('http://', 'https://', 'data:')):
                resources.append(ResourceInfo(
                    url=urljoin(base_url, href),
                    local_path='',
                    resource_type='css'
                ))
        
        # JS
        for script in soup.find_all('script', src=True):
            src = script.get('src')
            if src and not src.startswith(('http://', 'https://', 'data:')):
                resources.append(ResourceInfo(
                    url=urljoin(base_url, src),
                    local_path='',
                    resource_type='js'
                ))
        
        # Images
        for img in soup.find_all('img', src=True):
            src = img.get('src')
            if src and not src.startswith(('http://', 'https://', 'data:')):
                resources.append(ResourceInfo(
                    url=urljoin(base_url, src),
                    local_path='',
                    resource_type='img'
                ))
        
        return resources
    
    async def download_resources(self, resources: List[ResourceInfo]):
        """Download static resources concurrently"""
        tasks = []
        for resource in resources:
            if str(resource.url) not in self.static_cache:
                tasks.append(self.download_resource(resource))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def download_resource(self, resource: ResourceInfo) -> Optional[str]:
        """Download a single static resource"""
        url = str(resource.url)
        
        # Check cache
        if url in self.static_cache:
            return self.static_cache[url]
        
        content = await self.http_client.fetch_bytes(url)
        if content:
            # Generate filename
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)
            if not filename:
                filename = hashlib.md5(url.encode()).hexdigest()[:8]
            
            # Determine path
            if resource.resource_type == 'css':
                local_path = self.output_dir / "static" / "css" / filename
            elif resource.resource_type == 'js':
                local_path = self.output_dir / "static" / "js" / filename
            elif resource.resource_type == 'img':
                local_path = self.output_dir / "static" / "img" / filename
            else:
                local_path = self.output_dir / "static" / filename
            
            # Save file
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            if resource.resource_type in ['css', 'js'] or filename.endswith('.svg'):
                # Text content
                text = content.decode('utf-8', errors='replace')
                with open(local_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                
                # Process CSS for nested resources
                if resource.resource_type == 'css':
                    await self.process_css_resources(text, url)
            else:
                # Binary content
                with open(local_path, 'wb') as f:
                    f.write(content)
            
            # Update progress
            if self.progress_tracker:
                self.progress_tracker.add_resource_download(len(content))
            
            # Cache the path
            relative_path = str(local_path.relative_to(self.output_dir))
            self.static_cache[url] = relative_path
            resource.local_path = relative_path
            resource.size_bytes = len(content)
            
            return relative_path
        
        return None
    
    async def process_css_resources(self, css_content: str, base_url: str):
        """Extract and download resources referenced in CSS"""
        url_pattern = re.compile(r'url\(["\']?([^"\'()]+)["\']?\)')
        
        resources = []
        for match in url_pattern.finditer(css_content):
            resource_url = match.group(1)
            if not resource_url.startswith(('data:', 'http://', 'https://')):
                full_url = urljoin(base_url, resource_url)
                
                # Determine type based on extension
                if resource_url.endswith(('.woff', '.woff2', '.ttf', '.eot')):
                    resource_type = 'fonts'
                elif resource_url.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg')):
                    resource_type = 'img'
                else:
                    resource_type = 'other'
                
                resources.append(ResourceInfo(
                    url=full_url,
                    local_path='',
                    resource_type=resource_type
                ))
        
        if resources:
            await self.download_resources(resources)
    
    def create_route_path(self, project_name: str, doc_type: DocType, url: str) -> str:
        """Create a route path from URL"""
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.strip('/').split('/')
        
        # Simplify path
        if 'index.html' in path_parts[-1]:
            path_parts[-1] = ''
        
        # Create route
        route_parts = [project_name, doc_type.value]
        route_parts.extend([p for p in path_parts[-2:] if p])
        
        return '/' + '/'.join(route_parts)
    
    async def on_url_success(self, url: str, result: Any):
        """Callback for successful URL processing"""
        self.logger.debug(f"Successfully processed: {url}")
    
    async def on_url_failure(self, url: str, error: str):
        """Callback for failed URL processing"""
        self.logger.error(f"Failed to process {url}: {error}")
    
    async def create_spa_index(self):
        """Create the main SPA index.html"""
        # Reuse the existing SPA HTML from the sync version
        spa_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Spring Documentation - Async Edition</title>
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
        
        .performance-badge {
            display: inline-block;
            background: rgba(255,255,255,0.2);
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.8rem;
            margin-left: 1rem;
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
        
        .stat-value.performance {
            color: #ff6b6b;
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
        <h1>Spring Documentation Browser <span class="performance-badge">⚡ Async Edition</span></h1>
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
            const duration = data.scrape_duration_seconds || 0;
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
                <div class="stat-item">
                    <span class="stat-label">Scrape Time</span>
                    <span class="stat-value performance">${duration.toFixed(1)}s</span>
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
            
            const viewer = document.getElementById('doc-viewer');
            const frame = document.getElementById('viewer-frame');
            const titleElem = document.getElementById('viewer-title');
            
            titleElem.textContent = title;
            
            // Load the original scraped HTML for now
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
        
        index_path = self.output_dir / "index.html"
        with open(index_path, 'w') as f:
            f.write(spa_html)
    
    async def save_metadata(self):
        """Save project metadata and routes"""
        duration = (self.end_time - self.start_time).total_seconds() if self.end_time else 0
        
        # Convert Pydantic models to dict for JSON serialization
        projects_dict = {name: project.dict() for name, project in self.projects.items()}
        
        # Save main metadata
        metadata = ScrapeMetadata(
            total_projects=len(self.projects),
            projects=self.projects,
            total_routes=len(self.routes),
            total_static_resources=len(self.static_cache),
            scrape_duration_seconds=duration
        )
        
        metadata_path = self.output_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            f.write(metadata.json(indent=2))
        
        # Save routes
        routes_dict = {path: route.dict() for path, route in self.routes.items()}
        routes_path = self.output_dir / "routes.json"
        with open(routes_path, 'w') as f:
            json.dump(routes_dict, f, indent=2)
        
        # Get client and queue stats
        client_stats = self.http_client.get_stats()
        queue_stats = self.url_queue.get_stats()
        
        self.logger.info(f"Saved metadata for {len(self.projects)} projects")
        self.logger.info(f"Created {len(self.routes)} routes")
        self.logger.info(f"Downloaded {len(self.static_cache)} static resources")
        self.logger.info(f"HTTP client stats: {client_stats}")
        self.logger.info(f"Queue stats: {queue_stats}")
        
        # Create summary
        summary = f"""Spring Documentation Async Scrape Summary
Date: {metadata.scrape_date}
Duration: {duration:.2f} seconds
Total Projects: {metadata.total_projects}
Total Routes: {len(self.routes)}
Static Resources: {len(self.static_cache)}

Performance Metrics:
- Total HTTP requests: {client_stats.get('total_requests', 0)}
- Successful requests: {client_stats.get('successful_requests', 0)}
- Failed requests: {client_stats.get('failed_requests', 0)}
- Average rate: {client_stats.get('avg_rate', 0):.2f} req/s
- Total bytes downloaded: {client_stats.get('total_bytes', 0):,}

Queue Metrics:
- Total URLs queued: {queue_stats.get('total_queued', 0)}
- Total processed: {queue_stats.get('total_processed', 0)}
- Total failed: {queue_stats.get('total_failed', 0)}
- Average processing rate: {queue_stats.get('avg_rate', 0):.2f} URL/s

Projects with documentation:
"""
        for name, project in self.projects.items():
            if project.docs:
                summary += f"\n{name}:"
                summary += f"\n  Versions: {len(project.versions)}"
                summary += f"\n  Docs: {', '.join(doc_type.value for doc_type in project.docs.keys())}"
        
        summary_path = self.output_dir / "summary.txt"
        with open(summary_path, 'w') as f:
            f.write(summary)


async def main():
    import argparse
    parser = argparse.ArgumentParser(description='Enhanced async Spring documentation scraper')
    parser.add_argument('--clean', action='store_true', 
                        help='Clean existing documentation before scraping')
    parser.add_argument('--max-connections', type=int, default=20,
                        help='Maximum concurrent connections (default: 20)')
    parser.add_argument('--rate-limit', type=float, default=10.0,
                        help='Requests per second (default: 10.0)')
    parser.add_argument('--max-workers', type=int, default=10,
                        help='Maximum concurrent workers (default: 10)')
    parser.add_argument('--no-rich', action='store_true',
                        help='Disable rich console progress display')
    parser.add_argument('--no-checkpoint', action='store_true',
                        help='Disable checkpoint saving')
    args = parser.parse_args()
    
    scraper = AsyncSpringDocsScraperEnhanced(
        clean=args.clean,
        max_connections=args.max_connections,
        rate_limit=args.rate_limit,
        max_workers=args.max_workers,
        use_rich_progress=not args.no_rich,
        save_checkpoint=not args.no_checkpoint
    )
    
    try:
        await scraper.scrape_all()
    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
    except Exception as e:
        print(f"\nError during scraping: {e}")
        raise
    
    print("\nAsync scraping complete! Check 'spring-docs' directory for results.")
    print("Run 'python serve_docs.py' to browse the documentation.")


if __name__ == "__main__":
    asyncio.run(main())