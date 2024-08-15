"""
API calling tool with authentication and rate limiting.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Union
import httpx
from .base import BaseTool, ToolResult
import structlog

logger = structlog.get_logger(__name__)


class APITool(BaseTool):
    """Tool for making HTTP API calls with authentication and rate limiting."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        default_headers: Optional[Dict[str, str]] = None,
        timeout_seconds: int = 30,
        rate_limit_per_minute: int = 60,
        **kwargs
    ):
        super().__init__(
            name="api_tool",
            description="Make HTTP API calls with authentication and rate limiting",
            **kwargs
        )
        self.base_url = base_url
        self.default_headers = default_headers or {}
        self.timeout_seconds = timeout_seconds
        self.rate_limit_per_minute = rate_limit_per_minute
        
        # Rate limiting
        self.request_times: List[float] = []
        self.rate_limit_lock = asyncio.Lock()
    
    async def _check_rate_limit(self):
        """Check and enforce rate limiting."""
        async with self.rate_limit_lock:
            now = time.time()
            
            # Remove old requests (older than 1 minute)
            self.request_times = [t for t in self.request_times if now - t < 60]
            
            # Check if we're at the rate limit
            if len(self.request_times) >= self.rate_limit_per_minute:
                # Calculate wait time
                oldest_request = min(self.request_times)
                wait_time = 60 - (now - oldest_request)
                
                if wait_time > 0:
                    logger.info(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                    await asyncio.sleep(wait_time)
            
            # Record this request
            self.request_times.append(now)
    
    def _prepare_headers(self, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Prepare headers for the request."""
        request_headers = self.default_headers.copy()
        if headers:
            request_headers.update(headers)
        return request_headers
    
    def _prepare_url(self, endpoint: str) -> str:
        """Prepare the full URL for the request."""
        if endpoint.startswith(('http://', 'https://')):
            return endpoint
        elif self.base_url:
            base = self.base_url.rstrip('/')
            endpoint = endpoint.lstrip('/')
            return f"{base}/{endpoint}"
        else:
            raise ValueError("Either provide a full URL or set base_url")
    
    async def _make_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Union[str, bytes]] = None
    ) -> ToolResult:
        """Make the HTTP request."""
        try:
            # Check rate limit
            await self._check_rate_limit()
            
            # Prepare request
            full_url = self._prepare_url(url)
            request_headers = self._prepare_headers(headers)
            
            # Make request
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.request(
                    method=method.upper(),
                    url=full_url,
                    headers=request_headers,
                    params=params,
                    json=json_data,
                    data=data
                )
                
                # Parse response
                try:
                    response_data = response.json()
                except:
                    response_data = response.text
                
                return ToolResult(
                    success=response.status_code < 400,
                    data={
                        "status_code": response.status_code,
                        "headers": dict(response.headers),
                        "data": response_data,
                        "url": str(response.url)
                    },
                    metadata={
                        "method": method.upper(),
                        "status_code": response.status_code,
                        "response_time_ms": 0  # Could be measured
                    }
                )
        
        except httpx.TimeoutException:
            return ToolResult(
                success=False,
                data=None,
                error=f"Request timed out after {self.timeout_seconds} seconds"
            )
        except httpx.RequestError as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"Request failed: {str(e)}"
            )
        except Exception as e:
            logger.error(f"API request failed: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=f"Unexpected error: {str(e)}"
            )
    
    async def execute(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Union[str, bytes]] = None,
        **kwargs
    ) -> ToolResult:
        """Execute an API request."""
        return await self._make_request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json_data=json_data,
            data=data
        )
    
    def get_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for API tool parameters."""
        return {
            "type": "object",
            "properties": {
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
                    "description": "HTTP method"
                },
                "url": {
                    "type": "string",
                    "description": "API endpoint URL"
                },
                "headers": {
                    "type": "object",
                    "description": "HTTP headers",
                    "additionalProperties": {"type": "string"}
                },
                "params": {
                    "type": "object",
                    "description": "Query parameters",
                    "additionalProperties": True
                },
                "json": {
                    "type": "object",
                    "description": "JSON data to send in request body"
                },
                "data": {
                    "type": "string",
                    "description": "Raw data to send in request body"
                }
            },
            "required": ["method", "url"],
            "additionalProperties": False
        }
    
    async def get(self, url: str, **kwargs) -> ToolResult:
        """Make a GET request."""
        return await self.execute("GET", url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> ToolResult:
        """Make a POST request."""
        return await self.execute("POST", url, **kwargs)
    
    async def put(self, url: str, **kwargs) -> ToolResult:
        """Make a PUT request."""
        return await self.execute("PUT", url, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> ToolResult:
        """Make a DELETE request."""
        return await self.execute("DELETE", url, **kwargs)
    
    def set_auth_header(self, auth_type: str, token: str):
        """Set authentication header."""
        if auth_type.lower() == "bearer":
            self.default_headers["Authorization"] = f"Bearer {token}"
        elif auth_type.lower() == "api_key":
            self.default_headers["X-API-Key"] = token
        else:
            self.default_headers["Authorization"] = f"{auth_type} {token}"
        
        logger.info(f"Set {auth_type} authentication header")
    
    def set_base_url(self, base_url: str):
        """Set the base URL for API calls."""
        self.base_url = base_url
        logger.info(f"Set base URL: {base_url}")
    
    def set_rate_limit(self, requests_per_minute: int):
        """Set the rate limit for API calls."""
        self.rate_limit_per_minute = requests_per_minute
        logger.info(f"Set rate limit: {requests_per_minute} requests per minute")
