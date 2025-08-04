"""
Health Checker for API Gateway
==============================

Health checking system for monitoring upstream service instances
and maintaining service availability information.
"""

import asyncio
import time
import logging
from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum

import httpx

from .config import ServiceInstance, LoadBalancerConfig, HealthCheckMethod

logger = logging.getLogger(__name__)


@dataclass
class HealthCheckResult:
    """Health check result"""
    instance: ServiceInstance
    healthy: bool
    response_time: Optional[float] = None
    status_code: Optional[int] = None
    error: Optional[str] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class HealthChecker:
    """Health checker for service instances"""
    
    def __init__(self, config: LoadBalancerConfig):
        self.config = config
        self._health_history: Dict[str, List[HealthCheckResult]] = {}
        self._health_callbacks: List[Callable[[HealthCheckResult], None]] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        logger.info("Health checker initialized")
    
    async def check_instance_health(self, instance: ServiceInstance) -> HealthCheckResult:
        """
        Check health of a single service instance
        
        Args:
            instance: Service instance to check
            
        Returns:
            Health check result
        """
        start_time = time.time()
        
        try:
            if self.config.health_check_method == HealthCheckMethod.HTTP_GET:
                result = await self._http_health_check(instance, "GET")
            elif self.config.health_check_method == HealthCheckMethod.HTTP_POST:
                result = await self._http_health_check(instance, "POST")
            elif self.config.health_check_method == HealthCheckMethod.TCP_CONNECT:
                result = await self._tcp_health_check(instance)
            else:
                result = await self._custom_health_check(instance)
            
            # Update instance health status
            instance.healthy = result.healthy
            instance.last_health_check = result.timestamp
            
            # Store health history
            instance_key = f"{instance.host}:{instance.port}"
            if instance_key not in self._health_history:
                self._health_history[instance_key] = []
            
            self._health_history[instance_key].append(result)
            
            # Keep only last 100 health check results
            if len(self._health_history[instance_key]) > 100:
                self._health_history[instance_key].pop(0)
            
            # Notify callbacks
            for callback in self._health_callbacks:
                try:
                    callback(result)
                except Exception as e:
                    logger.error(f"Health check callback error: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Health check failed for {instance.url}: {e}")
            
            result = HealthCheckResult(
                instance=instance,
                healthy=False,
                error=str(e),
                response_time=time.time() - start_time
            )
            
            instance.healthy = False
            instance.last_health_check = result.timestamp
            
            return result
    
    async def _http_health_check(self, instance: ServiceInstance, method: str) -> HealthCheckResult:
        """Perform HTTP health check"""
        start_time = time.time()
        
        health_url = f"{instance.url}/health"
        
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.health_check_timeout)
        ) as client:
            
            if method == "GET":
                response = await client.get(health_url)
            else:  # POST
                response = await client.post(health_url)
            
            response_time = time.time() - start_time
            is_healthy = response.status_code == 200
            
            return HealthCheckResult(
                instance=instance,
                healthy=is_healthy,
                response_time=response_time,
                status_code=response.status_code
            )
    
    async def _tcp_health_check(self, instance: ServiceInstance) -> HealthCheckResult:
        """Perform TCP connection health check"""
        start_time = time.time()
        
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(instance.host, instance.port),
                timeout=self.config.health_check_timeout
            )
            
            writer.close()
            await writer.wait_closed()
            
            response_time = time.time() - start_time
            
            return HealthCheckResult(
                instance=instance,
                healthy=True,
                response_time=response_time
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            
            return HealthCheckResult(
                instance=instance,
                healthy=False,
                response_time=response_time,
                error=str(e)
            )
    
    async def _custom_health_check(self, instance: ServiceInstance) -> HealthCheckResult:
        """Perform custom health check (placeholder)"""
        # This would be implemented based on specific requirements
        return HealthCheckResult(
            instance=instance,
            healthy=True,
            response_time=0.001
        )
    
    async def check_all_instances(self, instances: List[ServiceInstance]) -> List[HealthCheckResult]:
        """
        Check health of all service instances
        
        Args:
            instances: List of service instances to check
            
        Returns:
            List of health check results
        """
        if not instances:
            return []
        
        # Run health checks concurrently
        tasks = [
            self.check_instance_health(instance)
            for instance in instances
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and log them
        health_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Health check exception for {instances[i].url}: {result}")
                health_results.append(HealthCheckResult(
                    instance=instances[i],
                    healthy=False,
                    error=str(result)
                ))
            else:
                health_results.append(result)
        
        return health_results
    
    async def start_continuous_health_checks(
        self,
        instances: List[ServiceInstance],
        interval: Optional[int] = None
    ) -> None:
        """
        Start continuous health checks for service instances
        
        Args:
            instances: List of service instances to monitor
            interval: Health check interval in seconds (uses config default if None)
        """
        if self._running:
            logger.warning("Health checks already running")
            return
        
        check_interval = interval or self.config.health_check_interval
        self._running = True
        
        async def health_check_loop():
            logger.info(f"Started continuous health checks (interval: {check_interval}s)")
            
            while self._running:
                try:
                    start_time = time.time()
                    
                    # Perform health checks
                    results = await self.check_all_instances(instances)
                    
                    # Log summary
                    healthy_count = sum(1 for result in results if result.healthy)
                    total_count = len(results)
                    
                    logger.info(
                        f"Health check cycle completed: {healthy_count}/{total_count} "
                        f"instances healthy (took {time.time() - start_time:.2f}s)"
                    )
                    
                    # Log unhealthy instances
                    for result in results:
                        if not result.healthy:
                            logger.warning(
                                f"Instance {result.instance.url} is unhealthy: "
                                f"{result.error or f'HTTP {result.status_code}'}"
                            )
                    
                except Exception as e:
                    logger.error(f"Health check cycle error: {e}")
                
                # Wait for next cycle
                await asyncio.sleep(check_interval)
        
        # Start health check task
        self._task = asyncio.create_task(health_check_loop())
    
    async def stop_continuous_health_checks(self) -> None:
        """Stop continuous health checks"""
        if not self._running:
            return
        
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        
        logger.info("Stopped continuous health checks")
    
    def add_health_callback(self, callback: Callable[[HealthCheckResult], None]) -> None:
        """
        Add callback to be called on each health check result
        
        Args:
            callback: Function to call with health check results
        """
        self._health_callbacks.append(callback)
    
    def remove_health_callback(self, callback: Callable[[HealthCheckResult], None]) -> None:
        """Remove health check callback"""
        if callback in self._health_callbacks:
            self._health_callbacks.remove(callback)
    
    def get_instance_health_history(
        self,
        instance: ServiceInstance,
        limit: int = 10
    ) -> List[HealthCheckResult]:
        """
        Get health check history for an instance
        
        Args:
            instance: Service instance
            limit: Maximum number of results to return
            
        Returns:
            List of recent health check results
        """
        instance_key = f"{instance.host}:{instance.port}"
        history = self._health_history.get(instance_key, [])
        return history[-limit:] if history else []
    
    def get_instance_health_stats(self, instance: ServiceInstance) -> Dict[str, Any]:
        """
        Get health statistics for an instance
        
        Args:
            instance: Service instance
            
        Returns:
            Dictionary with health statistics
        """
        instance_key = f"{instance.host}:{instance.port}"
        history = self._health_history.get(instance_key, [])
        
        if not history:
            return {
                "total_checks": 0,
                "healthy_checks": 0,
                "unhealthy_checks": 0,
                "success_rate": 0.0,
                "average_response_time": 0.0,
                "last_check": None
            }
        
        healthy_checks = sum(1 for result in history if result.healthy)
        unhealthy_checks = len(history) - healthy_checks
        
        response_times = [
            result.response_time for result in history
            if result.response_time is not None
        ]
        average_response_time = (
            sum(response_times) / len(response_times)
            if response_times else 0.0
        )
        
        return {
            "total_checks": len(history),
            "healthy_checks": healthy_checks,
            "unhealthy_checks": unhealthy_checks,
            "success_rate": healthy_checks / len(history),
            "average_response_time": average_response_time,
            "last_check": history[-1].timestamp if history else None,
            "current_status": "healthy" if instance.healthy else "unhealthy"
        }
    
    def get_overall_health_stats(self) -> Dict[str, Any]:
        """Get overall health statistics for all instances"""
        all_instances = []
        for instance_history in self._health_history.values():
            all_instances.extend(instance_history)
        
        if not all_instances:
            return {
                "total_instances": 0,
                "total_checks": 0,
                "healthy_checks": 0,
                "unhealthy_checks": 0,
                "overall_success_rate": 0.0,
                "average_response_time": 0.0
            }
        
        healthy_checks = sum(1 for result in all_instances if result.healthy)
        unhealthy_checks = len(all_instances) - healthy_checks
        
        response_times = [
            result.response_time for result in all_instances
            if result.response_time is not None
        ]
        average_response_time = (
            sum(response_times) / len(response_times)
            if response_times else 0.0
        )
        
        return {
            "total_instances": len(self._health_history),
            "total_checks": len(all_instances),
            "healthy_checks": healthy_checks,
            "unhealthy_checks": unhealthy_checks,
            "overall_success_rate": healthy_checks / len(all_instances),
            "average_response_time": average_response_time
        }
