#!/usr/bin/env python3
"""
Enhanced API Key Management module for SkedulesLive MCP server
Provides secure API key validation, rate limiting, and management
"""
import os
import time
import uuid
import hashlib
import logging
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)

class APIKeyManager:
    """
    API Key Manager class for handling API key validation, rate limiting, and management
    """
    def __init__(self):
        """Initialize API Key Manager with storage for API keys and rate limiting"""
        # API keys storage - in production this should be a database
        # Format: {"key_hash": {"scopes": [], "rate_limit": 100, "created_at": timestamp, "expires_at": timestamp}}
        self._api_keys = {}
        
        # Request tracking for rate limiting
        # Format: {"key_hash": {"requests": 0, "window_start": timestamp}}
        self._request_tracker = {}
        
        # Rate limiting window in seconds (default: 1 hour)
        self._rate_limit_window = 3600
        
        # Default rate limit per window
        self._default_rate_limit = 1000
        
        # Load default API key from environment (for development)
        self._load_default_api_key()
    
    def _load_default_api_key(self):
        """Load default API key from environment variable for development"""
        default_key = os.environ.get("MCP_API_KEY", "test-mcp-api-key-local-dev")
        default_key_hash = self._hash_key(default_key)
        
        # Add default key to storage if not exists
        if default_key_hash not in self._api_keys:
            self._api_keys[default_key_hash] = {
                "scopes": ["*"],  # All scopes
                "rate_limit": self._default_rate_limit,
                "created_at": time.time(),
                "expires_at": time.time() + (365 * 24 * 3600),  # 1 year expiration
                "metadata": {
                    "name": "Default Development API Key",
                    "created_by": "system"
                }
            }
            logger.info(f"Loaded default API key: {default_key_hash[:8]}...")
    
    def _hash_key(self, api_key: str) -> str:
        """Hash API key for secure storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def validate_key(self, api_key: str, scope: str = None) -> Tuple[bool, Optional[str]]:
        """
        Validate API key and check scope permission
        Returns (valid, error_message)
        """
        if not api_key:
            return False, "API key is required"
        
        key_hash = self._hash_key(api_key)
        
        # Check if key exists
        if key_hash not in self._api_keys:
            logger.warning(f"Invalid API key attempt: {api_key[:5]}...")
            return False, "Invalid API key"
        
        key_info = self._api_keys[key_hash]
        
        # Check if key has expired
        if key_info["expires_at"] < time.time():
            logger.warning(f"Expired API key attempt: {api_key[:5]}...")
            return False, "API key has expired"
        
        # Check scope permission if scope is provided
        if scope and scope not in key_info["scopes"] and "*" not in key_info["scopes"]:
            logger.warning(f"Unauthorized scope attempt: {scope} with key {api_key[:5]}...")
            return False, f"API key does not have permission for {scope}"
        
        return True, None
    
    def check_rate_limit(self, api_key: str) -> Tuple[bool, Optional[str]]:
        """
        Check if API key has exceeded rate limit
        Returns (allowed, error_message)
        """
        key_hash = self._hash_key(api_key)
        
        # Initialize request tracking if not exists
        if key_hash not in self._request_tracker:
            self._request_tracker[key_hash] = {
                "requests": 0,
                "window_start": time.time()
            }
        
        tracker = self._request_tracker[key_hash]
        key_info = self._api_keys[key_hash]
        
        # Reset window if needed
        current_time = time.time()
        if current_time - tracker["window_start"] > self._rate_limit_window:
            tracker["requests"] = 0
            tracker["window_start"] = current_time
        
        # Check rate limit
        rate_limit = key_info.get("rate_limit", self._default_rate_limit)
        if tracker["requests"] >= rate_limit:
            logger.warning(f"Rate limit exceeded for key {api_key[:5]}...")
            return False, "API rate limit exceeded"
        
        # Increment request count
        tracker["requests"] += 1
        return True, None
    
    def generate_key(self, scopes: List[str] = None, rate_limit: int = None,
                    expires_in_days: int = 90, metadata: Dict = None) -> str:
        """
        Generate a new API key with specified parameters
        Returns the generated API key
        """
        # Generate random UUID as API key
        api_key = f"sk-{uuid.uuid4().hex}"
        key_hash = self._hash_key(api_key)
        
        # Default values
        if scopes is None:
            scopes = ["*"]  # All scopes
            
        if rate_limit is None:
            rate_limit = self._default_rate_limit
            
        if metadata is None:
            metadata = {}
        
        # Store key info
        self._api_keys[key_hash] = {
            "scopes": scopes,
            "rate_limit": rate_limit,
            "created_at": time.time(),
            "expires_at": time.time() + (expires_in_days * 24 * 3600),
            "metadata": metadata
        }
        
        logger.info(f"Generated new API key: {key_hash[:8]}... with scopes: {scopes}")
        return api_key
    
    def revoke_key(self, api_key: str) -> bool:
        """Revoke an API key by removing it from storage"""
        key_hash = self._hash_key(api_key)
        
        if key_hash in self._api_keys:
            del self._api_keys[key_hash]
            if key_hash in self._request_tracker:
                del self._request_tracker[key_hash]
            logger.info(f"Revoked API key: {key_hash[:8]}...")
            return True
        
        return False
    
    def update_key(self, api_key: str, scopes: List[str] = None, 
                 rate_limit: int = None, expires_in_days: int = None,
                 metadata: Dict = None) -> bool:
        """Update API key parameters"""
        key_hash = self._hash_key(api_key)
        
        if key_hash not in self._api_keys:
            return False
        
        key_info = self._api_keys[key_hash]
        
        # Update values if provided
        if scopes is not None:
            key_info["scopes"] = scopes
            
        if rate_limit is not None:
            key_info["rate_limit"] = rate_limit
            
        if expires_in_days is not None:
            key_info["expires_at"] = time.time() + (expires_in_days * 24 * 3600)
            
        if metadata is not None:
            key_info["metadata"].update(metadata)
        
        logger.info(f"Updated API key: {key_hash[:8]}...")
        return True
    
    def get_key_info(self, api_key: str) -> Optional[Dict]:
        """Get information about an API key"""
        key_hash = self._hash_key(api_key)
        
        if key_hash in self._api_keys:
            key_info = self._api_keys[key_hash].copy()
            
            # Add usage information
            if key_hash in self._request_tracker:
                key_info["usage"] = {
                    "requests": self._request_tracker[key_hash]["requests"],
                    "window_start": datetime.fromtimestamp(
                        self._request_tracker[key_hash]["window_start"]
                    ).isoformat()
                }
            
            # Convert timestamps to ISO format
            key_info["created_at"] = datetime.fromtimestamp(
                key_info["created_at"]
            ).isoformat()
            
            key_info["expires_at"] = datetime.fromtimestamp(
                key_info["expires_at"]
            ).isoformat()
            
            return key_info
        
        return None
    
    def list_keys(self, include_usage: bool = False) -> List[Dict]:
        """List all API keys with their information"""
        keys_info = []
        
        for key_hash, key_info in self._api_keys.items():
            info = key_info.copy()
            
            # Add usage information if requested
            if include_usage and key_hash in self._request_tracker:
                info["usage"] = {
                    "requests": self._request_tracker[key_hash]["requests"],
                    "window_start": datetime.fromtimestamp(
                        self._request_tracker[key_hash]["window_start"]
                    ).isoformat()
                }
            
            # Convert timestamps to ISO format
            info["created_at"] = datetime.fromtimestamp(
                info["created_at"]
            ).isoformat()
            
            info["expires_at"] = datetime.fromtimestamp(
                info["expires_at"]
            ).isoformat()
            
            # Add hashed key identifier
            info["key_id"] = key_hash[:8]
            
            keys_info.append(info)
        
        return keys_info


# Singleton instance for application-wide use
api_key_manager = APIKeyManager()
