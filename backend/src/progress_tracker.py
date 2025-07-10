#!/usr/bin/env python3
"""
Progress tracking utilities for real-time WebSocket updates
"""
import logging
from typing import Dict, Callable, Optional

logger = logging.getLogger(__name__)

class ProgressTracker:
    """Helper class for tracking and emitting progress updates"""
    
    def __init__(self, callback: Optional[Callable] = None):
        self.callback = callback
        self.current_stage = None
        self.current_progress = 0
    
    async def emit_progress(self, task_id: str, stage: str, message: str, progress: int, 
                          details: Dict = None, error: str = None):
        """Emit a progress update"""
        if not self.callback or not task_id:
            return
            
        update_data = {
            'stage': stage,
            'message': message,
            'progress': progress,
            'timestamp': self._get_timestamp()
        }
        
        if details:
            update_data['details'] = details
            
        if error:
            update_data['error'] = error
            
        self.current_stage = stage
        self.current_progress = progress
        
        try:
            await self.callback(task_id, update_data)
        except Exception as e:
            logger.error(f"Error emitting progress: {e}")
    
    async def emit_stage(self, task_id: str, stage: str, message: str, progress: int, **kwargs):
        """Simplified stage emission"""
        await self.emit_progress(task_id, stage, message, progress, **kwargs)
    
    async def emit_error(self, task_id: str, message: str, error: str):
        """Emit an error update"""
        await self.emit_progress(task_id, 'error', message, 0, error=error)
    
    async def emit_complete(self, task_id: str, message: str, details: Dict = None):
        """Emit completion update"""
        await self.emit_progress(task_id, 'complete', message, 100, details=details)
    
    def _get_timestamp(self):
        """Get current timestamp"""
        import time
        return int(time.time() * 1000)  # milliseconds
    
    # Pre-defined stage constants for consistency
    STAGES = {
        'INIT': 'initialization',
        'URL_ANALYSIS': 'url_analysis', 
        'PAGE_FETCH': 'page_fetch',
        'NAVIGATION_EXTRACT': 'navigation_extraction',
        'AI_ANALYSIS': 'ai_analysis',
        'AI_GROUNDING': 'ai_grounding',
        'AI_CODE_EXECUTION': 'ai_code_execution',
        'VALIDATION': 'validation',
        'COMPLETE': 'complete',
        'ERROR': 'error'
    }