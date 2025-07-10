#!/usr/bin/env python3
import http.server
import socketserver
import os
import json
from urllib.parse import unquote
import threading
import webbrowser
import time

PORT = 8082
DOCS_DIR = os.environ.get('DOCS_PATH', '/app/docs')

class SpringDocsHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DOCS_DIR, **kwargs)
    
    def do_GET(self):
        path = unquote(self.path)
        
        # Serve the custom index page at root
        if path == "/" or path == "/index.html":
            self.serve_index_page()
            return
            
        # Serve static files normally
        super().do_GET()
    
    def serve_index_page(self):
        """Generate and serve the main index page listing all Spring projects"""
        try:
            # Load metadata
            metadata_path = os.path.join(DOCS_DIR, "metadata.json")
            with open(metadata_path, 'r') as f:
                full_metadata = json.load(f)
            
            # Extract projects from metadata
            metadata = full_metadata.get('projects', {})
            
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
    </style>
</head>
<body>
    <div class="container">
        <h1>🌱 Spring Documentation Browser</h1>
        <p class="subtitle">Browse local copies of Spring project documentation</p>
        
        <div class="stats">
            <span class="stat-item">Total Projects: <span class="stat-value">""" + str(len(metadata)) + """</span></span>
            <span class="stat-item">Server Port: <span class="stat-value">""" + str(PORT) + """</span></span>
        </div>
        
        <div class="projects-grid">
"""
            
            # Add project cards
            for project_name, project_data in sorted(metadata.items()):
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

def open_browser():
    """Open the browser after a short delay"""
    time.sleep(1)
    webbrowser.open(f'http://localhost:{PORT}')

def main():
    # Don't change directory in Docker environment
    if not os.environ.get('DOCS_PATH'):
        # Local development - change to script directory
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Check if docs directory exists
    if not os.path.exists(DOCS_DIR):
        print(f"Error: '{DOCS_DIR}' directory not found!")
        print("Please run 'python spring_docs_scraper.py' first to download documentation.")
        return
    
    # Create the server
    with socketserver.TCPServer(("", PORT), SpringDocsHandler) as httpd:
        print(f"🌱 Spring Documentation Server")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"Server running at: http://localhost:{PORT}")
        print(f"Press Ctrl+C to stop the server")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        # Open browser in a separate thread (only in local development)
        if not os.environ.get('DOCS_PATH'):
            browser_thread = threading.Thread(target=open_browser)
            browser_thread.daemon = True
            browser_thread.start()
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n✓ Server stopped")

if __name__ == "__main__":
    main()