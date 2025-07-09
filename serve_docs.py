#!/usr/bin/env python3
import http.server
import socketserver
import os
import json
from pathlib import Path
from urllib.parse import urlparse, unquote
import threading
import webbrowser
import time
import requests

PORT = 8081
DOCS_DIR = "spring-docs"

class SpringDocsHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Load metadata for proxy URLs
        with open(os.path.join(DOCS_DIR, "metadata.json"), 'r') as f:
            self.metadata = json.load(f).get('projects', {})
        super().__init__(*args, directory=DOCS_DIR, **kwargs)
    
    def do_GET(self):
        path = unquote(self.path)
        
        # Serve the custom index page at root
        if path == "/" or path == "/index.html":
            self.serve_index_page()
            return
        
        # Try to serve local file first
        local_path = os.path.join(DOCS_DIR, path.lstrip('/'))
        if os.path.exists(local_path) and os.path.isfile(local_path):
            # Inject navigation for HTML files
            if path.endswith('.html') and not path.endswith('/index.html'):
                self.inject_navigation(path)
                return
            # Serve other files normally
            super().do_GET()
            return
        
        # If file doesn't exist locally, try to proxy it from Spring docs
        self.proxy_resource(path)
    
    def proxy_resource(self, path):
        """Proxy missing resources from Spring documentation sites"""
        # Parse the path to extract project and resource type
        parts = path.strip('/').split('/')
        if len(parts) < 4:
            self.send_error(404, "File not found")
            return
        
        project_name = parts[0]
        version = parts[1]  # Should be 'current'
        doc_type = parts[2]  # 'api' or 'reference'
        resource_path = '/'.join(parts[3:])
        
        # Get base URL from metadata
        if project_name not in self.metadata:
            self.send_error(404, "Project not found")
            return
        
        project_data = self.metadata[project_name]
        docs = project_data.get('docs', {})
        
        if doc_type not in docs:
            self.send_error(404, "Documentation type not found")
            return
        
        # Construct the remote URL
        base_url = docs[doc_type]
        if base_url.endswith('index.html'):
            base_url = base_url[:-10]  # Remove index.html
        elif base_url.endswith('/'):
            base_url = base_url[:-1]
        
        remote_url = f"{base_url}/{resource_path}"
        
        try:
            # Fetch the resource from Spring docs
            response = requests.get(remote_url, timeout=10)
            response.raise_for_status()
            
            # Send the response
            self.send_response(200)
            
            # Set content type based on file extension
            if resource_path.endswith('.css'):
                content_type = 'text/css'
            elif resource_path.endswith('.js'):
                content_type = 'application/javascript'
            elif resource_path.endswith('.png'):
                content_type = 'image/png'
            elif resource_path.endswith('.svg'):
                content_type = 'image/svg+xml'
            elif resource_path.endswith('.ico'):
                content_type = 'image/x-icon'
            elif resource_path.endswith('.woff2'):
                content_type = 'font/woff2'
            else:
                content_type = 'application/octet-stream'
            
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(response.content)))
            self.send_header('Cache-Control', 'public, max-age=3600')  # Cache for 1 hour
            self.end_headers()
            
            self.wfile.write(response.content)
            
        except Exception as e:
            self.send_error(404, f"Resource not found: {str(e)}")
    
    def serve_index_page(self):
        """Generate and serve the main index page listing all Spring projects"""
        try:
            # Generate HTML
            html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Spring Documentation Browser</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #6db33f;
            margin-bottom: 10px;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
        }
        .projects-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }
        .project-card {
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            padding: 20px;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .project-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        .project-name {
            font-size: 18px;
            font-weight: 600;
            color: #333;
            margin-bottom: 10px;
        }
        .project-version {
            font-size: 14px;
            color: #666;
            margin-bottom: 15px;
        }
        .doc-links {
            display: flex;
            gap: 15px;
        }
        .doc-link {
            text-decoration: none;
            color: #6db33f;
            font-weight: 500;
            padding: 8px 16px;
            border: 1px solid #6db33f;
            border-radius: 4px;
            transition: background-color 0.2s, color 0.2s;
        }
        .doc-link:hover {
            background-color: #6db33f;
            color: white;
        }
        .stats {
            margin-top: 30px;
            padding: 20px;
            background-color: #f8f8f8;
            border-radius: 6px;
        }
        .stat-item {
            display: inline-block;
            margin-right: 30px;
            color: #666;
        }
        .stat-value {
            font-weight: 600;
            color: #333;
        }
        .info-box {
            background-color: #e8f5e9;
            border-left: 4px solid #6db33f;
            padding: 15px;
            margin-top: 20px;
            border-radius: 4px;
        }
        .info-box p {
            margin: 0;
            color: #2e7d32;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🌱 Spring Documentation Browser</h1>
        <p class="subtitle">Browse local copies of Spring project documentation with automatic resource loading</p>
        
        <div class="info-box">
            <p>📡 This server automatically fetches CSS, JavaScript, and images from Spring's servers when needed, ensuring documentation displays correctly.</p>
        </div>
        
        <div class="stats">
            <span class="stat-item">Total Projects: <span class="stat-value">""" + str(len(self.metadata)) + """</span></span>
            <span class="stat-item">Server Port: <span class="stat-value">""" + str(PORT) + """</span></span>
            <span class="stat-item">Mode: <span class="stat-value">Proxy-enabled</span></span>
        </div>
        
        <div class="projects-grid">
"""
            
            # Add project cards
            for project_name, project_data in sorted(self.metadata.items()):
                if not isinstance(project_data, dict):
                    continue
                    
                versions = project_data.get("versions", [])
                # Find the current version in the list
                version_number = "current"
                if isinstance(versions, list) and "current" in versions:
                    version_number = "current"
                elif isinstance(versions, list) and len(versions) > 0:
                    # Use the first non-snapshot version if available
                    for v in versions:
                        if "SNAPSHOT" not in v:
                            version_number = v
                            break
                
                html += f"""
            <div class="project-card">
                <div class="project-name">{project_name}</div>
                <div class="project-version">Version: {version_number}</div>
                <div class="doc-links">
"""
                
                # Check for API docs
                api_path = f"{project_name}/current/api/index.html"
                if os.path.exists(os.path.join(DOCS_DIR, api_path)):
                    html += f'                    <a href="/{api_path}" class="doc-link">API Docs</a>\n'
                
                # Check for Reference docs
                ref_path = f"{project_name}/current/reference/index.html"
                if os.path.exists(os.path.join(DOCS_DIR, ref_path)):
                    html += f'                    <a href="/{ref_path}" class="doc-link">Reference</a>\n'
                
                html += """                </div>
            </div>
"""
            
            html += """        </div>
    </div>
</body>
</html>"""
            
            # Send response
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.send_header("Content-length", str(len(html.encode())))
            self.end_headers()
            self.wfile.write(html.encode())
            
        except Exception as e:
            self.send_error(500, f"Error generating index page: {str(e)}")
    
    def inject_navigation(self, path):
        """Inject a navigation bar into HTML pages"""
        try:
            # Read the original HTML file
            file_path = os.path.join(DOCS_DIR, path.lstrip('/'))
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Create navigation bar
            nav_html = """
<style>
    .spring-docs-nav {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        background-color: #6db33f;
        color: white;
        padding: 10px 20px;
        z-index: 10000;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    .spring-docs-nav a {
        color: white;
        text-decoration: none;
        margin-right: 20px;
        font-weight: 500;
    }
    .spring-docs-nav a:hover {
        text-decoration: underline;
    }
    body {
        padding-top: 50px !important;
    }
</style>
<div class="spring-docs-nav">
    <a href="/">← All Projects</a>
    <span style="margin-left: 20px; opacity: 0.8;">Spring Documentation Browser (Proxy Mode)</span>
</div>
"""
            
            # Inject after <body> tag
            if '<body' in html_content:
                body_index = html_content.find('>', html_content.find('<body')) + 1
                html_content = html_content[:body_index] + nav_html + html_content[body_index:]
            else:
                # If no body tag, inject at the beginning
                html_content = nav_html + html_content
            
            # Send response
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.send_header("Content-length", str(len(html_content.encode())))
            self.end_headers()
            self.wfile.write(html_content.encode())
            
        except Exception as e:
            super().do_GET()  # Fall back to normal file serving

def open_browser():
    """Open the browser after a short delay"""
    time.sleep(1)
    webbrowser.open(f'http://localhost:{PORT}')

def main():
    # Change to the script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Check if docs directory exists
    if not os.path.exists(DOCS_DIR):
        print(f"Error: '{DOCS_DIR}' directory not found!")
        print("Please make sure you're running this script from the docs-scraper directory.")
        return
    
    # Create the server
    with socketserver.TCPServer(("", PORT), SpringDocsHandler) as httpd:
        print(f"🌱 Spring Documentation Server (Proxy-Enabled)")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"Server running at: http://localhost:{PORT}")
        print(f"Press Ctrl+C to stop the server")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"\n📡 This server will automatically fetch missing")
        print(f"   resources from Spring's documentation servers")
        print(f"   ensuring proper display of all content.\n")
        
        # Open browser in a separate thread
        browser_thread = threading.Thread(target=open_browser)
        browser_thread.daemon = True
        browser_thread.start()
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n✓ Server stopped")

if __name__ == "__main__":
    main()