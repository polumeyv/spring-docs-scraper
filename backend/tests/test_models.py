"""
Tests for Pydantic models
"""
import pytest
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models import (
    DocType, ProjectModel, NavigationItem, ScrapedContent,
    RouteModel, ScrapeMetadata, ScrapeProgress, ResourceInfo
)


class TestDocType:
    """Test DocType enum"""
    
    def test_doc_type_values(self):
        """Test DocType enum values"""
        assert DocType.REFERENCE.value == "reference"
        assert DocType.API.value == "api"
        assert DocType.GUIDE.value == "guide"


class TestProjectModel:
    """Test ProjectModel"""
    
    def test_project_model_creation(self):
        """Test creating ProjectModel"""
        project = ProjectModel(
            name="spring-boot",
            url="https://spring.io/projects/spring-boot",
            description="Spring Boot makes it easy to create stand-alone applications"
        )
        
        assert project.name == "spring-boot"
        assert str(project.url) == "https://spring.io/projects/spring-boot"
        assert project.description == "Spring Boot makes it easy to create stand-alone applications"
        assert project.versions == []
        assert project.docs == {}
    
    def test_project_model_with_data(self):
        """Test ProjectModel with versions and docs"""
        project = ProjectModel(
            name="spring-framework",
            url="https://spring.io/projects/spring-framework",
            versions=["6.0.0", "5.3.0", "current"],
            docs={
                DocType.REFERENCE: "https://docs.spring.io/spring-framework/docs/current/reference/html/",
                DocType.API: "https://docs.spring.io/spring-framework/docs/current/api/"
            }
        )
        
        assert len(project.versions) == 3
        assert "current" in project.versions
        assert DocType.REFERENCE in project.docs
        assert DocType.API in project.docs
    
    def test_project_model_json_serialization(self):
        """Test JSON serialization"""
        project = ProjectModel(
            name="spring-security",
            url="https://spring.io/projects/spring-security",
            docs={DocType.REFERENCE: "https://docs.spring.io/spring-security/reference/"}
        )
        
        json_data = project.json()
        assert "spring-security" in json_data
        
        # Test dict conversion
        dict_data = project.dict()
        assert dict_data['name'] == "spring-security"
        assert dict_data['url'] == "https://spring.io/projects/spring-security"
        assert dict_data['docs'] == {"reference": "https://docs.spring.io/spring-security/reference/"}


class TestNavigationItem:
    """Test NavigationItem model"""
    
    def test_navigation_item_simple(self):
        """Test simple navigation item"""
        nav = NavigationItem(
            text="Getting Started",
            href="/getting-started.html"
        )
        
        assert nav.text == "Getting Started"
        assert nav.href == "/getting-started.html"
        assert nav.children == []
    
    def test_navigation_item_with_children(self):
        """Test navigation item with children"""
        child1 = NavigationItem(text="Installation", href="/install.html")
        child2 = NavigationItem(text="Configuration", href="/config.html")
        
        parent = NavigationItem(
            text="Documentation",
            href="/docs/",
            children=[child1, child2]
        )
        
        assert len(parent.children) == 2
        assert parent.children[0].text == "Installation"
        assert parent.children[1].text == "Configuration"
    
    def test_navigation_item_recursive(self):
        """Test recursive navigation structure"""
        subchild = NavigationItem(text="Advanced Config", href="/config/advanced.html")
        child = NavigationItem(
            text="Configuration",
            href="/config/",
            children=[subchild]
        )
        parent = NavigationItem(
            text="Docs",
            href="/docs/",
            children=[child]
        )
        
        assert parent.children[0].children[0].text == "Advanced Config"


class TestScrapedContent:
    """Test ScrapedContent model"""
    
    def test_scraped_content_creation(self):
        """Test creating ScrapedContent"""
        content = ScrapedContent(
            title="Spring Boot Reference",
            content="<article>Content here</article>",
            type=DocType.REFERENCE,
            project="spring-boot"
        )
        
        assert content.title == "Spring Boot Reference"
        assert content.content == "<article>Content here</article>"
        assert content.type == DocType.REFERENCE
        assert content.project == "spring-boot"
        assert content.nav is None
        assert isinstance(content.scraped_at, datetime)
    
    def test_scraped_content_with_nav(self):
        """Test ScrapedContent with navigation"""
        nav = [
            NavigationItem(text="Overview", href="/overview.html"),
            NavigationItem(text="Getting Started", href="/start.html")
        ]
        
        content = ScrapedContent(
            title="Documentation",
            content="<div>Content</div>",
            nav=nav,
            type=DocType.REFERENCE,
            project="spring-framework"
        )
        
        assert len(content.nav) == 2
        assert content.nav[0].text == "Overview"
    
    def test_scraped_content_json_serialization(self):
        """Test JSON serialization with datetime"""
        content = ScrapedContent(
            title="API Docs",
            content="<main>API content</main>",
            type=DocType.API,
            project="spring-security"
        )
        
        json_str = content.json()
        assert '"scraped_at"' in json_str
        assert '"type": "api"' in json_str
        
        # Test dict conversion
        dict_data = content.dict()
        assert isinstance(dict_data['scraped_at'], datetime)


class TestRouteModel:
    """Test RouteModel"""
    
    def test_route_model_creation(self):
        """Test creating RouteModel"""
        route = RouteModel(
            content="/content/spring-boot-reference-abc123.json",
            title="Spring Boot Reference Documentation",
            project="spring-boot",
            type=DocType.REFERENCE
        )
        
        assert route.content == "/content/spring-boot-reference-abc123.json"
        assert route.title == "Spring Boot Reference Documentation"
        assert route.project == "spring-boot"
        assert route.type == DocType.REFERENCE
    
    def test_route_model_json_serialization(self):
        """Test JSON serialization"""
        route = RouteModel(
            content="/content/api-docs.json",
            title="API Documentation",
            project="spring-framework",
            type=DocType.API
        )
        
        dict_data = route.dict()
        assert dict_data['type'] == "api"


class TestScrapeMetadata:
    """Test ScrapeMetadata model"""
    
    def test_scrape_metadata_creation(self):
        """Test creating ScrapeMetadata"""
        metadata = ScrapeMetadata()
        
        assert isinstance(metadata.scrape_date, datetime)
        assert metadata.total_projects == 0
        assert metadata.projects == {}
        assert metadata.total_routes == 0
        assert metadata.total_static_resources == 0
        assert metadata.scrape_duration_seconds is None
    
    def test_scrape_metadata_with_data(self):
        """Test ScrapeMetadata with projects"""
        project1 = ProjectModel(
            name="spring-boot",
            url="https://spring.io/projects/spring-boot"
        )
        project2 = ProjectModel(
            name="spring-security",
            url="https://spring.io/projects/spring-security"
        )
        
        metadata = ScrapeMetadata(
            total_projects=2,
            projects={
                "spring-boot": project1,
                "spring-security": project2
            },
            total_routes=10,
            total_static_resources=50,
            scrape_duration_seconds=120.5
        )
        
        assert metadata.total_projects == 2
        assert len(metadata.projects) == 2
        assert metadata.total_routes == 10
        assert metadata.scrape_duration_seconds == 120.5
    
    def test_scrape_metadata_json_serialization(self):
        """Test JSON serialization"""
        metadata = ScrapeMetadata(
            total_projects=1,
            scrape_duration_seconds=60.0
        )
        
        json_str = metadata.json()
        assert '"scrape_date"' in json_str
        assert '"total_projects": 1' in json_str


class TestScrapeProgress:
    """Test ScrapeProgress model"""
    
    def test_scrape_progress_creation(self):
        """Test creating ScrapeProgress"""
        progress = ScrapeProgress()
        
        assert progress.total_urls == 0
        assert progress.processed_urls == 0
        assert progress.failed_urls == 0
        assert progress.current_project is None
        assert progress.current_action is None
        assert isinstance(progress.start_time, datetime)
    
    def test_scrape_progress_percentage(self):
        """Test percentage calculation"""
        progress = ScrapeProgress(
            total_urls=100,
            processed_urls=25,
            failed_urls=5
        )
        
        assert progress.percentage == 25.0
        
        # Test edge case
        progress_empty = ScrapeProgress()
        assert progress_empty.percentage == 0.0
    
    def test_scrape_progress_elapsed_seconds(self):
        """Test elapsed time calculation"""
        progress = ScrapeProgress()
        
        # Should have some elapsed time
        import time
        time.sleep(0.1)
        
        assert progress.elapsed_seconds > 0.1
    
    def test_scrape_progress_with_current_state(self):
        """Test progress with current state"""
        progress = ScrapeProgress(
            total_urls=50,
            processed_urls=10,
            failed_urls=2,
            current_project="spring-boot",
            current_action="Scraping reference documentation"
        )
        
        assert progress.current_project == "spring-boot"
        assert progress.current_action == "Scraping reference documentation"
        assert progress.percentage == 20.0


class TestResourceInfo:
    """Test ResourceInfo model"""
    
    def test_resource_info_creation(self):
        """Test creating ResourceInfo"""
        resource = ResourceInfo(
            url="https://docs.spring.io/css/main.css",
            local_path="static/css/main.css",
            resource_type="css"
        )
        
        assert str(resource.url) == "https://docs.spring.io/css/main.css"
        assert resource.local_path == "static/css/main.css"
        assert resource.resource_type == "css"
        assert resource.content_hash is None
        assert resource.size_bytes is None
    
    def test_resource_info_with_metadata(self):
        """Test ResourceInfo with metadata"""
        resource = ResourceInfo(
            url="https://docs.spring.io/js/app.js",
            local_path="static/js/app.js",
            resource_type="js",
            content_hash="abc123def456",
            size_bytes=1024
        )
        
        assert resource.content_hash == "abc123def456"
        assert resource.size_bytes == 1024
    
    def test_resource_info_json_serialization(self):
        """Test JSON serialization"""
        resource = ResourceInfo(
            url="https://docs.spring.io/img/logo.png",
            local_path="static/img/logo.png",
            resource_type="img",
            size_bytes=5000
        )
        
        dict_data = resource.dict()
        assert dict_data['url'] == "https://docs.spring.io/img/logo.png"
        assert dict_data['size_bytes'] == 5000


if __name__ == '__main__':
    pytest.main([__file__, '-v'])