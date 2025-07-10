"""
Pydantic models for the async documentation scraper
"""
from pydantic import BaseModel, HttpUrl, Field
from typing import List, Dict, Optional, Set
from datetime import datetime
from enum import Enum


class DocType(str, Enum):
    """Types of documentation"""
    REFERENCE = "reference"
    API = "api"
    GUIDE = "guide"


class ProjectModel(BaseModel):
    """Model for a Spring project"""
    name: str
    url: HttpUrl
    description: Optional[str] = None
    versions: List[str] = Field(default_factory=list)
    docs: Dict[DocType, HttpUrl] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            HttpUrl: str
        }


class NavigationItem(BaseModel):
    """Model for navigation menu items"""
    text: str
    href: str
    children: List['NavigationItem'] = Field(default_factory=list)


class ScrapedContent(BaseModel):
    """Model for scraped documentation content"""
    title: str
    content: str
    nav: Optional[List[NavigationItem]] = None
    type: DocType
    project: str
    scraped_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class RouteModel(BaseModel):
    """Model for SPA routes"""
    content: str  # Path to content file
    title: str
    project: str
    type: DocType
    
    class Config:
        json_encoders = {
            DocType: lambda v: v.value
        }


class ScrapeMetadata(BaseModel):
    """Model for scrape metadata"""
    scrape_date: datetime = Field(default_factory=datetime.now)
    total_projects: int = 0
    projects: Dict[str, ProjectModel] = Field(default_factory=dict)
    total_routes: int = 0
    total_static_resources: int = 0
    scrape_duration_seconds: Optional[float] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            HttpUrl: str
        }


class ScrapeProgress(BaseModel):
    """Model for tracking scrape progress"""
    total_urls: int = 0
    processed_urls: int = 0
    failed_urls: int = 0
    current_project: Optional[str] = None
    current_action: Optional[str] = None
    start_time: datetime = Field(default_factory=datetime.now)
    
    @property
    def percentage(self) -> float:
        """Calculate completion percentage"""
        if self.total_urls == 0:
            return 0.0
        return (self.processed_urls / self.total_urls) * 100
    
    @property
    def elapsed_seconds(self) -> float:
        """Calculate elapsed time in seconds"""
        return (datetime.now() - self.start_time).total_seconds()


class ResourceInfo(BaseModel):
    """Model for static resource information"""
    url: HttpUrl
    local_path: str
    resource_type: str
    content_hash: Optional[str] = None
    size_bytes: Optional[int] = None
    
    class Config:
        json_encoders = {
            HttpUrl: str
        }


# Update forward references
NavigationItem.model_rebuild()