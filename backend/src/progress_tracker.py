"""
Progress tracking with rich console for async scraping
"""
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from rich.console import Console
from rich.progress import (
    Progress, SpinnerColumn, TextColumn, BarColumn, 
    TimeElapsedColumn, TimeRemainingColumn, MofNCompleteColumn
)
from rich.table import Table
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.text import Text


class ProgressTracker:
    """Progress tracker with rich console display"""
    
    def __init__(self):
        self.console = Console()
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=self.console,
            transient=False
        )
        
        # Task IDs
        self.main_task = None
        self.project_task = None
        self.url_task = None
        self.resource_task = None
        
        # Statistics
        self.stats = {
            'start_time': None,
            'projects_total': 0,
            'projects_completed': 0,
            'urls_total': 0,
            'urls_completed': 0,
            'urls_failed': 0,
            'resources_downloaded': 0,
            'bytes_downloaded': 0,
            'current_project': None,
            'current_url': None
        }
        
        self.live = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.stop()
    
    async def start(self):
        """Start progress tracking"""
        self.stats['start_time'] = datetime.now()
        self.live = Live(self.create_layout(), console=self.console, refresh_per_second=4)
        self.live.start()
        
        # Create main progress task
        self.main_task = self.progress.add_task(
            "[cyan]Overall Progress", 
            total=100
        )
    
    async def stop(self):
        """Stop progress tracking"""
        if self.live:
            self.live.stop()
        
        # Show final summary
        self.show_summary()
    
    def create_layout(self) -> Layout:
        """Create the display layout"""
        layout = Layout()
        
        # Create sections
        layout.split(
            Layout(name="header", size=3),
            Layout(name="progress", size=10),
            Layout(name="stats", size=12),
            Layout(name="current", size=5)
        )
        
        # Header
        header_text = Text("Spring Documentation Async Scraper", style="bold cyan", justify="center")
        layout["header"].update(Panel(header_text))
        
        # Progress bars
        layout["progress"].update(Panel(self.progress, title="Progress", border_style="green"))
        
        # Statistics table
        layout["stats"].update(self.create_stats_panel())
        
        # Current activity
        layout["current"].update(self.create_current_panel())
        
        return layout
    
    def create_stats_panel(self) -> Panel:
        """Create statistics panel"""
        table = Table(show_header=False, padding=1, expand=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        # Calculate elapsed time
        elapsed = datetime.now() - self.stats['start_time'] if self.stats['start_time'] else None
        elapsed_str = str(elapsed).split('.')[0] if elapsed else "00:00:00"
        
        # Calculate rates
        elapsed_seconds = elapsed.total_seconds() if elapsed and elapsed.total_seconds() > 0 else 1
        url_rate = self.stats['urls_completed'] / elapsed_seconds
        mb_downloaded = self.stats['bytes_downloaded'] / (1024 * 1024)
        
        # Add rows
        table.add_row("Elapsed Time", elapsed_str)
        table.add_row("Projects", f"{self.stats['projects_completed']} / {self.stats['projects_total']}")
        table.add_row("URLs Processed", f"{self.stats['urls_completed']} / {self.stats['urls_total']}")
        table.add_row("URLs Failed", str(self.stats['urls_failed']))
        table.add_row("Processing Rate", f"{url_rate:.1f} URLs/sec")
        table.add_row("Resources Downloaded", str(self.stats['resources_downloaded']))
        table.add_row("Data Downloaded", f"{mb_downloaded:.2f} MB")
        
        return Panel(table, title="Statistics", border_style="blue")
    
    def create_current_panel(self) -> Panel:
        """Create current activity panel"""
        lines = []
        
        if self.stats['current_project']:
            lines.append(f"[yellow]Project:[/yellow] {self.stats['current_project']}")
        
        if self.stats['current_url']:
            # Truncate long URLs
            url = self.stats['current_url']
            if len(url) > 80:
                url = url[:77] + "..."
            lines.append(f"[yellow]URL:[/yellow] {url}")
        
        content = "\n".join(lines) if lines else "[dim]Waiting for activity...[/dim]"
        
        return Panel(content, title="Current Activity", border_style="yellow")
    
    def update_layout(self):
        """Update the live display"""
        if self.live:
            self.live.update(self.create_layout())
    
    def set_projects_total(self, total: int):
        """Set total number of projects"""
        self.stats['projects_total'] = total
        if self.project_task is None:
            self.project_task = self.progress.add_task(
                "[green]Projects", 
                total=total
            )
        self.update_layout()
    
    def update_project(self, project_name: str):
        """Update current project being processed"""
        self.stats['current_project'] = project_name
        self.stats['projects_completed'] += 1
        
        if self.project_task is not None:
            self.progress.update(self.project_task, advance=1)
        
        # Update overall progress
        if self.stats['projects_total'] > 0:
            project_progress = (self.stats['projects_completed'] / self.stats['projects_total']) * 30
            self.progress.update(self.main_task, completed=project_progress)
        
        self.update_layout()
    
    def set_urls_total(self, total: int):
        """Set total number of URLs to process"""
        self.stats['urls_total'] = total
        if self.url_task is None:
            self.url_task = self.progress.add_task(
                "[yellow]URLs", 
                total=total
            )
        else:
            self.progress.update(self.url_task, total=total)
        self.update_layout()
    
    def update_url(self, url: str, success: bool = True):
        """Update URL processing status"""
        self.stats['current_url'] = url
        
        if success:
            self.stats['urls_completed'] += 1
        else:
            self.stats['urls_failed'] += 1
        
        if self.url_task is not None:
            self.progress.update(self.url_task, advance=1)
        
        # Update overall progress (URLs are 60% of total progress)
        if self.stats['urls_total'] > 0:
            url_progress = (self.stats['urls_completed'] / self.stats['urls_total']) * 60
            project_progress = (self.stats['projects_completed'] / self.stats['projects_total']) * 30 if self.stats['projects_total'] > 0 else 0
            self.progress.update(self.main_task, completed=30 + url_progress)
        
        self.update_layout()
    
    def add_resource_download(self, size_bytes: int):
        """Track resource download"""
        self.stats['resources_downloaded'] += 1
        self.stats['bytes_downloaded'] += size_bytes
        
        if self.resource_task is None:
            self.resource_task = self.progress.add_task(
                "[magenta]Resources", 
                total=None  # Indeterminate
            )
        
        self.progress.update(
            self.resource_task, 
            description=f"[magenta]Resources ({self.stats['resources_downloaded']} files)"
        )
        
        self.update_layout()
    
    def update_queue_stats(self, queue_stats: Dict[str, Any]):
        """Update statistics from queue"""
        if 'total_queued' in queue_stats:
            self.set_urls_total(queue_stats['total_queued'])
        
        if 'total_processed' in queue_stats:
            processed_diff = queue_stats['total_processed'] - (self.stats['urls_completed'] + self.stats['urls_failed'])
            for _ in range(processed_diff):
                self.update_url("", success=True)
        
        if 'total_failed' in queue_stats:
            failed_diff = queue_stats['total_failed'] - self.stats['urls_failed']
            for _ in range(failed_diff):
                self.update_url("", success=False)
    
    def show_summary(self):
        """Show final summary"""
        elapsed = datetime.now() - self.stats['start_time'] if self.stats['start_time'] else None
        elapsed_str = str(elapsed).split('.')[0] if elapsed else "00:00:00"
        
        # Create summary table
        table = Table(title="Scraping Summary", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")
        
        table.add_row("Total Time", elapsed_str)
        table.add_row("Projects Scraped", f"{self.stats['projects_completed']} / {self.stats['projects_total']}")
        table.add_row("URLs Processed", str(self.stats['urls_completed']))
        table.add_row("URLs Failed", str(self.stats['urls_failed']))
        table.add_row("Success Rate", f"{(self.stats['urls_completed'] / max(self.stats['urls_completed'] + self.stats['urls_failed'], 1) * 100):.1f}%")
        table.add_row("Resources Downloaded", str(self.stats['resources_downloaded']))
        table.add_row("Total Data", f"{self.stats['bytes_downloaded'] / (1024 * 1024):.2f} MB")
        
        if elapsed and elapsed.total_seconds() > 0:
            table.add_row("Average Speed", f"{self.stats['urls_completed'] / elapsed.total_seconds():.2f} URLs/sec")
        
        self.console.print("\n")
        self.console.print(table)
        self.console.print("\n[bold green]✓ Scraping completed![/bold green]\n")


class SimpleProgressTracker:
    """Simple progress tracker for environments without rich console"""
    
    def __init__(self):
        self.stats = {
            'start_time': datetime.now(),
            'projects_completed': 0,
            'urls_completed': 0,
            'urls_failed': 0
        }
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    
    async def start(self):
        print("Starting async scraping...")
    
    async def stop(self):
        elapsed = datetime.now() - self.stats['start_time']
        print(f"\nCompleted in {elapsed}")
        print(f"URLs processed: {self.stats['urls_completed']}")
        print(f"URLs failed: {self.stats['urls_failed']}")
    
    def set_projects_total(self, total: int):
        print(f"Found {total} projects to scrape")
    
    def update_project(self, project_name: str):
        self.stats['projects_completed'] += 1
        print(f"Processing project: {project_name}")
    
    def set_urls_total(self, total: int):
        print(f"Queued {total} URLs for processing")
    
    def update_url(self, url: str, success: bool = True):
        if success:
            self.stats['urls_completed'] += 1
        else:
            self.stats['urls_failed'] += 1
        
        if self.stats['urls_completed'] % 10 == 0:
            print(f"Progress: {self.stats['urls_completed']} URLs processed")
    
    def add_resource_download(self, size_bytes: int):
        pass
    
    def update_queue_stats(self, queue_stats: Dict[str, Any]):
        pass
    
    def show_summary(self):
        pass


@asynccontextmanager
async def create_progress_tracker(use_rich: bool = True):
    """Create appropriate progress tracker based on environment"""
    if use_rich:
        try:
            tracker = ProgressTracker()
        except Exception:
            # Fallback to simple tracker if rich fails
            tracker = SimpleProgressTracker()
    else:
        tracker = SimpleProgressTracker()
    
    await tracker.start()
    try:
        yield tracker
    finally:
        await tracker.stop()