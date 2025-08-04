"""
Load Balancer Implementation
===========================

Advanced load balancing algorithms for API Gateway including round robin,
least connections, weighted round robin, IP hash, and random selection.
"""

import asyncio
import hashlib
import random
import time
from typing import List, Optional, Dict, Any
from enum import Enum
import logging
from dataclasses import dataclass, field

from .config import ServiceInstance, LoadBalancingAlgorithm

logger = logging.getLogger(__name__)


@dataclass
class ConnectionStats:
    """Connection statistics for a service instance"""
    active_connections: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    last_request_time: float = field(default_factory=time.time)
    response_times: List[float] = field(default_factory=list)
    
    @property
    def average_response_time(self) -> float:
        """Calculate average response time"""
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_requests == 0:
            return 1.0
        return (self.total_requests - self.failed_requests) / self.total_requests


class LoadBalancer:
    """Advanced load balancer with multiple algorithms"""
    
    def __init__(
        self,
        algorithm: LoadBalancingAlgorithm = LoadBalancingAlgorithm.ROUND_ROBIN,
        health_check_enabled: bool = True
    ):
        self.algorithm = algorithm
        self.health_check_enabled = health_check_enabled
        
        # State tracking
        self._round_robin_index = 0
        self._connection_stats: Dict[str, ConnectionStats] = {}
        self._lock = asyncio.Lock()
        
        logger.info(f"Load balancer initialized with algorithm: {algorithm}")
    
    async def select_instance(
        self,
        instances: List[ServiceInstance],
        client_ip: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Optional[ServiceInstance]:
        """
        Select a service instance based on the configured algorithm
        
        Args:
            instances: List of available service instances
            client_ip: Client IP address for IP hash algorithm
            session_id: Session ID for sticky sessions
            
        Returns:
            Selected service instance or None if no healthy instances
        """
        if not instances:
            logger.warning("No service instances available")
            return None
        
        # Filter healthy instances
        healthy_instances = [
            instance for instance in instances
            if not self.health_check_enabled or instance.healthy
        ]
        
        if not healthy_instances:
            logger.warning("No healthy service instances available")
            return None
        
        # Select instance based on algorithm
        if self.algorithm == LoadBalancingAlgorithm.ROUND_ROBIN:
            return await self._round_robin_select(healthy_instances)
        elif self.algorithm == LoadBalancingAlgorithm.LEAST_CONNECTIONS:
            return await self._least_connections_select(healthy_instances)
        elif self.algorithm == LoadBalancingAlgorithm.WEIGHTED_ROUND_ROBIN:
            return await self._weighted_round_robin_select(healthy_instances)
        elif self.algorithm == LoadBalancingAlgorithm.IP_HASH:
            return await self._ip_hash_select(healthy_instances, client_ip)
        elif self.algorithm == LoadBalancingAlgorithm.RANDOM:
            return await self._random_select(healthy_instances)
        else:
            logger.error(f"Unknown load balancing algorithm: {self.algorithm}")
            return healthy_instances[0]
    
    async def _round_robin_select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Round robin selection"""
        async with self._lock:
            instance = instances[self._round_robin_index % len(instances)]
            self._round_robin_index = (self._round_robin_index + 1) % len(instances)
            return instance
    
    async def _least_connections_select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Least connections selection"""
        min_connections = float('inf')
        selected_instance = instances[0]
        
        for instance in instances:
            instance_key = f"{instance.host}:{instance.port}"
            stats = self._connection_stats.get(instance_key, ConnectionStats())
            
            if stats.active_connections < min_connections:
                min_connections = stats.active_connections
                selected_instance = instance
        
        return selected_instance
    
    async def _weighted_round_robin_select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Weighted round robin selection"""
        total_weight = sum(instance.weight for instance in instances)
        if total_weight == 0:
            return instances[0]
        
        # Create weighted list
        weighted_instances = []
        for instance in instances:
            weighted_instances.extend([instance] * instance.weight)
        
        async with self._lock:
            instance = weighted_instances[self._round_robin_index % len(weighted_instances)]
            self._round_robin_index = (self._round_robin_index + 1) % len(weighted_instances)
            return instance
    
    async def _ip_hash_select(
        self,
        instances: List[ServiceInstance],
        client_ip: Optional[str]
    ) -> ServiceInstance:
        """IP hash selection for sticky sessions"""
        if not client_ip:
            return instances[0]
        
        # Hash client IP to select instance
        hash_value = int(hashlib.md5(client_ip.encode()).hexdigest(), 16)
        index = hash_value % len(instances)
        return instances[index]
    
    async def _random_select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Random selection"""
        return random.choice(instances)
    
    async def record_request_start(self, instance: ServiceInstance) -> None:
        """Record the start of a request to an instance"""
        instance_key = f"{instance.host}:{instance.port}"
        
        if instance_key not in self._connection_stats:
            self._connection_stats[instance_key] = ConnectionStats()
        
        stats = self._connection_stats[instance_key]
        stats.active_connections += 1
        stats.total_requests += 1
        stats.last_request_time = time.time()
    
    async def record_request_end(
        self,
        instance: ServiceInstance,
        success: bool = True,
        response_time: Optional[float] = None
    ) -> None:
        """Record the end of a request to an instance"""
        instance_key = f"{instance.host}:{instance.port}"
        
        if instance_key not in self._connection_stats:
            return
        
        stats = self._connection_stats[instance_key]
        stats.active_connections = max(0, stats.active_connections - 1)
        
        if not success:
            stats.failed_requests += 1
        
        if response_time is not None:
            # Keep only last 100 response times
            stats.response_times.append(response_time)
            if len(stats.response_times) > 100:
                stats.response_times.pop(0)
    
    def get_instance_stats(self, instance: ServiceInstance) -> ConnectionStats:
        """Get statistics for a service instance"""
        instance_key = f"{instance.host}:{instance.port}"
        return self._connection_stats.get(instance_key, ConnectionStats())
    
    def get_all_stats(self) -> Dict[str, ConnectionStats]:
        """Get statistics for all instances"""
        return self._connection_stats.copy()
    
    async def health_check_instance(self, instance: ServiceInstance) -> bool:
        """
        Perform health check on a service instance
        
        Args:
            instance: Service instance to check
            
        Returns:
            True if instance is healthy, False otherwise
        """
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{instance.url}/health")
                is_healthy = response.status_code == 200
                
                # Update instance health status
                instance.healthy = is_healthy
                instance.last_health_check = time.time()
                
                logger.debug(
                    f"Health check for {instance.url}: "
                    f"{'healthy' if is_healthy else 'unhealthy'}"
                )
                
                return is_healthy
                
        except Exception as e:
            logger.warning(f"Health check failed for {instance.url}: {e}")
            instance.healthy = False
            instance.last_health_check = time.time()
            return False
    
    async def start_health_checks(
        self,
        instances: List[ServiceInstance],
        interval: int = 30
    ) -> None:
        """
        Start background health checks for service instances
        
        Args:
            instances: List of service instances to monitor
            interval: Health check interval in seconds
        """
        async def health_check_loop():
            while True:
                try:
                    tasks = [
                        self.health_check_instance(instance)
                        for instance in instances
                    ]
                    await asyncio.gather(*tasks, return_exceptions=True)
                    
                    healthy_count = sum(1 for instance in instances if instance.healthy)
                    logger.info(
                        f"Health check completed: {healthy_count}/{len(instances)} "
                        f"instances healthy"
                    )
                    
                except Exception as e:
                    logger.error(f"Error during health check cycle: {e}")
                
                await asyncio.sleep(interval)
        
        # Start health check task
        asyncio.create_task(health_check_loop())
        logger.info(f"Started health checks with {interval}s interval")


class StickySessionManager:
    """Manage sticky sessions for load balancing"""
    
    def __init__(self, session_timeout: int = 3600):
        self.session_timeout = session_timeout
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
    
    async def get_session_instance(
        self,
        session_id: str,
        instances: List[ServiceInstance]
    ) -> Optional[ServiceInstance]:
        """Get the instance associated with a session"""
        async with self._lock:
            session_data = self._sessions.get(session_id)
            
            if not session_data:
                return None
            
            # Check if session is expired
            if time.time() - session_data['created_at'] > self.session_timeout:
                del self._sessions[session_id]
                return None
            
            # Find the instance
            instance_key = session_data['instance_key']
            for instance in instances:
                if f"{instance.host}:{instance.port}" == instance_key:
                    return instance
            
            # Instance no longer available
            del self._sessions[session_id]
            return None
    
    async def create_session(
        self,
        session_id: str,
        instance: ServiceInstance
    ) -> None:
        """Create a new sticky session"""
        async with self._lock:
            self._sessions[session_id] = {
                'instance_key': f"{instance.host}:{instance.port}",
                'created_at': time.time()
            }
    
    async def cleanup_expired_sessions(self) -> None:
        """Clean up expired sessions"""
        current_time = time.time()
        expired_sessions = []
        
        async with self._lock:
            for session_id, session_data in self._sessions.items():
                if current_time - session_data['created_at'] > self.session_timeout:
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                del self._sessions[session_id]
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
