#!/usr/bin/python3
"""
Proxy Management System
Handles proxy rotation and management for bot instances
Author: Peter Ekwere
"""

import random
import time
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


@dataclass
class ProxyConfig:
    """Proxy configuration with health monitoring"""
    server: str
    port: int
    username: str
    password: str
    protocol: str = "http"
    timezone: str = ""
    location: str = ""
    country: str = ""
    is_working: bool = True
    last_checked: float = 0
    response_time: float = 0
    failure_count: int = 0
    success_count: int = 0
    
    def __post_init__(self):
        """Initialize proxy with health check"""
        if not self.timezone:
            self.timezone = "America/New_York"  # Default fallback
        if not self.location:
            self.location = "Unknown"
        if not self.country:
            self.country = "US"
    
    @property
    def url(self) -> str:
        """Get full proxy URL"""
        return f"{self.protocol}://{self.username}:{self.password}@{self.server}:{self.port}"
    
    @property
    def selenium_format(self) -> str:
        """Get proxy in Selenium format"""
        return f"{self.server}:{self.port}"
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        total = self.success_count + self.failure_count
        return (self.success_count / total) if total > 0 else 0.0
    
    def mark_success(self, response_time: float = 0):
        """Mark proxy as successful"""
        self.is_working = True
        self.success_count += 1
        self.failure_count = 0
        self.response_time = response_time
        self.last_checked = time.time()
    
    def mark_failure(self):
        """Mark proxy as failed"""
        self.failure_count += 1
        self.last_checked = time.time()
        
        # Mark as not working if too many failures
        if self.failure_count >= 3:
            self.is_working = False


class ProxyManager:
    """Manages proxy rotation and health monitoring"""
    
    def __init__(self, proxies: List[Dict] = None):
        self.proxies = []
        self.current_index = 0
        self.health_check_interval = 300  # 5 minutes
        self.max_concurrent_checks = 10
        
        if proxies:
            self.load_proxies(proxies)
    
    def load_proxies(self, proxy_data: List[Dict]):
        """
        Load proxies from configuration data
        
        Args:
            proxy_data: List of proxy dictionaries
        """
        self.proxies = []
        
        for proxy_dict in proxy_data:
            try:
                proxy = ProxyConfig(
                    server=proxy_dict["server"],
                    port=int(proxy_dict["port"]),
                    username=proxy_dict["username"],
                    password=proxy_dict["password"],
                    protocol=proxy_dict.get("protocol", "http"),
                    timezone=proxy_dict.get("timezone", ""),
                    location=proxy_dict.get("location", ""),
                    country=proxy_dict.get("country", "")
                )
                self.proxies.append(proxy)
                logger.info(f"Loaded proxy: {proxy.server}:{proxy.port}")
            except KeyError as e:
                logger.error(f"Invalid proxy configuration: missing {e}")
            except Exception as e:
                logger.error(f"Error loading proxy: {e}")
        
        logger.info(f"Loaded {len(self.proxies)} proxies")
    
    def load_from_file(self, filepath: str):
        """
        Load proxies from a text file
        
        File format (one per line): server:port:username:password:protocol:timezone:location:country
        """
        proxies = []
        
        try:
            with open(filepath, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    parts = line.split(':')
                    if len(parts) >= 4:
                        proxy_dict = {
                            "server": parts[0],
                            "port": int(parts[1]),
                            "username": parts[2],
                            "password": parts[3],
                            "protocol": parts[4] if len(parts) > 4 else "http",
                            "timezone": parts[5] if len(parts) > 5 else "",
                            "location": parts[6] if len(parts) > 6 else "",
                            "country": parts[7] if len(parts) > 7 else ""
                        }
                        proxies.append(proxy_dict)
                    else:
                        logger.warning(f"Invalid proxy format at line {line_num}: {line}")
            
            self.load_proxies(proxies)
            
        except FileNotFoundError:
            logger.error(f"Proxy file not found: {filepath}")
        except Exception as e:
            logger.error(f"Error loading proxies from file: {e}")
    
    def get_next_proxy(self) -> Optional[ProxyConfig]:
        """
        Get next working proxy in rotation
        
        Returns:
            Next working proxy or None if none available
        """
        if not self.proxies:
            logger.warning("No proxies available")
            return None
        
        # Filter working proxies
        working_proxies = [p for p in self.proxies if p.is_working]
        
        if not working_proxies:
            logger.warning("No working proxies available")
            return None
        
        # Use round-robin selection
        proxy = working_proxies[self.current_index % len(working_proxies)]
        self.current_index += 1
        
        return proxy
    
    def get_random_proxy(self) -> Optional[ProxyConfig]:
        """
        Get a random working proxy
        
        Returns:
            Random working proxy or None if none available
        """
        if not self.proxies:
            return None
        
        working_proxies = [p for p in self.proxies if p.is_working]
        
        if not working_proxies:
            return None
        
        return random.choice(working_proxies)
    
    def get_proxy_by_location(self, country: str = None, location: str = None) -> Optional[ProxyConfig]:
        """
        Get proxy by location preference
        
        Args:
            country: Preferred country
            location: Preferred location
            
        Returns:
            Matching proxy or random working proxy
        """
        if not self.proxies:
            return None
        
        working_proxies = [p for p in self.proxies if p.is_working]
        
        if not working_proxies:
            return None
        
        # Filter by country if specified
        if country:
            country_proxies = [p for p in working_proxies if p.country.lower() == country.lower()]
            if country_proxies:
                working_proxies = country_proxies
        
        # Filter by location if specified
        if location:
            location_proxies = [p for p in working_proxies if location.lower() in p.location.lower()]
            if location_proxies:
                working_proxies = location_proxies
        
        return random.choice(working_proxies) if working_proxies else None
    
    def health_check_proxy(self, proxy: ProxyConfig, timeout: int = 10) -> bool:
        """
        Perform health check on a single proxy
        
        Args:
            proxy: Proxy to check
            timeout: Request timeout in seconds
            
        Returns:
            True if proxy is working, False otherwise
        """
        try:
            start_time = time.time()
            
            # Test proxy with a simple request
            test_url = "http://httpbin.org/ip"
            proxies = {
                "http": proxy.url,
                "https": proxy.url
            }
            
            response = requests.get(
                test_url,
                proxies=proxies,
                timeout=timeout,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                proxy.mark_success(response_time)
                logger.debug(f"Proxy {proxy.server}:{proxy.port} is working (response time: {response_time:.2f}s)")
                return True
            else:
                proxy.mark_failure()
                logger.warning(f"Proxy {proxy.server}:{proxy.port} returned status {response.status_code}")
                return False
                
        except Exception as e:
            proxy.mark_failure()
            logger.warning(f"Proxy {proxy.server}:{proxy.port} health check failed: {e}")
            return False
    
    def health_check_all(self, max_workers: int = None) -> Dict[str, int]:
        """
        Perform health check on all proxies concurrently
        
        Args:
            max_workers: Maximum number of concurrent health checks
            
        Returns:
            Dictionary with health check results
        """
        if not self.proxies:
            return {"total": 0, "working": 0, "failed": 0}
        
        max_workers = max_workers or min(self.max_concurrent_checks, len(self.proxies))
        results = {"total": len(self.proxies), "working": 0, "failed": 0}
        
        logger.info(f"Starting health check for {len(self.proxies)} proxies...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all health checks
            future_to_proxy = {
                executor.submit(self.health_check_proxy, proxy): proxy 
                for proxy in self.proxies
            }
            
            # Process results as they complete
            for future in as_completed(future_to_proxy):
                proxy = future_to_proxy[future]
                try:
                    is_working = future.result()
                    if is_working:
                        results["working"] += 1
                    else:
                        results["failed"] += 1
                except Exception as e:
                    logger.error(f"Health check error for {proxy.server}:{proxy.port}: {e}")
                    results["failed"] += 1
        
        logger.info(f"Health check complete: {results['working']} working, {results['failed']} failed")
        return results
    
    def get_proxy_stats(self) -> Dict:
        """
        Get statistics about proxy health
        
        Returns:
            Dictionary with proxy statistics
        """
        if not self.proxies:
            return {"total": 0, "working": 0, "failed": 0, "avg_response_time": 0}
        
        working_proxies = [p for p in self.proxies if p.is_working]
        failed_proxies = [p for p in self.proxies if not p.is_working]
        
        avg_response_time = 0
        if working_proxies:
            response_times = [p.response_time for p in working_proxies if p.response_time > 0]
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            "total": len(self.proxies),
            "working": len(working_proxies),
            "failed": len(failed_proxies),
            "avg_response_time": avg_response_time,
            "success_rates": {f"{p.server}:{p.port}": p.success_rate for p in self.proxies}
        }
    
    def reset_failed_proxies(self):
        """Reset failed proxies to give them another chance"""
        for proxy in self.proxies:
            if not proxy.is_working and proxy.failure_count > 0:
                proxy.failure_count = 0
                proxy.is_working = True
                logger.info(f"Reset proxy {proxy.server}:{proxy.port}")
    
    def get_best_proxies(self, count: int = 5) -> List[ProxyConfig]:
        """
        Get the best performing proxies
        
        Args:
            count: Number of best proxies to return
            
        Returns:
            List of best performing proxies
        """
        if not self.proxies:
            return []
        
        # Sort by success rate and response time
        sorted_proxies = sorted(
            [p for p in self.proxies if p.is_working],
            key=lambda p: (p.success_rate, -p.response_time),
            reverse=True
        )
        
        return sorted_proxies[:count]
    
    def distribute_proxies(self, bot_count: int) -> List[ProxyConfig]:
        """
        Distribute proxies among bots for load balancing
        
        Args:
            bot_count: Number of bots to distribute proxies among
            
        Returns:
            List of proxies distributed among bots
        """
        if not self.proxies:
            return []
        
        working_proxies = [p for p in self.proxies if p.is_working]
        
        if not working_proxies:
            logger.warning("No working proxies available for distribution")
            return []
        
        # Distribute proxies evenly
        distributed = []
        for i in range(bot_count):
            proxy = working_proxies[i % len(working_proxies)]
            distributed.append(proxy)
        
        return distributed
    
    def save_proxy_config(self, filepath: str):
        """
        Save current proxy configuration to file
        
        Args:
            filepath: Path to save configuration
        """
        try:
            with open(filepath, 'w') as f:
                f.write("# Proxy Configuration\n")
                f.write("# Format: server:port:username:password:protocol:timezone:location:country\n")
                f.write("# Generated by ProxyManager\n\n")
                
                for proxy in self.proxies:
                    line = f"{proxy.server}:{proxy.port}:{proxy.username}:{proxy.password}:{proxy.protocol}:{proxy.timezone}:{proxy.location}:{proxy.country}\n"
                    f.write(line)
            
            logger.info(f"Proxy configuration saved to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving proxy configuration: {e}")
