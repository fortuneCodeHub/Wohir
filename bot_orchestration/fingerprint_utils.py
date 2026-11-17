#!/usr/bin/python3
"""
Advanced Fingerprinting and Anti-Detection Utilities
BrowserForge-style fingerprint generation and stealth techniques
Author: Peter Ekwere
"""

import random
import hashlib
import json
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class FingerprintData:
    """Complete fingerprint data for anti-detection"""
    user_agent: str
    platform: str
    languages: List[str]
    vendor: str
    webgl_vendor: str
    webgl_renderer: str
    screen_width: int
    screen_height: int
    pixel_ratio: float
    timezone: str
    locale: str
    canvas_fingerprint: str
    audio_fingerprint: str
    font_fingerprint: str
    hardware_concurrency: int
    device_memory: int
    max_touch_points: int
    plugins: List[Dict]
    mime_types: List[Dict]
    battery_info: Dict
    connection_info: Dict
    media_devices: List[Dict]
    permissions: Dict
    full_fingerprint: Dict


class FingerprintGenerator:
    """Generates realistic browser fingerprints for anti-detection"""
    
    def __init__(self):
        # WebGL vendor and renderer combinations (realistic distributions)
        self.webgl_combinations = [
            ("Intel Inc.", "Intel Iris OpenGL Engine", 0.25),
            ("Intel Inc.", "Intel HD Graphics 620", 0.15),
            ("Intel Inc.", "Intel UHD Graphics 630", 0.10),
            ("NVIDIA Corporation", "NVIDIA GeForce GTX 1060/PCIe/SSE2", 0.08),
            ("NVIDIA Corporation", "NVIDIA GeForce RTX 3070/PCIe/SSE2", 0.05),
            ("NVIDIA Corporation", "NVIDIA GeForce RTX 3080/PCIe/SSE2", 0.03),
            ("AMD", "AMD Radeon RX 580", 0.06),
            ("AMD", "AMD Radeon RX 6600 XT", 0.04),
            ("Apple Inc.", "Apple M1", 0.08),
            ("Apple Inc.", "Apple M2", 0.05),
            ("Apple Inc.", "Apple M2 Pro", 0.03),
            ("Qualcomm", "Adreno 650", 0.04),
            ("Qualcomm", "Adreno 730", 0.03),
            ("ARM", "Mali-G78 MP14", 0.03),
            ("ARM", "Mali-G710 MP7", 0.02)
        ]
        
        # Common browser plugins
        self.plugin_templates = {
            "chrome": [
                {"name": "Chrome PDF Plugin", "filename": "internal-pdf-viewer", "description": "Portable Document Format"},
                {"name": "Chrome PDF Viewer", "filename": "mhjfbmdgcfjbbpaeojofohoefgiehjai", "description": ""},
                {"name": "Native Client", "filename": "internal-nacl-plugin", "description": ""},
                {"name": "WebKit built-in PDF", "filename": "internal-pdf-viewer", "description": "Portable Document Format"},
                {"name": "Microsoft Edge PDF Viewer", "filename": "pdf", "description": "Portable Document Format"},
                {"name": "WebKit built-in PDF", "filename": "internal-pdf-viewer", "description": "Portable Document Format"}
            ],
            "firefox": [
                {"name": "PDF.js", "filename": "pdfjs-dist", "description": "Portable Document Format"},
                {"name": "OpenH264 Video Codec", "filename": "gmp-gmpopenh264", "description": "OpenH264 Video Codec provided by Cisco Systems, Inc."},
                {"name": "Widevine Content Decryption Module", "filename": "gmp-widevinecdm", "description": "Enables Widevine licenses for playback of HTML audio/video content."}
            ],
            "safari": [
                {"name": "WebKit built-in PDF", "filename": "internal-pdf-viewer", "description": "Portable Document Format"},
                {"name": "WebKit built-in QuickTime Plugin", "filename": "internal-qt-plugin", "description": "QuickTime Plugin 7.7.3"},
                {"name": "WebKit built-in Silverlight Plug-In", "filename": "internal-silverlight-plugin", "description": "Silverlight Plug-In"}
            ]
        }
        
        # MIME types by browser
        self.mime_type_templates = {
            "chrome": [
                {"type": "application/pdf", "description": "Portable Document Format", "suffixes": "pdf"},
                {"type": "application/x-google-chrome-pdf", "description": "Portable Document Format", "suffixes": "pdf"},
                {"type": "application/x-nacl", "description": "Native Client Executable", "suffixes": ""},
                {"type": "application/x-pnacl", "description": "Portable Native Client Executable", "suffixes": ""}
            ],
            "firefox": [
                {"type": "application/pdf", "description": "Portable Document Format", "suffixes": "pdf"},
                {"type": "application/x-google-chrome-pdf", "description": "Portable Document Format", "suffixes": "pdf"},
                {"type": "video/mp4", "description": "MP4 Video", "suffixes": "mp4"},
                {"type": "audio/mp4", "description": "MP4 Audio", "suffixes": "mp4"}
            ],
            "safari": [
                {"type": "application/pdf", "description": "Portable Document Format", "suffixes": "pdf"},
                {"type": "video/quicktime", "description": "QuickTime movie", "suffixes": "mov"},
                {"type": "application/x-silverlight", "description": "Silverlight", "suffixes": "xap"}
            ]
        }
        
        # Font lists by platform
        self.font_lists = {
            "windows": [
                "Arial", "Arial Black", "Calibri", "Cambria", "Candara", "Comic Sans MS",
                "Consolas", "Courier New", "Georgia", "Impact", "Lucida Console",
                "Lucida Sans Unicode", "Microsoft Sans Serif", "Palatino Linotype",
                "Segoe UI", "Tahoma", "Times New Roman", "Trebuchet MS", "Verdana"
            ],
            "macos": [
                "Arial", "Arial Black", "Arial Narrow", "Arial Rounded MT Bold",
                "Avenir", "Avenir Next", "Baskerville", "Big Caslon", "Bodoni 72",
                "Bradley Hand", "Brush Script MT", "Chalkduster", "Charter",
                "Cochin", "Comic Sans MS", "Copperplate", "Courier", "Courier New",
                "Didot", "Futura", "Geneva", "Georgia", "Gill Sans", "Helvetica",
                "Helvetica Neue", "Hoefler Text", "Impact", "Lucida Grande",
                "Marker Felt", "Menlo", "Monaco", "Optima", "Palatino", "Papyrus",
                "Phosphate", "Skia", "Tahoma", "Times", "Times New Roman",
                "Trebuchet MS", "Verdana", "Zapfino"
            ],
            "linux": [
                "Arial", "Arial Black", "Bitstream Vera Sans", "Bitstream Vera Serif",
                "Century Schoolbook L", "Courier", "Courier New", "DejaVu Sans",
                "DejaVu Sans Mono", "DejaVu Serif", "FreeMono", "FreeSans",
                "FreeSerif", "Georgia", "Liberation Mono", "Liberation Sans",
                "Liberation Serif", "Nimbus Mono L", "Nimbus Roman No9 L",
                "Nimbus Sans L", "Times New Roman", "URW Bookman L",
                "URW Gothic L", "URW Palladio L", "Verdana"
            ]
        }
    
    def generate_fingerprint(self, device_profile, persona) -> FingerprintData:
        """
        Generate complete fingerprint data
        
        Args:
            device_profile: DeviceProfile object
            persona: UserPersona object
            
        Returns:
            Complete FingerprintData object
        """
        # Generate WebGL fingerprint
        webgl_vendor, webgl_renderer = self._generate_webgl_fingerprint(device_profile)
        
        # Generate canvas fingerprint
        canvas_fingerprint = self._generate_canvas_fingerprint(device_profile)
        
        # Generate audio fingerprint
        audio_fingerprint = self._generate_audio_fingerprint(device_profile)
        
        # Generate font fingerprint
        font_fingerprint = self._generate_font_fingerprint(device_profile)
        
        # Generate hardware info
        hardware_concurrency = self._generate_hardware_concurrency(device_profile)
        device_memory = self._generate_device_memory(device_profile)
        max_touch_points = self._generate_touch_points(device_profile)
        
        # Generate plugins and MIME types
        plugins = self._generate_plugins(device_profile)
        mime_types = self._generate_mime_types(device_profile)
        
        # Generate battery info
        battery_info = self._generate_battery_info(device_profile)
        
        # Generate connection info
        connection_info = self._generate_connection_info(device_profile)
        
        # Generate media devices
        media_devices = self._generate_media_devices(device_profile)
        
        # Generate permissions
        permissions = self._generate_permissions(device_profile, persona)
        
        # Create full fingerprint
        full_fingerprint = {
            "user_agent": device_profile.user_agent,
            "platform": device_profile.platform,
            "languages": device_profile.languages,
            "vendor": device_profile.vendor,
            "webgl": {
                "vendor": webgl_vendor,
                "renderer": webgl_renderer
            },
            "screen": {
                "width": device_profile.screen_width,
                "height": device_profile.screen_height,
                "pixel_ratio": device_profile.pixel_ratio
            },
            "timezone": device_profile.timezone,
            "locale": device_profile.locale,
            "canvas": canvas_fingerprint,
            "audio": audio_fingerprint,
            "fonts": font_fingerprint,
            "hardware": {
                "concurrency": hardware_concurrency,
                "memory": device_memory,
                "touch_points": max_touch_points
            },
            "plugins": plugins,
            "mime_types": mime_types,
            "battery": battery_info,
            "connection": connection_info,
            "media_devices": media_devices,
            "permissions": permissions
        }
        
        return FingerprintData(
            user_agent=device_profile.user_agent,
            platform=device_profile.platform,
            languages=device_profile.languages,
            vendor=device_profile.vendor,
            webgl_vendor=webgl_vendor,
            webgl_renderer=webgl_renderer,
            screen_width=device_profile.screen_width,
            screen_height=device_profile.screen_height,
            pixel_ratio=device_profile.pixel_ratio,
            timezone=device_profile.timezone,
            locale=device_profile.locale,
            canvas_fingerprint=canvas_fingerprint,
            audio_fingerprint=audio_fingerprint,
            font_fingerprint=font_fingerprint,
            hardware_concurrency=hardware_concurrency,
            device_memory=device_memory,
            max_touch_points=max_touch_points,
            plugins=plugins,
            mime_types=mime_types,
            battery_info=battery_info,
            connection_info=connection_info,
            media_devices=media_devices,
            permissions=permissions,
            full_fingerprint=full_fingerprint
        )
    
    def _generate_webgl_fingerprint(self, device_profile) -> Tuple[str, str]:
        """Generate WebGL vendor and renderer"""
        # Weighted selection based on device type
        if device_profile.device_type.value == "iphone":
            # iPhone typically uses Apple GPUs
            apple_combinations = [combo for combo in self.webgl_combinations if "Apple" in combo[0]]
            if apple_combinations:
                return random.choice(apple_combinations)[:2]
        
        elif device_profile.device_type.value == "android":
            # Android uses Qualcomm or ARM GPUs
            mobile_combinations = [combo for combo in self.webgl_combinations if any(x in combo[0] for x in ["Qualcomm", "ARM"])]
            if mobile_combinations:
                return random.choice(mobile_combinations)[:2]
        
        # Default weighted selection
        weights = [combo[2] for combo in self.webgl_combinations]
        selected = random.choices(self.webgl_combinations, weights=weights)[0]
        return selected[0], selected[1]
    
    def _generate_canvas_fingerprint(self, device_profile) -> str:
        """Generate canvas fingerprint hash"""
        # Create a deterministic but varied canvas fingerprint
        base_string = f"{device_profile.platform}_{device_profile.screen_width}_{device_profile.screen_height}_{device_profile.pixel_ratio}"
        
        # Add some randomness but keep it consistent for the same device
        random.seed(hash(base_string))
        noise = random.randint(1000, 9999)
        random.seed()  # Reset random seed
        
        fingerprint_string = f"{base_string}_{noise}"
        return hashlib.md5(fingerprint_string.encode()).hexdigest()[:16]
    
    def _generate_audio_fingerprint(self, device_profile) -> str:
        """Generate audio fingerprint hash"""
        # Audio fingerprint based on device characteristics
        base_string = f"audio_{device_profile.platform}_{device_profile.vendor}"
        
        # Add device-specific audio characteristics
        if device_profile.is_mobile:
            base_string += "_mobile"
        else:
            base_string += "_desktop"
        
        return hashlib.sha256(base_string.encode()).hexdigest()[:16]
    
    def _generate_font_fingerprint(self, device_profile) -> str:
        """Generate font fingerprint based on platform"""
        platform = device_profile.platform.lower()
        
        if "win" in platform:
            font_list = self.font_lists["windows"]
        elif "mac" in platform:
            font_list = self.font_lists["macos"]
        else:
            font_list = self.font_lists["linux"]
        
        # Select a subset of fonts (realistic for most systems)
        selected_fonts = random.sample(font_list, min(len(font_list), random.randint(15, 25)))
        font_string = ",".join(sorted(selected_fonts))
        
        return hashlib.md5(font_string.encode()).hexdigest()[:16]
    
    def _generate_hardware_concurrency(self, device_profile) -> int:
        """Generate realistic hardware concurrency"""
        if device_profile.is_mobile:
            # Mobile devices typically have 4-8 cores
            return random.choice([4, 6, 8])
        else:
            # Desktop devices typically have 4-16 cores
            return random.choice([4, 6, 8, 12, 16])
    
    def _generate_device_memory(self, device_profile) -> int:
        """Generate realistic device memory in GB"""
        if device_profile.is_mobile:
            # Mobile devices typically have 4-16GB
            return random.choice([4, 6, 8, 12, 16])
        else:
            # Desktop devices typically have 8-32GB
            return random.choice([8, 16, 32])
    
    def _generate_touch_points(self, device_profile) -> int:
        """Generate max touch points"""
        if device_profile.is_mobile:
            return random.choice([5, 10, 20])
        else:
            return 0
    
    def _generate_plugins(self, device_profile) -> List[Dict]:
        """Generate realistic browser plugins"""
        user_agent = device_profile.user_agent.lower()
        
        if "chrome" in user_agent:
            browser_type = "chrome"
        elif "firefox" in user_agent:
            browser_type = "firefox"
        elif "safari" in user_agent:
            browser_type = "safari"
        else:
            browser_type = "chrome"  # Default
        
        plugins = self.plugin_templates[browser_type].copy()
        
        # Randomly remove some plugins (not all systems have all plugins)
        if random.random() < 0.3:
            plugins = random.sample(plugins, random.randint(2, len(plugins)))
        
        return plugins
    
    def _generate_mime_types(self, device_profile) -> List[Dict]:
        """Generate MIME types based on browser"""
        user_agent = device_profile.user_agent.lower()
        
        if "chrome" in user_agent:
            browser_type = "chrome"
        elif "firefox" in user_agent:
            browser_type = "firefox"
        elif "safari" in user_agent:
            browser_type = "safari"
        else:
            browser_type = "chrome"
        
        return self.mime_type_templates[browser_type].copy()
    
    def _generate_battery_info(self, device_profile) -> Dict:
        """Generate battery information"""
        if device_profile.is_mobile:
            return {
                "charging": random.choice([True, False]),
                "chargingTime": random.randint(0, 7200) if random.choice([True, False]) else float('inf'),
                "dischargingTime": random.randint(1800, 28800),
                "level": round(random.uniform(0.1, 1.0), 2)
            }
        else:
            # Desktop devices typically don't have battery info
            return {}
    
    def _generate_connection_info(self, device_profile) -> Dict:
        """Generate connection information"""
        connection_types = ["4g", "wifi", "ethernet", "bluetooth"]
        
        if device_profile.is_mobile:
            connection_type = random.choice(["4g", "wifi"])
            downlink = random.choice([10, 50, 100, 200])  # Mbps
        else:
            connection_type = random.choice(["wifi", "ethernet"])
            downlink = random.choice([50, 100, 200, 500, 1000])  # Mbps
        
        return {
            "effectiveType": connection_type,
            "downlink": downlink,
            "rtt": random.randint(20, 200),  # Round trip time in ms
            "saveData": random.choice([True, False])
        }
    
    def _generate_media_devices(self, device_profile) -> List[Dict]:
        """Generate media devices"""
        devices = []
        
        # Camera
        if random.random() < 0.8:  # 80% chance of having camera
            devices.append({
                "deviceId": f"camera_{random.randint(1000, 9999)}",
                "kind": "videoinput",
                "label": "Camera",
                "groupId": f"group_{random.randint(1000, 9999)}"
            })
        
        # Microphone
        if random.random() < 0.9:  # 90% chance of having microphone
            devices.append({
                "deviceId": f"mic_{random.randint(1000, 9999)}",
                "kind": "audioinput",
                "label": "Microphone",
                "groupId": f"group_{random.randint(1000, 9999)}"
            })
        
        # Speakers
        devices.append({
            "deviceId": f"speaker_{random.randint(1000, 9999)}",
            "kind": "audiooutput",
            "label": "Speakers",
            "groupId": f"group_{random.randint(1000, 9999)}"
        })
        
        return devices
    
    def _generate_permissions(self, device_profile, persona) -> Dict:
        """Generate permission states based on device and persona"""
        permissions = {}
        
        # Camera permission
        if device_profile.is_mobile and random.random() < 0.7:
            permissions["camera"] = random.choice(["granted", "denied", "prompt"])
        
        # Microphone permission
        if random.random() < 0.6:
            permissions["microphone"] = random.choice(["granted", "denied", "prompt"])
        
        # Location permission
        if device_profile.is_mobile and random.random() < 0.5:
            permissions["geolocation"] = random.choice(["granted", "denied", "prompt"])
        
        # Notification permission
        if random.random() < 0.3:
            permissions["notifications"] = random.choice(["granted", "denied", "prompt"])
        
        return permissions
    
    def apply_fingerprint_to_driver(self, driver, fingerprint):
        """
        Apply fingerprint CORRECTLY with CDP Page.addScriptToEvaluateOnNewDocument
        This ensures fingerprint is applied BEFORE any page loads
        """
        try:
            from selenium_stealth import stealth
            
            # Step 1: Use selenium-stealth for core fingerprinting
            stealth(
                driver,
                languages=fingerprint.languages,
                vendor=fingerprint.vendor,
                platform=fingerprint.platform,
                webgl_vendor=fingerprint.webgl_vendor,
                renderer=fingerprint.webgl_renderer,
                fix_hairline=True,
            )
            
        
            # Step 1: Build the comprehensive fingerprint script
            script = self._build_fingerprint_script(fingerprint)
            
            # Step 2: Inject using CDP (applies to ALL pages before they load)
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': script
            })
            
            # Step 3: Apply CDP overrides
            self._apply_cdp_overrides(driver, fingerprint)
            # Step 3: Add minimal custom JavaScript for properties stealth doesn't handle
            custom_script = f"""
            Object.defineProperty(navigator, 'hardwareConcurrency', {{
                get: () => {fingerprint.hardware_concurrency}
            }});
            Object.defineProperty(navigator, 'deviceMemory', {{
                get: () => {fingerprint.device_memory}
            }});
            Object.defineProperty(navigator, 'maxTouchPoints', {{
                get: () => {fingerprint.max_touch_points}
            }});
            """
            
            driver.execute_script(custom_script)
            
            print(f"✅ Fingerprint applied: {fingerprint.platform} - {fingerprint.user_agent[:50]}...")
            
        except Exception as e:
            print(f"❌ Error applying fingerprint: {e}")

        return driver
            
            
    def _build_fingerprint_script(self, fingerprint) -> str:
        """Build the complete fingerprint injection script"""
        
        # Convert Python objects to JavaScript-safe JSON
        plugins_js = json.dumps([{
            'name': p.get('name', ''),
            'filename': p.get('filename', ''),
            'description': p.get('description', '')
        } for p in fingerprint.plugins])
        
        mime_types_js = json.dumps([{
            'type': m.get('type', ''),
            'description': m.get('description', ''),
            'suffixes': m.get('suffixes', '')
        } for m in fingerprint.mime_types])
        
        languages_js = json.dumps(fingerprint.languages)
        battery_js = json.dumps(fingerprint.battery_info) if fingerprint.battery_info else '{}'
        connection_js = json.dumps(fingerprint.connection_info)
        media_devices_js = json.dumps(fingerprint.media_devices)
        permissions_js = json.dumps(fingerprint.permissions)
        
        # Build comprehensive script
        script = f"""
        (function() {{
            'use strict';
            
            try {{
            // ============ NAVIGATOR OVERRIDES ============
            
            // Platform (CRITICAL - this shows OS)
            Object.defineProperty(navigator, 'platform', {{
                get: () => '{fingerprint.platform}'
            }});
            
            // User Agent
            Object.defineProperty(navigator, 'userAgent', {{
                get: () => '{fingerprint.user_agent}'
            }});
            
            // App Version
            Object.defineProperty(navigator, 'appVersion', {{
                get: () => '{fingerprint.user_agent.replace("Mozilla/", "")}'
            }});
            
            // Vendor
            Object.defineProperty(navigator, 'vendor', {{
                get: () => '{fingerprint.vendor}'
            }});
            
            // Languages
            Object.defineProperty(navigator, 'languages', {{
                get: () => {languages_js}
            }});
            
            Object.defineProperty(navigator, 'language', {{
                get: () => '{fingerprint.languages[0] if fingerprint.languages else "en-US"}'
            }});
            
            // Hardware
            Object.defineProperty(navigator, 'hardwareConcurrency', {{
                get: () => {fingerprint.hardware_concurrency}
            }});
            
            Object.defineProperty(navigator, 'deviceMemory', {{
                get: () => {fingerprint.device_memory}
            }});
            
            Object.defineProperty(navigator, 'maxTouchPoints', {{
                get: () => {fingerprint.max_touch_points}
            }});
            
            // ============ WEBGL OVERRIDES ============
            
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {{
                // UNMASKED_VENDOR_WEBGL
                if (parameter === 37445) {{
                    return '{fingerprint.webgl_vendor}';
                }}
                // UNMASKED_RENDERER_WEBGL
                if (parameter === 37446) {{
                    return '{fingerprint.webgl_renderer}';
                }}
                return getParameter.call(this, parameter);
            }};
            
            // WebGL2 support
            if (typeof WebGL2RenderingContext !== 'undefined') {{
                const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
                WebGL2RenderingContext.prototype.getParameter = function(parameter) {{
                    if (parameter === 37445) {{
                        return '{fingerprint.webgl_vendor}';
                    }}
                    if (parameter === 37446) {{
                        return '{fingerprint.webgl_renderer}';
                    }}
                    return getParameter2.call(this, parameter);
                }};
            }}
            
            // ============ SCREEN OVERRIDES ============
            
            Object.defineProperty(screen, 'width', {{
                get: () => {fingerprint.screen_width}
            }});
            
            Object.defineProperty(screen, 'height', {{
                get: () => {fingerprint.screen_height}
            }});
            
            Object.defineProperty(screen, 'availWidth', {{
                get: () => {fingerprint.screen_width}
            }});
            
            Object.defineProperty(screen, 'availHeight', {{
                get: () => {fingerprint.screen_height}
            }});
            
            Object.defineProperty(window, 'devicePixelRatio', {{
                get: () => {fingerprint.pixel_ratio}
            }});
            
            // ============ CANVAS FINGERPRINTING ============
            
            const canvasNoise = {random.randint(1, 5)};
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            const originalToBlob = HTMLCanvasElement.prototype.toBlob;
            const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;
            
            // Add consistent noise to canvas
            HTMLCanvasElement.prototype.toDataURL = function() {{
                const context = this.getContext('2d');
                if (context) {{
                    const imageData = context.getImageData(0, 0, this.width, this.height);
                    for (let i = 0; i < imageData.data.length; i += 4) {{
                        imageData.data[i] = (imageData.data[i] + canvasNoise) % 256;
                    }}
                    context.putImageData(imageData, 0, 0);
                }}
                return originalToDataURL.apply(this, arguments);
            }};
            
            // ============ PLUGINS & MIME TYPES ============
            
            // Convert to PluginArray-like object
            const pluginsArray = {plugins_js};
            Object.setPrototypeOf(pluginsArray, PluginArray.prototype);
            Object.defineProperty(navigator, 'plugins', {{
                get: () => pluginsArray
            }});
            
            // Convert to MimeTypeArray-like object
            const mimeTypesArray = {mime_types_js};
            Object.setPrototypeOf(mimeTypesArray, MimeTypeArray.prototype);
            Object.defineProperty(navigator, 'mimeTypes', {{
                get: () => mimeTypesArray
            }});
            
            // ============ BATTERY API ============
            
            if ('getBattery' in navigator) {{
                const batteryInfo = {battery_js};
                navigator.getBattery = () => Promise.resolve(batteryInfo);
            }}
            
            // ============ CONNECTION API ============
            
            const connectionInfo = {connection_js};
            if ('connection' in navigator) {{
                Object.defineProperty(navigator, 'connection', {{
                    get: () => connectionInfo,
                    configurable: true
                }});
            }}
            
            // ============ MEDIA DEVICES API ============
            
            const mediaDevicesList = {media_devices_js};
            if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {{
                navigator.mediaDevices.enumerateDevices = () => Promise.resolve(mediaDevicesList);
            }}
            
            // ============ PERMISSIONS API ============
            
            const permissionsMap = {permissions_js};
            if (navigator.permissions && navigator.permissions.query) {{
                const originalQuery = navigator.permissions.query;
                navigator.permissions.query = function(descriptor) {{
                    const state = permissionsMap[descriptor.name] || 'prompt';
                    return Promise.resolve({{ state: state, onchange: null }});
                }};
            }}
            
            // ============ TIMEZONE OVERRIDE ============
            
            const timezone = '{fingerprint.timezone}';
            Date.prototype.getTimezoneOffset = function() {{
                // This is a simplified override - real implementation would be more complex
                return 0; // UTC offset
            }};
            
            // ============ WEBDRIVER DETECTION ============
            
            // Remove webdriver property
            Object.defineProperty(navigator, 'webdriver', {{
                get: () => undefined
            }});
            
            // Remove automation flags
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            
            // Chrome runtime
            if (window.chrome) {{
                Object.defineProperty(window.chrome, 'runtime', {{
                    get: () => ({{}}),
                    configurable: true
                }});
            }}
            
            console.log('🎭 Fingerprint injected successfully');

        }} catch (error) {{
            console.error('❌ Fingerprint injection failed:', error);
        }}
        }})();
        """
        return script
    
    def _apply_cdp_overrides(self, driver, fingerprint):
        """Apply Chrome DevTools Protocol overrides"""
        try:
            # User Agent Override
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                'userAgent': fingerprint.user_agent,
                'platform': fingerprint.platform,
                'acceptLanguage': ','.join(fingerprint.languages)
            })
            
            # Timezone Override
            try:
                driver.execute_cdp_cmd('Emulation.setTimezoneOverride', {
                    'timezoneId': fingerprint.timezone
                })
            except:
                pass  # Not supported in all Chrome versions
            
            # Locale Override
            try:
                driver.execute_cdp_cmd('Emulation.setLocaleOverride', {
                    'locale': fingerprint.locale
                })
            except:
                pass
            
            # Device Metrics Override
            driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {
                'width': fingerprint.screen_width,
                'height': fingerprint.screen_height,
                'deviceScaleFactor': fingerprint.pixel_ratio,
                'mobile': fingerprint.max_touch_points > 0
            })
            
        except Exception as e:
            print(f"⚠️ CDP override warning: {e}")
    
    def generate_unique_fingerprint(self, device_profile, persona, session_id: str = None) -> FingerprintData:
        """
        Generate a unique fingerprint for each bot session
        
        Args:
            device_profile: DeviceProfile object
            persona: UserPersona object
            session_id: Unique session identifier
            
        Returns:
            Unique FingerprintData object
        """
        # Generate base fingerprint
        fingerprint = self.generate_fingerprint(device_profile, persona)
        
        # Add session-specific variations
        if session_id:
            # Use session ID to create unique but consistent variations
            random.seed(hash(session_id))
            
            # Vary some properties slightly
            fingerprint.canvas_fingerprint = hashlib.md5(
                f"{fingerprint.canvas_fingerprint}_{session_id}".encode()
            ).hexdigest()[:16]
            
            fingerprint.audio_fingerprint = hashlib.md5(
                f"{fingerprint.audio_fingerprint}_{session_id}".encode()
            ).hexdigest()[:16]
            
            # Reset random seed
            random.seed()
        
        return fingerprint
