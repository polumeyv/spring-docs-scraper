"""
Tests for async queue system
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
import sys
import os
import json
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from async_queue import URLQueue, QueueItem, Priority


class TestQueueItem:
    """Test QueueItem dataclass"""
    
    def test_queue_item_creation(self):
        """Test creating queue items"""
        item = QueueItem(url='http://example.com', priority=Priority.HIGH)
        
        assert item.url == 'http://example.com'
        assert item.priority == Priority.HIGH
        assert item.retry_count == 0
        assert item.metadata == {}
        assert item.created_at is not None
    
    def test_queue_item_comparison(self):
        """Test queue item priority comparison"""
        high_item = QueueItem(url='http://high.com', priority=Priority.HIGH)
        low_item = QueueItem(url='http://low.com', priority=Priority.LOW)
        
        # Higher priority (lower value) should be "less than"
        assert high_item < low_item
        assert not low_item < high_item


class TestURLQueue:
    """Test URL queue functionality"""
    
    @pytest.fixture
    def queue(self):
        """Create queue fixture"""
        return URLQueue(max_workers=2, max_queue_size=100)
    
    @pytest.mark.asyncio
    async def test_add_url(self, queue):
        """Test adding URLs to queue"""
        await queue.add_url('http://example.com')
        
        assert queue.queue.qsize() == 1
        assert 'http://example.com' in queue.seen_urls
        assert queue.stats['total_queued'] == 1
    
    @pytest.mark.asyncio
    async def test_url_deduplication(self, queue):
        """Test URL deduplication"""
        await queue.add_url('http://example.com')
        await queue.add_url('http://example.com')  # Duplicate
        await queue.add_url('http://example.com/')  # Normalized duplicate
        
        assert queue.queue.qsize() == 1
        assert len(queue.seen_urls) == 1
    
    @pytest.mark.asyncio
    async def test_url_normalization(self, queue):
        """Test URL normalization"""
        # These should all normalize to the same URL
        urls = [
            'http://example.com',
            'http://example.com/',
            'http://example.com#fragment',
            'http://example.com/#another'
        ]
        
        for url in urls:
            await queue.add_url(url)
        
        assert queue.queue.qsize() == 1
        assert len(queue.seen_urls) == 1
    
    @pytest.mark.asyncio
    async def test_priority_ordering(self, queue):
        """Test priority ordering in queue"""
        await queue.add_url('http://low.com', Priority.LOW)
        await queue.add_url('http://high.com', Priority.HIGH)
        await queue.add_url('http://normal.com', Priority.NORMAL)
        await queue.add_url('http://critical.com', Priority.CRITICAL)
        
        # Get items in order
        items = []
        while not queue.queue.empty():
            _, item = await queue.queue.get()
            items.append(item)
        
        # Check order (CRITICAL=0, HIGH=1, NORMAL=2, LOW=3)
        assert items[0].url == 'http://critical.com'
        assert items[1].url == 'http://high.com'
        assert items[2].url == 'http://normal.com'
        assert items[3].url == 'http://low.com'
    
    @pytest.mark.asyncio
    async def test_worker_processing(self, queue):
        """Test worker processing URLs"""
        processed_urls = []
        
        async def mock_processor(url, metadata):
            processed_urls.append(url)
            await asyncio.sleep(0.01)  # Simulate work
            return f"Processed {url}"
        
        # Add URLs
        urls = ['http://example1.com', 'http://example2.com', 'http://example3.com']
        for url in urls:
            await queue.add_url(url)
        
        # Start processing
        await queue.start(mock_processor)
        await queue.wait_complete()
        await queue.stop()
        
        # Check all URLs were processed
        assert len(processed_urls) == 3
        assert set(processed_urls) == set(urls)
        assert queue.stats['total_processed'] == 3
        assert len(queue.processed) == 3
    
    @pytest.mark.asyncio
    async def test_worker_error_handling(self, queue):
        """Test worker error handling and retries"""
        attempt_counts = {}
        
        async def failing_processor(url, metadata):
            attempt_counts[url] = attempt_counts.get(url, 0) + 1
            if attempt_counts[url] < 3:
                raise Exception(f"Failed attempt {attempt_counts[url]}")
            return "Success"
        
        # Add URL
        await queue.add_url('http://example.com')
        
        # Start processing
        await queue.start(failing_processor)
        await queue.wait_complete()
        await queue.stop()
        
        # Check retries happened
        assert attempt_counts['http://example.com'] == 3
        assert queue.stats['total_retried'] == 2
        assert 'http://example.com' in queue.processed
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, queue):
        """Test max retries exceeded"""
        async def always_failing_processor(url, metadata):
            raise Exception("Always fails")
        
        # Set max retries to 2
        queue.max_retries = 2
        
        # Add URL
        await queue.add_url('http://example.com')
        
        # Start processing
        await queue.start(always_failing_processor)
        await queue.wait_complete()
        await queue.stop()
        
        # Check URL failed
        assert 'http://example.com' in queue.failed
        assert queue.stats['total_failed'] == 1
        assert queue.stats['total_retried'] == 2
    
    @pytest.mark.asyncio
    async def test_callbacks(self, queue):
        """Test success and failure callbacks"""
        success_calls = []
        failure_calls = []
        complete_called = False
        
        async def on_success(url, result):
            success_calls.append((url, result))
        
        async def on_failure(url, error):
            failure_calls.append((url, error))
        
        async def on_complete(stats):
            nonlocal complete_called
            complete_called = True
        
        queue.on_success = on_success
        queue.on_failure = on_failure
        queue.on_complete = on_complete
        
        async def mixed_processor(url, metadata):
            if 'fail' in url:
                raise Exception("Intentional failure")
            return f"Processed {url}"
        
        # Add URLs
        await queue.add_url('http://success.com')
        await queue.add_url('http://fail.com')
        
        # Process
        await queue.start(mixed_processor)
        await queue.wait_complete()
        await queue.stop()
        
        # Check callbacks
        assert len(success_calls) == 1
        assert success_calls[0][0] == 'http://success.com'
        assert len(failure_calls) == 1
        assert failure_calls[0][0] == 'http://fail.com'
        assert complete_called
    
    @pytest.mark.asyncio
    async def test_concurrent_workers(self, queue):
        """Test concurrent worker execution"""
        processing_times = {}
        
        async def slow_processor(url, metadata):
            start = asyncio.get_event_loop().time()
            await asyncio.sleep(0.1)  # Simulate slow processing
            end = asyncio.get_event_loop().time()
            processing_times[url] = (start, end)
            return "Done"
        
        # Add multiple URLs
        urls = [f'http://example{i}.com' for i in range(4)]
        for url in urls:
            await queue.add_url(url)
        
        # Process with 2 workers
        start_time = asyncio.get_event_loop().time()
        await queue.start(slow_processor)
        await queue.wait_complete()
        await queue.stop()
        end_time = asyncio.get_event_loop().time()
        
        # With 2 workers and 4 URLs taking 0.1s each, should take ~0.2s
        assert end_time - start_time < 0.3
        
        # Check overlap in processing times (concurrent execution)
        times = sorted(processing_times.values())
        overlaps = 0
        for i in range(len(times) - 1):
            if times[i][1] > times[i + 1][0]:  # End time > next start time
                overlaps += 1
        assert overlaps > 0  # Should have some overlap
    
    @pytest.mark.asyncio
    async def test_queue_stats(self, queue):
        """Test queue statistics"""
        stats = queue.get_stats()
        assert stats['total_queued'] == 0
        assert stats['queue_size'] == 0
        assert stats['processing'] == 0
        
        # Add and process URLs
        async def dummy_processor(url, metadata):
            return "OK"
        
        await queue.add_url('http://example.com')
        stats = queue.get_stats()
        assert stats['total_queued'] == 1
        assert stats['queue_size'] == 1
        
        await queue.start(dummy_processor)
        await queue.wait_complete()
        await queue.stop()
        
        stats = queue.get_stats()
        assert stats['total_processed'] == 1
        assert stats['processed'] == 1
        assert 'avg_rate' in stats
        assert stats['avg_rate'] > 0
    
    @pytest.mark.asyncio
    async def test_save_and_load_state(self, queue):
        """Test saving and loading queue state"""
        # Add some URLs and process some
        await queue.add_url('http://processed.com')
        await queue.add_url('http://pending.com')
        await queue.add_url('http://failed.com')
        
        # Simulate processing
        queue.processed.add('http://processed.com')
        queue.failed['http://failed.com'] = 'Test error'
        
        # Save state
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_file = f.name
        
        await queue.save_state(temp_file)
        
        # Create new queue and load state
        new_queue = URLQueue()
        await new_queue.load_state(temp_file)
        
        # Check state restored
        assert 'http://processed.com' in new_queue.seen_urls
        assert 'http://processed.com' in new_queue.processed
        assert 'http://failed.com' in new_queue.failed
        assert new_queue.queue.qsize() == 1  # pending.com
        
        # Cleanup
        os.unlink(temp_file)
    
    @pytest.mark.asyncio
    async def test_queue_full_handling(self):
        """Test queue full handling"""
        # Create small queue
        small_queue = URLQueue(max_queue_size=2)
        
        # Fill queue
        await small_queue.add_url('http://url1.com')
        await small_queue.add_url('http://url2.com')
        
        # Try to add more (should be dropped)
        await small_queue.add_url('http://url3.com')
        
        # Queue should still have 2 items
        assert small_queue.queue.qsize() == 2
        # But seen_urls should only have 2 (3rd was not added)
        assert len(small_queue.seen_urls) == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])