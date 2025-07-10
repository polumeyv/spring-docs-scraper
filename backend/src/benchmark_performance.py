#!/usr/bin/env python3
"""
Performance benchmark comparing sync vs async scrapers
"""

import asyncio
import time
import psutil
import os
import sys
from datetime import datetime
from typing import Dict, Any, List
import json
import argparse
import subprocess
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spring_docs_scraper import SmartSpringDocsScraper
from async_spring_scraper_enhanced import AsyncSpringDocsScraperEnhanced


class PerformanceMetrics:
    """Track performance metrics during scraping"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.start_memory = None
        self.peak_memory = None
        self.cpu_samples = []
        self.memory_samples = []
        self.process = psutil.Process()
        self.monitoring = False
        self.monitor_task = None
    
    async def start_monitoring(self):
        """Start monitoring system resources"""
        self.start_time = time.time()
        self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.peak_memory = self.start_memory
        self.monitoring = True
        
        # Start monitoring task
        self.monitor_task = asyncio.create_task(self._monitor_resources())
    
    async def stop_monitoring(self):
        """Stop monitoring and calculate final metrics"""
        self.monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        self.end_time = time.time()
        
    async def _monitor_resources(self):
        """Monitor CPU and memory usage"""
        while self.monitoring:
            try:
                # CPU usage
                cpu_percent = self.process.cpu_percent(interval=None)
                self.cpu_samples.append(cpu_percent)
                
                # Memory usage
                memory_mb = self.process.memory_info().rss / 1024 / 1024
                self.memory_samples.append(memory_mb)
                self.peak_memory = max(self.peak_memory, memory_mb)
                
                await asyncio.sleep(1)  # Sample every second
            except (psutil.NoSuchProcess, asyncio.CancelledError):
                break
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics"""
        duration = self.end_time - self.start_time if self.end_time else 0
        
        return {
            'duration_seconds': duration,
            'start_memory_mb': self.start_memory,
            'peak_memory_mb': self.peak_memory,
            'memory_growth_mb': self.peak_memory - self.start_memory if self.start_memory else 0,
            'avg_cpu_percent': sum(self.cpu_samples) / len(self.cpu_samples) if self.cpu_samples else 0,
            'max_cpu_percent': max(self.cpu_samples) if self.cpu_samples else 0,
            'memory_samples': self.memory_samples,
            'cpu_samples': self.cpu_samples
        }


class BenchmarkRunner:
    """Run benchmarks for sync and async scrapers"""
    
    def __init__(self, output_base_dir: str = 'benchmark-results'):
        self.output_base_dir = Path(output_base_dir)
        self.output_base_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    def run_sync_benchmark(self, projects_limit: int = 5) -> Dict[str, Any]:
        """Run synchronous scraper benchmark"""
        print("\n=== Running Synchronous Scraper Benchmark ===")
        output_dir = self.output_base_dir / f"sync_{self.timestamp}"
        
        # Create a modified scraper that limits projects
        class LimitedSyncScraper(SmartSpringDocsScraper):
            def get_projects(self):
                super().get_projects()
                # Limit projects for benchmark
                project_names = list(self.projects.keys())[:projects_limit]
                self.projects = {name: self.projects[name] for name in project_names}
        
        metrics = PerformanceMetrics()
        
        # Start monitoring in a separate thread
        import threading
        monitor_thread = threading.Thread(target=self._sync_monitor, args=(metrics,))
        monitor_thread.start()
        
        try:
            # Run scraper
            scraper = LimitedSyncScraper(output_dir=str(output_dir), clean=True)
            start_time = time.time()
            metrics.start_time = start_time
            metrics.start_memory = metrics.process.memory_info().rss / 1024 / 1024
            metrics.monitoring = True
            
            scraper.scrape_all()
            
            end_time = time.time()
            metrics.end_time = end_time
            
            # Get scraper stats
            with open(output_dir / 'metadata.json', 'r') as f:
                metadata = json.load(f)
            
            with open(output_dir / 'routes.json', 'r') as f:
                routes = json.load(f)
            
            result = {
                'type': 'synchronous',
                'projects_scraped': metadata['total_projects'],
                'routes_created': len(routes),
                'metrics': metrics.get_metrics()
            }
            
        finally:
            metrics.monitoring = False
            monitor_thread.join()
        
        return result
    
    def _sync_monitor(self, metrics: PerformanceMetrics):
        """Monitor resources for sync scraper (runs in thread)"""
        while metrics.monitoring:
            try:
                # CPU usage
                cpu_percent = metrics.process.cpu_percent(interval=None)
                metrics.cpu_samples.append(cpu_percent)
                
                # Memory usage
                memory_mb = metrics.process.memory_info().rss / 1024 / 1024
                metrics.memory_samples.append(memory_mb)
                metrics.peak_memory = max(metrics.peak_memory, memory_mb)
                
                time.sleep(1)
            except:
                break
    
    async def run_async_benchmark(self, projects_limit: int = 5, 
                                 max_connections: int = 20,
                                 rate_limit: float = 10.0) -> Dict[str, Any]:
        """Run asynchronous scraper benchmark"""
        print("\n=== Running Asynchronous Scraper Benchmark ===")
        output_dir = self.output_base_dir / f"async_{self.timestamp}"
        
        # Create a modified scraper that limits projects
        class LimitedAsyncScraper(AsyncSpringDocsScraperEnhanced):
            async def get_projects(self):
                await super().get_projects()
                # Limit projects for benchmark
                project_names = list(self.projects.keys())[:projects_limit]
                self.projects = {name: self.projects[name] for name in project_names}
        
        metrics = PerformanceMetrics()
        await metrics.start_monitoring()
        
        try:
            # Run scraper
            scraper = LimitedAsyncScraper(
                output_dir=str(output_dir),
                clean=True,
                max_connections=max_connections,
                rate_limit=rate_limit,
                use_rich_progress=False,  # Disable for benchmark
                save_checkpoint=False
            )
            
            await scraper.scrape_all()
            
            # Get scraper stats
            with open(output_dir / 'metadata.json', 'r') as f:
                metadata = json.load(f)
            
            with open(output_dir / 'routes.json', 'r') as f:
                routes = json.load(f)
            
            result = {
                'type': 'asynchronous',
                'projects_scraped': metadata['total_projects'],
                'routes_created': len(routes),
                'scrape_duration': metadata.get('scrape_duration_seconds', 0),
                'metrics': metrics.get_metrics()
            }
            
        finally:
            await metrics.stop_monitoring()
        
        return result
    
    def compare_results(self, sync_result: Dict[str, Any], async_result: Dict[str, Any]) -> Dict[str, Any]:
        """Compare benchmark results"""
        sync_metrics = sync_result['metrics']
        async_metrics = async_result['metrics']
        
        comparison = {
            'summary': {
                'sync_duration': sync_metrics['duration_seconds'],
                'async_duration': async_metrics['duration_seconds'],
                'speedup': sync_metrics['duration_seconds'] / async_metrics['duration_seconds'] if async_metrics['duration_seconds'] > 0 else 0,
                'sync_peak_memory': sync_metrics['peak_memory_mb'],
                'async_peak_memory': async_metrics['peak_memory_mb'],
                'memory_improvement': (sync_metrics['peak_memory_mb'] - async_metrics['peak_memory_mb']) / sync_metrics['peak_memory_mb'] * 100 if sync_metrics['peak_memory_mb'] > 0 else 0,
                'sync_avg_cpu': sync_metrics['avg_cpu_percent'],
                'async_avg_cpu': async_metrics['avg_cpu_percent']
            },
            'details': {
                'sync': sync_result,
                'async': async_result
            }
        }
        
        return comparison
    
    def save_results(self, comparison: Dict[str, Any]):
        """Save benchmark results"""
        results_file = self.output_base_dir / f"benchmark_results_{self.timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(comparison, f, indent=2)
        
        # Create summary report
        summary = comparison['summary']
        report = f"""
Performance Benchmark Report
============================
Timestamp: {self.timestamp}

Results Summary:
---------------
Synchronous Duration: {summary['sync_duration']:.2f} seconds
Asynchronous Duration: {summary['async_duration']:.2f} seconds
Performance Improvement: {summary['speedup']:.2f}x faster

Memory Usage:
------------
Sync Peak Memory: {summary['sync_peak_memory']:.2f} MB
Async Peak Memory: {summary['async_peak_memory']:.2f} MB
Memory Improvement: {summary['memory_improvement']:.1f}% less memory

CPU Usage:
----------
Sync Average CPU: {summary['sync_avg_cpu']:.1f}%
Async Average CPU: {summary['async_avg_cpu']:.1f}%

Conclusion:
----------
The asynchronous implementation is {summary['speedup']:.2f}x faster than the synchronous version.
"""
        
        if summary['memory_improvement'] > 0:
            report += f"It also uses {summary['memory_improvement']:.1f}% less memory at peak.\n"
        else:
            report += f"However, it uses {-summary['memory_improvement']:.1f}% more memory at peak.\n"
        
        report_file = self.output_base_dir / f"benchmark_report_{self.timestamp}.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        
        print(report)
        print(f"\nDetailed results saved to: {results_file}")
        print(f"Report saved to: {report_file}")
    
    def create_visualization(self, comparison: Dict[str, Any]):
        """Create visualization of benchmark results (requires matplotlib)"""
        try:
            import matplotlib.pyplot as plt
            
            # Create figure with subplots
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
            fig.suptitle('Sync vs Async Scraper Performance Comparison', fontsize=16)
            
            summary = comparison['summary']
            
            # 1. Duration comparison
            methods = ['Sync', 'Async']
            durations = [summary['sync_duration'], summary['async_duration']]
            colors = ['#ff7f0e', '#2ca02c']
            
            bars1 = ax1.bar(methods, durations, color=colors)
            ax1.set_ylabel('Duration (seconds)')
            ax1.set_title('Execution Time Comparison')
            
            # Add value labels on bars
            for bar, duration in zip(bars1, durations):
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height,
                        f'{duration:.1f}s', ha='center', va='bottom')
            
            # 2. Memory usage comparison
            memory_data = [summary['sync_peak_memory'], summary['async_peak_memory']]
            bars2 = ax2.bar(methods, memory_data, color=colors)
            ax2.set_ylabel('Peak Memory (MB)')
            ax2.set_title('Memory Usage Comparison')
            
            for bar, memory in zip(bars2, memory_data):
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height,
                        f'{memory:.1f}MB', ha='center', va='bottom')
            
            # 3. CPU usage over time
            sync_cpu = comparison['details']['sync']['metrics']['cpu_samples']
            async_cpu = comparison['details']['async']['metrics']['cpu_samples']
            
            ax3.plot(sync_cpu, label='Sync', color=colors[0], linewidth=2)
            ax3.plot(async_cpu, label='Async', color=colors[1], linewidth=2)
            ax3.set_xlabel('Time (seconds)')
            ax3.set_ylabel('CPU Usage (%)')
            ax3.set_title('CPU Usage Over Time')
            ax3.legend()
            ax3.grid(True, alpha=0.3)
            
            # 4. Memory usage over time
            sync_memory = comparison['details']['sync']['metrics']['memory_samples']
            async_memory = comparison['details']['async']['metrics']['memory_samples']
            
            ax4.plot(sync_memory, label='Sync', color=colors[0], linewidth=2)
            ax4.plot(async_memory, label='Async', color=colors[1], linewidth=2)
            ax4.set_xlabel('Time (seconds)')
            ax4.set_ylabel('Memory Usage (MB)')
            ax4.set_title('Memory Usage Over Time')
            ax4.legend()
            ax4.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # Save plot
            plot_file = self.output_base_dir / f"benchmark_plot_{self.timestamp}.png"
            plt.savefig(plot_file, dpi=150, bbox_inches='tight')
            print(f"\nVisualization saved to: {plot_file}")
            
            # Show plot if not in headless environment
            if os.environ.get('DISPLAY'):
                plt.show()
            
        except ImportError:
            print("\nMatplotlib not available. Skipping visualization.")


async def main():
    parser = argparse.ArgumentParser(description='Benchmark sync vs async scrapers')
    parser.add_argument('--projects', type=int, default=5,
                       help='Number of projects to scrape (default: 5)')
    parser.add_argument('--max-connections', type=int, default=20,
                       help='Max connections for async scraper (default: 20)')
    parser.add_argument('--rate-limit', type=float, default=10.0,
                       help='Rate limit for async scraper (default: 10.0)')
    parser.add_argument('--visualize', action='store_true',
                       help='Create visualization of results')
    args = parser.parse_args()
    
    runner = BenchmarkRunner()
    
    print(f"Running benchmark with {args.projects} projects...")
    
    # Run sync benchmark
    sync_result = runner.run_sync_benchmark(projects_limit=args.projects)
    
    # Run async benchmark
    async_result = await runner.run_async_benchmark(
        projects_limit=args.projects,
        max_connections=args.max_connections,
        rate_limit=args.rate_limit
    )
    
    # Compare results
    comparison = runner.compare_results(sync_result, async_result)
    
    # Save results
    runner.save_results(comparison)
    
    # Create visualization if requested
    if args.visualize:
        runner.create_visualization(comparison)


if __name__ == "__main__":
    asyncio.run(main())