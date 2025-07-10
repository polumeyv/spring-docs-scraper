#!/usr/bin/env python3
"""
Minimal test scraper that completes quickly for demo purposes
"""
import asyncio
import json
from pathlib import Path
from datetime import datetime

async def create_test_data():
    """Create minimal test data for demonstration"""
    output_dir = Path('/app/docs/spring-docs')
    
    # Ensure directories exist
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / 'content').mkdir(exist_ok=True)
    (output_dir / 'static').mkdir(exist_ok=True)
    
    # Create minimal metadata
    metadata = {
        "scrape_date": datetime.now().isoformat(),
        "total_projects": 2,
        "projects": {
            "spring-boot": {
                "name": "spring-boot",
                "url": "https://spring.io/projects/spring-boot",
                "description": "Spring Boot makes it easy to create stand-alone applications",
                "versions": ["3.2.0", "3.1.0", "current"],
                "docs": {
                    "reference": "https://docs.spring.io/spring-boot/docs/current/reference/html/",
                    "api": "https://docs.spring.io/spring-boot/docs/current/api/"
                }
            },
            "spring-framework": {
                "name": "spring-framework",
                "url": "https://spring.io/projects/spring-framework",
                "description": "Core support for dependency injection and transaction management",
                "versions": ["6.1.0", "6.0.0", "current"],
                "docs": {
                    "reference": "https://docs.spring.io/spring-framework/reference/",
                    "api": "https://docs.spring.io/spring-framework/docs/current/api/"
                }
            }
        },
        "total_routes": 4,
        "total_static_resources": 10,
        "scrape_duration_seconds": 15.5
    }
    
    # Create routes
    routes = {
        "/spring-boot/reference": {
            "content": "/content/spring-boot-reference.json",
            "title": "Spring Boot Reference",
            "project": "spring-boot",
            "type": "reference"
        },
        "/spring-boot/api": {
            "content": "/content/spring-boot-api.json",
            "title": "Spring Boot API",
            "project": "spring-boot",
            "type": "api"
        },
        "/spring-framework/reference": {
            "content": "/content/spring-framework-reference.json",
            "title": "Spring Framework Reference",
            "project": "spring-framework",
            "type": "reference"
        },
        "/spring-framework/api": {
            "content": "/content/spring-framework-api.json",
            "title": "Spring Framework API",
            "project": "spring-framework",
            "type": "api"
        }
    }
    
    # Create sample content files
    sample_content = {
        "spring-boot-reference": {
            "title": "Spring Boot Reference Documentation",
            "content": "<h1>Spring Boot Reference</h1><p>Welcome to Spring Boot! This is a demo.</p>",
            "type": "reference",
            "project": "spring-boot"
        },
        "spring-boot-api": {
            "title": "Spring Boot API Documentation",
            "content": "<h1>Spring Boot API</h1><p>API documentation demo content.</p>",
            "type": "api", 
            "project": "spring-boot"
        },
        "spring-framework-reference": {
            "title": "Spring Framework Reference",
            "content": "<h1>Spring Framework Reference</h1><p>Core framework documentation demo.</p>",
            "type": "reference",
            "project": "spring-framework"
        },
        "spring-framework-api": {
            "title": "Spring Framework API",
            "content": "<h1>Spring Framework API</h1><p>Framework API documentation demo.</p>",
            "type": "api",
            "project": "spring-framework"
        }
    }
    
    # Write content files
    for filename, content in sample_content.items():
        with open(output_dir / 'content' / f'{filename}.json', 'w') as f:
            json.dump(content, f, indent=2)
    
    # Copy existing index.html if available or create a simple one
    existing_index = Path('/app/docs/spring-docs/index.html')
    if not existing_index.exists():
        # Create a simple index
        index_html = """<!DOCTYPE html>
<html>
<head>
    <title>Spring Documentation - Test</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .project { margin: 20px 0; padding: 20px; border: 1px solid #ddd; }
        h1 { color: #6db33f; }
    </style>
</head>
<body>
    <h1>Spring Documentation (Test Data)</h1>
    <p>This is test data created for demonstration purposes.</p>
    
    <div class="project">
        <h2>Spring Boot</h2>
        <p>Spring Boot makes it easy to create stand-alone applications</p>
        <a href="/content/spring-boot-reference.json">Reference</a> | 
        <a href="/content/spring-boot-api.json">API</a>
    </div>
    
    <div class="project">
        <h2>Spring Framework</h2>
        <p>Core support for dependency injection and transaction management</p>
        <a href="/content/spring-framework-reference.json">Reference</a> | 
        <a href="/content/spring-framework-api.json">API</a>
    </div>
    
    <hr>
    <p><small>Generated by async scraper test</small></p>
</body>
</html>"""
        with open(output_dir / 'index.html', 'w') as f:
            f.write(index_html)
    
    # Write metadata files
    with open(output_dir / 'metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2)
    
    with open(output_dir / 'routes.json', 'w') as f:
        json.dump(routes, f, indent=2)
    
    # Create summary
    summary = f"""Spring Documentation Test Summary
Date: {metadata['scrape_date']}
Duration: {metadata['scrape_duration_seconds']} seconds
Total Projects: {metadata['total_projects']}
Total Routes: {len(routes)}

This is test data for demonstration purposes.
The async scraper would normally create much more comprehensive documentation.
"""
    
    with open(output_dir / 'summary.txt', 'w') as f:
        f.write(summary)
    
    print("✅ Test data created successfully!")
    print(f"Files created in: {output_dir}")
    print("\nYou can now access the documentation at:")
    print("- http://localhost:8082 (main server)")
    print("- http://localhost:8083 (test server)")

if __name__ == "__main__":
    asyncio.run(create_test_data())