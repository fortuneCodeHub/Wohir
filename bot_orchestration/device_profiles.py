#!/usr/bin/python3
"""
Device Profile Management System
Generates realistic device profiles with proper distributions
Author: Fortune Nwohiri
"""

import random
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DeviceType(Enum):
    """Device types for bot profiles"""
    IPHONE = "iphone"
    ANDROID = "android"
    WINDOWS = "windows"
    MACOS = "macos"


@dataclass
class DeviceProfile:
    """Represents a complete device profile for bot simulation"""
    device_type: DeviceType
    model: str
    user_agent: str
    platform: str
    languages: List[str]
    vendor: str
    webgl_vendor: str
    renderer: str
    screen_width: int
    screen_height: int
    pixel_ratio: float
    timezone: str
    locale: str
    is_mobile: bool
    fingerprint_data: Dict


class DeviceProfileManager:
    """Manages device profile generation and distribution"""
    
    # Realistic device model distributions (weighted probabilities)
    DEVICE_MODELS = {
        DeviceType.IPHONE: {
            "iPhone 15 Pro Max": 5,
            "iPhone 15 Pro": 8,
            "iPhone 15": 10,
            "iPhone 14 Pro Max": 12,
            "iPhone 14": 15,
            "iPhone 13 Pro": 8,
            "iPhone 13": 18,
            "iPhone 12 Pro": 6,
            "iPhone 12": 12,
            "iPhone 11 Pro": 4,
            "iPhone 11": 8,
            "iPhone XR": 5,
            "iPhone X": 4,
            "iPhone 8": 3,
            "iPhone SE": 2
        },
        DeviceType.ANDROID: {
            "Samsung Galaxy S23 Ultra": 8,
            "Samsung Galaxy S23": 10,
            "Samsung Galaxy S22 Ultra": 6,
            "Samsung Galaxy S22": 8,
            "Samsung Galaxy A54": 15,
            "Samsung Galaxy A34": 12,
            "Google Pixel 8 Pro": 6,
            "Google Pixel 8": 8,
            "Google Pixel 7 Pro": 5,
            "Google Pixel 7": 7,
            "OnePlus 11": 5,
            "OnePlus 10 Pro": 4,
            "Xiaomi 13 Pro": 7,
            "Xiaomi 12": 6,
            "Motorola Edge 40": 10,
            "OPPO Find X6": 5,
            "Realme 11 Pro": 14,
            "Nothing Phone 2": 3
        },
        DeviceType.WINDOWS: {
            "Windows 11 - Chrome": 35,
            "Windows 11 - Edge": 25,
            "Windows 11 - Firefox": 8,
            "Windows 10 - Chrome": 20,
            "Windows 10 - Edge": 7,
            "Windows 10 - Firefox": 5
        },
        DeviceType.MACOS: {
            "macOS Sonoma - Safari": 30,
            "macOS Sonoma - Chrome": 20,
            "macOS Ventura - Safari": 25,
            "macOS Ventura - Chrome": 15,
            "macOS Monterey - Safari": 10
        }
    }
    
    # Screen resolutions and specifications for each device
    DEVICE_SPECS = {
        "iPhone 15 Pro Max": {
            "screen_width": 430, "screen_height": 932, "pixel_ratio": 3.0,
            "platform": "iPhone", "is_mobile": True
        },
        "iPhone 15 Pro": {
            "screen_width": 393, "screen_height": 852, "pixel_ratio": 3.0,
            "platform": "iPhone", "is_mobile": True
        },
        "iPhone 15": {
            "screen_width": 393, "screen_height": 852, "pixel_ratio": 3.0,
            "platform": "iPhone", "is_mobile": True
        },
        "iPhone 14 Pro Max": {
            "screen_width": 430, "screen_height": 932, "pixel_ratio": 3.0,
            "platform": "iPhone", "is_mobile": True
        },
        "iPhone 14": {
            "screen_width": 390, "screen_height": 844, "pixel_ratio": 3.0,
            "platform": "iPhone", "is_mobile": True
        },
        "iPhone 13 Pro": {
            "screen_width": 390, "screen_height": 844, "pixel_ratio": 3.0,
            "platform": "iPhone", "is_mobile": True
        },
        "iPhone 13": {
            "screen_width": 390, "screen_height": 844, "pixel_ratio": 3.0,
            "platform": "iPhone", "is_mobile": True
        },
        "iPhone 12 Pro": {
            "screen_width": 390, "screen_height": 844, "pixel_ratio": 3.0,
            "platform": "iPhone", "is_mobile": True
        },
        "iPhone 12": {
            "screen_width": 390, "screen_height": 844, "pixel_ratio": 3.0,
            "platform": "iPhone", "is_mobile": True
        },
        "iPhone 11 Pro": {
            "screen_width": 375, "screen_height": 812, "pixel_ratio": 3.0,
            "platform": "iPhone", "is_mobile": True
        },
        "iPhone 11": {
            "screen_width": 414, "screen_height": 896, "pixel_ratio": 2.0,
            "platform": "iPhone", "is_mobile": True
        },
        "iPhone XR": {
            "screen_width": 414, "screen_height": 896, "pixel_ratio": 2.0,
            "platform": "iPhone", "is_mobile": True
        },
        "iPhone X": {
            "screen_width": 375, "screen_height": 812, "pixel_ratio": 3.0,
            "platform": "iPhone", "is_mobile": True
        },
        "iPhone 8": {
            "screen_width": 375, "screen_height": 667, "pixel_ratio": 2.0,
            "platform": "iPhone", "is_mobile": True
        },
        "iPhone SE": {
            "screen_width": 375, "screen_height": 667, "pixel_ratio": 2.0,
            "platform": "iPhone", "is_mobile": True
        },
        "Samsung Galaxy S23 Ultra": {
            "screen_width": 412, "screen_height": 915, "pixel_ratio": 3.36,  # Updated DPR to exact (from ~3.5 approximation)
            "platform": "Linux armv8l", "is_mobile": True
        },
        "Samsung Galaxy S23": {
            "screen_width": 360, "screen_height": 780, "pixel_ratio": 3.0,
            "platform": "Linux armv8l", "is_mobile": True
        },
        "Samsung Galaxy S22 Ultra": {
            "screen_width": 412, "screen_height": 915, "pixel_ratio": 3.36,  # Updated DPR to match S23 Ultra equivalent
            "platform": "Linux armv8l", "is_mobile": True
        },
        "Samsung Galaxy S22": {
            "screen_width": 360, "screen_height": 780, "pixel_ratio": 3.0,
            "platform": "Linux armv8l", "is_mobile": True
        },
        "Samsung Galaxy A54": {
            "screen_width": 412, "screen_height": 915, "pixel_ratio": 2.625,  # Refined DPR for precision
            "platform": "Linux armv8l", "is_mobile": True
        },
        "Samsung Galaxy A34": {
            "screen_width": 412, "screen_height": 915, "pixel_ratio": 2.625,  # Refined DPR
            "platform": "Linux armv8l", "is_mobile": True
        },
        "Google Pixel 8 Pro": {
            "screen_width": 412, "screen_height": 915, "pixel_ratio": 3.0,  # Adjusted to standard emulation (from 3.5)
            "platform": "Linux armv8l", "is_mobile": True
        },
        "Google Pixel 8": {
            "screen_width": 412, "screen_height": 915, "pixel_ratio": 2.6,  # Refined DPR based on PPI
            "platform": "Linux armv8l", "is_mobile": True
        },
        "Google Pixel 7 Pro": {
            "screen_width": 412, "screen_height": 915, "pixel_ratio": 3.5,
            "platform": "Linux armv8l", "is_mobile": True
        },
        "Google Pixel 7": {
            "screen_width": 412, "screen_height": 915, "pixel_ratio": 2.6,  # Refined DPR
            "platform": "Linux armv8l", "is_mobile": True
        },
        "OnePlus 11": {
            "screen_width": 412, "screen_height": 915, "pixel_ratio": 3.5,  # Updated to match physical specs
            "platform": "Linux armv8l", "is_mobile": True
        },
        "OnePlus 10 Pro": {
            "screen_width": 412, "screen_height": 915, "pixel_ratio": 3.5,  # Updated DPR
            "platform": "Linux armv8l", "is_mobile": True
        },
        "Xiaomi 13 Pro": {
            "screen_width": 412, "screen_height": 915, "pixel_ratio": 3.2,  # Adjusted to approximate PPI-based DPR
            "platform": "Linux armv8l", "is_mobile": True
        },
        "Xiaomi 12": {
            "screen_width": 412, "screen_height": 915, "pixel_ratio": 3.0,
            "platform": "Linux armv8l", "is_mobile": True
        },
        "Motorola Edge 40": {
            "screen_width": 412, "screen_height": 915, "pixel_ratio": 2.6,
            "platform": "Linux armv8l", "is_mobile": True
        },
        "OPPO Find X6": {
            "screen_width": 412, "screen_height": 915, "pixel_ratio": 3.0,
            "platform": "Linux armv8l", "is_mobile": True
        },
        "Realme 11 Pro": {
            "screen_width": 412, "screen_height": 915, "pixel_ratio": 2.6,
            "platform": "Linux armv8l", "is_mobile": True
        },
        "Nothing Phone 2": {
            "screen_width": 412, "screen_height": 915, "pixel_ratio": 2.75,  # Refined DPR based on specs
            "platform": "Linux armv8l", "is_mobile": True
        },
        "Windows 11 - Chrome": {
            "screen_width": 1920, "screen_height": 1080, "pixel_ratio": 1.0,
            "platform": "Win32", "is_mobile": False
        },
        "Windows 11 - Edge": {
            "screen_width": 1920, "screen_height": 1080, "pixel_ratio": 1.0,
            "platform": "Win32", "is_mobile": False
        },
        "Windows 11 - Firefox": {
            "screen_width": 1920, "screen_height": 1080, "pixel_ratio": 1.0,
            "platform": "Win32", "is_mobile": False
        },
        "Windows 10 - Chrome": {
            "screen_width": 1920, "screen_height": 1080, "pixel_ratio": 1.0,
            "platform": "Win32", "is_mobile": False
        },
        "Windows 10 - Edge": {
            "screen_width": 1920, "screen_height": 1080, "pixel_ratio": 1.0,
            "platform": "Win32", "is_mobile": False
        },
        "Windows 10 - Firefox": {
            "screen_width": 1920, "screen_height": 1080, "pixel_ratio": 1.0,
            "platform": "Win32", "is_mobile": False
        },
        "macOS Sonoma - Safari": {
            "screen_width": 1440, "screen_height": 900, "pixel_ratio": 2.0,
            "platform": "MacIntel", "is_mobile": False
        },
        "macOS Sonoma - Chrome": {
            "screen_width": 1440, "screen_height": 900, "pixel_ratio": 2.0,
            "platform": "MacIntel", "is_mobile": False
        },
        "macOS Ventura - Safari": {
            "screen_width": 1440, "screen_height": 900, "pixel_ratio": 2.0,
            "platform": "MacIntel", "is_mobile": False
        },
        "macOS Ventura - Chrome": {
            "screen_width": 1440, "screen_height": 900, "pixel_ratio": 2.0,
            "platform": "MacIntel", "is_mobile": False
        },
        "macOS Monterey - Safari": {
            "screen_width": 1440, "screen_height": 900, "pixel_ratio": 2.0,
            "platform": "MacIntel", "is_mobile": False
        }
    }
    
    # User agent templates
    USER_AGENTS = {
        "iPhone 15 Pro Max": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        "iPhone 15 Pro": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        "iPhone 15": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        "iPhone 14 Pro Max": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "iPhone 14": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "iPhone 13 Pro": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        "iPhone 13": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        "iPhone 12 Pro": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
        "iPhone 12": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
        "iPhone 11 Pro": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
        "iPhone 11": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
        "iPhone XR": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
        "iPhone X": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
        "iPhone 8": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
        "iPhone SE": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
        "Samsung Galaxy S23 Ultra": "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Mobile Safari/537.36",
        "Samsung Galaxy S23": "Mozilla/5.0 (Linux; Android 13; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Mobile Safari/537.36",
        "Samsung Galaxy S22 Ultra": "Mozilla/5.0 (Linux; Android 12; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Mobile Safari/537.36",
        "Samsung Galaxy S22": "Mozilla/5.0 (Linux; Android 12; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Mobile Safari/537.36",
        "Samsung Galaxy A54": "Mozilla/5.0 (Linux; Android 13; SM-A546B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Mobile Safari/537.36",
        "Samsung Galaxy A34": "Mozilla/5.0 (Linux; Android 13; SM-A346B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Mobile Safari/537.36",
        "Google Pixel 8 Pro": "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36",
        "Google Pixel 8": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36",
        "Google Pixel 7 Pro": "Mozilla/5.0 (Linux; Android 13; Pixel 7 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Mobile Safari/537.36",
        "Google Pixel 7": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Mobile Safari/537.36",
        "OnePlus 11": "Mozilla/5.0 (Linux; Android 13; CPH2447) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Mobile Safari/537.36",
        "OnePlus 10 Pro": "Mozilla/5.0 (Linux; Android 12; CPH2207) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Mobile Safari/537.36",
        "Xiaomi 13 Pro": "Mozilla/5.0 (Linux; Android 13; 2211133C) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Mobile Safari/537.36",
        "Xiaomi 12": "Mozilla/5.0 (Linux; Android 12; 2201123G) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Mobile Safari/537.36",
        "Motorola Edge 40": "Mozilla/5.0 (Linux; Android 13; motorola edge 40) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Mobile Safari/537.36",
        "OPPO Find X6": "Mozilla/5.0 (Linux; Android 13; PGFM10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Mobile Safari/537.36",
        "Realme 11 Pro": "Mozilla/5.0 (Linux; Android 13; RMX3771) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Mobile Safari/537.36",
        "Nothing Phone 2": "Mozilla/5.0 (Linux; Android 13; A065) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Mobile Safari/537.36",
        "Windows 11 - Chrome": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Windows 11 - Edge": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
        "Windows 11 - Firefox": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
        "Windows 10 - Chrome": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "Windows 10 - Edge": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.2088.76",
        "Windows 10 - Firefox": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/118.0",
        "macOS Sonoma - Safari": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "macOS Sonoma - Chrome": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "macOS Ventura - Safari": "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
        "macOS Ventura - Chrome": "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "macOS Monterey - Safari": "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6.1 Safari/605.1.15"
    }
    
    # WebGL vendor and renderer combinations
    WEBGL_COMBINATIONS = [
        ("Intel Inc.", "Intel Iris OpenGL Engine"),
        ("Intel Inc.", "Intel HD Graphics 620"),
        ("Intel Inc.", "Intel UHD Graphics 630"),
        ("NVIDIA Corporation", "NVIDIA GeForce GTX 1060/PCIe/SSE2"),
        ("NVIDIA Corporation", "NVIDIA GeForce RTX 3070/PCIe/SSE2"),
        ("NVIDIA Corporation", "NVIDIA GeForce RTX 3080/PCIe/SSE2"),
        ("AMD", "AMD Radeon RX 580"),
        ("AMD", "AMD Radeon RX 6600 XT"),
        ("Apple Inc.", "Apple M1"),
        ("Apple Inc.", "Apple M2"),
        ("Apple Inc.", "Apple M2 Pro"),
        ("Qualcomm", "Adreno 650"),
        ("Qualcomm", "Adreno 730"),
        ("ARM", "Mali-G78 MP14"),
        ("ARM", "Mali-G710 MP7")
    ]
    
    # Language and locale combinations
    LANGUAGE_COMBINATIONS = {
        DeviceType.IPHONE: [
            ["en-US", "en"],
            ["en-GB", "en"],
            ["en-CA", "en"],
            ["en-AU", "en"],
            ["es-US", "es", "en"],
            ["fr-CA", "fr", "en"],
            ["de-DE", "de", "en"],
            ["ja-JP", "ja", "en"],
            ["ko-KR", "ko", "en"],
            ["zh-CN", "zh", "en"]
        ],
        DeviceType.ANDROID: [
            ["en-US", "en"],
            ["en-GB", "en"],
            ["en-IN", "en"],
            ["es-ES", "es", "en"],
            ["es-MX", "es", "en"],
            ["fr-FR", "fr", "en"],
            ["de-DE", "de", "en"],
            ["ja-JP", "ja", "en"],
            ["ko-KR", "ko", "en"],
            ["zh-CN", "zh", "en"],
            ["hi-IN", "hi", "en"],
            ["pt-BR", "pt", "en"]
        ],
        DeviceType.WINDOWS: [
            ["en-US", "en"],
            ["en-GB", "en"],
            ["en-CA", "en"],
            ["es-ES", "es", "en"],
            ["es-MX", "es", "en"],
            ["fr-FR", "fr", "en"],
            ["de-DE", "de", "en"],
            ["ja-JP", "ja", "en"],
            ["ko-KR", "ko", "en"],
            ["zh-CN", "zh", "en"],
            ["pt-BR", "pt", "en"],
            ["ru-RU", "ru", "en"]
        ],
        DeviceType.MACOS: [
            ["en-US", "en"],
            ["en-GB", "en"],
            ["en-CA", "en"],
            ["en-AU", "en"],
            ["es-ES", "es", "en"],
            ["es-MX", "es", "en"],
            ["fr-FR", "fr", "en"],
            ["fr-CA", "fr", "en"],
            ["de-DE", "de", "en"],
            ["ja-JP", "ja", "en"],
            ["ko-KR", "ko", "en"],
            ["zh-CN", "zh", "en"]
        ]
    }
    
    # Timezone distributions by region
    TIMEZONE_DISTRIBUTIONS = {
        "US": ["America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles"],
        "EU": ["Europe/London", "Europe/Paris", "Europe/Berlin", "Europe/Rome", "Europe/Madrid"],
        "ASIA": ["Asia/Tokyo", "Asia/Shanghai", "Asia/Seoul", "Asia/Hong_Kong", "Asia/Singapore"],
        "GLOBAL": ["America/New_York", "Europe/London", "Asia/Tokyo", "Australia/Sydney", "America/Sao_Paulo"]
    }
    
    @classmethod
    def distribute_devices(cls, device_type: DeviceType, count: int) -> Dict[str, int]:
        """
        Distribute device models based on weighted probabilities
        
        Args:
            device_type: Type of device to distribute
            count: Total number of devices to distribute
            
        Returns:
            Dict of {model: count} distribution
        """
        if device_type not in cls.DEVICE_MODELS:
            raise ValueError(f"Unsupported device type: {device_type}")
        
        models = cls.DEVICE_MODELS[device_type]
        weights = list(models.values())
        model_names = list(models.keys())
        
        # Generate distribution using weighted random selection
        distribution = {}
        for _ in range(count):
            chosen_model = random.choices(model_names, weights=weights)[0]
            distribution[chosen_model] = distribution.get(chosen_model, 0) + 1
        
        return distribution
    
    @classmethod
    def get_profile_by_name(cls, model_name: str) -> Optional[DeviceProfile]:
        """
        Get a specific device profile by model name
        
        Args:
            model_name: Exact model name (e.g., "Motorola Edge 40", "iPhone 13 Pro")
            
        Returns:
            DeviceProfile object or None if not found
        """
        # Find the device type for this model
        device_type = None
        for dt, models in cls.DEVICE_MODELS.items():
            if model_name in models:
                device_type = dt
                break
        
        if device_type is None:
            logger.warning(f"Model '{model_name}' not found in device models")
            return None
        
        # Generate profile with specific model
        return cls.generate_profile(device_type, model_name)
    
    @classmethod
    def list_available_models(cls) -> Dict[DeviceType, List[str]]:
        """
        Get a list of all available device models by type
        
        Returns:
            Dictionary mapping device types to lists of model names
        """
        return {dt: list(models.keys()) for dt, models in cls.DEVICE_MODELS.items()}
    
    @classmethod
    def search_models(cls, search_term: str) -> List[str]:
        """
        Search for device models containing the search term
        
        Args:
            search_term: Term to search for in model names
            
        Returns:
            List of matching model names
        """
        search_term = search_term.lower()
        matches = []
        
        for models in cls.DEVICE_MODELS.values():
            for model in models.keys():
                if search_term in model.lower():
                    matches.append(model)
        
        return matches

    @classmethod
    def generate_profile(cls, device_type: DeviceType, model: str = None) -> DeviceProfile:
        """
        Generate a complete device profile
        
        Args:
            device_type: Type of device
            model: Specific model (if None, randomly selected)
            
        Returns:
            Complete DeviceProfile object
        """
        if model is None:
            # Select random model based on distribution
            models = cls.DEVICE_MODELS[device_type]
            weights = list(models.values())
            model_names = list(models.keys())
            model = random.choices(model_names, weights=weights)[0]
        
        # Get device specifications
        specs = cls.DEVICE_SPECS.get(model, {
            "screen_width": 1920, "screen_height": 1080, "pixel_ratio": 1.0,
            "platform": "Win32", "is_mobile": False
        })
        
        # Get user agent
        user_agent = cls.USER_AGENTS.get(model, cls._generate_generic_ua(device_type))
        
        # Select languages
        languages = random.choice(cls.LANGUAGE_COMBINATIONS[device_type])
        
        # Select WebGL combination based on device type
        if device_type == DeviceType.IPHONE:
            webgl_vendor, renderer = "Apple Inc.", "Apple GPU"
        elif device_type == DeviceType.ANDROID:
            webgl_vendor, renderer = random.choice([
                ("Qualcomm", "Adreno 650"),
                ("Qualcomm", "Adreno 730"),
                ("ARM", "Mali-G78 MP14"),
                ("ARM", "Mali-G710 MP7")
            ])
        else:
            webgl_vendor, renderer = random.choice(cls.WEBGL_COMBINATIONS)
        
        # Select timezone based on device type (more consistent)
        if device_type == DeviceType.IPHONE:
            timezone = "America/New_York"  # Default iPhone timezone
        elif device_type == DeviceType.ANDROID:
            timezone = "Asia/Tokyo"  # Default Android timezone
        else:
            timezone = random.choice(random.choice(list(cls.TIMEZONE_DISTRIBUTIONS.values())))
        
        # Generate locale from languages
        locale = languages[0] if languages else "en-US"
        
        # Generate fingerprint data
        fingerprint_data = {
            "webgl_vendor": webgl_vendor,
            "webgl_renderer": renderer,
            "platform": specs["platform"],
            "languages": languages,
            "timezone": timezone,
            "screen_resolution": f"{specs['screen_width']}x{specs['screen_height']}",
            "pixel_ratio": specs["pixel_ratio"],
            "is_mobile": specs["is_mobile"],
            "user_agent": user_agent,
            "vendor": "Apple Computer, Inc." if device_type == DeviceType.IPHONE else "Google Inc." if device_type == DeviceType.ANDROID else "Mozilla"
        }
        
        return DeviceProfile(
            device_type=device_type,
            model=model,
            user_agent=user_agent,
            platform=specs["platform"],
            languages=languages,
            vendor=fingerprint_data["vendor"],
            webgl_vendor=webgl_vendor,
            renderer=renderer,
            screen_width=specs["screen_width"],
            screen_height=specs["screen_height"],
            pixel_ratio=specs["pixel_ratio"],
            timezone=timezone,
            locale=locale,
            is_mobile=specs["is_mobile"],
            fingerprint_data=fingerprint_data
        )
    
    @classmethod
    def _generate_generic_ua(cls, device_type: DeviceType) -> str:
        """Generate a generic user agent based on device type"""
        if device_type == DeviceType.IPHONE:
            return "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
        elif device_type == DeviceType.ANDROID:
            return "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Mobile Safari/537.36"
        elif device_type == DeviceType.WINDOWS:
            return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        else:  # macOS
            return "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15"
    
    @classmethod
    def get_device_summary(cls, device_type: DeviceType, count: int) -> str:
        """
        Get a summary of device distribution for logging
        
        Args:
            device_type: Type of device
            count: Number of devices
            
        Returns:
            Formatted summary string
        """
        distribution = cls.distribute_devices(device_type, count)
        
        summary = f"\n{device_type.value.upper()} Distribution ({count} bots):\n"
        summary += "-" * 40 + "\n"
        
        for model, model_count in sorted(distribution.items(), key=lambda x: x[1], reverse=True):
            percentage = (model_count / count) * 100
            summary += f"  {model}: {model_count} bots ({percentage:.1f}%)\n"
        
        return summary
