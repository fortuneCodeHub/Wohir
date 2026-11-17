#!/usr/bin/python3
"""
Bot Orchestration System
Multi-bot management with realistic device profiles and anti-detection
Author: Peter Ekwere
"""

from .device_profiles import DeviceProfileManager, DeviceProfile, DeviceType
from .persona_generator import PersonaGenerator, UserPersona
from .proxy_manager import ProxyManager, ProxyConfig
from .fingerprint_utils import FingerprintGenerator
from .thread_executor import BotThreadExecutor

__version__ = "1.0.0"
__author__ = "Peter Ekwere"

__all__ = [
    'DeviceProfileManager',
    'DeviceProfile',
    'DeviceType',
    'PersonaGenerator',
    'UserPersona',
    'CampaignType',
    'ProxyManager',
    'ProxyConfig',
    'FingerprintGenerator',
    'BotThreadExecutor',
]
