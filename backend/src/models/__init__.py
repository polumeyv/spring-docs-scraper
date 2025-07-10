"""
Models for async documentation scraper
"""
from .scraper_models import (
    DocType,
    ProjectModel,
    NavigationItem,
    ScrapedContent,
    RouteModel,
    ScrapeMetadata,
    ScrapeProgress,
    ResourceInfo
)

from .async_base import (
    AsyncScraperBase,
    AsyncResourceDownloader
)

__all__ = [
    'DocType',
    'ProjectModel',
    'NavigationItem',
    'ScrapedContent',
    'RouteModel',
    'ScrapeMetadata',
    'ScrapeProgress',
    'ResourceInfo',
    'AsyncScraperBase',
    'AsyncResourceDownloader'
]