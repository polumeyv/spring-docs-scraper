"""
Tests for async HTTP client
"""
import pytest
import asyncio
import aiohttp
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from async_http_client import AsyncHTTPClient, RateLimiter


class TestRateLimiter:
    """Test rate limiter functionality"""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_basic(self):
        """Test basic rate limiting"""
        limiter = RateLimiter(rate=2.0, burst=2)  # 2 requests per second
        
        # Should allow burst requests immediately
        start_time = asyncio.get_event_loop().time()
        await limiter.acquire()
        await limiter.acquire()
        
        # Third request should be delayed
        await limiter.acquire()
        end_time = asyncio.get_event_loop().time()
        
        # Should have waited at least 0.5 seconds
        assert end_time - start_time >= 0.4  # Allow some tolerance
    
    @pytest.mark.asyncio
    async def test_rate_limiter_concurrent(self):
        """Test rate limiting with concurrent requests"""
        limiter = RateLimiter(rate=5.0, burst=2)
        
        async def make_request():
            await limiter.acquire()
            return asyncio.get_event_loop().time()
        
        # Make 5 concurrent requests
        times = await asyncio.gather(*[make_request() for _ in range(5)])
        
        # First 2 should be immediate, rest should be spaced
        assert times[1] - times[0] < 0.1  # First two are burst
        assert times[2] - times[1] >= 0.15  # Then rate limited


class TestAsyncHTTPClient:
    """Test async HTTP client"""
    
    @pytest.fixture
    async def client(self):
        """Create HTTP client fixture"""
        client = AsyncHTTPClient(
            max_connections=5,
            max_per_host=2,
            rate_limit=10.0,
            timeout=5
        )
        await client.start()
        yield client
        await client.close()
    
    @pytest.mark.asyncio
    async def test_client_lifecycle(self):
        """Test client start and close"""
        client = AsyncHTTPClient()
        
        # Should not have session initially
        assert client.session is None
        
        # Start client
        await client.start()
        assert client.session is not None
        assert isinstance(client.session, aiohttp.ClientSession)
        
        # Close client
        await client.close()
        assert client.session is None
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test client as context manager"""
        async with AsyncHTTPClient() as client:
            assert client.session is not None
        
        # Should be closed after context
        assert client.session is None
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.request')
    async def test_successful_fetch(self, mock_request, client):
        """Test successful fetch"""
        # Mock response
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.read = AsyncMock(return_value=b'Test content')
        mock_request.return_value.__aenter__.return_value = mock_resp
        
        # Make request
        response = await client.fetch('http://example.com')
        
        assert response is not None
        assert response._content == b'Test content'
        assert client.stats['successful_requests'] == 1
        assert client.stats['total_bytes'] == 12
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.request')
    async def test_retry_on_server_error(self, mock_request, client):
        """Test retry on server error"""
        # Mock responses - first two fail, third succeeds
        responses = []
        for i in range(3):
            mock_resp = AsyncMock()
            if i < 2:
                mock_resp.status = 500
                mock_resp.read = AsyncMock(return_value=b'Server error')
            else:
                mock_resp.status = 200
                mock_resp.read = AsyncMock(return_value=b'Success')
            responses.append(mock_resp)
        
        mock_request.return_value.__aenter__.side_effect = responses
        
        # Make request (should retry and succeed)
        response = await client.fetch('http://example.com')
        
        assert response is not None
        assert response._content == b'Success'
        assert mock_request.call_count == 3
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.request')
    async def test_no_retry_on_client_error(self, mock_request, client):
        """Test no retry on client error"""
        # Mock 404 response
        mock_resp = AsyncMock()
        mock_resp.status = 404
        mock_resp.read = AsyncMock(return_value=b'Not found')
        mock_request.return_value.__aenter__.return_value = mock_resp
        
        # Make request (should not retry)
        response = await client.fetch('http://example.com')
        
        assert response is None
        assert mock_request.call_count == 1
        assert client.stats['failed_requests'] == 1
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.request')
    async def test_rate_limiting(self, mock_request, client):
        """Test rate limiting is applied"""
        # Mock successful responses
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.read = AsyncMock(return_value=b'OK')
        mock_request.return_value.__aenter__.return_value = mock_resp
        
        # Make multiple requests
        start_time = asyncio.get_event_loop().time()
        await asyncio.gather(*[
            client.fetch(f'http://example.com/{i}') 
            for i in range(5)
        ])
        end_time = asyncio.get_event_loop().time()
        
        # Should be rate limited (but allow for burst)
        assert mock_request.call_count == 5
        # With rate=10/s and burst=20, 5 requests should be quick
        assert end_time - start_time < 1.0
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.request')
    async def test_fetch_text(self, mock_request, client):
        """Test fetch_text method"""
        # Mock response
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.read = AsyncMock(return_value='Hello World'.encode('utf-8'))
        mock_request.return_value.__aenter__.return_value = mock_resp
        
        # Fetch text
        text = await client.fetch_text('http://example.com')
        
        assert text == 'Hello World'
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.request')
    async def test_fetch_json(self, mock_request, client):
        """Test fetch_json method"""
        # Mock response
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.read = AsyncMock(return_value=b'{"key": "value"}')
        mock_request.return_value.__aenter__.return_value = mock_resp
        
        # Fetch JSON
        data = await client.fetch_json('http://example.com')
        
        assert data == {'key': 'value'}
    
    @pytest.mark.asyncio
    async def test_stats_tracking(self, client):
        """Test statistics tracking"""
        # Initial stats
        stats = client.get_stats()
        assert stats['total_requests'] == 0
        assert stats['successful_requests'] == 0
        assert stats['failed_requests'] == 0
        
        # Make some requests with mocked responses
        with patch('aiohttp.ClientSession.request') as mock_request:
            # Success
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.read = AsyncMock(return_value=b'OK')
            mock_request.return_value.__aenter__.return_value = mock_resp
            
            await client.fetch('http://example.com')
            
            # Failure
            mock_resp.status = 404
            await client.fetch('http://example.com/404')
        
        # Check updated stats
        stats = client.get_stats()
        assert stats['total_requests'] == 2
        assert stats['successful_requests'] == 1
        assert stats['failed_requests'] == 1
        assert 'avg_rate' in stats
        assert 'duration' in stats


if __name__ == '__main__':
    pytest.main([__file__, '-v'])