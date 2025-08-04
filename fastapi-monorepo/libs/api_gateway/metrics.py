"""
Metrics Collection for API Gateway
==================================

Metrics collection and monitoring system for API Gateway including
request metrics, error tracking, performance monitoring, and health metrics.
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta

from .config import MetricsConfig

logger = logging.getLogger(__name__)


@dataclass
class RequestMetric:
    """Individual request metric"""
    timestamp: float
    method: str
    path: str
    status_code: int
    duration: float
    service: str
    user_id: Optional[str] = None
    trace_id: Optional[str] = None


@dataclass
class ErrorMetric:
    """Error metric"""
    timestamp: float
    method: str
    path: str
    error_type: str
    error_message: str
    service: str
    user_id: Optional[str] = None
    trace_id: Optional[str] = None


@dataclass
class ServiceMetrics:
    """Metrics for a specific service"""
    service_name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_duration: float = 0.0
    min_duration: float = float('inf')
    max_duration: float = 0.0
    recent_requests: deque = field(default_factory=lambda: deque(maxlen=1000))
    error_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests
    
    @property
    def average_duration(self) -> float:
        """Calculate average request duration"""
        if self.total_requests == 0:
            return 0.0
        return self.total_duration / self.total_requests
    
    @property
    def requests_per_minute(self) -> float:
        """Calculate requests per minute (last minute)"""
        current_time = time.time()
        recent_requests = [
            req for req in self.recent_requests
            if current_time - req.timestamp < 60
        ]
        return len(recent_requests)


class GatewayMetrics:
    """Gateway metrics collection and reporting"""
    
    def __init__(self, config: MetricsConfig):
        self.config = config
        
        # Metrics storage
        self._service_metrics: Dict[str, ServiceMetrics] = {}
        self._request_history: deque = deque(maxlen=10000)
        self._error_history: deque = deque(maxlen=1000)
        
        # Gateway-level metrics
        self._gateway_start_time = time.time()
        self._active_connections = 0
        self._total_requests = 0
        self._total_errors = 0
        
        # Performance tracking
        self._response_time_buckets = {
            "0-50ms": 0,
            "50-100ms": 0,
            "100-250ms": 0,
            "250-500ms": 0,
            "500-1000ms": 0,
            "1000ms+": 0
        }
        
        # Status code tracking
        self._status_code_counts = defaultdict(int)
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info("Gateway metrics initialized")
    
    async def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration: float,
        service: str,
        user_id: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> None:
        """Record a request metric"""
        
        # Create request metric
        metric = RequestMetric(
            timestamp=time.time(),
            method=method,
            path=path,
            status_code=status_code,
            duration=duration,
            service=service,
            user_id=user_id,
            trace_id=trace_id
        )
        
        # Add to history
        self._request_history.append(metric)
        
        # Update gateway-level metrics
        self._total_requests += 1
        self._status_code_counts[status_code] += 1
        
        # Update response time buckets
        self._update_response_time_bucket(duration)
        
        # Update service metrics
        await self._update_service_metrics(metric)
        
        logger.debug(f"Recorded request: {method} {path} -> {status_code} ({duration:.3f}s)")
    
    async def record_error(
        self,
        method: str,
        path: str,
        error_type: str,
        service: str,
        error_message: str = "",
        user_id: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> None:
        """Record an error metric"""
        
        # Create error metric
        metric = ErrorMetric(
            timestamp=time.time(),
            method=method,
            path=path,
            error_type=error_type,
            error_message=error_message,
            service=service,
            user_id=user_id,
            trace_id=trace_id
        )
        
        # Add to history
        self._error_history.append(metric)
        
        # Update gateway-level metrics
        self._total_errors += 1
        
        # Update service error metrics
        if service in self._service_metrics:
            self._service_metrics[service].error_counts[error_type] += 1
        
        logger.debug(f"Recorded error: {method} {path} -> {error_type}")
    
    async def _update_service_metrics(self, metric: RequestMetric) -> None:
        """Update service-specific metrics"""
        
        service_name = metric.service
        
        # Initialize service metrics if not exists
        if service_name not in self._service_metrics:
            self._service_metrics[service_name] = ServiceMetrics(service_name=service_name)
        
        service_metrics = self._service_metrics[service_name]
        
        # Update counters
        service_metrics.total_requests += 1
        service_metrics.recent_requests.append(metric)
        
        if 200 <= metric.status_code < 400:
            service_metrics.successful_requests += 1
        else:
            service_metrics.failed_requests += 1
        
        # Update duration metrics
        service_metrics.total_duration += metric.duration
        service_metrics.min_duration = min(service_metrics.min_duration, metric.duration)
        service_metrics.max_duration = max(service_metrics.max_duration, metric.duration)
    
    def _update_response_time_bucket(self, duration: float) -> None:
        """Update response time bucket counters"""
        duration_ms = duration * 1000
        
        if duration_ms < 50:
            self._response_time_buckets["0-50ms"] += 1
        elif duration_ms < 100:
            self._response_time_buckets["50-100ms"] += 1
        elif duration_ms < 250:
            self._response_time_buckets["100-250ms"] += 1
        elif duration_ms < 500:
            self._response_time_buckets["250-500ms"] += 1
        elif duration_ms < 1000:
            self._response_time_buckets["500-1000ms"] += 1
        else:
            self._response_time_buckets["1000ms+"] += 1
    
    def increment_active_connections(self) -> None:
        """Increment active connections counter"""
        self._active_connections += 1
    
    def decrement_active_connections(self) -> None:
        """Decrement active connections counter"""
        self._active_connections = max(0, self._active_connections - 1)
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics"""
        
        current_time = time.time()
        uptime = current_time - self._gateway_start_time
        
        # Gateway overview
        gateway_metrics = {
            "gateway": {
                "uptime_seconds": uptime,
                "uptime_human": self._format_duration(uptime),
                "active_connections": self._active_connections,
                "total_requests": self._total_requests,
                "total_errors": self._total_errors,
                "error_rate": self._total_errors / max(self._total_requests, 1),
                "requests_per_second": self._total_requests / max(uptime, 1)
            }
        }
        
        # Response time distribution
        gateway_metrics["response_times"] = self._response_time_buckets.copy()
        
        # Status code distribution
        gateway_metrics["status_codes"] = dict(self._status_code_counts)
        
        # Service metrics
        service_metrics = {}
        for service_name, metrics in self._service_metrics.items():
            service_metrics[service_name] = {
                "total_requests": metrics.total_requests,
                "successful_requests": metrics.successful_requests,
                "failed_requests": metrics.failed_requests,
                "success_rate": metrics.success_rate,
                "average_duration": metrics.average_duration,
                "min_duration": metrics.min_duration if metrics.min_duration != float('inf') else 0,
                "max_duration": metrics.max_duration,
                "requests_per_minute": metrics.requests_per_minute,
                "error_counts": dict(metrics.error_counts)
            }
        
        gateway_metrics["services"] = service_metrics
        
        # Recent activity (last 5 minutes)
        recent_cutoff = current_time - 300  # 5 minutes
        recent_requests = [
            req for req in self._request_history
            if req.timestamp > recent_cutoff
        ]
        
        recent_errors = [
            err for err in self._error_history
            if err.timestamp > recent_cutoff
        ]
        
        gateway_metrics["recent_activity"] = {
            "requests_last_5min": len(recent_requests),
            "errors_last_5min": len(recent_errors),
            "avg_response_time_5min": (
                sum(req.duration for req in recent_requests) / len(recent_requests)
                if recent_requests else 0
            )
        }
        
        # Top errors
        error_counts = defaultdict(int)
        for error in recent_errors:
            error_counts[error.error_type] += 1
        
        gateway_metrics["top_errors"] = dict(
            sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        )
        
        return gateway_metrics
    
    async def get_prometheus_metrics(self) -> str:
        """Get metrics in Prometheus format"""
        
        if not self.config.prometheus_enabled:
            return ""
        
        metrics = await self.get_metrics()
        prometheus_metrics = []
        
        # Gateway metrics
        gateway = metrics["gateway"]
        prometheus_metrics.extend([
            f"# HELP gateway_uptime_seconds Gateway uptime in seconds",
            f"# TYPE gateway_uptime_seconds counter",
            f"gateway_uptime_seconds {gateway['uptime_seconds']}",
            "",
            f"# HELP gateway_active_connections Current active connections",
            f"# TYPE gateway_active_connections gauge",
            f"gateway_active_connections {gateway['active_connections']}",
            "",
            f"# HELP gateway_requests_total Total number of requests",
            f"# TYPE gateway_requests_total counter",
            f"gateway_requests_total {gateway['total_requests']}",
            "",
            f"# HELP gateway_errors_total Total number of errors",
            f"# TYPE gateway_errors_total counter",
            f"gateway_errors_total {gateway['total_errors']}",
            ""
        ])
        
        # Response time buckets
        prometheus_metrics.extend([
            f"# HELP gateway_response_time_bucket Response time distribution",
            f"# TYPE gateway_response_time_bucket histogram"
        ])
        
        for bucket, count in metrics["response_times"].items():
            prometheus_metrics.append(f"gateway_response_time_bucket{{le=\"{bucket}\"}} {count}")
        
        prometheus_metrics.append("")
        
        # Status codes
        prometheus_metrics.extend([
            f"# HELP gateway_status_codes_total HTTP status code counts",
            f"# TYPE gateway_status_codes_total counter"
        ])
        
        for status_code, count in metrics["status_codes"].items():
            prometheus_metrics.append(f"gateway_status_codes_total{{code=\"{status_code}\"}} {count}")
        
        prometheus_metrics.append("")
        
        # Service metrics
        for service_name, service_metrics in metrics["services"].items():
            prometheus_metrics.extend([
                f"# HELP service_requests_total Total requests per service",
                f"# TYPE service_requests_total counter",
                f"service_requests_total{{service=\"{service_name}\"}} {service_metrics['total_requests']}",
                "",
                f"# HELP service_success_rate Success rate per service",
                f"# TYPE service_success_rate gauge",
                f"service_success_rate{{service=\"{service_name}\"}} {service_metrics['success_rate']}",
                "",
                f"# HELP service_avg_duration_seconds Average request duration per service",
                f"# TYPE service_avg_duration_seconds gauge",
                f"service_avg_duration_seconds{{service=\"{service_name}\"}} {service_metrics['average_duration']}",
                ""
            ])
        
        return "\n".join(prometheus_metrics)
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        elif seconds < 86400:
            return f"{seconds/3600:.1f}h"
        else:
            return f"{seconds/86400:.1f}d"
    
    async def start(self) -> None:
        """Start metrics collection"""
        if self._running:
            return
        
        self._running = True
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_old_metrics())
        
        logger.info("Metrics collection started")
    
    async def stop(self) -> None:
        """Stop metrics collection"""
        if not self._running:
            return
        
        self._running = False
        
        # Stop cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
        
        logger.info("Metrics collection stopped")
    
    async def _cleanup_old_metrics(self) -> None:
        """Cleanup old metrics periodically"""
        while self._running:
            try:
                current_time = time.time()
                cutoff_time = current_time - 3600  # Keep 1 hour of history
                
                # Clean request history
                while (self._request_history and 
                       self._request_history[0].timestamp < cutoff_time):
                    self._request_history.popleft()
                
                # Clean error history
                while (self._error_history and 
                       self._error_history[0].timestamp < cutoff_time):
                    self._error_history.popleft()
                
                # Clean service metrics recent requests
                for service_metrics in self._service_metrics.values():
                    while (service_metrics.recent_requests and
                           service_metrics.recent_requests[0].timestamp < cutoff_time):
                        service_metrics.recent_requests.popleft()
                
                logger.debug("Cleaned up old metrics")
                
            except Exception as e:
                logger.error(f"Error during metrics cleanup: {e}")
            
            # Sleep for 5 minutes before next cleanup
            await asyncio.sleep(300)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of metrics system"""
        return {
            "status": "healthy" if self._running else "stopped",
            "uptime": time.time() - self._gateway_start_time,
            "request_history_size": len(self._request_history),
            "error_history_size": len(self._error_history),
            "services_tracked": len(self._service_metrics),
            "total_requests": self._total_requests,
            "total_errors": self._total_errors
        }
