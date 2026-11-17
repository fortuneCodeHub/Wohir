#!/usr/bin/python3
"""
Thread Pool Executor for Bot Orchestration
Automatically calculates optimal worker count and manages concurrent bot execution
Author: Peter Ekwere
"""

import os
import psutil
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, List, Any, Optional, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class BotThreadExecutor:
    """
    Intelligent thread pool executor for bot orchestration.
    Automatically calculates optimal worker count based on system resources.
    """
    
    def __init__(self):
        """Initialize the executor with optimal worker count."""
        import sys
        # ESSENTIAL: Enable thread locking for SeleniumBase
        if "-n" not in sys.argv:
            sys.argv.append("-n")
        self.max_workers = self._calculate_optimal_workers()
        self.executor = None
        logger.info(f"BotThreadExecutor initialized with {self.max_workers} max workers")
    
    def _calculate_optimal_workers(self) -> int:
        """
        Calculate optimal number of workers for Selenium browser automation.
        
        Key factors:
        - CPU cores (for browser rendering)
        - Available RAM (Chrome is memory-hungry: 500MB-1GB per instance)
        - I/O operations (network requests, page loading)
        
        For I/O-bound tasks like web automation: 2-3x CPU cores is optimal
        But limited by memory constraints for Chrome browsers
        """
        try:
            # Get system resources
            cpu_count = os.cpu_count() or 1
            memory_gb = psutil.virtual_memory().available / (1024**3)
            
            logger.info(f"System resources - CPUs: {cpu_count}, Available RAM: {memory_gb:.2f}GB")
            
            # Chrome memory calculation
            # Conservative estimate: 800MB per Chrome instance (with profile, extensions, etc.)
            memory_per_browser_gb = 0.8
            
            # Leave 2GB for system + main process
            usable_memory_gb = max(0, memory_gb - 2)
            
            # Calculate limits
            memory_limit = int(usable_memory_gb / memory_per_browser_gb)
            
            # For I/O-bound tasks (web automation), use 2-3x CPU cores
            # But we're conservative due to Chrome's resource intensity
            cpu_limit = cpu_count * 2
            
            # Take the minimum (bottleneck determines max workers)
            optimal = min(cpu_limit, memory_limit)
            
            # Safety bounds: minimum 1, maximum 10 (more can cause instability)
            optimal = max(1, min(optimal, 10))
            
            logger.info(f"Worker calculation - CPU limit: {cpu_limit}, Memory limit: {memory_limit}, Optimal: {optimal}")
            
            return optimal
            
        except Exception as e:
            logger.warning(f"Error calculating optimal workers: {e}. Using safe default of 2.")
            return 2
    
    def get_max_workers(self) -> int:
        """Get the maximum number of workers this executor can handle."""
        return self.max_workers
    
    def can_run_bots(self, bot_count: int) -> bool:
        """
        Check if the system can handle the requested number of bots.
        
        Args:
            bot_count: Number of bots to run
            
        Returns:
            bool: True if system can handle the load, False otherwise
        """
        if bot_count <= 0:
            logger.error("Bot count must be greater than 0")
            return False
            
        if bot_count > self.max_workers:
            logger.error(f"Requested {bot_count} bots exceeds maximum capacity of {self.max_workers}")
            return False
            
        return True
    
    def run_bots_with_configs(
        self, 
        bot_function: Callable, 
        configs: List[Dict[str, Any]], 
        timeout: int = 300
    ) -> List[Any]:
        """
        Run multiple bots concurrently with different configurations.
        Perfect for running different device profiles, personas, or settings simultaneously.
        
        Args:
            bot_function: Function to execute for each bot. 
                         Should accept unpacked config dict as arguments
            configs: List of configuration dictionaries. Each dict will be unpacked 
                    as **kwargs to bot_function
            timeout: Timeout in seconds for each bot (default: 300s/5min)
            
        Returns:
            List of results from bot executions (same order as configs)
            
        Raises:
            ValueError: If config count exceeds system capacity
            
        Example:
            ```python
            def run_mobile_bot(device_profile, persona, device_name):
                # Bot logic here
                return True
            
            executor = BotThreadExecutor()
            
            configs = [
                {
                    'device_profile': iphone_profile,
                    'persona': iphone_persona,
                    'device_name': 'iPhone'
                },
                {
                    'device_profile': samsung_profile,
                    'persona': samsung_persona,
                    'device_name': 'Samsung'
                }
            ]
            
            results = executor.run_bots_with_configs(run_mobile_bot, configs)
            ```
        """
        bot_count = len(configs)
        
        if not self.can_run_bots(bot_count):
            raise ValueError(f"Cannot run {bot_count} bots. Maximum capacity: {self.max_workers}")
        
        logger.info(f"Starting {bot_count} bots with different configurations")
        
        results = []
        with ThreadPoolExecutor(max_workers=min(bot_count, self.max_workers)) as executor:
            # Submit all bot tasks with their specific configs
            futures = []
            for i, config in enumerate(configs):
                future = executor.submit(bot_function, **config)
                futures.append((i, future, config))
                
                # Log config info if available
                config_name = config.get('device_name') or config.get('name') or f"Bot {i+1}"
                logger.debug(f"Submitted {config_name} ({i+1}/{bot_count})")
            
            # Collect results in order
            results = [None] * bot_count  # Pre-allocate to maintain order
            
            for i, future, config in futures:
                config_name = config.get('device_name') or config.get('name') or f"Bot {i+1}"
                try:
                    result = future.result(timeout=timeout)
                    results[i] = result
                    logger.info(f"{config_name} completed successfully")
                except Exception as e:
                    logger.error(f"{config_name} failed: {e}")
                    results[i] = None
        
        successful_bots = sum(1 for r in results if r is not None)
        logger.info(f"Multi-config execution completed: {successful_bots}/{bot_count} successful")
        
        return results