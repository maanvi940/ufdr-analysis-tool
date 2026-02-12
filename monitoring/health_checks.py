"""
UFDR Analysis Tool - Health Check Endpoints
===========================================

Provides health check endpoints for monitoring:
- Liveness probe: Is the application running?
- Readiness probe: Is the application ready to serve traffic?
- Dependency checks: Are dependencies healthy?

Endpoints:
- /health/live - Liveness check
- /health/ready - Readiness check
- /health/detailed - Detailed health status
"""

import time
import os
import psutil
from datetime import datetime
from typing import Dict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class HealthStatus:
    """Health status constants."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


class HealthChecker:
    """
    Performs health checks on application and dependencies.
    """
    
    def __init__(self):
        self.start_time = time.time()
        self.checks_enabled = True
        
    def liveness_check(self) -> Dict:
        """
        Liveness check: Is the application running?
        
        This should be a simple check that returns 200 if the app is alive.
        Used by Kubernetes to determine if pod should be restarted.
        
        Returns:
            Dict with status and timestamp
        """
        return {
            "status": HealthStatus.HEALTHY,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "uptime_seconds": time.time() - self.start_time
        }
    
    def readiness_check(self) -> Dict:
        """
        Readiness check: Is the application ready to serve traffic?
        
        Checks critical dependencies. If any fail, application is not ready.
        Used by Kubernetes to determine if pod should receive traffic.
        
        Returns:
            Dict with status, checks, and details
        """
        checks = {
            "disk_space": self._check_disk_space(),
            "memory": self._check_memory(),
            "data_directories": self._check_data_directories(),
            "python_modules": self._check_python_modules()
        }
        
        # Determine overall status
        all_healthy = all(check["status"] == HealthStatus.HEALTHY for check in checks.values())
        any_unhealthy = any(check["status"] == HealthStatus.UNHEALTHY for check in checks.values())
        
        if all_healthy:
            overall_status = HealthStatus.HEALTHY
        elif any_unhealthy:
            overall_status = HealthStatus.UNHEALTHY
        else:
            overall_status = HealthStatus.DEGRADED
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "checks": checks,
            "ready": overall_status == HealthStatus.HEALTHY
        }
    
    def detailed_check(self) -> Dict:
        """
        Detailed health check: Comprehensive system and application status.
        
        Returns:
            Dict with detailed status of all components
        """
        checks = {
            # System checks
            "system": {
                "cpu": self._check_cpu(),
                "memory": self._check_memory(),
                "disk_space": self._check_disk_space(),
                "process": self._check_process()
            },
            
            # Application checks
            "application": {
                "uptime": self._check_uptime(),
                "data_directories": self._check_data_directories(),
                "python_modules": self._check_python_modules(),
                "configuration": self._check_configuration()
            }
        }
        
        # Calculate overall health
        all_checks = []
        for category in checks.values():
            all_checks.extend(category.values())
        
        all_healthy = all(check["status"] == HealthStatus.HEALTHY for check in all_checks)
        any_unhealthy = any(check["status"] == HealthStatus.UNHEALTHY for check in all_checks)
        
        if all_healthy:
            overall_status = HealthStatus.HEALTHY
        elif any_unhealthy:
            overall_status = HealthStatus.UNHEALTHY
        else:
            overall_status = HealthStatus.DEGRADED
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "checks": checks
        }
    
    # ============================================================
    # Individual Health Checks
    # ============================================================
    
    def _check_cpu(self) -> Dict:
        """Check CPU usage."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            if cpu_percent < 80:
                status = HealthStatus.HEALTHY
                message = f"CPU usage: {cpu_percent:.1f}%"
            elif cpu_percent < 95:
                status = HealthStatus.DEGRADED
                message = f"High CPU usage: {cpu_percent:.1f}%"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Critical CPU usage: {cpu_percent:.1f}%"
            
            return {
                "status": status,
                "message": message,
                "cpu_percent": cpu_percent,
                "cpu_count": psutil.cpu_count()
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Failed to check CPU: {str(e)}"
            }
    
    def _check_memory(self) -> Dict:
        """Check memory usage."""
        try:
            memory = psutil.virtual_memory()
            
            if memory.percent < 80:
                status = HealthStatus.HEALTHY
                message = f"Memory usage: {memory.percent:.1f}%"
            elif memory.percent < 90:
                status = HealthStatus.DEGRADED
                message = f"High memory usage: {memory.percent:.1f}%"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Critical memory usage: {memory.percent:.1f}%"
            
            return {
                "status": status,
                "message": message,
                "memory_percent": memory.percent,
                "memory_used_gb": memory.used / (1024**3),
                "memory_total_gb": memory.total / (1024**3)
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Failed to check memory: {str(e)}"
            }
    
    def _check_disk_space(self) -> Dict:
        """Check disk space."""
        try:
            # Check current directory disk usage
            disk = psutil.disk_usage('.')
            
            if disk.percent < 80:
                status = HealthStatus.HEALTHY
                message = f"Disk usage: {disk.percent:.1f}%"
            elif disk.percent < 90:
                status = HealthStatus.DEGRADED
                message = f"High disk usage: {disk.percent:.1f}%"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Critical disk usage: {disk.percent:.1f}%"
            
            return {
                "status": status,
                "message": message,
                "disk_percent": disk.percent,
                "disk_used_gb": disk.used / (1024**3),
                "disk_total_gb": disk.total / (1024**3),
                "disk_free_gb": disk.free / (1024**3)
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Failed to check disk: {str(e)}"
            }
    
    def _check_process(self) -> Dict:
        """Check current process health."""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                "status": HealthStatus.HEALTHY,
                "message": "Process is running",
                "pid": process.pid,
                "memory_rss_mb": memory_info.rss / (1024**2),
                "cpu_percent": process.cpu_percent(),
                "threads": process.num_threads(),
                "create_time": datetime.fromtimestamp(process.create_time()).isoformat()
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Failed to check process: {str(e)}"
            }
    
    def _check_uptime(self) -> Dict:
        """Check application uptime."""
        uptime = time.time() - self.start_time
        
        return {
            "status": HealthStatus.HEALTHY,
            "message": f"Application uptime: {uptime:.0f} seconds",
            "uptime_seconds": uptime,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat()
        }
    
    def _check_data_directories(self) -> Dict:
        """Check that required data directories exist and are writable."""
        try:
            required_dirs = [
                "data",
                "logs",
                "exports"
            ]
            
            missing_dirs = []
            unwritable_dirs = []
            
            for dir_name in required_dirs:
                dir_path = Path(dir_name)
                
                if not dir_path.exists():
                    missing_dirs.append(dir_name)
                elif not os.access(dir_path, os.W_OK):
                    unwritable_dirs.append(dir_name)
            
            if missing_dirs or unwritable_dirs:
                status = HealthStatus.UNHEALTHY
                messages = []
                if missing_dirs:
                    messages.append(f"Missing directories: {', '.join(missing_dirs)}")
                if unwritable_dirs:
                    messages.append(f"Unwritable directories: {', '.join(unwritable_dirs)}")
                message = "; ".join(messages)
            else:
                status = HealthStatus.HEALTHY
                message = "All required directories present and writable"
            
            return {
                "status": status,
                "message": message,
                "checked_directories": required_dirs
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Failed to check directories: {str(e)}"
            }
    
    def _check_python_modules(self) -> Dict:
        """Check that critical Python modules can be imported."""
        try:
            critical_modules = [
                "pandas",
                "pydantic",
                "cryptography"
            ]
            
            missing_modules = []
            
            for module_name in critical_modules:
                try:
                    __import__(module_name)
                except ImportError:
                    missing_modules.append(module_name)
            
            if missing_modules:
                status = HealthStatus.UNHEALTHY
                message = f"Missing modules: {', '.join(missing_modules)}"
            else:
                status = HealthStatus.HEALTHY
                message = "All critical modules available"
            
            return {
                "status": status,
                "message": message,
                "checked_modules": critical_modules
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Failed to check modules: {str(e)}"
            }
    
    def _check_configuration(self) -> Dict:
        """Check configuration file presence."""
        try:
            # Check if config files exist
            config_files = [
                "config.env",
                "README.md"
            ]
            
            existing_files = []
            missing_files = []
            
            for config_file in config_files:
                if Path(config_file).exists():
                    existing_files.append(config_file)
                else:
                    missing_files.append(config_file)
            
            if missing_files:
                status = HealthStatus.DEGRADED
                message = f"Some config files missing: {', '.join(missing_files)}"
            else:
                status = HealthStatus.HEALTHY
                message = "Configuration files present"
            
            return {
                "status": status,
                "message": message,
                "existing_files": existing_files,
                "missing_files": missing_files
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Failed to check configuration: {str(e)}"
            }


# ============================================================
# Global Health Checker Instance
# ============================================================

health_checker = HealthChecker()


# ============================================================
# Convenience Functions
# ============================================================

def liveness() -> Dict:
    """Check if application is alive."""
    return health_checker.liveness_check()


def readiness() -> Dict:
    """Check if application is ready to serve traffic."""
    return health_checker.readiness_check()


def detailed() -> Dict:
    """Get detailed health status."""
    return health_checker.detailed_check()


def is_healthy() -> bool:
    """Simple boolean health check."""
    result = health_checker.readiness_check()
    return result["status"] == HealthStatus.HEALTHY


# ============================================================
# Flask/FastAPI Integration Helpers
# ============================================================

def get_liveness_response() -> tuple:
    """
    Get liveness response for Flask/FastAPI.
    
    Returns:
        Tuple of (json_dict, status_code)
    """
    result = liveness()
    return result, 200


def get_readiness_response() -> tuple:
    """
    Get readiness response for Flask/FastAPI.
    
    Returns:
        Tuple of (json_dict, status_code)
    """
    result = readiness()
    status_code = 200 if result["ready"] else 503
    return result, status_code


def get_detailed_response() -> tuple:
    """
    Get detailed health response for Flask/FastAPI.
    
    Returns:
        Tuple of (json_dict, status_code)
    """
    result = detailed()
    status_code = 200 if result["status"] == HealthStatus.HEALTHY else 503
    return result, status_code


if __name__ == "__main__":
    import json
    
    print("Testing Health Checks")
    print("=" * 60)
    
    print("\n1. Liveness Check:")
    print(json.dumps(liveness(), indent=2))
    
    print("\n2. Readiness Check:")
    print(json.dumps(readiness(), indent=2))
    
    print("\n3. Detailed Check:")
    print(json.dumps(detailed(), indent=2))
    
    print(f"\n4. Simple Health Check: {is_healthy()}")