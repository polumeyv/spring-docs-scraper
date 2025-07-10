#!/usr/bin/env python3
"""
Test documentation server that serves from spring-docs subdirectory
"""
import http.server
import socketserver
import os
import json
from urllib.parse import unquote

PORT = 8083
DOCS_BASE = os.environ.get('DOCS_PATH', '/app/docs')

class TestDocsHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Look for spring-docs subdirectory first
        docs_dir = os.path.join(DOCS_BASE, 'spring-docs')
        if os.path.exists(docs_dir):
            print(f"Serving from: {docs_dir}")
            super().__init__(*args, directory=docs_dir, **kwargs)
        else:
            print(f"Serving from: {DOCS_BASE}")
            super().__init__(*args, directory=DOCS_BASE, **kwargs)
    
    def do_GET(self):
        path = unquote(self.path)
        
        # Serve index.html at root
        if path == "/":
            if os.path.exists(os.path.join(self.directory, 'index.html')):
                self.path = "/index.html"
            else:
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(self.generate_status_page().encode())
                return
        
        # Serve files normally
        super().do_GET()
    
    def generate_status_page(self):
        """Generate a status page showing current scraping progress"""
        html = """<!DOCTYPE html>
<html>
<head>
    <title>Spring Docs - Test Server</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .status { background: #f0f0f0; padding: 20px; border-radius: 8px; }
        .file-list { margin-top: 20px; }
        .file-list h3 { color: #333; }
        ul { list-style-type: none; padding-left: 0; }
        li { padding: 5px 0; }
        a { color: #007bff; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>Spring Documentation Test Server</h1>
    <div class="status">
        <h2>Status</h2>
"""
        
        # Check for metadata
        metadata_path = os.path.join(self.directory, 'metadata.json')
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                html += f"<p>✅ Scraping complete!</p>"
                html += f"<p>Projects: {metadata.get('total_projects', 0)}</p>"
                html += f"<p>Routes: {metadata.get('total_routes', 0)}</p>"
                html += f"<p><a href='/index.html'>View Documentation</a></p>"
            except:
                html += "<p>⏳ Reading metadata...</p>"
        else:
            # Count content files to show progress
            content_dir = os.path.join(self.directory, 'content')
            if os.path.exists(content_dir):
                file_count = len([f for f in os.listdir(content_dir) if f.endswith('.json')])
                html += f"<p>⏳ Scraping in progress...</p>"
                html += f"<p>Content files created: {file_count}</p>"
            else:
                html += "<p>⏳ Waiting for scraper to start...</p>"
        
        html += """
    </div>
    <div class="file-list">
        <h3>Available Files:</h3>
        <ul>
"""
        
        # List available files
        for item in sorted(os.listdir(self.directory)):
            if not item.startswith('.'):
                path = f"/{item}"
                if os.path.isdir(os.path.join(self.directory, item)):
                    html += f'<li>📁 <a href="{path}/">{item}/</a></li>'
                else:
                    html += f'<li>📄 <a href="{path}">{item}</a></li>'
        
        html += """
        </ul>
    </div>
    <script>
        // Auto-refresh every 5 seconds while scraping
        if (!document.querySelector('a[href="/index.html"]')) {
            setTimeout(() => location.reload(), 5000);
        }
    </script>
</body>
</html>"""
        return html

    def log_message(self, format, *args):
        # Reduce logging noise
        if '/favicon.ico' not in args[0]:
            super().log_message(format, *args)

def main():
    with socketserver.TCPServer(("", PORT), TestDocsHandler) as httpd:
        print(f"Test documentation server running at http://localhost:{PORT}")
        print("This server auto-refreshes the status page during scraping.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")

if __name__ == "__main__":
    main()