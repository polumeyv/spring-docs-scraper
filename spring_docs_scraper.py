#!/usr/bin/env python3
"""
Spring Documentation Scraper
Scrapes documentation from all Spring projects
"""

import requests
import json
import time
import re
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class SpringDocsScraper:
    def __init__(self, output_dir='spring-docs'):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Compatible; Spring Docs Scraper)'
        })
        self.output_dir = output_dir
        self.projects = {}
        self.rate_limit = 0.3  # seconds between requests
        
    def scrape_all(self):
        """Main method to scrape all Spring documentation"""
        logging.info("Starting Spring documentation scrape...")
        
        # 1. Get all projects
        self.get_projects()
        
        # 2. For each project, get versions
        self.get_all_versions()
        
        # 3. Scrape documentation for current versions
        self.scrape_current_docs()
        
        # 4. Save metadata
        self.save_metadata()
        
    def get_projects(self):
        """Get all Spring projects from the main projects page"""
        url = "https://spring.io/projects"
        response = self.session.get(url)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all project links
            links = soup.find_all('a', href=re.compile(r'/projects/spring-[\w-]+'))
            
            for link in links:
                project_url = urljoin(url, link.get('href'))
                project_name = project_url.split('/')[-1]
                
                # Get project info
                project_response = self.session.get(project_url)
                if project_response.status_code == 200:
                    project_soup = BeautifulSoup(project_response.text, 'html.parser')
                    
                    # Extract description
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
        # Try common version listing URLs
        urls = [
            f"https://docs.spring.io/{project_name}/docs/",
            f"https://docs.spring.io/{project_name}/site/docs/"
        ]
        
        for url in urls:
            try:
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Check if it's a directory listing
                    if soup.find('pre') or 'Index of' in soup.text:
                        versions = []
                        
                        # Extract version links
                        for link in soup.find_all('a'):
                            href = link.get('href', '')
                            if href and href != '../':
                                version = href.rstrip('/')
                                # Check if it looks like a version
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
                # Use the latest version
                self.scrape_project_docs(project_name, project['versions'][0])
                
    def scrape_project_docs(self, project_name, version):
        """Scrape documentation for a specific project version"""
        logging.info(f"Scraping {project_name} {version}")
        
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
                        
                        # Save the documentation
                        self.save_doc(project_name, version, doc_type, response.text)
                        break
                        
                    time.sleep(self.rate_limit)
                except:
                    pass
                    
    def save_doc(self, project_name, version, doc_type, content):
        """Save documentation content to disk"""
        # Create directory structure
        doc_dir = os.path.join(self.output_dir, project_name, version, doc_type)
        os.makedirs(doc_dir, exist_ok=True)
        
        # Save index.html
        with open(os.path.join(doc_dir, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(content)
            
        logging.info(f"Saved {project_name}/{version}/{doc_type}")
        
    def save_metadata(self):
        """Save project metadata"""
        metadata = {
            'scrape_date': datetime.now().isoformat(),
            'total_projects': len(self.projects),
            'projects': self.projects
        }
        
        os.makedirs(self.output_dir, exist_ok=True)
        with open(os.path.join(self.output_dir, 'metadata.json'), 'w') as f:
            json.dump(metadata, f, indent=2)
            
        logging.info("Metadata saved")
        
        # Create simple summary
        summary = f"""Spring Documentation Scrape Summary
Date: {metadata['scrape_date']}
Total Projects: {metadata['total_projects']}

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
    scraper = SpringDocsScraper()
    scraper.scrape_all()
    print("\nScraping complete! Check 'spring-docs' directory for results.")


if __name__ == "__main__":
    main()