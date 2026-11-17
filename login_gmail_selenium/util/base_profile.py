import os
import shutil
import json

#import undetected_chromedriver as uc2
from selenium.webdriver.chrome.service import Service

import login_gmail_selenium.common.constant as Constant
from seleniumbase.plugins.driver_manager import Driver
#from login_gmail_selenium.util.driver import Driver
from login_gmail_selenium.util.helper import sleep_for, get_version
from selenium_stealth import stealth
import random
import uuid
from bot_orchestration.fingerprint_utils import FingerprintGenerator

current_path = os.path.dirname(os.path.abspath(__file__))
root_path = os.path.dirname(current_path)
extension_path = os.path.join(root_path, 'extension')

WEBRTC = os.path.join(extension_path, 'webrtc_control')
ACTIVE = os.path.join(extension_path, 'always_active')
FINGERPRINT = os.path.join(extension_path, 'fingerprint_defender.')
TIMEZONE = os.path.join(extension_path, 'spoof_timezone')
VEEPN = os.path.join(extension_path, 'veepn')

NO_PROXY_POSTFIX = '_no_proxy'
PUBLIC_PROXY_POSTFIX = '_public_proxy'
AUTH_TYPES = [
    'private',
    'public',
    None
]


class ChromeProfile:
    VIEWPORTS = ['2560,1440', '1920,1080', '1440,900',
                 '1536,864', '1366,768', '1280,1024', '1024,768']

    def __init__(self,
                 auth_type=AUTH_TYPES[2],
                 path=None,
                 prox=None,
                 prox_type=None,
                 insecure=False,
                 device_profile=None,
                 persona=None,
                 fingerprint=None,
                 proxy_config=None):
        self.proxy_folder = Constant.PROXY_FOLDER
        self.auth_type = auth_type
        self.path = path
        self.proxy = prox or "empty"
        self.proxy_type = prox_type
        self.driver = None
        self.insecure = insecure
        self.profile_name = None
        self.cache_folders = []
        # Use the profile folder from constants
        self.profile_folder = Constant.PROFILE_GOOGLE_FOLDER
        # Store device profile, persona, fingerprint, and proxy for future use
        self.device_profile = device_profile
        self.persona = persona
        self.fingerprint = fingerprint
        self.proxy_config = proxy_config



    def create_driver(self):
        # Determine folder name based on auth type
        # folder_suffix = ""
        # if self.auth_type == AUTH_TYPES[0]:  # private
        #     folder_suffix = ""
        # elif self.auth_type == AUTH_TYPES[1]:  # public
        #     folder_suffix = PUBLIC_PROXY_POSTFIX
        # else:  # None
        #     folder_suffix = NO_PROXY_POSTFIX
        
        folder_name = f"{self.profile_name}"
        profile_path = os.path.join(Constant.PROFILE_GOOGLE_FOLDER, folder_name)
        
        # Set up cache folders
        self._setup_cache_folders(profile_path)
        
        # Clean up the profile path for SeleniumBase
        clean_profile_path = profile_path.replace("\\", "/").replace(" ", "")
        print(f"🔧 Clean profile path: {clean_profile_path}")

        # Prepare device-specific arguments
        chromium_args = [
            f"--profile-directory={folder_name}",
            "--disable-blink-features=AutomationControlled",
            "--no-restore-last-session",
            "--restore-last-session=false",
            "--disable-sync",
            "--disable-extensions-except=",
        ]
        
        if self.device_profile:
            window_size = f"{self.device_profile.screen_width},{self.device_profile.screen_height}"
            chromium_args.append(f"--user-agent={self.device_profile.user_agent}")
        else:
            window_size = "1920,1080"
        
        # Create custom proxy extension if needed
        if self.proxy_config:
            proxy_ext_path = self._create_persistent_proxy_extension()
            if proxy_ext_path:
                # Add the extension directory to chromium args instead of using SeleniumBase's proxy
                chromium_args.append(f"--load-extension={proxy_ext_path}")
                print(f"✅ Loading proxy extension from: {proxy_ext_path}")
        
        # Prepare driver arguments WITHOUT proxy (we handle it via extension)
        driver_kwargs = {
            'uc': True,
            'browser': 'chrome',
            'user_data_dir': clean_profile_path,
            'chromium_arg': ",".join(chromium_args),
            'undetectable': True,
            'window_size': window_size,
        }
        
        # Create the driver WITHOUT passing proxy to SeleniumBase
        # This prevents SeleniumBase from creating its own proxy extension
        driver = Driver(**driver_kwargs)
        
        # Apply fingerprint if available
        if self.fingerprint:
            print("Applying fingerprint...")
            fingerprint_generator = FingerprintGenerator()
            fingerprint_generator.apply_fingerprint_to_driver(driver, self.fingerprint)
            print("✅ Fingerprint applied")
        
        # Apply device metrics override
        if self.device_profile:
            driver.execute_cdp_cmd(
                cmd='Emulation.setDeviceMetricsOverride',
                cmd_args={
                    'width': self.device_profile.screen_width,
                    'height': self.device_profile.screen_height,
                    'deviceScaleFactor': self.device_profile.pixel_ratio,
                    'mobile': self.device_profile.is_mobile
                }
        )
        
        return driver



    def retrieve_driver(self):
        self.driver = self.create_driver()
        return self.driver

    def start(self):
        sleep_for(Constant.SHORT_WAIT)
        self.driver.execute_cdp_cmd(cmd='Network.clearBrowserCache', cmd_args={})

    def adjust_viewport(self):
        pass

    def _create_persistent_proxy_extension(self):
        """Create a persistent proxy extension that won't be overwritten"""
        if not self.proxy_config:
            return None
            
        # Create a simple, matching proxy folder name
        # Remove spaces and special characters for consistency
        clean_profile_name = self.profile_name.replace(" ", "").replace("-", "").replace("_", "")
        proxy_folder_name = f"proxy_{clean_profile_name}"
        self.proxy_folder = os.path.join(Constant.PROXY_FOLDER, proxy_folder_name)
        
        # Check if extension already exists with correct config
        config_file = os.path.join(self.proxy_folder, "config.json")
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                existing_config = json.load(f)
                # Check if proxy config matches
                if (existing_config.get('server') == self.proxy_config.server and
                    existing_config.get('port') == self.proxy_config.port and
                    existing_config.get('username') == self.proxy_config.username):
                    print(f"♻️ Reusing existing proxy extension: {self.proxy_folder}")
                    return self.proxy_folder
        
        # Create new extension
        os.makedirs(self.proxy_folder, exist_ok=True)
        
        # Save config for future verification
        with open(config_file, 'w') as f:
            json.dump({
                'server': self.proxy_config.server,
                'port': self.proxy_config.port,
                'username': self.proxy_config.username
            }, f)
        
        # Create manifest.json for Manifest V3
        manifest = {
            "version": "1.0.0",
            "manifest_version": 3,
            "name": f"Proxy Auth {self.profile_name}",
            "description": "Proxy authentication extension",
            "permissions": [
                "proxy",
                "storage",
                "webRequest",
                "webRequestAuthProvider"
            ],
            "host_permissions": ["<all_urls>"],
            "background": {
                "service_worker": "background.js"
            },
            "minimum_chrome_version": "88.0.0"
        }
        
        # Create background.js
        background_js = f"""
// Proxy configuration
const config = {{
                mode: "fixed_servers",
    rules: {{
        singleProxy: {{
                    scheme: "http",
            host: "{self.proxy_config.server}",
            port: {self.proxy_config.port}
        }},
        bypassList: ["localhost", "127.0.0.1"]
    }}
}};

// Set proxy configuration
chrome.proxy.settings.set(
    {{value: config, scope: "regular"}},
    function() {{
        console.log("Proxy configured:", config);
    }}
);

// Handle authentication
        chrome.webRequest.onAuthRequired.addListener(
    function(details) {{
        console.log("Authentication required for:", details.url);
        return {{
            authCredentials: {{
                username: "{self.proxy_config.username}",
                password: "{self.proxy_config.password}"
            }}
        }};
    }},
    {{urls: ["<all_urls>"]}},
    ["blocking"]
);

console.log("Proxy extension loaded for {self.profile_name}");
"""
        
        # Write files
        with open(os.path.join(self.proxy_folder, "manifest.json"), 'w') as f:
            json.dump(manifest, f, indent=2)
        
        with open(os.path.join(self.proxy_folder, "background.js"), 'w') as f:
            f.write(background_js)
        
        print(f"🔧 Created new proxy extension: {self.proxy_folder}")
        print(f"   Proxy: {self.proxy_config.server}:{self.proxy_config.port}")
        
        return self.proxy_folder

    def _setup_cache_folders(self, profile_path):
        """Setup cache folders for the profile"""
        self.cache_folders = [
            os.path.join(profile_path, 'optimization_guide_prediction_model_downloads'),
            os.path.join(profile_path, 'Cache'),
            os.path.join(profile_path, 'Service Worker', 'CacheStorage'),
            os.path.join(Constant.PROFILE_GOOGLE_FOLDER, 'SwReporter'),
            os.path.join(Constant.PROFILE_GOOGLE_FOLDER, 'pnacl'),
            os.path.join(Constant.PROFILE_GOOGLE_FOLDER, 'OnDeviceHeadSuggestModel'),
            os.path.join(Constant.PROFILE_GOOGLE_FOLDER, 'MediaFoundationWidevineCdm'),
            os.path.join(Constant.PROFILE_GOOGLE_FOLDER, 'GrShaderCache'),
            os.path.join(Constant.PROFILE_GOOGLE_FOLDER, 'ClientSidePhishing'),
            os.path.join(Constant.PROFILE_GOOGLE_FOLDER, 'hyphen-data'),
            os.path.join(Constant.PROFILE_GOOGLE_FOLDER, 'ZxcvbnData'),
            os.path.join(Constant.PROFILE_GOOGLE_FOLDER, 'Safe Browsing')
        ]

    def clear_cache(self):
        """Clear cache folders"""
        for folder in self.cache_folders:
            if os.path.exists(folder):
                shutil.rmtree(folder, ignore_errors=True)
        
    def cleanup_proxy_extension(self):
        """Clean up proxy extension if needed"""
        if self.proxy_folder and os.path.exists(self.proxy_folder):
            try:
                shutil.rmtree(self.proxy_folder, ignore_errors=True)
                print(f"🧹 Cleaned up proxy extension: {self.proxy_folder}")
            except Exception as e:
                print(f"⚠️ Failed to clean proxy extension: {e}")

    @staticmethod
    def delete_profile(profile_name, profile_folder=None, proxy_folder=None):
        """
        Delete a profile and its corresponding proxy extension
        
        Args:
            profile_name: Name of the profile to delete (can be partial match)
            profile_folder: Optional custom profile folder path
            proxy_folder: Optional custom proxy folder path
            
        Returns:
            dict: Results of deletion operation
        """
        results = {
            'profile_deleted': False,
            'proxy_deleted': False,
            'errors': []
        }
        
        try:
            # Determine profile path
            if profile_folder:
                profile_path = profile_folder
            else:
                # First, try exact matches
                possible_paths = [
                    os.path.join(Constant.PROFILE_GOOGLE_FOLDER, f"{profile_name}_no_proxy"),
                    os.path.join(Constant.PROFILE_GOOGLE_FOLDER, f"{profile_name}_public_proxy"),
                    os.path.join(Constant.PROFILE_GOOGLE_FOLDER, profile_name),
                ]
                
                profile_path = None
                for path in possible_paths:
                    if os.path.exists(path):
                        profile_path = path
                        break
                
                # If no exact match, try partial matching
                if not profile_path:
                    # Clean the search name (remove spaces, hyphens, underscores)
                    clean_search_name = profile_name.replace(" ", "").replace("-", "").replace("_", "")
                    
                    # List all profiles and find matches
                    if os.path.exists(Constant.PROFILE_GOOGLE_FOLDER):
                        for item in os.listdir(Constant.PROFILE_GOOGLE_FOLDER):
                            item_path = os.path.join(Constant.PROFILE_GOOGLE_FOLDER, item)
                            if os.path.isdir(item_path):
                                # Clean the profile name for comparison
                                clean_item_name = item.replace(" ", "").replace("-", "").replace("_", "")
                                
                                # Check if the search name is contained in the profile name
                                if clean_search_name in clean_item_name or clean_item_name in clean_search_name:
                                    profile_path = item_path
                                    print(f"🔍 Found matching profile: {item}")
                                    break
                
                if not profile_path:
                    results['errors'].append(f"Profile not found: {profile_name}")
                    return results
            
            # Delete profile directory
            if os.path.exists(profile_path):
                shutil.rmtree(profile_path, ignore_errors=True)
                results['profile_deleted'] = True
                print(f"✅ Deleted profile: {profile_path}")
            else:
                results['errors'].append(f"Profile path does not exist: {profile_path}")
            
            # Determine proxy path
            if proxy_folder:
                proxy_path = proxy_folder
            else:
                # Create clean profile name for proxy lookup
                clean_profile_name = profile_name.replace(" ", "").replace("-", "").replace("_", "")
                proxy_path = os.path.join(Constant.PROXY_FOLDER, f"proxy_{clean_profile_name}")
                
                # If exact proxy path doesn't exist, try to find matching proxy
                if not os.path.exists(proxy_path):
                    if os.path.exists(Constant.PROXY_FOLDER):
                        for item in os.listdir(Constant.PROXY_FOLDER):
                            if item.startswith("proxy_"):
                                item_path = os.path.join(Constant.PROXY_FOLDER, item)
                                if os.path.isdir(item_path):
                                    # Clean the proxy name for comparison
                                    clean_proxy_name = item.replace("proxy_", "").replace(" ", "").replace("-", "").replace("_", "")
                                    
                                    # Check if the search name matches the proxy name
                                    if clean_profile_name in clean_proxy_name or clean_proxy_name in clean_profile_name:
                                        proxy_path = item_path
                                        print(f"🔍 Found matching proxy: {item}")
                                        break
            
            # Delete proxy extension
            if os.path.exists(proxy_path):
                shutil.rmtree(proxy_path, ignore_errors=True)
                results['proxy_deleted'] = True
                print(f"✅ Deleted proxy extension: {proxy_path}")
            else:
                print(f"ℹ️  No proxy extension found: {proxy_path}")
            
            return results
            
        except Exception as e:
            error_msg = f"Error deleting profile {profile_name}: {e}"
            results['errors'].append(error_msg)
            print(f"❌ {error_msg}")
            return results

    @staticmethod
    def list_profiles():
        """
        List all available profiles and their corresponding proxy extensions
        
        Returns:
            dict: Profile information
        """
        profiles_info = {
            'profiles': [],
            'proxy_extensions': [],
            'orphaned_proxies': []
        }
        
        try:
            # List profiles
            if os.path.exists(Constant.PROFILE_GOOGLE_FOLDER):
                for item in os.listdir(Constant.PROFILE_GOOGLE_FOLDER):
                    item_path = os.path.join(Constant.PROFILE_GOOGLE_FOLDER, item)
                    if os.path.isdir(item_path):
                        profiles_info['profiles'].append({
                            'name': item,
                            'path': item_path,
                            'size': sum(os.path.getsize(os.path.join(dirpath, filename))
                                      for dirpath, dirnames, filenames in os.walk(item_path)
                                      for filename in filenames)
                        })
            
            # List proxy extensions
            if os.path.exists(Constant.PROXY_FOLDER):
                for item in os.listdir(Constant.PROXY_FOLDER):
                    if item.startswith('proxy_'):
                        item_path = os.path.join(Constant.PROXY_FOLDER, item)
                        if os.path.isdir(item_path):
                            # Extract profile name from proxy folder
                            profile_name = item.replace('proxy_', '')
                            
                            # Check if corresponding profile exists
                            profile_exists = False
                            for profile in profiles_info['profiles']:
                                if profile_name in profile['name']:
                                    profile_exists = True
                                    break
                            
                            proxy_info = {
                                'name': item,
                                'path': item_path,
                                'profile_name': profile_name,
                                'has_corresponding_profile': profile_exists
                            }
                            
                            if profile_exists:
                                profiles_info['proxy_extensions'].append(proxy_info)
                            else:
                                profiles_info['orphaned_proxies'].append(proxy_info)
            
            return profiles_info
            
        except Exception as e:
            print(f"❌ Error listing profiles: {e}")
            return profiles_info

    @staticmethod
    def cleanup_orphaned_proxies():
        """
        Clean up proxy extensions that don't have corresponding profiles
        
        Returns:
            int: Number of orphaned proxies cleaned up
        """
        profiles_info = ChromeProfile.list_profiles()
        cleaned_count = 0
        
        for orphaned_proxy in profiles_info['orphaned_proxies']:
            try:
                shutil.rmtree(orphaned_proxy['path'], ignore_errors=True)
                print(f"🧹 Cleaned orphaned proxy: {orphaned_proxy['name']}")
                cleaned_count += 1
            except Exception as e:
                print(f"⚠️ Failed to clean orphaned proxy {orphaned_proxy['name']}: {e}")
        
        return cleaned_count

    @staticmethod
    def get_profile(profile_path, proxy_ext_path=None, device_name="Unknown Device", device_profile=None):
        """
        Load an existing profile with its proxy extension
        
        Args:
            profile_path: Path to the existing user data directory
            proxy_ext_path: Path to the existing proxy extension directory
            device_name: Name of the device for logging
            device_profile: Device profile for the device
            
        Returns:
            Driver instance with the loaded profile
        """
        print(f"🔄 Loading existing profile: {device_name}")
        print(f"   Profile path: {profile_path}")
        if proxy_ext_path:
            print(f"   Proxy extension: {proxy_ext_path}")
        
        # Clean up the profile path for SeleniumBase
        clean_profile_path = profile_path.replace("\\", "/").replace(" ", "")
        window_size = f"{device_profile.screen_width},{device_profile.screen_height}"
        
        # Prepare chromium arguments
        chromium_args = [
            "--disable-blink-features=AutomationControlled",
        ]
        
        # Add proxy extension if provided
        if proxy_ext_path and os.path.exists(proxy_ext_path):
            chromium_args.append(f"--load-extension={proxy_ext_path}")
            print(f"✅ Loading proxy extension from: {proxy_ext_path}")

        if device_profile:
            window_size = f"{device_profile.screen_width},{device_profile.screen_height}"
            chromium_args.append(f"--user-agent={device_profile.user_agent}")
        
        # Prepare driver arguments
        driver_kwargs = {
            'uc': True,
            'browser': 'chrome',
            'user_data_dir': clean_profile_path,
            'chromium_arg': ",".join(chromium_args),
            'undetectable': True,
            'window_size': window_size,  # Default size, can be overridden
        }
        
        # Create the driver
        driver = Driver(**driver_kwargs)
        if device_profile:
            driver.execute_cdp_cmd(
                cmd='Emulation.setDeviceMetricsOverride',
                cmd_args={
                    'width': device_profile.screen_width,
                    'height': device_profile.screen_height,
                    'deviceScaleFactor': device_profile.pixel_ratio,
                    'mobile': device_profile.is_mobile
                }
        )
        
        print(f"✅ Successfully loaded profile: {device_name}")
        return driver
