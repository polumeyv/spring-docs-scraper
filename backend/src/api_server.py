#!/usr/bin/env python3
"""
API server with WebSocket support for real-time scraping updates
"""
import os
import asyncio
import uuid
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
import logging
from doc_search_service import DocSearchService
from intelligent_doc_finder import IntelligentDocFinder
from scraper_service import ScraperService
from enhanced_topic_discovery import EnhancedTopicDiscoveryService
from intelligent_scraper_service import IntelligentScraperService

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store active tasks
active_tasks = {}

@socketio.on('connect')
def handle_connect():
    client_id = request.sid
    join_room(client_id)
    logger.info(f"Client connected: {client_id}")
    emit('connected', {'client_id': client_id})

@socketio.on('disconnect')
def handle_disconnect():
    client_id = request.sid
    leave_room(client_id)
    logger.info(f"Client disconnected: {client_id}")

@socketio.on('subscribe_task')
def handle_subscribe(data):
    task_id = data.get('task_id')
    client_id = request.sid
    
    if task_id in active_tasks:
        join_room(f"task_{task_id}")
        # Send current task status
        task = active_tasks[task_id]
        emit('task_update', task)

@app.route('/api/search-docs', methods=['GET'])
def search_docs():
    """Find official documentation for a given framework/tool with intelligent discovery"""
    framework = request.args.get('q', '').strip()
    
    if not framework:
        return jsonify({'error': 'Please provide a framework name'}), 400
    
    try:
        # Run the intelligent doc finder
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def run_intelligent_search():
            async with IntelligentDocFinder() as doc_finder:
                return await doc_finder.find_official_documentation(framework)
        
        result = loop.run_until_complete(run_intelligent_search())
        loop.close()
        
        return jsonify(result)
            
    except Exception as e:
        logger.error(f"Error in intelligent search: {e}")
        return jsonify({'error': 'Failed to find documentation'}), 500

@app.route('/api/discover-topics', methods=['POST'])
def discover_topics():
    """Discover documentation topics using AI"""
    data = request.json
    url = data.get('url', '').strip()
    framework = data.get('framework', '').strip()
    task_id = data.get('task_id')  # Optional task_id for WebSocket updates
    
    if not url or not framework:
        return jsonify({'error': 'URL and framework are required'}), 400
    
    try:
        # Create progress callback for WebSocket updates
        async def progress_callback(task_id: str, updates: dict):
            if task_id:
                # Emit to all clients subscribed to this task
                socketio.emit('topic_discovery_update', {
                    'task_id': task_id,
                    **updates
                }, room=f"task_{task_id}")
        
        # Run the async topic discovery
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def run_discovery():
            async with EnhancedTopicDiscoveryService(progress_callback) as discovery_service:
                return await discovery_service.discover_topics_with_progress(url, framework, task_id)
        
        result = loop.run_until_complete(run_discovery())
        loop.close()
        
        return jsonify(result)
            
    except Exception as e:
        logger.error(f"Error discovering topics: {e}")
        return jsonify({'error': 'Failed to discover topics'}), 500

@app.route('/api/scrape', methods=['POST'])
def start_scraping():
    """Start scraping documentation"""
    data = request.json
    url = data.get('url', '').strip()
    framework = data.get('framework', '').strip()
    topic_name = data.get('topic_name', '').strip()
    mode = data.get('mode', 'intelligent')  # 'intelligent' or 'basic'
    
    if not url or not framework:
        return jsonify({'error': 'URL and framework are required'}), 400
    
    # Create task
    task_id = str(uuid.uuid4())
    active_tasks[task_id] = {
        'id': task_id,
        'url': url,
        'framework': framework,
        'topic_name': topic_name or framework,
        'mode': mode,
        'status': 'queued',
        'progress': 0,
        'message': 'Starting...'
    }
    
    # Start scraping in background
    if mode == 'intelligent':
        socketio.start_background_task(run_intelligent_scraping, task_id, url, topic_name or framework, framework)
    else:
        socketio.start_background_task(run_scraping, task_id, url, framework)
    
    return jsonify({
        'task_id': task_id,
        'message': 'Scraping started'
    })

def run_scraping(task_id: str, url: str, framework: str):
    """Run the basic scraping task"""
    async def progress_callback(task_id: str, updates: dict):
        """Emit progress updates via WebSocket"""
        task = active_tasks.get(task_id, {})
        task.update(updates)
        active_tasks[task_id] = task
        
        # Emit to all clients subscribed to this task
        socketio.emit('task_update', task, room=f"task_{task_id}")
    
    # Run the async scraper
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def run_scraper():
        async with ScraperService(progress_callback) as scraper:
            await scraper.scrape_documentation(task_id, url, framework)
    
    try:
        loop.run_until_complete(run_scraper())
    except Exception as e:
        logger.error(f"Scraping error: {e}")
        # Send error update
        loop.run_until_complete(progress_callback(task_id, {
            'status': 'error',
            'message': str(e),
            'error': str(e)
        }))
    finally:
        loop.close()

def run_intelligent_scraping(task_id: str, url: str, topic_name: str, framework: str):
    """Run the intelligent scraping task"""
    async def progress_callback(task_id: str, updates: dict):
        """Emit progress updates via WebSocket"""
        task = active_tasks.get(task_id, {})
        task.update(updates)
        active_tasks[task_id] = task
        
        # Emit to all clients subscribed to this task
        socketio.emit('task_update', task, room=f"task_{task_id}")
    
    # Run the intelligent scraper
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def run_scraper():
        async with IntelligentScraperService(progress_callback) as scraper:
            await scraper.scrape_topic(task_id, url, topic_name, framework)
    
    try:
        loop.run_until_complete(run_scraper())
    except Exception as e:
        logger.error(f"Intelligent scraping error: {e}")
        # Send error update
        loop.run_until_complete(progress_callback(task_id, {
            'status': 'error',
            'message': str(e),
            'error': str(e)
        }))
    finally:
        loop.close()

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    port = int(os.environ.get('API_PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)