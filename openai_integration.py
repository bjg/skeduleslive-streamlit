#!/usr/bin/env python3
"""
SkedulesLive MCP Server - OpenAI Integration

This script demonstrates how to integrate the MCP server with OpenAI's API
for AI-powered management of SkedulesLive content.
"""
import os
import json
import requests
import tempfile
from dotenv import load_dotenv
import streamlit as st
from openai import OpenAI
from skeduleslive_client import SkedulesLiveClient

# Load environment variables from .env file for local development
load_dotenv()

# Function to get config values from Streamlit secrets or environment variables
def get_config_value(key, default=None):
    """Get a configuration value from Streamlit secrets or environment variables"""
    # First try to get from Streamlit secrets (for Streamlit Cloud)
    if 'secrets' in dir(st) and key in st.secrets:
        return st.secrets[key]
    # Fall back to environment variables (for local development)
    return os.getenv(key, default)

# OpenAI API Configuration
OPENAI_API_KEY = get_config_value("OPENAI_API_KEY")

# MCP Server Configuration
MCP_SERVER_URL = get_config_value("MCP_SERVER_URL", "http://localhost:8000")
MCP_API_KEY = get_config_value("MCP_API_KEY")

# SkedulesLive API Configuration
SKEDULESLIVE_CLIENT_ID = get_config_value("SKEDULESLIVE_CLIENT_ID", "4phj7kbdr1c95p6hmhomoie6o3")
SKEDULESLIVE_EMAIL = get_config_value("SKEDULESLIVE_EMAIL", "")
SKEDULESLIVE_PASSWORD = get_config_value("SKEDULESLIVE_PASSWORD", "")

# Define the MCP functions for OpenAI
MCP_FUNCTIONS = [
    {
        "type": "function",
        "function": {
            "name": "authenticate",
            "description": "Authenticate with SkedulesLive API",
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {"type": "string", "description": "User email"},
                    "password": {"type": "string", "description": "User password"},
                    "keep_me_logged": {"type": "boolean", "description": "Keep user logged in"}
                },
                "required": ["email", "password"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_skedules",
            "description": "Get all skedules for the authenticated user",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_skedule",
            "description": "Get a specific skedule by ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "skedule_id": {"type": "string", "description": "ID of the skedule to retrieve"}
                },
                "required": ["skedule_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_skedule",
            "description": "Create a new skedule",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Skedule name"},
                    "description": {"type": "string", "description": "Skedule description"},
                    "start_date": {"type": "string", "description": "Start date (ISO format)"},
                    "end_date": {"type": "string", "description": "End date (ISO format)"},
                    "timezone": {"type": "string", "description": "Timezone"},
                    "social_links": {"type": "array", "items": {"type": "object"}, "description": "List of social links"}
                },
                "required": ["name", "description", "start_date", "end_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_skedule",
            "description": "Update an existing skedule",
            "parameters": {
                "type": "object",
                "properties": {
                    "skedule_id": {"type": "string", "description": "ID of the skedule to update"},
                    "name": {"type": "string", "description": "Skedule name"},
                    "description": {"type": "string", "description": "Skedule description"},
                    "start_date": {"type": "string", "description": "Start date (ISO format)"},
                    "end_date": {"type": "string", "description": "End date (ISO format)"},
                    "timezone": {"type": "string", "description": "Timezone"},
                    "social_links": {"type": "array", "items": {"type": "object"}, "description": "List of social links"}
                },
                "required": ["skedule_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_skedule",
            "description": "Delete a skedule",
            "parameters": {
                "type": "object",
                "properties": {
                    "skedule_id": {"type": "string", "description": "ID of the skedule to delete"}
                },
                "required": ["skedule_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_events",
            "description": "Get all events for a skedule",
            "parameters": {
                "type": "object",
                "properties": {
                    "skedule_id": {"type": "string", "description": "ID of the skedule to get events for"}
                },
                "required": ["skedule_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_event",
            "description": "Get a specific event by ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {"type": "string", "description": "ID of the event to retrieve"}
                },
                "required": ["event_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_event",
            "description": "Create a new event in a skedule",
            "parameters": {
                "type": "object",
                "properties": {
                    "skedule_id": {"type": "string", "description": "ID of the skedule to create the event in"},
                    "title": {"type": "string", "description": "Event title"},
                    "description": {"type": "string", "description": "Event description"},
                    "start_time": {"type": "string", "description": "Start time (ISO format)"},
                    "end_time": {"type": "string", "description": "End time (ISO format)"},
                    "location": {"type": "string", "description": "Event location"},
                    "speakers": {"type": "array", "items": {"type": "object"}, "description": "List of speakers"}
                },
                "required": ["skedule_id", "title", "start_time", "end_time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_profile",
            "description": "Get the current user's profile",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_skedules",
            "description": "Search for skedules",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "page": {"type": "integer", "description": "Page number"},
                    "page_size": {"type": "integer", "description": "Number of items per page"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_events",
            "description": "Search for events",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "page": {"type": "integer", "description": "Page number"},
                    "page_size": {"type": "integer", "description": "Number of items per page"}
                },
                "required": ["query"]
            }
        }
    }
]

# Initialize the SkedulesLive client
def get_skeduleslive_client():
    """Get or initialize the SkedulesLive client"""
    if 'skeduleslive_client' not in st.session_state:
        # Create a temporary file for storing tokens
        temp_token_file = tempfile.NamedTemporaryFile(delete=False, prefix="skeduleslive_", suffix=".json")
        
        # Initialize the client with the base URL from MCP_SERVER_URL
        client = SkedulesLiveClient(
            base_url=MCP_SERVER_URL,  # Using the same URL as the MCP server
            client_id=SKEDULESLIVE_CLIENT_ID,
            token_file=temp_token_file.name  # Store tokens in a temp file
        )
        st.session_state.skeduleslive_client = client
        st.session_state.authenticated = False
    
    return st.session_state.skeduleslive_client

def execute_demo_function(function_name, arguments=None):
    """Execute a function in demo mode with mock data"""
    import time
    
    if arguments is None:
        arguments = {}
    
    # Handle different function types with appropriate mock data
    if function_name == "get_skedules":
        print("Using mock data for get_skedules for demo purposes")
        # Return a simulated successful response with sample data
        return {
            "skedules": [
                {
                    "id": "demo-skedule-001",
                    "name": "Product Launch Conference",
                    "description": "Annual product launch featuring new SkedulesLive features",
                    "startDate": "2025-09-15T09:00:00Z",
                    "endDate": "2025-09-17T18:00:00Z",
                    "timezone": "America/Los_Angeles",
                    "status": "PUBLISHED",
                    "events": 8
                },
                {
                    "id": "demo-skedule-002",
                    "name": "Developer Workshop Series",
                    "description": "Weekly technical workshops for developers",
                    "startDate": "2025-08-05T13:00:00Z",
                    "endDate": "2025-10-28T16:00:00Z",
                    "timezone": "Europe/London",
                    "status": "DRAFT",
                    "events": 12
                },
                {
                    "id": "demo-skedule-003",
                    "name": "Annual Team Summit",
                    "description": "Company-wide strategy and team building event",
                    "startDate": "2025-11-10T08:00:00Z",
                    "endDate": "2025-11-12T17:00:00Z",
                    "timezone": "Europe/Berlin",
                    "status": "PUBLISHED",
                    "events": 15
                }
            ]
        }
    
    elif function_name == "get_skedule":
        print("Using mock data for get_skedule for demo purposes")
        skedule_id = arguments.get("skedule_id", "demo-skedule-001")
        return {
            "skedule": {
                "id": skedule_id,
                "name": "Product Launch Conference" if skedule_id == "demo-skedule-001" else "Demo Event",
                "description": "Annual product launch featuring new SkedulesLive features",
                "startDate": "2025-09-15T09:00:00Z",
                "endDate": "2025-09-17T18:00:00Z",
                "timezone": "America/Los_Angeles",
                "status": "PUBLISHED",
                "events": [
                    {
                        "id": "event-001",
                        "title": "Opening Keynote",
                        "description": "Welcome address and product vision",
                        "startTime": "2025-09-15T10:00:00Z",
                        "endTime": "2025-09-15T11:30:00Z",
                        "location": "Main Hall"
                    },
                    {
                        "id": "event-002",
                        "title": "New Features Demo",
                        "description": "Live demonstration of upcoming features",
                        "startTime": "2025-09-15T13:00:00Z",
                        "endTime": "2025-09-15T14:30:00Z",
                        "location": "Demo Room A"
                    }
                ]
            }
        }
        
    elif function_name == "get_events":
        print("Using mock data for get_events for demo purposes")
        skedule_id = arguments.get("skedule_id", "demo-skedule-001")
        
        # Define mock events based on skedule ID
        events_by_skedule = {
            "demo-skedule-001": [
                {
                    "id": "event-001",
                    "title": "Opening Keynote",
                    "description": "Welcome address and product vision",
                    "startTime": "2025-09-15T10:00:00Z",
                    "endTime": "2025-09-15T11:30:00Z",
                    "location": "Main Hall",
                    "speakers": ["Jane Smith", "John Doe"],
                    "type": "keynote"
                },
                {
                    "id": "event-002",
                    "title": "New Features Demo",
                    "description": "Live demonstration of upcoming features",
                    "startTime": "2025-09-15T13:00:00Z",
                    "endTime": "2025-09-15T14:30:00Z",
                    "location": "Demo Room A",
                    "speakers": ["Alice Johnson"],
                    "type": "demo"
                },
                {
                    "id": "event-003",
                    "title": "Developer Workshop",
                    "description": "Hands-on workshop with the new API",
                    "startTime": "2025-09-16T09:00:00Z",
                    "endTime": "2025-09-16T12:00:00Z",
                    "location": "Workshop Room B",
                    "speakers": ["Bob Martin", "Carol Taylor"],
                    "type": "workshop"
                },
                {
                    "id": "event-004",
                    "title": "Partner Showcase",
                    "description": "Demonstrations from technology partners",
                    "startTime": "2025-09-16T14:00:00Z",
                    "endTime": "2025-09-16T17:00:00Z",
                    "location": "Exhibition Hall",
                    "speakers": [],
                    "type": "showcase"
                },
                {
                    "id": "event-005",
                    "title": "Closing Remarks",
                    "description": "Conference summary and future roadmap",
                    "startTime": "2025-09-17T16:00:00Z",
                    "endTime": "2025-09-17T17:00:00Z",
                    "location": "Main Hall",
                    "speakers": ["Jane Smith"],
                    "type": "keynote"
                }
            ],
            "demo-skedule-002": [
                {
                    "id": "event-101",
                    "title": "Intro to SkedulesLive API",
                    "description": "Introduction to working with our REST API",
                    "startTime": "2025-08-05T13:00:00Z",
                    "endTime": "2025-08-05T14:30:00Z",
                    "location": "Virtual",
                    "speakers": ["Dave Wilson"],
                    "type": "workshop"
                },
                {
                    "id": "event-102",
                    "title": "Advanced Integration Patterns",
                    "description": "Best practices for system integration",
                    "startTime": "2025-08-12T13:00:00Z",
                    "endTime": "2025-08-12T14:30:00Z",
                    "location": "Virtual",
                    "speakers": ["Eve Adams"],
                    "type": "workshop"
                }
            ],
            "demo-skedule-003": [
                {
                    "id": "event-201",
                    "title": "Annual Review",
                    "description": "Company performance and highlights",
                    "startTime": "2025-11-10T09:00:00Z",
                    "endTime": "2025-11-10T10:30:00Z",
                    "location": "Conference Center",
                    "speakers": ["Frank Johnson"],
                    "type": "presentation"
                },
                {
                    "id": "event-202",
                    "title": "Team Building Activity",
                    "description": "Outdoor team building exercises",
                    "startTime": "2025-11-11T13:00:00Z",
                    "endTime": "2025-11-11T17:00:00Z",
                    "location": "Park Area",
                    "speakers": [],
                    "type": "activity"
                }
            ]
        }
        
        # Return events for the specified skedule, or empty if not found
        events = events_by_skedule.get(skedule_id, [])
        return {"events": events}
        
    elif function_name == "get_event":
        print("Using mock data for get_event for demo purposes")
        skedule_id = arguments.get("skedule_id", "demo-skedule-001")
        event_id = arguments.get("event_id", "event-001")
        
        # Define some mock events
        event_data = {
            "event-001": {
                "id": "event-001",
                "title": "Opening Keynote",
                "description": "Welcome address and product vision",
                "startTime": "2025-09-15T10:00:00Z",
                "endTime": "2025-09-15T11:30:00Z",
                "location": "Main Hall",
                "speakers": ["Jane Smith", "John Doe"],
                "type": "keynote",
                "skedule_id": "demo-skedule-001",
                "resources": [
                    {"type": "slides", "url": "https://example.com/slides"},
                    {"type": "recording", "url": "https://example.com/recording"}
                ],
                "tracks": ["Main Track"]
            },
            "event-002": {
                "id": "event-002",
                "title": "New Features Demo",
                "description": "Live demonstration of upcoming features",
                "startTime": "2025-09-15T13:00:00Z",
                "endTime": "2025-09-15T14:30:00Z",
                "location": "Demo Room A",
                "speakers": ["Alice Johnson"],
                "type": "demo",
                "skedule_id": "demo-skedule-001",
                "resources": [],
                "tracks": ["Technical Track"]
            }
        }
        
        # Return the event if found, otherwise return an error
        if event_id in event_data:
            return {"event": event_data[event_id]}
        else:
            return {"error": f"Event {event_id} not found"}
        
    elif function_name == "authenticate":
        print("Using mock data for authenticate for demo purposes")
        email = arguments.get("email", "")
        password = arguments.get("password", "")
        
        # Always return successful authentication for demo
        return {
            "success": True,
            "message": "Authentication successful",
            "tokens": {
                "token": "demo-auth-token-12345",
                "refresh_token": "demo-refresh-token-67890",
                "id_token": "demo-id-token-abcde"
            },
            "user": {
                "id": "user-001",
                "email": email or "demo@example.com",
                "name": "Demo User",
                "role": "PUBLISHER"
            }
        }
        
    elif function_name == "create_skedule":
        print("Using mock data for create_skedule for demo purposes")
        name = arguments.get("name", "New Demo Skedule")
        description = arguments.get("description", "A demo skedule created via the API")
        
        return {
            "success": True,
            "skedule": {
                "id": "new-skedule-" + str(int(time.time())),
                "name": name,
                "description": description,
                "startDate": arguments.get("startDate", "2025-10-01T09:00:00Z"),
                "endDate": arguments.get("endDate", "2025-10-03T17:00:00Z"),
                "timezone": arguments.get("timezone", "UTC"),
                "status": "DRAFT",
                "events": []
            }
        }
    
    # Default response for unimplemented functions
    return {"error": f"Demo mode not implemented for function: {function_name}"}


def execute_mcp_function(function_name, arguments=None):
    """Execute a function on the MCP server and return the response"""
    global MCP_API_KEY
    
    # Check if we're in demo mode
    use_demo_mode = False
    if hasattr(st, 'session_state') and 'use_demo_mode' in st.session_state:
        use_demo_mode = st.session_state.use_demo_mode
        
    if use_demo_mode:
        # In demo mode, return mock data
        print(f"Using demo mode for {function_name}")
        return execute_demo_function(function_name, arguments)
    else:
        # In live mode, call the actual MCP server
        print(f"Using live API for {function_name}")
        
        # Debug auth state for live mode
        auth_status = "Not authenticated"
        if hasattr(st, 'session_state') and st.session_state.get('authenticated', False):
            auth_status = "Authenticated"
            if 'auth_tokens' in st.session_state and st.session_state.auth_tokens:
                token_keys = list(st.session_state.auth_tokens.keys())
                auth_status += f" with tokens: {token_keys}"
        print(f"Debug: Authentication status: {auth_status}")
        
        # Log MCP server URL
        print(f"Debug: Using MCP server: {MCP_SERVER_URL}")

    
    # Set up headers
    headers = {
        "Content-Type": "application/json"
    }
    
    # Add API key to headers
    headers["X-API-Key"] = MCP_API_KEY
    
    # Handle authentication requests
    if function_name == "authenticate":
        try:
            # Actually call the MCP server authenticate endpoint
            endpoint = f"{MCP_SERVER_URL}/mcp/authenticate"
            print(f"Debug: Authenticating with MCP server at {endpoint}")
            
            # Make the authentication request
            auth_response = requests.post(
                endpoint,
                json=arguments,
                headers=headers
            )
            
            # Check if authentication was successful
            if auth_response.status_code == 200:
                # Parse the response
                response_data = auth_response.json()
                # Redact sensitive data before logging
                safe_response = {k: ("[REDACTED]" if k in ['tokens', 'password'] else v) for k, v in response_data.items()}
                print(f"Debug: Authentication response: {safe_response}")
                
                if response_data.get('success', False):
                    # Store the tokens in session state
                    st.session_state.authenticated = True
                    tokens = response_data.get('tokens', {})
                    st.session_state.auth_tokens = tokens
                    
                    # Log token types but not values
                    token_types = list(tokens.keys()) if tokens else []
                    print(f"Debug: Authentication successful, token types stored: {token_types}")
                    
                    # Also store user information if available
                    if 'user' in response_data:
                        st.session_state.user = response_data.get('user', {})
                        print(f"Debug: User info stored: {st.session_state.user.get('email', 'unknown')}")
                    return {"status": "success", "message": "Authentication successful"}
                else:
                    # Authentication failed but server responded
                    print(f"Debug: Authentication failed: {response_data.get('message', 'Unknown error')}")
                    return {"status": "error", "message": f"Authentication failed: {response_data.get('message', 'Invalid credentials')}"}
            
            # Handle HTTP errors
            auth_response.raise_for_status()
            return {"status": "error", "message": "Authentication failed with unexpected error"}
            
        except Exception as e:
            print(f"Debug: Authentication exception: {str(e)}")
            return {"status": "error", "message": f"Authentication error: {str(e)}"}
    
    # For all other functions, use the API key and auth tokens if available
    endpoint = f"{MCP_SERVER_URL}/mcp/{function_name}"
        # Add auth tokens to headers if available
    if hasattr(st, 'session_state') and 'auth_tokens' in st.session_state and st.session_state.auth_tokens:
        # Extract the token from the auth_tokens dictionary
        if 'token' in st.session_state.auth_tokens:
            headers['Authorization'] = f"Bearer {st.session_state.auth_tokens['token']}"
            print("Debug: Added authorization token to headers")
        else:
            print("Debug: No 'token' found in auth_tokens")
            print(f"Debug: Available token types: {list(st.session_state.auth_tokens.keys())}")
            
        # Add cookies based on auth tokens - this is critical for the SkedulesLive API
        cookie_headers = []
        for token_name, token_value in st.session_state.auth_tokens.items():
            if token_value:  # Only add non-empty tokens
                cookie_headers.append(f"{token_name}={token_value}")
            
        if cookie_headers:
            headers['Cookie'] = "; ".join(cookie_headers)
            print(f"Debug: Added {len(cookie_headers)} auth cookies to headers")
        else:
            print("Debug: No valid cookies to add")
            
        # Also add token to query params for redundancy
        if 'token' in st.session_state.auth_tokens and isinstance(arguments, dict):
            token_val = st.session_state.auth_tokens['token']
            if token_val:
                arguments['token'] = token_val
                print("Debug: Added token to query params")
            else:
                print("Debug: Token exists but is empty, not adding to params")
        elif not 'token' in st.session_state.auth_tokens:
            print("Debug: No 'token' found for query params")
        elif not isinstance(arguments, dict):
            print("Debug: Arguments is not a dict, can't add token")
            arguments = {}  # Initialize as empty dict if None
    
    # Set up default parameters for get_skedules
    if function_name == "get_skedules" and not arguments:
        # Try with default parameters that might be expected
        arguments = {"page": 1, "page_size": 10}
        print(f"Debug: Adding default parameters to get_skedules: {arguments}")
    
    # Debug API key (redacting most of it for security)
    if MCP_API_KEY:
        masked_key = f"{MCP_API_KEY[:3]}...{MCP_API_KEY[-3:]}" if len(MCP_API_KEY) > 6 else "***"
        print(f"Debug: Using API key starting with {masked_key}")
    else:
        print("Debug: API key is None or empty!")
    
    # Make sure the API key header is correct (MCP server might expect X-API-Key)  
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": MCP_API_KEY,  # This is the standard header name
    }
    
    try:
        # Print what we're sending for debugging
        redacted_headers = {}
        for k, v in headers.items():
            if k.lower() in ["x-api-key", "authorization"]:
                redacted_headers[k] = f"{v[:3]}...{v[-3:]}" if v and len(v) > 6 else "[REDACTED]"
            elif k.lower() == "cookie":
                redacted_headers[k] = "[COOKIES PRESENT]"
            else:
                redacted_headers[k] = v
                
        # Redact any sensitive data in arguments
        safe_args = {}
        if arguments:
            for k, v in arguments.items():
                if k.lower() in ["password", "token", "refresh_token", "id_token"]:
                    safe_args[k] = "[REDACTED]"
                else:
                    safe_args[k] = v
        
        print(f"Debug: Sending to {endpoint} with headers: {redacted_headers} and data: {safe_args}")
        
        # Make the API call with just the API key
        response = requests.post(endpoint, json=arguments, headers=headers)
        
        # Handle common error responses from the MCP server
        if response.status_code in (400, 401, 403, 500):
            try:
                error_content = response.json()
                print(f"Debug: Server returned {response.status_code} with content: {error_content}")
                
                # Check for specific authentication error messages
                if 'detail' in error_content:
                    error_detail = error_content['detail']
                    if isinstance(error_detail, str) and 'no stored credentials' in error_detail.lower():
                        # Clear any stored auth tokens as they're invalid
                        if hasattr(st, 'session_state'):
                            st.session_state.authenticated = False
                            if 'auth_tokens' in st.session_state:
                                del st.session_state.auth_tokens
                        
                        return {
                            "status": "error", 
                            "message": "I'm sorry, but you need to authenticate before I can access any scheduled content for you. Can you please authenticate with your email and password so that I can retrieve the schedule for you?",
                            "technical_details": "The MCP server requires user authentication to access this endpoint."
                        }
                    elif isinstance(error_detail, str) and 'invalid api key' in error_detail.lower():
                        return {
                            "status": "error", 
                            "message": "The API key provided is not valid. Please check your API key configuration.",
                            "technical_details": "MCP server rejected the API key."
                        }
            except Exception as json_error:
                print(f"Debug: Could not parse JSON from error response: {json_error}")
                print(f"Debug: Raw response: {response.text}")
        
        response.raise_for_status()  # Raise an exception for any other 4XX/5XX responses
        return response.json()
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        print(f"Error calling MCP endpoint {endpoint}: {error_msg}")
        
        # Try to get more error details if possible
        if hasattr(e, 'response') and e.response is not None:
            try:
                print(f"Debug: Response status code: {e.response.status_code}")
                print(f"Debug: Response headers: {e.response.headers}")
                print(f"Debug: Response content: {e.response.text}")
                
                # Check for auth errors in the response content
                try:
                    error_content = e.response.json()
                    if 'detail' in error_content and 'no stored credentials' in error_content['detail'].lower():
                        return {
                            "status": "error", 
                            "message": "I'm sorry, but you need to authenticate before I can access any scheduled content for you. Can you please authenticate so that I can retrieve the schedule for you?"
                        }
                except:
                    pass
            except Exception as inner_e:
                print(f"Debug: Could not extract error details: {inner_e}")
        
        # Handle different HTTP error codes
        if hasattr(e, 'response') and e.response is not None:
            if e.response.status_code in (401, 403):
                return {"status": "error", "message": "API key authentication failed. Please check your API key."}
            elif e.response.status_code == 500:
                return {"status": "error", "message": "The server encountered an error processing your request. This could be because the endpoint is not fully implemented or there is a server-side issue."}
        
        return {"status": "error", "message": error_msg}

def chat_with_skeduleslive(user_message):
    """Process a user message with OpenAI and execute any tool calls"""
    
    if not OPENAI_API_KEY:
        return "Error: OPENAI_API_KEY environment variable is not set"
        
    # Check if we have a SkedulesLive client and credentials
    if not st.session_state.get("authenticated", False) and not (SKEDULESLIVE_EMAIL and SKEDULESLIVE_PASSWORD):
        # We don't have credentials and aren't authenticated, but we'll let the flow continue
        # The execute_mcp_function will handle authentication errors if needed
        pass
    
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an assistant that helps manage SkedulesLive content. You can help create and manage schedules, events, and other content."},
                {"role": "user", "content": user_message}
            ],
            tools=MCP_FUNCTIONS
        )
        
        # Check if the model wants to call a function
        if response.choices[0].message.tool_calls:
            # Process each tool call
            for tool_call in response.choices[0].message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                print(f"Calling function: {function_name} with args: {function_args}")
                
                # Execute the function
                function_response = execute_mcp_function(function_name, function_args)
                
                # Send the function result back to the model
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are an assistant that helps manage SkedulesLive content. You can help create and manage schedules, events, and other content."},
                        {"role": "user", "content": user_message},
                        {"role": "assistant", "content": None, "tool_calls": [tool_call]},
                        {"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(function_response)}
                    ]
                )
        
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

# Simple CLI interface for testing
if __name__ == "__main__":
    print("SkedulesLive AI Assistant")
    print("-------------------------")
    print("Type 'exit' to quit")
    
    if not MCP_API_KEY:
        print("\nWARNING: MCP_API_KEY environment variable is not set!")
        print("Set this in your .env file or export it before running this script.")
    
    if not OPENAI_API_KEY:
        print("\nWARNING: OPENAI_API_KEY environment variable is not set!")
        print("Set this in your .env file or export it before running this script.")
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() == 'exit':
            break
        
        response = chat_with_skeduleslive(user_input)
        print(f"\nAI: {response}")
