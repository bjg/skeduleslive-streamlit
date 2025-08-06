#!/usr/bin/env python3
"""
API Key validation middleware for FastAPI
"""
import time
import logging
from typing import Callable, Dict, Optional
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .api_key_manager import api_key_manager

# Configure logging
logger = logging.getLogger(__name__)


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Middleware for API key validation and rate limiting
    """
    def __init__(
        self, 
        app,
        exclude_paths: list = None,
        header_name: str = "X-API-Key"
    ):
        """
        Initialize the middleware
        
        Args:
            app: FastAPI application
            exclude_paths: List of paths to exclude from API key validation
            header_name: Name of the header containing the API key
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/docs", "/redoc", "/openapi.json", "/health"]
        self.header_name = header_name
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request through middleware
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response: FastAPI response object
        """
        # Skip API key validation for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Start timing for performance monitoring
        start_time = time.time()
        
        # Extract API key from header
        api_key = request.headers.get(self.header_name)
        
        # Validate API key
        is_valid, error_message = api_key_manager.validate_key(api_key)
        if not is_valid:
            logger.warning(f"API key validation failed: {error_message} - Path: {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"success": False, "message": error_message}
            )
        
        # Check rate limit
        is_allowed, limit_message = api_key_manager.check_rate_limit(api_key)
        if not is_allowed:
            logger.warning(f"Rate limit exceeded for API key - Path: {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"success": False, "message": limit_message}
            )
        
        # Proceed with request
        response = await call_next(request)
        
        # Log request details for monitoring (exclude sensitive data)
        process_time = time.time() - start_time
        logger.debug(
            f"Request: {request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Process time: {process_time:.4f}s"
        )
        
        return response


# Helper function to add middleware to FastAPI app
def add_api_key_middleware(app, exclude_paths=None, header_name="X-API-Key"):
    """
    Add API key middleware to FastAPI app
    
    Args:
        app: FastAPI application
        exclude_paths: List of paths to exclude from API key validation
        header_name: Name of the header containing the API key
    """
    app.add_middleware(
        APIKeyMiddleware,
        exclude_paths=exclude_paths,
        header_name=header_name
    )
    logger.info("API Key middleware added to FastAPI application")
