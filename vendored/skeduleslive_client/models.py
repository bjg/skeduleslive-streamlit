from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime


@dataclass
class SocialLink:
    """
    Represents a social media link associated with a Skedule
    """
    network: str
    url: str
    skeduleId: Optional[str] = None
    id: Optional[str] = None


@dataclass
class Event:
    """
    Represents an event within a Skedule
    """
    name: str
    description: str
    startDate: str  # ISO format date string
    endDate: str    # ISO format date string
    location: Optional[str] = None
    isVirtual: bool = False
    skeduleId: Optional[str] = None
    id: Optional[str] = None


@dataclass
class Skedule:
    """
    Represents a Skedule, which is the main entity in the SkedulesLive application
    """
    name: str
    description: str
    location: Optional[str] = None
    isVirtual: bool = False
    isPublic: bool = True
    type: str = "BUSINESS"
    phone: Optional[str] = None
    image: Optional[str] = None
    thumbnail: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    categories: List[str] = field(default_factory=list)
    socialLinks: List[SocialLink] = field(default_factory=list)
    events: List[Event] = field(default_factory=list)
    id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the Skedule object to a dictionary for API requests"""
        result = {
            "name": self.name,
            "description": self.description,
            "isVirtual": self.isVirtual,
            "isPublic": self.isPublic,
            "type": self.type,
        }
        
        # Add optional fields if they exist
        for field in ["location", "phone", "image", "thumbnail", "lat", "lng", "id"]:
            value = getattr(self, field)
            if value is not None:
                result[field] = value
                
        # Add list fields if they're not empty
        if self.categories:
            result["categories"] = self.categories
            
        # Handle nested objects
        if self.socialLinks:
            result["socialLinks"] = [
                {k: v for k, v in link.__dict__.items() if v is not None}
                for link in self.socialLinks
            ]
        
        if self.events:
            result["events"] = [
                {k: v for k, v in event.__dict__.items() if v is not None}
                for event in self.events
            ]
            
        return result


@dataclass
class User:
    """
    Represents a user in the SkedulesLive system
    """
    email: str
    role: str
    name: Optional[str] = None
    id: Optional[str] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None


@dataclass
class UserProfile:
    """
    Represents a user's profile information
    """
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    bio: Optional[str] = None
    avatar: Optional[str] = None
    id: Optional[str] = None


@dataclass
class MediaItem:
    """
    Represents a media item (image, document, etc.)
    """
    url: str
    type: str  # e.g., 'image', 'document', etc.
    filename: str
    description: Optional[str] = None
    size: Optional[int] = None
    createdAt: Optional[str] = None
    id: Optional[str] = None


@dataclass
class Analytics:
    """
    Represents analytics data for a skedule or event
    """
    views: int = 0
    shares: int = 0
    clicks: int = 0
    registrations: int = 0
    period: Optional[str] = None  # e.g., 'day', 'week', 'month', 'all'
    startDate: Optional[str] = None
    endDate: Optional[str] = None
