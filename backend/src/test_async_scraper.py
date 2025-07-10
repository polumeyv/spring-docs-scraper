#!/usr/bin/env python3
"""
Test version of async scraper with limited projects for quick testing
"""
import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from async_spring_scraper_enhanced import AsyncSpringDocsScraperEnhanced


class TestAsyncScraper(AsyncSpringDocsScraperEnhanced):
    """Test scraper that limits projects for quick testing"""
    
    def __init__(self, max_projects=3, **kwargs):
        super().__init__(**kwargs)
        self.max_projects = max_projects
    
    async def get_projects(self):
        """Get limited number of projects for testing"""
        # Call parent method
        await super().get_projects()
        
        # Limit projects
        if len(self.projects) > self.max_projects:
            project_names = list(self.projects.keys())[:self.max_projects]
            self.projects = {name: self.projects[name] for name in project_names}
            self.logger.info(f"Limited to {self.max_projects} projects for testing")


async def main():
    import argparse
    parser = argparse.ArgumentParser(description='Test async Spring documentation scraper')
    parser.add_argument('--projects', type=int, default=3,
                        help='Number of projects to scrape (default: 3)')
    parser.add_argument('--clean', action='store_true', 
                        help='Clean existing documentation before scraping')
    parser.add_argument('--max-connections', type=int, default=10,
                        help='Maximum concurrent connections (default: 10)')
    parser.add_argument('--rate-limit', type=float, default=5.0,
                        help='Requests per second (default: 5.0)')
    parser.add_argument('--max-workers', type=int, default=5,
                        help='Maximum concurrent workers (default: 5)')
    parser.add_argument('--no-rich', action='store_true',
                        help='Disable rich console progress display')
    args = parser.parse_args()
    
    scraper = TestAsyncScraper(
        max_projects=args.projects,
        clean=args.clean,
        max_connections=args.max_connections,
        rate_limit=args.rate_limit,
        max_workers=args.max_workers,
        use_rich_progress=not args.no_rich,
        save_checkpoint=False,  # Disable for testing
        output_dir='/app/docs/spring-docs'  # Use subdirectory in Docker volume
    )
    
    try:
        await scraper.scrape_all()
    except KeyboardInterrupt:
        print("\nTest scraping interrupted by user")
    except Exception as e:
        print(f"\nError during test scraping: {e}")
        raise
    
    print(f"\nTest scraping complete! Scraped {len(scraper.projects)} projects.")
    print("Check http://localhost:8082 to view the results.")


if __name__ == "__main__":
    asyncio.run(main())