"""
UFDR Analysis Tool - Prometheus Metrics Collector
=================================================

Exports application, system, and business metrics in Prometheus format.

Metrics Categories:
- Application metrics (requests, errors, latency)
- System metrics (CPU, memory, disk)
- Business metrics (cases processed, entities extracted, linkages found)
- Database metrics (Neo4j queries, vector searches)

Endpoint: /metrics (Prometheus scrape endpoint)
"""

import time
import psutil
import platform
from datetime import datetime
from typing import Dict, Optional
from collections import defaultdict
from threading import Lock
import logging

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Collects and exposes metrics in Prometheus format.
    
    Thread-safe singleton for application-wide metric collection.
    """
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.start_time = time.time()
        
        # Counter metrics
        self.counters = defaultdict(int)
        
        # Gauge metrics
        self.gauges = defaultdict(float)
        
        # Histogram metrics (for latency)
        self.histograms = defaultdict(list)
        
        # Business metrics
        self.business_metrics = {
            'cases_processed': 0,
            'entities_extracted': 0,
            'cross_case_links_found': 0,
            'alerts_generated': 0,
            'queries_executed': 0,
            'exports_generated': 0
        }
        
        # System info
        self.system_info = {
            'platform': platform.system(),
            'python_version': platform.python_version(),
            'cpu_count': psutil.cpu_count(),
            'hostname': platform.node()
        }
        
        logger.info("Metrics collector initialized")
    
    # ============================================================
    # Counter Methods
    # ============================================================
    
    def increment_counter(self, name: str, value: int = 1, labels: Optional[Dict] = None):
        """Increment a counter metric."""
        key = self._make_key(name, labels)
        with self._lock:
            self.counters[key] += value
    
    def get_counter(self, name: str, labels: Optional[Dict] = None) -> int:
        """Get current counter value."""
        key = self._make_key(name, labels)
        return self.counters.get(key, 0)
    
    # ============================================================
    # Gauge Methods
    # ============================================================
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict] = None):
        """Set a gauge metric."""
        key = self._make_key(name, labels)
        with self._lock:
            self.gauges[key] = value
    
    def increment_gauge(self, name: str, value: float = 1.0, labels: Optional[Dict] = None):
        """Increment a gauge metric."""
        key = self._make_key(name, labels)
        with self._lock:
            self.gauges[key] = self.gauges.get(key, 0.0) + value
    
    def get_gauge(self, name: str, labels: Optional[Dict] = None) -> float:
        """Get current gauge value."""
        key = self._make_key(name, labels)
        return self.gauges.get(key, 0.0)
    
    # ============================================================
    # Histogram Methods (for latency tracking)
    # ============================================================
    
    def observe_histogram(self, name: str, value: float, labels: Optional[Dict] = None):
        """Record a histogram observation."""
        key = self._make_key(name, labels)
        with self._lock:
            self.histograms[key].append(value)
            # Keep only last 1000 observations to prevent memory growth
            if len(self.histograms[key]) > 1000:
                self.histograms[key] = self.histograms[key][-1000:]
    
    def get_histogram_stats(self, name: str, labels: Optional[Dict] = None) -> Dict:
        """Get histogram statistics (count, sum, quantiles)."""
        key = self._make_key(name, labels)
        values = self.histograms.get(key, [])
        
        if not values:
            return {'count': 0, 'sum': 0.0, 'p50': 0.0, 'p95': 0.0, 'p99': 0.0}
        
        sorted_values = sorted(values)
        count = len(sorted_values)
        
        return {
            'count': count,
            'sum': sum(sorted_values),
            'p50': sorted_values[int(count * 0.5)] if count > 0 else 0.0,
            'p95': sorted_values[int(count * 0.95)] if count > 0 else 0.0,
            'p99': sorted_values[int(count * 0.99)] if count > 0 else 0.0
        }
    
    # ============================================================
    # Business Metrics
    # ============================================================
    
    def record_case_processed(self):
        """Record a case being processed."""
        with self._lock:
            self.business_metrics['cases_processed'] += 1
    
    def record_entities_extracted(self, count: int):
        """Record entities extracted from a case."""
        with self._lock:
            self.business_metrics['entities_extracted'] += count
    
    def record_cross_case_link_found(self):
        """Record a cross-case linkage found."""
        with self._lock:
            self.business_metrics['cross_case_links_found'] += 1
    
    def record_alert_generated(self):
        """Record an alert being generated."""
        with self._lock:
            self.business_metrics['alerts_generated'] += 1
    
    def record_query_executed(self):
        """Record a query execution."""
        with self._lock:
            self.business_metrics['queries_executed'] += 1
    
    def record_export_generated(self):
        """Record an export being generated."""
        with self._lock:
            self.business_metrics['exports_generated'] += 1
    
    # ============================================================
    # System Metrics
    # ============================================================
    
    def collect_system_metrics(self):
        """Collect current system metrics."""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.set_gauge('system_cpu_usage_percent', cpu_percent)
            
            # Memory
            memory = psutil.virtual_memory()
            self.set_gauge('system_memory_usage_bytes', memory.used)
            self.set_gauge('system_memory_total_bytes', memory.total)
            self.set_gauge('system_memory_percent', memory.percent)
            
            # Disk
            disk = psutil.disk_usage('/')
            self.set_gauge('system_disk_usage_bytes', disk.used)
            self.set_gauge('system_disk_total_bytes', disk.total)
            self.set_gauge('system_disk_percent', disk.percent)
            
            # Process-specific
            process = psutil.Process()
            self.set_gauge('process_memory_rss_bytes', process.memory_info().rss)
            self.set_gauge('process_cpu_percent', process.cpu_percent())
            self.set_gauge('process_threads', process.num_threads())
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    # ============================================================
    # Prometheus Export
    # ============================================================
    
    def export_prometheus(self) -> str:
        """
        Export all metrics in Prometheus text format.
        
        Returns:
            Prometheus-formatted metrics string
        """
        self.collect_system_metrics()
        
        lines = []
        
        # Add timestamp
        lines.append(f"# Generated at {datetime.utcnow().isoformat()}Z")
        lines.append("")
        
        # Application info
        lines.append("# HELP ufdr_info Application information")
        lines.append("# TYPE ufdr_info gauge")
        lines.append(f'ufdr_info{{version="2.0.0",platform="{self.system_info["platform"]}",python="{self.system_info["python_version"]}"}} 1')
        lines.append("")
        
        # Uptime
        uptime = time.time() - self.start_time
        lines.append("# HELP ufdr_uptime_seconds Application uptime in seconds")
        lines.append("# TYPE ufdr_uptime_seconds gauge")
        lines.append(f"ufdr_uptime_seconds {uptime:.2f}")
        lines.append("")
        
        # Counters
        lines.append("# Counters")
        for key, value in sorted(self.counters.items()):
            name, labels = self._parse_key(key)
            label_str = self._format_labels(labels)
            lines.append(f"# HELP ufdr_{name} Counter metric")
            lines.append(f"# TYPE ufdr_{name} counter")
            lines.append(f"ufdr_{name}{label_str} {value}")
        lines.append("")
        
        # Gauges
        lines.append("# Gauges")
        for key, value in sorted(self.gauges.items()):
            name, labels = self._parse_key(key)
            label_str = self._format_labels(labels)
            lines.append(f"# HELP ufdr_{name} Gauge metric")
            lines.append(f"# TYPE ufdr_{name} gauge")
            lines.append(f"ufdr_{name}{label_str} {value:.2f}")
        lines.append("")
        
        # Histograms
        lines.append("# Histograms")
        for key, values in sorted(self.histograms.items()):
            name, labels = self._parse_key(key)
            label_str = self._format_labels(labels)
            stats = self.get_histogram_stats(name, labels)
            
            lines.append(f"# HELP ufdr_{name} Histogram metric")
            lines.append(f"# TYPE ufdr_{name} histogram")
            lines.append(f'ufdr_{name}_count{label_str} {stats["count"]}')
            lines.append(f'ufdr_{name}_sum{label_str} {stats["sum"]:.4f}')
            lines.append(f'ufdr_{name}{{quantile="0.5"{self._add_to_labels(label_str, "quantile", "0.5")}}} {stats["p50"]:.4f}')
            lines.append(f'ufdr_{name}{{quantile="0.95"{self._add_to_labels(label_str, "quantile", "0.95")}}} {stats["p95"]:.4f}')
            lines.append(f'ufdr_{name}{{quantile="0.99"{self._add_to_labels(label_str, "quantile", "0.99")}}} {stats["p99"]:.4f}')
        lines.append("")
        
        # Business metrics
        lines.append("# Business Metrics")
        for metric_name, value in sorted(self.business_metrics.items()):
            lines.append(f"# HELP ufdr_business_{metric_name} Business metric")
            lines.append(f"# TYPE ufdr_business_{metric_name} counter")
            lines.append(f"ufdr_business_{metric_name} {value}")
        lines.append("")
        
        return "\n".join(lines)
    
    # ============================================================
    # Helper Methods
    # ============================================================
    
    def _make_key(self, name: str, labels: Optional[Dict] = None) -> str:
        """Create a unique key for a metric with labels."""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def _parse_key(self, key: str) -> tuple:
        """Parse a key back into name and labels."""
        if '{' not in key:
            return key, {}
        
        name, label_part = key.split('{', 1)
        label_part = label_part.rstrip('}')
        
        labels = {}
        if label_part:
            for pair in label_part.split(','):
                k, v = pair.split('=')
                labels[k] = v
        
        return name, labels
    
    def _format_labels(self, labels: Dict) -> str:
        """Format labels for Prometheus."""
        if not labels:
            return ""
        label_pairs = [f'{k}="{v}"' for k, v in sorted(labels.items())]
        return "{" + ",".join(label_pairs) + "}"
    
    def _add_to_labels(self, label_str: str, key: str, value: str) -> str:
        """Add a label to existing label string."""
        if not label_str or label_str == "{}":
            return f',{key}="{value}"'
        # Remove trailing }
        return f',{key}="{value}"'
    
    def reset_metrics(self):
        """Reset all metrics (for testing)."""
        with self._lock:
            self.counters.clear()
            self.gauges.clear()
            self.histograms.clear()
            self.business_metrics = {
                'cases_processed': 0,
                'entities_extracted': 0,
                'cross_case_links_found': 0,
                'alerts_generated': 0,
                'queries_executed': 0,
                'exports_generated': 0
            }
        logger.info("Metrics reset")


# ============================================================
# Global Metrics Instance
# ============================================================

metrics = MetricsCollector()


# ============================================================
# Convenience Functions
# ============================================================

def increment_counter(name: str, value: int = 1, labels: Optional[Dict] = None):
    """Convenience function to increment counter."""
    metrics.increment_counter(name, value, labels)


def set_gauge(name: str, value: float, labels: Optional[Dict] = None):
    """Convenience function to set gauge."""
    metrics.set_gauge(name, value, labels)


def observe_latency(name: str, duration: float, labels: Optional[Dict] = None):
    """Convenience function to observe latency."""
    metrics.observe_histogram(f"{name}_duration_seconds", duration, labels)


def record_case_processed():
    """Convenience function to record case processed."""
    metrics.record_case_processed()


def record_entities_extracted(count: int):
    """Convenience function to record entities extracted."""
    metrics.record_entities_extracted(count)


def record_cross_case_link():
    """Convenience function to record cross-case link."""
    metrics.record_cross_case_link_found()


def record_alert():
    """Convenience function to record alert."""
    metrics.record_alert_generated()


def record_query():
    """Convenience function to record query."""
    metrics.record_query_executed()


def record_export():
    """Convenience function to record export."""
    metrics.record_export_generated()


def export_metrics() -> str:
    """Export all metrics in Prometheus format."""
    return metrics.export_prometheus()


# ============================================================
# Decorator for Timing Functions
# ============================================================

def timed_operation(operation_name: str):
    """
    Decorator to automatically time an operation and record metrics.
    
    Usage:
        @timed_operation("parse_ufdr")
        def parse_ufdr_file(path):
            # ... do work
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                observe_latency(operation_name, duration, {'status': 'success'})
                increment_counter(f"{operation_name}_total", labels={'status': 'success'})
                return result
            except Exception as e:
                duration = time.time() - start_time
                observe_latency(operation_name, duration, {'status': 'error'})
                increment_counter(f"{operation_name}_total", labels={'status': 'error'})
                raise
        return wrapper
    return decorator


if __name__ == "__main__":
    # Test metrics collector
    print("Testing Metrics Collector")
    print("=" * 60)
    
    # Record some test metrics
    increment_counter("requests_total", labels={'endpoint': '/api/cases'})
    increment_counter("requests_total", labels={'endpoint': '/api/cases'})
    increment_counter("requests_total", labels={'endpoint': '/api/query'})
    
    set_gauge("active_connections", 10.0)
    
    observe_latency("api_request", 0.123, labels={'endpoint': '/api/cases'})
    observe_latency("api_request", 0.156, labels={'endpoint': '/api/cases'})
    observe_latency("api_request", 0.089, labels={'endpoint': '/api/query'})
    
    record_case_processed()
    record_entities_extracted(15)
    record_cross_case_link()
    record_alert()
    
    # Export metrics
    print(export_metrics())