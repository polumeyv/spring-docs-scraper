#!/usr/bin/env python3
import os
import json
import asyncio
import re
from flask import Flask, jsonify, request
from flask_cors import CORS
from typing import List, Dict, Optional
import logging
from doc_search_service import DocSearchService

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route('/api/search-docs', methods=['GET'])
def search_docs():
    """Search for documentation links for a given framework/tool"""
    framework = request.args.get('q', '').strip()
    
    if not framework:
        return jsonify({'error': 'Please provide a framework name'}), 400
    
    try:
        # Run the async search in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def run_search():
            async with DocSearchService() as search_service:
                return await search_service.search_documentation(framework)
        
        results = loop.run_until_complete(run_search())
        loop.close()
        
        return jsonify({
            'framework': framework,
            'links': results
        })
            
    except Exception as e:
        logger.error(f"Error in search_docs: {e}")
        return jsonify({'error': 'Failed to search documentation'}), 500

@app.route('/api/scrape', methods=['POST'])
def scrape_documentation():
    """Scrape documentation from a given URL"""
    data = request.json
    url = data.get('url', '').strip()
    folder = data.get('folder', '').strip()
    framework = data.get('framework', '').strip()
    
    if not all([url, folder, framework]):
        return jsonify({'error': 'Missing required parameters'}), 400
    
    # TODO: Implement actual scraping logic
    # This would integrate with the existing scraper modules
    
    return jsonify({
        'status': 'started',
        'message': f'Started scraping {url} for {framework}',
        'folder': folder
    })

@app.route('/api/folders', methods=['GET'])
def list_folders():
    """List available folders for storing documentation"""
    docs_dir = os.environ.get('DOCS_PATH', '/app/docs')
    
    try:
        # List all directories in the docs folder
        folders = []
        if os.path.exists(docs_dir):
            for item in os.listdir(docs_dir):
                item_path = os.path.join(docs_dir, item)
                if os.path.isdir(item_path):
                    folders.append({
                        'name': item,
                        'path': item_path,
                        'created': os.path.getctime(item_path)
                    })
        
        # Sort by creation time (newest first)
        folders.sort(key=lambda x: x['created'], reverse=True)
        
        return jsonify({'folders': folders})
    except Exception as e:
        logger.error(f"Error listing folders: {e}")
        return jsonify({'error': 'Failed to list folders'}), 500

@app.route('/api/folders', methods=['POST'])
def create_folder():
    """Create a new folder for storing documentation"""
    data = request.json
    folder_name = data.get('name', '').strip()
    
    if not folder_name:
        return jsonify({'error': 'Folder name is required'}), 400
    
    # Sanitize folder name
    folder_name = re.sub(r'[^\w\s-]', '', folder_name)
    folder_name = re.sub(r'[-\s]+', '-', folder_name)
    
    docs_dir = os.environ.get('DOCS_PATH', '/app/docs')
    folder_path = os.path.join(docs_dir, folder_name)
    
    try:
        if os.path.exists(folder_path):
            return jsonify({'error': 'Folder already exists'}), 409
        
        os.makedirs(folder_path, exist_ok=True)
        
        return jsonify({
            'message': 'Folder created successfully',
            'folder': {
                'name': folder_name,
                'path': folder_path
            }
        })
    except Exception as e:
        logger.error(f"Error creating folder: {e}")
        return jsonify({'error': 'Failed to create folder'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    port = int(os.environ.get('API_PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)