#!/usr/bin/env python3
"""
Enhanced topic discovery service with real-time progress tracking
"""
from topic_discovery_service import TopicDiscoveryService
from progress_tracker import ProgressTracker
import logging
from typing import Dict, Callable, Optional

logger = logging.getLogger(__name__)

class EnhancedTopicDiscoveryService(TopicDiscoveryService):
    """Enhanced topic discovery with real-time progress updates"""
    
    def __init__(self, progress_callback: Optional[Callable] = None):
        super().__init__()
        self.progress = ProgressTracker(progress_callback)
    
    async def discover_topics_with_progress(self, url: str, framework: str, task_id: str = None) -> Dict:
        """Discover topics with detailed progress tracking"""
        try:
            # Stage 1: URL Analysis
            await self.progress.emit_stage(
                task_id, 
                self.progress.STAGES['URL_ANALYSIS'],
                f'Analyzing URL for {framework}',
                10,
                details={'input_url': url, 'framework': framework}
            )
            
            discovery_url = self._get_discovery_url(url, framework)
            logger.info(f"Using discovery URL: {discovery_url}")
            
            # Stage 2: Page Fetch  
            await self.progress.emit_stage(
                task_id,
                self.progress.STAGES['PAGE_FETCH'], 
                f'Fetching documentation page',
                20,
                details={'discovery_url': discovery_url}
            )
            
            html_content = await self._fetch_page(discovery_url)
            if not html_content:
                await self.progress.emit_error(
                    task_id,
                    'Failed to fetch documentation page',
                    'Page fetch failed'
                )
                return {'error': 'Failed to fetch documentation page'}
            
            # Stage 3: Navigation Extraction
            await self.progress.emit_stage(
                task_id,
                self.progress.STAGES['NAVIGATION_EXTRACT'],
                'Extracting navigation structure',
                40,
                details={'content_size': len(html_content)}
            )
            
            navigation_data = self._extract_navigation(html_content, discovery_url)
            
            # Stage 4: AI Analysis
            await self.progress.emit_stage(
                task_id,
                self.progress.STAGES['AI_ANALYSIS'],
                'Analyzing with AI to discover topics',
                60,
                details={
                    'navigation_items': len(navigation_data.get('navigation', [])),
                    'sections_found': len(navigation_data.get('sections', []))
                }
            )
            
            # Check for intelligent fallback first
            intelligent_fallback = self._try_intelligent_fallback(framework, discovery_url, navigation_data)
            if intelligent_fallback:
                await self.progress.emit_stage(
                    task_id,
                    'intelligent_fallback',
                    f'Using optimized patterns for {framework}',
                    80,
                    details={'strategy': 'intelligent_fallback', 'framework': framework}
                )
                topics = intelligent_fallback
            else:
                # Use AI analysis
                topics = await self._analyze_with_gemini_enhanced(navigation_data, framework, discovery_url, task_id)
            
            # Stage 5: Validation
            await self.progress.emit_stage(
                task_id,
                self.progress.STAGES['VALIDATION'],
                'Validating and enhancing discovered topics',
                90,
                details={'raw_topics': len(topics) if isinstance(topics, list) else 0}
            )
            
            validated_topics = self._validate_and_enhance_topics(topics, discovery_url, navigation_data)
            
            # Stage 6: Complete
            await self.progress.emit_complete(
                task_id,
                f'Successfully discovered {len(validated_topics)} topics',
                details={'final_topics': len(validated_topics)}
            )
            
            return {
                'framework': framework,
                'base_url': discovery_url,
                'topics': validated_topics
            }
            
        except Exception as e:
            logger.error(f"Error discovering topics: {e}")
            await self.progress.emit_error(
                task_id,
                f'Error discovering topics: {str(e)}',
                str(e)
            )
            return {'error': str(e)}
    
    async def _analyze_with_gemini_enhanced(self, navigation_data: Dict, framework: str, base_url: str, task_id: str = None):
        """Enhanced AI analysis with progress tracking"""
        strategy = self._choose_enhancement_strategy(framework, base_url, navigation_data)
        
        # Emit strategy-specific progress
        if strategy == "grounding":
            await self.progress.emit_stage(
                task_id,
                self.progress.STAGES['AI_GROUNDING'],
                'Using Google Search grounding for enhanced accuracy',
                70,
                details={'strategy': 'grounding', 'enhancement': 'google_search'}
            )
        elif strategy == "code_execution":
            await self.progress.emit_stage(
                task_id,
                'ai_code_execution',
                'Using code execution for complex analysis', 
                70,
                details={'strategy': 'code_execution', 'enhancement': 'python_analysis'}
            )
        
        # Call the original analyze method
        return await self._analyze_with_gemini(navigation_data, framework, base_url)