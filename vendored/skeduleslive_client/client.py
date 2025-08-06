import requests
import json
import time
import os
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union
from .models import Skedule, Event, SocialLink, User, UserProfile, MediaItem

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SkedulesLiveClient")


class SkedulesLiveClient:
    def __init__(self, base_url: str, client_id: str, token_file: Optional[str] = None):
        """
        Initialize the API client
        
        Args:
            base_url: The base URL of the SkedulesLive API
            client_id: The AWS Cognito client ID
            token_file: Optional path to a file to store tokens for persistence
        """
        # Ensure the base URL has the correct format (www subdomain is required)
        if base_url == "https://skdl.es":
            self.base_url = "https://www.skdl.es"
            logger.info(f"Converted base URL from {base_url} to {self.base_url}")
        else:
            self.base_url = base_url
            
        self.client_id = client_id
        self.session = requests.Session()
        self.tokens = None
        self.token_expiry = None
        self.token_file = token_file
        
        # Load tokens from file if available
        if token_file:
            self._load_tokens()
    
    def _load_tokens(self):
        """Load tokens from file if available"""
        if not self.token_file:
            return
            
        try:
            with open(self.token_file, 'r') as f:
                saved_data = json.load(f)
                self.tokens = saved_data.get('tokens')
                if saved_data.get('expiry'):
                    self.token_expiry = datetime.fromisoformat(saved_data['expiry'])
                logger.info("Loaded authentication tokens from file")
        except (FileNotFoundError, json.JSONDecodeError):
            logger.info("No valid token file found, will need to authenticate")
    
    def _save_tokens(self):
        """Save tokens to file if token_file is specified"""
        if not self.token_file:
            return
            
        with open(self.token_file, 'w') as f:
            json.dump({
                'tokens': self.tokens,
                'expiry': self.token_expiry.isoformat() if self.token_expiry else None
            }, f)
        logger.info("Saved authentication tokens to file")
    
    def authenticate(self, email: str, password: str, keep_me_logged: bool = True) -> bool:
        """
        Authenticate with the SkedulesLive API
        
        Args:
            email: User email
            password: User password
            keep_me_logged: Whether to keep the user logged in
            
        Returns:
            bool: True if authentication was successful
        """
        # Store credentials for token refresh
        self._email = email
        self._password = password
        
        # Based on the API implementation, the sign-in endpoint expects specific parameters
        # The server-side code shows it uses AWS Cognito with USER_PASSWORD_AUTH flow
        auth_data = {
            "email": email.lower(),  # API lowercases the email
            "password": password,
            "keepMeLogged": keep_me_logged,
            "role": "PUBLISHER"  # The API expects PUBLISHER in uppercase based on the memory
        }
        
        logger.info(f"Auth data being sent: {auth_data}")
        
        logger.info(f"Authenticating user: {email}")
        logger.info(f"Using base URL: {self.base_url}")
        logger.info(f"Using client ID: {self.client_id}")
        
        try:
            # Set proper headers for the request
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            response = self.session.post(
                f"{self.base_url}/api/auth/sign-in",
                json=auth_data,
                headers=headers
            )
            
            logger.info(f"Authentication response status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    logger.info("Authentication response data structure: " + str(list(data.keys())))
                    if "data" in data:
                        logger.info("Data fields: " + str(list(data["data"].keys())))
                    
                    # More flexible token extraction
                    if "data" in data:
                        token_data = data["data"]
                        self.tokens = {}
                        
                        # Try to extract tokens from different possible locations
                        for token_key in ["token", "refreshToken", "expToken", "idToken"]:
                            if token_key in token_data:
                                self.tokens[token_key] = token_data[token_key]
                        
                        # If we couldn't find any tokens in the data, authentication failed
                        if not self.tokens:
                            logger.error("No tokens found in response data")
                            return False
                    else:
                        logger.error("Response missing 'data' field")
                        return False
                    
                    # Store cookies from the response
                    cookie_count = 0
                    for cookie in response.cookies:
                        cookie_count += 1
                        if cookie.name in ["idToken", "token", "refreshToken", "expToken", "role", "userEmail"]:
                            self.tokens[cookie.name] = cookie.value
                    
                    logger.info(f"Extracted {cookie_count} cookies from response")
                    
                    # Set token expiry
                    if "expToken" in self.tokens:
                        try:
                            exp_time = int(self.tokens["expToken"]) / 1000  # Convert from milliseconds
                            self.token_expiry = datetime.fromtimestamp(exp_time)
                        except (ValueError, TypeError):
                            # If expToken is not a valid timestamp, use default expiry
                            self.token_expiry = datetime.now() + timedelta(hours=1)
                    else:
                        self.token_expiry = datetime.now() + timedelta(hours=1)  # Default expiry
                    
                    # Save tokens to file
                    self._save_tokens()
                    logger.info("Authentication successful")
                    return True
                except Exception as e:
                    logger.error(f"Error processing authentication response: {str(e)}")
                    return False
            
            logger.error(f"Authentication failed with status code: {response.status_code}")
            logger.error(f"Response content: {response.text}")
            return False
        except Exception as e:
            logger.error(f"Authentication exception: {str(e)}")
            return False
    
    def _ensure_authenticated(self):
        """Ensure the client is authenticated before making requests"""
        if not self.tokens:
            raise Exception("Not authenticated. Call authenticate() first.")
        
        # Check if token is about to expire and refresh if needed
        if self.token_expiry and datetime.now() > self.token_expiry - timedelta(minutes=5):
            logger.info("Token is about to expire, refreshing...")
            self._refresh_token()
    
    def _refresh_token(self):
        """Refresh the authentication token"""
        if not self.tokens or not self.tokens.get("refreshToken"):
            raise Exception("No refresh token available")
        
        try:
            # For SkedulesLive API, we need to re-authenticate instead of using a refresh endpoint
            # This is because the token refresh is handled in the middleware, not via a dedicated endpoint
            logger.info("Re-authenticating to refresh token")
            
            # Check if we have stored credentials
            if hasattr(self, "_email") and hasattr(self, "_password"):
                return self.authenticate(self._email, self._password)
            else:
                # If we don't have stored credentials, we can't refresh the token
                # In a real-world scenario, you might want to prompt the user for credentials
                logger.error("Cannot refresh token: no stored credentials")
                raise Exception("Cannot refresh token: no stored credentials. Please re-authenticate manually.")
        except Exception as e:
            logger.error(f"Error refreshing token: {str(e)}")
            raise
    
    def _prepare_request_cookies(self):
        """Prepare cookies for API requests"""
        cookies = {}
        for key in ["token", "refreshToken", "expToken", "idToken", "role", "userEmail"]:
            if key in self.tokens:
                cookies[key] = self.tokens[key]
        return cookies
    
    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, data: Optional[Dict] = None):
        """Make an API request with authentication"""
        self._ensure_authenticated()
        
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}
        cookies = self._prepare_request_cookies()
        
        try:
            if method.lower() == "get":
                response = self.session.get(url, params=params, headers=headers, cookies=cookies)
            elif method.lower() == "post":
                response = self.session.post(url, json=data, headers=headers, cookies=cookies)
            elif method.lower() == "patch":
                response = self.session.patch(url, json=data, headers=headers, cookies=cookies)
            elif method.lower() == "delete":
                response = self.session.delete(url, headers=headers, cookies=cookies)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            if response.status_code >= 200 and response.status_code < 300:
                return response.json()
            else:
                error_msg = f"API request failed with status {response.status_code}: {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
        except Exception as e:
            logger.error(f"Error making API request: {str(e)}")
            raise
    
    # Skedule Methods
    def get_skedules(self, page: int = 1, page_size: int = 10) -> Dict:
        """Get a list of skedules with pagination"""
        return self._make_request(
            "get", 
            "/api/skedule", 
            params={"page": page, "pageSize": page_size}
        )
    
    def create_skedule(self, skedule: Union[Skedule, Dict]) -> Dict:
        """Create a new skedule"""
        if isinstance(skedule, Skedule):
            # Use the to_dict method if available
            if hasattr(skedule, 'to_dict') and callable(getattr(skedule, 'to_dict')):
                skedule_data = skedule.to_dict()
            else:
                # Convert dataclass to dict
                skedule_data = {k: v for k, v in skedule.__dict__.items() if v is not None}
                
                # Handle nested objects
                if skedule.socialLinks:
                    skedule_data["socialLinks"] = [
                        {k: v for k, v in link.__dict__.items() if v is not None}
                        for link in skedule.socialLinks
                    ]
                
                if skedule.events:
                    skedule_data["events"] = [
                        {k: v for k, v in event.__dict__.items() if v is not None}
                        for event in skedule.events
                    ]
        else:
            skedule_data = skedule
            
        return self._make_request("post", "/api/skedule", data=skedule_data)
    
    def get_skedule(self, skedule_id: str) -> Dict:
        """Get a specific skedule by ID"""
        return self._make_request("get", f"/api/skedule/{skedule_id}")
    
    def update_skedule(self, skedule_id: str, skedule: Union[Skedule, Dict]) -> Dict:
        """Update an existing skedule"""
        if isinstance(skedule, Skedule):
            # Use the to_dict method if available
            if hasattr(skedule, 'to_dict') and callable(getattr(skedule, 'to_dict')):
                skedule_data = skedule.to_dict()
            else:
                # Convert dataclass to dict
                skedule_data = {k: v for k, v in skedule.__dict__.items() if v is not None}
                
                # Handle nested objects
                if skedule.socialLinks:
                    skedule_data["socialLinks"] = [
                        {k: v for k, v in link.__dict__.items() if v is not None}
                        for link in skedule.socialLinks
                    ]
                
                if skedule.events:
                    skedule_data["events"] = [
                        {k: v for k, v in event.__dict__.items() if v is not None}
                        for event in skedule.events
                    ]
        else:
            skedule_data = skedule
            
        return self._make_request("patch", f"/api/skedule/{skedule_id}", data=skedule_data)
    
    def delete_skedule(self, skedule_id: str) -> Dict:
        """Delete a skedule"""
        return self._make_request("delete", f"/api/skedule/{skedule_id}")
    
    # Event Methods
    def update_event(self, event_id: str, event: Union[Event, Dict]) -> Dict:
        """Update an event"""
        if isinstance(event, Event):
            event_data = {k: v for k, v in event.__dict__.items() if v is not None}
        else:
            event_data = event
            
        return self._make_request("post", f"/api/event/{event_id}", data=event_data)
    
    def get_events_for_skedule(self, skedule_id: str) -> Dict:
        """Get events for a specific skedule"""
        return self._make_request("get", f"/api/skedule/{skedule_id}/event")
    
    def create_event(self, skedule_id: str, event: Union[Event, Dict]) -> Dict:
        """Create a new event for a skedule"""
        if isinstance(event, Event):
            event_data = {k: v for k, v in event.__dict__.items() if v is not None}
        else:
            event_data = event

        # Enhanced logging to debug the API call
        logger.info(f"Creating event for skedule {skedule_id}")
        logger.info(f"Event data: {event_data}")
        
        # Based on the SkedulesLive API structure, events should be created by updating a skedule
        # Using the PATCH /api/skedule/[id] endpoint with events in the create array
        
        # First, ensure we have the required fields properly formatted
        formatted_event = {
            "title": event_data.get("title"),
            "description": event_data.get("description"),
            # Handle both camelCase and snake_case variations
            "startTime": event_data.get("startTime") or event_data.get("start_time"),
            "endTime": event_data.get("endTime") or event_data.get("end_time"),
        }
        
        # Add optional fields if present
        if "location" in event_data:
            formatted_event["location"] = event_data["location"]
            
        # Construct the update payload for the skedule
        update_payload = {
            # The events.create array is used to add new events to a skedule
            "events": {
                "create": [formatted_event]
            }
        }
        
        logger.info(f"Using PATCH /api/skedule/{skedule_id} with payload: {update_payload}")
        
        try:
            # Update the skedule with the new event
            response = self._make_request("patch", f"/api/skedule/{skedule_id}", data=update_payload)
            
            # Enhanced response logging for debugging
            logger.info("=== EVENT CREATION RESPONSE DETAILS ===")
            logger.info(f"Full response: {response}")
            
            # Inspect and log the structure of the response
            if isinstance(response, dict):
                logger.info(f"Response keys at root level: {list(response.keys())}")
            
            # CRITICAL FIX: The PATCH response doesn't include events, so we need to make a separate GET request
            # to get the latest events and extract the newly created event's ID
            logger.info("Making additional request to get skedule events after creation")
            
            # First try to get the skedule including events
            events_response = self._make_request("get", f"/api/skedule/{skedule_id}")
            
            logger.info("=== EVENTS FETCH RESPONSE DETAILS ===")
            logger.info(f"Full events response: {events_response}")
            
            # If the skedule doesn't include events, make another call to specifically get events
            if (not isinstance(events_response, dict) or 
                'skedule' not in events_response or 
                not isinstance(events_response['skedule'], dict) or
                'events' not in events_response['skedule'] or 
                not isinstance(events_response['skedule']['events'], list)):
                
                logger.info("No events found in skedule response, making specific call to get events")
                events_specific_response = self._make_request("get", f"/api/skedule/{skedule_id}/event")
                logger.info(f"Events specific response: {events_specific_response}")
                
                if isinstance(events_specific_response, dict) and 'events' in events_specific_response:
                    # Replace the events_response with this more specific response
                    events_response = {
                        'skedule': {'id': skedule_id, 'events': events_specific_response['events']}
                    }
                    logger.info(f"Updated events response with specific events data: {len(events_specific_response['events'])} events")
            
            # Try to find the newly created event in the GET response
            event_id = None
            if isinstance(events_response, dict):
                logger.info(f"Events response keys at root level: {list(events_response.keys())}")
                
                # Check if events are directly in the response
                if 'events' in events_response and isinstance(events_response['events'], list):
                    events = events_response['events']
                    logger.info(f"Found {len(events)} events in response")
                    
                    # Try to match the event by name/title and time
                    for event in events:
                        # Use the event name/title for matching
                        event_name = event.get('name') or event.get('title')
                        if event_name and event_name == event_data.get('name', event_data.get('title')):
                            # Double-check with start time if available
                            event_start = event.get('startDate') or event.get('start_date') or event.get('start_time')
                            data_start = event_data.get('startDate') or event_data.get('start_date') or event_data.get('start_time')
                            
                            if event_start == data_start:
                                event_id = event.get('id')
                                logger.info(f"Found matching event with ID: {event_id}")
                                break
                
                # Check if events are in the skedule object
                elif 'skedule' in events_response and isinstance(events_response['skedule'], dict):
                    skedule = events_response['skedule']
                    if 'events' in skedule and isinstance(skedule['events'], list):
                        events = skedule['events']
                        logger.info(f"Found {len(events)} events in skedule.events")
                        
                        # Try to match the event by name/title and time
                        for event in events:
                            # Use the event name/title for matching
                            event_name = event.get('name') or event.get('title')
                            if event_name and event_name == event_data.get('name', event_data.get('title')):
                                # Double-check with start time if available
                                event_start = event.get('startDate') or event.get('start_date') or event.get('start_time')
                                data_start = event_data.get('startDate') or event_data.get('start_date') or event_data.get('start_time')
                                
                                if event_start == data_start:
                                    event_id = event.get('id')
                                    logger.info(f"Found matching event with ID: {event_id}")
                                    break
            
            # Original log
            logger.info(f"Event creation response summary: {response}")
            logger.info(f"Extracted event ID: {event_id}")
            
            # Add the event_id to the response to propagate it to the MCP server
            if event_id is not None and isinstance(response, dict):
                response['event_id'] = event_id
                logger.info(f"Added event_id to response: {event_id}")
            
            # Return the response with added event_id if found
            # (Note: we've already added it above if it was found)
                
            return response
            
        except Exception as e:
            logger.error(f"Error creating event: {str(e)}")
            # Re-raise to let the caller handle the error
            raise
    
    def get_event(self, event_id: str) -> Dict:
        """Get a specific event by ID"""
        return self._make_request("get", f"/api/event/{event_id}")
    
    def delete_event(self, event_id: str) -> Dict:
        """Delete an event"""
        return self._make_request("delete", f"/api/event/{event_id}")
        
    # User Management Methods
    def get_user_profile(self) -> Dict:
        """Get the current user's profile"""
        return self._make_request("get", "/api/user/profile")
    
    def update_user_profile(self, profile: Union[UserProfile, Dict]) -> Dict:
        """Update user profile information"""
        if isinstance(profile, UserProfile):
            profile_data = {k: v for k, v in profile.__dict__.items() if v is not None}
        else:
            profile_data = profile
            
        return self._make_request("patch", "/api/user/profile", data=profile_data)
    
    def get_users(self, page: int = 1, page_size: int = 10) -> Dict:
        """Get a list of users (for admin/publisher roles)"""
        return self._make_request(
            "get", 
            "/api/user",
            params={"page": page, "pageSize": page_size}
        )
    
    def invite_user(self, email: str, role: str = "PUBLISHER") -> Dict:
        """Invite a new user to the platform"""
        return self._make_request("post", "/api/user/invite", data={"email": email, "role": role})
    
    # Media Management Methods
    def get_media(self, page: int = 1, page_size: int = 10) -> Dict:
        """Get a list of uploaded media"""
        return self._make_request(
            "get", 
            "/api/media",
            params={"page": page, "pageSize": page_size}
        )
    
    def upload_media(self, file_path: str, description: str = None) -> Dict:
        """Upload a media file"""
        # For file uploads, we need to use multipart/form-data
        import os
        from requests_toolbelt.multipart.encoder import MultipartEncoder
        
        filename = os.path.basename(file_path)
        
        # Prepare multipart form data
        fields = {
            'file': (filename, open(file_path, 'rb'), 'application/octet-stream'),
        }
        
        if description:
            fields['description'] = description
            
        multipart_data = MultipartEncoder(fields=fields)
        
        # Set up headers with the correct content type
        headers = self._prepare_request_cookies()
        headers['Content-Type'] = multipart_data.content_type
        
        # Make the request
        response = self.session.post(
            f"{self.base_url}/api/media/upload",
            data=multipart_data,
            headers=headers
        )
        
        if response.status_code >= 400:
            logger.error(f"Upload failed with status code: {response.status_code}")
            logger.error(f"Response content: {response.text}")
            raise Exception(f"Upload failed: {response.text}")
            
        return response.json()
    
    def delete_media(self, media_id: str) -> Dict:
        """Delete a media item"""
        return self._make_request("delete", f"/api/media/{media_id}")
    
    # Analytics Methods
    def get_skedule_analytics(self, skedule_id: str, start_date: str = None, end_date: str = None) -> Dict:
        """Get analytics for a specific skedule"""
        params = {}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
            
        return self._make_request("get", f"/api/analytics/skedule/{skedule_id}", params=params)
    
    def get_event_analytics(self, event_id: str) -> Dict:
        """Get analytics for a specific event"""
        return self._make_request("get", f"/api/analytics/event/{event_id}")
    
    # Search Methods
    def search_skedules(self, query: str, page: int = 1, page_size: int = 10) -> Dict:
        """Search for skedules"""
        return self._make_request(
            "get", 
            "/api/search/skedule",
            params={"q": query, "page": page, "pageSize": page_size}
        )
    
    def search_events(self, query: str, page: int = 1, page_size: int = 10) -> Dict:
        """Search for events"""
        return self._make_request(
            "get", 
            "/api/search/event",
            params={"q": query, "page": page, "pageSize": page_size}
        )
