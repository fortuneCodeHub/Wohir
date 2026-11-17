#!/usr/bin/python3
"""
    YouTube Actions - Atomic low-level YouTube interactions
    Author: Fortune Nwohiri
"""
import time
import random
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.common.exceptions import JavascriptException, TimeoutException, ElementClickInterceptedException
from selenium.webdriver.common.action_chains import ActionChains
from urllib.parse import urlparse
from logging_config.logger import get_logger
from selenium.common.exceptions import JavascriptException, TimeoutException, ElementClickInterceptedException, NoSuchElementException, StaleElementReferenceException
import multiprocessing as mp
from threading import Thread
from itertools import cycle, repeat
import random
from selenium_stealth import stealth
from time import sleep
from urllib.parse import urlparse, parse_qs, unquote
import re
from bs4 import BeautifulSoup
from selenium.webdriver.common.action_chains import ActionChains
from login_gmail_selenium.util.helper import enter_text
from seleniumbase.fixtures import js_utils

logger = get_logger("GoogleActions")


class GoogleActions:
    """Contains tiny, mechanical, atomic moves for Google interactions"""

    def focus_search_bar(self, driver):
        """
        Focus the Google search bar - handles both textarea and input variants.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            bool: True if search bar was focused successfully, False otherwise
        """
        logger.info("🔍 Focus Search Bar")
        try:
            # Try to find the search box using multiple selectors
            search_selectors = [
                "textarea[name='q']",          # Primary Google selector
                "input[name='search_query']",  # Primary YouTube selector  
                "textarea.gLFyf",              # Google class-based
                "input.ytSearchboxComponentInput",  # YouTube class-based
                "div.a4bIc textarea",          # Google container-based
                "yt-searchbox input",          # YouTube custom element
                "textarea#APjFqb",             # Google ID-based (specific)
                "input[name='q']",             # Legacy Google input
                "input#input",                           # ID-based (short & stable)
                "#input",                                # Shorthand for the same ID
                "input.truncate",                        # Class-based
                "#inputWrapper > input",                 # Parent-child structure
                "input[type='search']",                  # Attribute-based
                "input[placeholder='Search Google or type a URL']",
            ]
            
            search_box = None
            for selector in search_selectors:
                try:
                    search_box = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    logger.info(f"Found search box with selector: {selector}")
                    break
                except:
                    continue
            
            if search_box is None:
                logger.error("Could not find any search box")
                return False
                
            logger.info(f"search box {search_box}")
            
            # Clear any existing text and focus
            search_box.clear()
            search_box.click()
            driver.execute_script("arguments[0].focus();", search_box)
            time.sleep(random.uniform(0.5, 1.0))
            return True
            
        except Exception as e:
            logger.error(f"Error focusing search bar: {e}")
            return False


    # ===== Basic Browser Operations (driver-parameterized) =====
    def navigate_to(self, driver, url):
        """Navigate to a specific URL and wait for full load."""
        try:
            driver.open(url)
            WebDriverWait(driver, 30).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            return True
        except Exception as e:
            logger.error(f"Error navigating to {url}: {e}")
            return False

    def refresh_page(self, driver):
        """Refresh the current page and wait for load."""
        try:
            driver.refresh()
            WebDriverWait(driver, 30).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            return True
        except Exception as e:
            logger.error(f"Error refreshing page: {e}")
            return False
    
    def _click_navbar_item(self, driver):
        """Click a random item in the account navigation sidebar"""
        logger.info("📋 Clicking random navbar item")
        
        try:
            # Find all navigation items
            nav_items = driver.find_elements(By.CSS_SELECTOR, "nav.ky9loc ul.b3qkse li a")
            
            if not nav_items:
                logger.warning("📋 No navbar items found")
                return False
                
            # Filter only visible and interactable items
            interactable_items = []
            for item in nav_items:
                try:
                    if item.is_displayed() and item.is_enabled():
                        interactable_items.append(item)
                except StaleElementReferenceException:
                    continue  # Skip stale elements
                    
            if not interactable_items:
                logger.warning("📋 No interactable navbar items found")
                return False
                
            # Choose a random item (avoid the first one which is usually "Home")
            item = random.choice(interactable_items[1:]) if len(interactable_items) > 1 else interactable_items[0]
            item_text = item.text
            logger.info(f"📋 Clicking navbar item: {item_text}")
            
            # Click the item
            item.click()
            return True
                
        except Exception as e:
            logger.error(f"❌ Error clicking navbar item: {e}")
            return False

    def _click_main_content_button(self, driver):
        """Click a random interactive element in the main content area"""
        logger.info("🔘 Clicking random main content element")
        
        try:
            # Multiple selectors for different types of interactive elements
            selectors = [
                "div.N5YmOc div.ouwJ0b a",  # Main content buttons
                "a.RlFDUe",  # Card links
                "div.VfPpkd-ksKsZd-XxIAqe a",  # Material design buttons
                "div.I6g62c a",  # Interactive cards
                "div[jscontroller='fjYfSd'] a"  # JS-controlled elements
            ]
            
            all_elements = []
            for selector in selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        try:
                            if element.is_displayed() and element.is_enabled():
                                all_elements.append(element)
                        except StaleElementReferenceException:
                            continue
                except Exception:
                    continue  # Skip if selector doesn't work
                    
            if not all_elements:
                logger.warning("🔘 No main content elements found")
                return False
                
            # Choose a random element
            element = random.choice(all_elements)
            element_text = element.text or element.get_attribute("aria-label") or "Unlabeled element"
            logger.info(f"🔘 Clicking element: {element_text}")
            
            # Click the element
            element.click()
            return True
                
        except Exception as e:
            logger.error(f"❌ Error clicking main content element: {e}")
            return False

    def _use_search_bar(self, driver):
        """Interact with the search bar in a natural way"""
        logger.info("🔍 Using account search bar")
        
        try:
            # First click the search button to expand it
            search_button = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Search']")
            search_button.click()
            time.sleep(random.uniform(0.5, 1.5))
            
            # Find the search input
            search_input = driver.find_element(By.CSS_SELECTOR, "input[aria-label='Search Google Account']")
            
            # Type a random search term slowly (like a human)
            search_terms = ["security", "privacy", "password", "activity", "email"]
            term = random.choice(search_terms)
            
            logger.info(f"⌨️ Typing search term: {term}")
            if search_input:
                ok = enter_text(
                    driver,
                    search_input,
                    term,
                    button=False,
                    timeout=30
                )
                return bool(ok)
            
            # Sometimes press enter, sometimes just clear the field
            if random.random() < 0.3:  # 30% chance to search
                time.sleep(random.uniform(0.5, 1.0))
                search_input.send_keys(Keys.ENTER)
                logger.info("↵ Performing search")
                
                # Wait for results briefly
                time.sleep(random.uniform(2.0, 4.0))
                
                # Most of the time, go back to account home
                if random.random() < 0.7:  # 70% chance to go back
                    self.go_back()
                    time.sleep(random.uniform(1.0, 2.0))
            else:
                # Clear the field without searching
                time.sleep(random.uniform(0.5, 1.0))
                search_input.clear()
                logger.info("✖️ Clearing search without submitting")
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Error using search bar")
            return False

    def _scroll_account_page(self, driver):
        """Scroll the account page - finds visible elements and scrolls to one randomly"""
        logger.info("📜 Scrolling account page with specific selectors")
        
        # More specific selectors based on the actual HTML structure
        scroll_targets = [
            # Privacy section with specific class combination
            'div.QW4Pie.XAdKte.qoyPsd div.sieBfb',
            
            # "Choose what others see" - About Me section
            'a.RlFDUe[href*="profile"][data-rid="10050"]',
            
            # Language setting
            'a[href*="language"][aria-label="Language"]',
            
            # Input Tools
            'a[href*="inputtools"][aria-label="Input Tools"]', 
            
            # Accessibility setting
            'a[href*="accessibility"][aria-label="Accessibility"]',
            
            # Google Fit section
            'a[href*="fit.google.com/privacy"]',
            
            # Apps and services dashboard
            'a[href*="dashboard"][data-rid="214"]',
            
            # Third-party apps
            'a[href*="connections"][aria-label*="Third-party"]',
            
            # Search Google Account
            'div[aria-label="Search Google Account"]',
            
            # Help options
            'div[aria-label="See help options"]'
        ]
        
        # First pass: find all visible elements
        visible_elements = []
        
        for selector in scroll_targets:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed():
                        visible_elements.append((element, selector))
                        logger.debug(f"✅ Found visible element: {selector}")
                        
            except Exception as e:
                logger.debug(f"⚠️ Error checking selector {selector}: {str(e)}")
                continue
        
        # If we found visible elements, pick one randomly and scroll to it
        if visible_elements:
            chosen_element, chosen_selector = random.choice(visible_elements)
            logger.info(f"🎯 Scrolling to randomly chosen element: {chosen_selector}")
            
            try:
                # Use js_utils slow scroll function
                self.scroll_to_element(driver, chosen_element)
                
                # Natural pause after scrolling
                time.sleep(random.uniform(1.2, 2.5))
                
                logger.info("✅ Successfully scrolled to element")
                
            except Exception as e:
                logger.warning(f"⚠️ Error scrolling to chosen element: {str(e)}")
                
        else:
            logger.info("ℹ️ No visible scroll targets found on page")
        
        logger.info(f"✅ Scrolling completed. Found {len(visible_elements)} visible elements, scrolled to 1")

        


    def go_back(self, driver):
        """Go back to previous page with a short human-like delay."""
        try:
            driver.go_back()
            time.sleep(random.uniform(1.0, 3.0))
            return True
        except Exception as e:
            logger.error(f"Error going back: {e}")
            return False

    def go_forward(self, driver):
        """Go forward in history with a short human-like delay."""
        try:
            driver.go_forward()
            time.sleep(random.uniform(1.0, 3.0))
            return True
        except Exception as e:
            logger.error(f"Error going forward: {e}")
            return False

    # ===== Navigation and URL Handling =====
    def get_current_url(self, driver):
        """Return the current URL from the browser."""
        try:
            return driver.current_url
        except Exception:
            return None

    def extract_domain(self, url):
        """Extract a normalized domain (without www) from a URL."""
        try:
            parsed = urlparse(url)
            return parsed.netloc.replace("www.", "").lower()
        except Exception:
            return ""


    def is_same_domain(self, url1, url2):
        """Check if two URLs share the same domain."""
        return self.extract_domain(url1) == self.extract_domain(url2)

    # ===== Element Interaction =====
    def find_element(self, driver, by, value, timeout=10):
        """Find a single element, waiting up to timeout seconds."""
        try:
            return WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            logger.error(f"Element not found: {by}={value}")
            return None

    def find_elements(self, driver, by, value, timeout=10):
        """Find multiple elements, waiting up to timeout seconds."""
        try:
            return WebDriverWait(driver, timeout).until(
                EC.presence_of_all_elements_located((by, value))
            )
        except TimeoutException:
            logger.error(f"Elements not found: {by}={value}")
            return []

    def find_short_videos_section(self, driver):
        """Find the Short videos section by heading text"""
        try:
            # Wait for page to load and scroll to ensure content is visible
            time.sleep(random.uniform(0.3, 0.5))
            
            # Find the section by the heading and get its ancestor div
            section = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.XPATH, "//span[text()='Short videos']/ancestor::div[contains(@class, 'adDDi')]"))
            )
            
            # Additional wait to ensure section is fully loaded
            time.sleep(random.uniform(0.2, 0.3))
            return section
        except Exception as e:
            return None

    def find_short_videos_fab(self, driver, section=None):
        """Find the fab button in the Short videos section"""
        if section is None:
            section = self.find_short_videos_section(driver)
        
        if section is not None:
            try:
                # Wait for section to be fully loaded and scroll into view
                time.sleep(random.uniform(0.2, 0.3))
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", section)
                time.sleep(random.uniform(0.2, 0.3))
                
                # Try multiple strategies to find the fab button
                
                # Strategy 1: Look for g-right-button with Next label
                try:
                    return WebDriverWait(section, 2).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "g-right-button[aria-label='Next']"))
                    )
                except:
                    pass
                
                # Strategy 2: Look for g-right-button with jsname
                try:
                    return WebDriverWait(section, 1).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "g-right-button[jsname='IHFM4']"))
                    )
                except:
                    pass
                
                # Strategy 3: Look for any g-right-button
                try:
                    return WebDriverWait(section, 1).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "g-right-button"))
                    )
                except:
                    pass
                
                # Strategy 4: Look for g-fab directly (less specific selector)
                try:
                    return WebDriverWait(section, 1).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "g-fab.sr9hec"))
                    )
                except:
                    pass
                
                # Strategy 5: XPath for the SVG's parent elements
                try:
                    return WebDriverWait(section, 1).until(
                        EC.element_to_be_clickable((By.XPATH, ".//svg[@viewBox='0 0 24 24']/ancestor::g-right-button"))
                    )
                except:
                    pass
                    
            except Exception as e:
                pass
        
        return None

    def find_short_videos(self, driver, section=None):
        """Find video elements in the Short videos section"""
        if section is None:
            section = self.find_short_videos_section(driver)
        
        if section:
            try:
                # Wait for section to be fully loaded and scroll into view
                time.sleep(random.uniform(0.2, 0.3))
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", section)
                time.sleep(random.uniform(0.3, 0.5))  # Wait for videos to load
                
                # Try multiple selectors for finding videos
                videos = []
                
                # Strategy 1: Original selector
                try:
                    videos = WebDriverWait(section, 2).until(
                        lambda s: s.find_elements(By.CSS_SELECTOR, ".rIRoqf")
                    )
                    if videos:
                        return videos
                except:
                    pass
                
                # Strategy 2: Look for any anchor tags with video-related hrefs
                try:
                    videos = WebDriverWait(section, 1).until(
                        lambda s: s.find_elements(By.XPATH, ".//a[contains(@href, 'youtube.com') or contains(@href, 'youtu.be')]")
                    )
                    if videos:
                        return videos
                except:
                    pass
                
                # Strategy 3: Look for divs that might contain video thumbnails
                try:
                    videos = WebDriverWait(section, 1).until(
                        lambda s: s.find_elements(By.CSS_SELECTOR, "div[role='listitem'] a, div[data-vid] a")
                    )
                    if videos:
                        return videos
                except:
                    pass
                
                # Strategy 4: Generic anchor tags within the section
                try:
                    videos = WebDriverWait(section, 1).until(
                        lambda s: s.find_elements(By.CSS_SELECTOR, "a[href*='watch'], a[href*='shorts']")
                    )
                    if videos:
                        return videos
                except:
                    pass
                    
            except Exception as e:
                pass
        
        return []

    def find_youtube_videos_in_main(self, driver):
        """Find YouTube video links in the main results (All tab)"""
        try:
            # Wait for page to load and search results to appear
            time.sleep(random.uniform(0.3, 0.4))
            
            # Wait for search results to be present
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div#search, div[data-ved], h3"))
            )
            
            # Additional wait for dynamic content to load
            time.sleep(random.uniform(0.2, 0.5))
            
            # Use multiple strategies to find YouTube videos
            videos = []
            
            # Strategy 1: Direct YouTube watch links
            try:
                videos = WebDriverWait(driver, 3).until(
                    lambda d: d.find_elements(By.XPATH, "//a[contains(@href, 'youtube.com/watch')]")
                )
            except:
                pass
            
            # Strategy 2: YouTube shorts links
            if not videos:
                try:
                    videos = WebDriverWait(driver, 2).until(
                        lambda d: d.find_elements(By.XPATH, "//a[contains(@href, 'youtube.com/shorts')]")
                    )
                except:
                    pass
            
            # Strategy 3: Any YouTube links that look like videos
            if not videos:
                try:
                    videos = WebDriverWait(driver, 2).until(
                        lambda d: d.find_elements(By.XPATH, "//a[contains(@href, 'youtube.com') and (contains(@href, '/watch') or contains(@href, '/shorts'))]")
                    )
                except:
                    pass
            
            return videos
        except Exception as e:
            return []

    def find_youtube_videos_in_videos_tab(self, driver):
        """Find video elements in the Videos tab"""
        try:
            # Wait for videos tab to load
            time.sleep(random.uniform(0.3, 0.4))
            
            # Wait for video results to be present
            WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div#search, div[data-ved], h3"))
            )
            
            # Additional wait for video thumbnails to load
            time.sleep(random.uniform(0.3, 0.5))
            
            videos = []
            
            # Strategy 1: Original selector
            try:
                videos = WebDriverWait(driver, 2).until(
                    lambda d: d.find_elements(By.CSS_SELECTOR, "a.rIRoqf")
                )
            except:
                pass
            
            # Strategy 2: Alternative selectors for video results
            if not videos:
                try:
                    videos = WebDriverWait(driver, 1).until(
                        lambda d: d.find_elements(By.CSS_SELECTOR, "div.g a[href*='youtube.com'], div.rc a[href*='youtube.com']")
                    )
                except:
                    pass
            
            # Strategy 3: Any YouTube links in the videos tab
            if not videos:
                try:
                    videos = WebDriverWait(driver, 1).until(
                        lambda d: d.find_elements(By.XPATH, "//a[contains(@href, 'youtube.com')]")
                    )
                except:
                    pass
            
            return videos
        except Exception as e:
            return []

    def is_on_videos_tab(self, driver):
        """Check if the current page is the Videos tab"""
        current_url = driver.current_url
        if "tbm=vid" in current_url or "udm=7" in current_url:
            return True
        
        try:
            # Check for the selected tab with text "Videos"
            driver.find_element(By.XPATH, "//a[@aria-selected='true']//span[text()='Videos']")
            return True
        except:
            pass
        
        try:
            # Alternative: Check for active Videos tab
            driver.find_element(By.XPATH, "//div[@role='tab'][@aria-selected='true'][.//text()='Videos']")
            return True
        except:
            pass
        
        return False

    def get_interactable_elements(self, elements):
        """Filter elements that are visible and enabled"""
        interactable = []
        for idx, element in enumerate(elements):
            try:
                if element.is_displayed() and element.is_enabled():
                    # Additional check for clickability
                    size = element.size
                    if size.get('height', 0) > 0 and size.get('width', 0) > 0:
                        interactable.append(element)
            except (StaleElementReferenceException, Exception) as e:
                logger.debug(f"Element not interactable: {e}")
                logger.info(f" ❌ element[{idx}] not interactable: {e}")
                continue
        
        return interactable


    def scroll_down(self, driver, max_scrolls=10, scroll_duration=5):
        """
        Scroll down the page with human-like behavior, stopping when reaching the bottom
        or after a maximum number of scrolls.
        
        Args:
            driver: WebDriver instance
            max_scrolls: Maximum number of scroll attempts
            scroll_duration: Approximate time in seconds for the scrolling session
        """
        # logger.error("Now entering the scroll down function")
        # Get initial page dimensions
        initial_height = js_utils.execute_script(driver, "return document.body.scrollHeight")
        viewport_height = driver.get_window_size()["height"]
        # logger.error("Now Gotten viewport and initial height")
        # Calculate scroll parameters based on duration
        scrolls_completed = 0
        start_time = time.time()
        
        while scrolls_completed < max_scrolls and (time.time() - start_time) < scroll_duration:
            # Get current scroll position
            current_position = js_utils.execute_script(driver, "return window.scrollY")
            max_scroll = initial_height - viewport_height
            # logger.error("now gotten current postion and max scroll")
            
            # Check if we're at the bottom
            if current_position >= max_scroll - 10:  # 10px tolerance
                print("Reached bottom of page")
                break
                
            # Calculate scroll distance with some randomness
            scroll_distance = random.randint(viewport_height // 2, viewport_height - 100)
            target_position = min(current_position + scroll_distance, max_scroll)
            # logger.error("Now gotten scroll distance and target position")
            
            # Human-like scroll to target position
            self._human_like_scroll(driver, current_position, target_position, "down")
            # logger.error("Now done with human like scroll")
            # Wait a variable time before next scroll (like a human reading)
            read_time = random.uniform(0.5, 2.5)
            time.sleep(read_time)
            
            # Check if content has loaded (page height increased)
            new_height = js_utils.execute_script(driver, "return document.body.scrollHeight")
            if new_height > initial_height:
                initial_height = new_height
                print("New content loaded, continuing to scroll")
            else:
                # If no new content after a few scrolls, we might be at the end
                scrolls_completed += 1
                
        # Final pause at the end of scrolling
        time.sleep(random.uniform(0.5, 1.5))

    def scroll_up(self, driver, target_position=0, scroll_duration=5):
        """
        Scroll up the page with human-like behavior, either to the top or a specific position.
        
        Args:
            driver: WebDriver instance
            target_position: Y position to scroll to (0 for top of page)
            scroll_duration: Approximate time in seconds for the scrolling session
        """
        # Get current position
        current_position = js_utils.execute_script(driver, "return window.scrollY")
        
        # If already at or near target, do nothing
        if abs(current_position - target_position) < 10:
            return
            
        # Human-like scroll to target position
        self._human_like_scroll(driver, current_position, target_position, "up")
        
        # Final pause at the end of scrolling
        time.sleep(random.uniform(0.5, 1.5))

    def _human_like_scroll(self, driver, start_pos, end_pos, direction):
        """
        Internal function to perform human-like scrolling between two positions.
        
        Args:
            driver: WebDriver instance
            start_pos: Starting scroll position
            end_pos: Target scroll position
            direction: "up" or "down" for behavioral variations
        """
        distance = end_pos - start_pos
        if distance == 0:
            return
            
        # Calculate steps based on distance
        total_steps = int(abs(distance) / random.randint(40, 70)) + random.randint(2, 5)
        step_value = float(distance) / total_steps
        
        # Behavioral variations based on direction
        if direction == "down":
            # When scrolling down, people tend to be more exploratory
            initial_slowdown = random.uniform(0.7, 0.9)  # Start slower
            mid_speedup = random.uniform(1.1, 1.3)       # Speed up in middle
        else:
            # When scrolling up, people tend to be more purposeful
            initial_slowdown = random.uniform(0.8, 1.0)  # More consistent speed
            mid_speedup = random.uniform(1.0, 1.2)       # Less speed variation
        
        # Perform the scroll with human-like variations
        new_position = start_pos
        for step in range(int(total_steps)):
            # Variable speed based on scroll phase
            if step < total_steps * 0.2:
                # Beginning of scroll - slower
                speed_factor = initial_slowdown
                pause_time = random.uniform(0.015, 0.025)
            elif step > total_steps * 0.8:
                # End of scroll - slower (preparing to stop)
                speed_factor = initial_slowdown
                pause_time = random.uniform(0.015, 0.025)
            else:
                # Middle of scroll - faster
                speed_factor = mid_speedup
                pause_time = random.uniform(0.008, 0.015)
                
            time.sleep(pause_time)
            
            # Add slight randomness to movement
            current_step = step_value * speed_factor * (1 + random.uniform(-0.1, 0.1))
            new_position += current_step
            
            # Ensure we don't overshoot our target
            if (direction == "down" and new_position > end_pos) or (direction == "up" and new_position < end_pos):
                new_position = end_pos
                
            scroll_script = "window.scrollTo(0, %s);" % new_position
            js_utils.execute_script(driver, scroll_script)
            
            # Occasionally add micro-pauses
            if random.random() < 0.1:
                time.sleep(random.uniform(0.05, 0.1))
        
        # Final adjustment to ensure we're at the exact position
        scroll_script = "window.scrollTo(0, %s);" % end_pos
        js_utils.execute_script(driver, scroll_script)
        
        # Final pause based on distance scrolled
        distance = abs(end_pos - start_pos)
        if distance > 1000:
            time.sleep(random.uniform(0.2, 0.4))
        elif distance > 300:
            time.sleep(random.uniform(0.1, 0.2))
        else:
            time.sleep(random.uniform(0.05, 0.1))

            
    def scroll_to_element(self, driver, element):
        """
            This Function Scrolls to an element
        """
        if driver.capabilities["browserName"] == "internet explorer":
            # IE breaks on slow-scrolling. Do a fast scroll instead.
            js_utils.scroll_to_element(driver, element)
            return
            
        scroll_position = js_utils.execute_script(driver, "return window.scrollY;")
        element_location_y = None
        
        try:
            if js_utils.shared_utils.is_cdp_swap_needed(driver):
                element_location_y = element.get_position().y
            else:
                element_location_y = element.location["y"]
        except Exception:
            element.location_once_scrolled_into_view
            return
            
        try:
            element_location_x = element.location["x"]
            element_width = element.size["width"]
            screen_width = driver.get_window_size()["width"]
        except Exception:
            element_location_x = 0
            
        element_location_y = element_location_y - js_utils.constants.Scroll.Y_OFFSET
        if element_location_y < 0:
            element_location_y = 0
            
        element_location_x_fix = element_location_x - 400
        if element_location_x_fix < 0:
            element_location_x_fix = 0
            
        if element_location_x + element_width <= screen_width:
            element_location_x_fix = 0
            
        distance = element_location_y - scroll_position
        # Default to downward direction; will be corrected if needed
        scroll_direction = 1
        
        if distance != 0:
            # Human-like scrolling behavior based on research
            total_steps = int(abs(distance) / random.randint(40, 70)) + random.randint(2, 5)
            step_value = float(distance) / total_steps
            
            # Variable scrolling speed (slower at beginning and end, faster in middle)
            new_position = scroll_position
            scroll_direction = 1 if distance > 0 else -1
            
            for step in range(int(total_steps)):
                # Variable pause based on scrolling phase (F-pattern attention)
                if step < total_steps * 0.2 or step > total_steps * 0.8:
                    # Beginning or end of scroll - more attentive, slower
                    pause_time = random.uniform(0.015, 0.025)
                else:
                    # Middle of scroll - less attentive, faster
                    pause_time = random.uniform(0.008, 0.015)
                    
                time.sleep(pause_time)
                
                # Add slight randomness to movement to mimic human imprecision
                current_step = step_value * (1 + random.uniform(-0.1, 0.1))
                new_position += current_step
                
                scroll_script = "window.scrollTo(0, %s);" % new_position
                js_utils.execute_script(driver, scroll_script)
                
                # Occasionally add micro-pauses (humans don't scroll perfectly smoothly)
                if random.random() < 0.1:  # 10% chance of micro-pause
                    time.sleep(random.uniform(0.05, 0.1))
        
        # Final adjustment with potential slight overshoot (human-like behavior)
        if distance != 0:
            time.sleep(0.01)
            
            # Sometimes overshoot slightly then correct (like humans do)
            if random.random() < 0.3:  # 30% chance of slight overshoot
                overshoot = random.randint(20, 60) * scroll_direction
                scroll_script = "window.scrollTo(%s, %s);" % (element_location_x_fix, element_location_y + overshoot)
                js_utils.execute_script(driver, scroll_script)
                time.sleep(0.1)
        
        scroll_script = "window.scrollTo(%s, %s);" % (element_location_x_fix, element_location_y)
        js_utils.execute_script(driver, scroll_script)
        
        # Final reading pause based on content length and position
        if distance > 1000:
            # Long scroll - user would need more recovery time
            time.sleep(random.uniform(0.2, 0.4))
        elif distance > 300:
            # Medium scroll - brief recovery
            time.sleep(random.uniform(0.1, 0.2))
        else:
            # Short scroll - minimal pause
            time.sleep(random.uniform(0.05, 0.1))    


    def click_element(self, driver, element, description="element"):
        """Click on an element with scroll-into-view and human-like hesitation."""
        logger.info("Clicking element")
        try:
            self.scroll_to_element(driver, element)
            
            # Move mouse to element before clicking
            try:
                ActionChains(driver).move_to_element(element).perform()
                time.sleep(random.uniform(0.2, 0.6))
            except Exception:
                pass
            
            # Natural pause after scrolling and mouse movement
            time.sleep(random.uniform(0.75, 2.25))
            
            try:
                element.click()
                logger.info(f"Clicked {description}")
            except Exception as e:
                logger.warning(f"Standard click failed. Trying JavaScript click...")
                driver.execute_script("arguments[0].click();", element)
                logger.info(f"Clicked {description} using JavaScript")
            
            # Post-click pause
            time.sleep(random.uniform(0.5, 1.5))
            
            return True
            
        except Exception as e:
            logger.error(f"Error clicking {description}")
            return False

    def type_text_into(self, driver, element, text, description="text"):
        """Type text into a specific element using enter_text when possible."""
        try:
            # Try to build a selector if element has name or id; fallback to direct send_keys
            selector = None
            try:
                element_id = element.get_attribute("id")
                if element_id:
                    selector = f"#{element_id}"
                else:
                    name_attr = element.get_attribute("name")
                    if name_attr:
                        selector = f"[name='{name_attr}']"
            except Exception:
                selector = None

            if selector:
                ok = enter_text(
                    driver,
                    selector,
                    text,
                    button=False,
                    timeout=30
                )
                return bool(ok)
            else:
                # Fallback to direct element interaction
                element.clear()
                for char in text:
                    element.send_keys(char)
                    time.sleep(random.uniform(0.05, 0.3))
                logger.info(f"Typed {description}: {text}")
                return True
        except Exception as e:
            logger.error(f"Error typing {description}: {e}")
            return False

    def press_enter_on(self, driver, element):
        """Press Enter on a given input element."""
        try:
            element.send_keys(Keys.ENTER)
            time.sleep(random.uniform(0.5, 1.5))
            return True
        except Exception as e:
            logger.error(f"Error pressing enter: {e}")
            return False
    
    def press_enter(self, driver):
        """Press enter key - handles both Google and YouTube search boxes"""
        try:
            logger.info("🔍 Attempting to press Enter...")
            
            # Try to find the search box using multiple selectors
            search_selectors = [
                "textarea[name='q']",  # Google search (textarea)
                "input[name='q']",     # Google search (input)
                "#APjFqb",  # Google search by ID
                "[jsname='yZiJbe']"  # Google search by jsname
            ]
            
            search_box = None
            for selector in search_selectors:
                try:
                    logger.info(f"🔍 Trying to find search box with selector: {selector}")
                    search_box = driver.find_element(By.CSS_SELECTOR, selector)
                    logger.info(f"✅ Found search box with selector: {selector}")
                    break
                except Exception as e:
                    logger.info(f"❌ Selector {selector} failed: {e}")
                    continue
            
            if search_box is None:
                logger.error("❌ Could not find search box for pressing Enter")
                return False
            
            # Press Enter
            logger.info("⌨️ Pressing Enter...")
            search_box.send_keys(Keys.ENTER)
            time.sleep(random.uniform(1.0, 2.0))
            logger.info("✅ Successfully pressed Enter")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error pressing enter: {e}")
            return False

    # # ===== Scrolling and Viewport Management =====
    # def scroll_viewport(self, driver, direction="down", amount=None):
    #     """Scroll viewport in a given direction or by a custom amount."""
    #     try:
    #         if direction == "down":
    #             script = "window.scrollBy(0, window.innerHeight / 2);"
    #         elif direction == "up":
    #             script = "window.scrollBy(0, -window.innerHeight / 2);"
    #         elif direction == "to_top":
    #             script = "window.scrollTo(0, 0);"
    #         elif direction == "to_bottom":
    #             script = "window.scrollTo(0, document.body.scrollHeight);"
    #         else:
    #             script = f"window.scrollBy(0, {amount});"
    #         driver.execute_script(script)
    #         time.sleep(random.uniform(0.5, 1.5))
    #         return True
    #     except Exception as e:
    #         logger.error(f"Scroll error: {e}")
    #         return False

    # ===== Form Interaction =====
    def fill_form(self, driver, form_data):
        """Fill a form using enter_text for each field."""
        try:
            for selector, value in form_data.items():
                ok = enter_text(
                    driver,
                    selector,
                    value,
                    button=False,
                    timeout=30
                )
                if not ok:
                    logger.warning(f"Failed to fill form field: {selector}")
            return True
        except Exception as e:
            logger.error(f"Error filling form: {e}")
            return False

    def submit_form(self, driver, form_element=None):
        """Submit a form element, or first form on the page if not provided."""
        try:
            if form_element:
                form_element.submit()
            else:
                forms = self.find_elements(driver, By.TAG_NAME, "form")
                if forms:
                    forms[0].submit()
            time.sleep(random.uniform(1.0, 3.0))
            return True
        except Exception as e:
            logger.error(f"Error submitting form: {e}")
            return False

    # ===== Search Helpers =====
    def search_google(self, driver, query):
        """
        Type a query into Google's search box using enter_text (no submit).
        
        Args:
            driver: Selenium WebDriver instance
            query (str): Search query to type into the search box
            
        Returns:
            bool: True if query was typed successfully, False otherwise
        """
        try:
            ok = enter_text(
                driver,
                "q",
                query,
                button=False,
                by=By.NAME,
                timeout=30
            )
            return bool(ok)
        except Exception as e:
            logger.error(f"Error typing Google search: {e}")
            return False

    def search_youtube(self, driver, query):
        """Type a query into YouTube's search box using enter_text (no submit)."""
        try:
            ok = enter_text(
                driver,
                "input[name='search_query']",
                query,
                button=False,
                timeout=30
            )
            return bool(ok)
        except Exception as e:
            logger.error(f"Error typing YouTube search: {e}")
            return False

    # ===== Link and Navigation Helpers =====
    def find_links_by_domain(self, driver, domain):
        """Return all anchor elements whose href contains a given domain substring."""
        links = self.find_elements(driver, By.TAG_NAME, "a")
        matching = []
        for link in links:
            try:
                href = link.get_attribute("href")
                if href and domain in href:
                    matching.append(link)
            except Exception:
                continue
        return matching

    def click_random_link(self, driver, links=None):
        """Click a random link from a provided list or from the page anchors."""
        if not links:
            links = self.find_elements(driver, By.TAG_NAME, "a")
        if links:
            link = random.choice(links)
            return self.click_element(driver, link, "random link")
        return False

    def click_link_by_text(self, driver, link_text, partial_match=False):
        """Click a link by its visible text (exact or partial match)."""
        try:
            xpath = f"//a[contains(text(), '{link_text}')]" if partial_match else f"//a[text()='{link_text}']"
            link = self.find_element(driver, By.XPATH, xpath)
            if link:
                return self.click_element(driver, link, f"link with text '{link_text}'")
            return False
        except Exception as e:
            logger.error(f"Error clicking link by text: {e}")
            return False

    # ===== Page State and Content Checking =====
    def wait_for_page_load(self, driver, timeout=30):
        """Wait until document.readyState is 'complete'."""
        try:
            WebDriverWait(driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            return True
        except TimeoutException:
            logger.error("Page did not load in time")
            return False

    def is_element_visible(self, driver, by, value):
        """Return True if element exists and is displayed."""
        try:
            el = self.find_element(driver, by, value)
            return el.is_displayed() if el else False
        except Exception:
            return False

    def get_page_title(self, driver):
        """Return the current page title."""
        try:
            return driver.title
        except Exception:
            return ""

    def get_page_text(self, driver):
        """Return all visible text from the body element."""
        try:
            return driver.find_element(By.TAG_NAME, "body").text
        except Exception:
            return ""

    # ===== Tab Management =====
    def open_new_tab(self, driver, url=None):
        """Open a new tab and optionally navigate to a URL."""
        try:
            driver.execute_script("window.open();")
            driver.switch_to.window(driver.window_handles[-1])
            if url:
                self.navigate_to(driver, url)
            return True
        except Exception as e:
            logger.error(f"Error opening new tab: {e}")
            return False

    def switch_to_tab(self, driver, index):
        """Switch to a specific tab by index if it exists."""
        try:
            if 0 <= index < len(driver.window_handles):
                driver.switch_to.window(driver.window_handles[index])
                return True
            return False
        except Exception as e:
            logger.error(f"Error switching tab: {e}")
            return False

    def close_current_tab(self, driver):
        """Close the current tab and switch to the first tab if others remain."""
        try:
            if len(driver.window_handles) > 1:
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                return True
            return False
        except Exception as e:
            logger.error(f"Error closing tab: {e}")
            return False

    # ===== JavaScript Execution =====
    def execute_script(self, driver, script, *args):
        """Execute a JavaScript snippet and return its result."""
        try:
            return driver.execute_script(script, *args)
        except JavascriptException as e:
            logger.error(f"JavaScript execution failed: {e}")
            return None

    # ===== Mouse and Keyboard Actions =====
    def move_mouse_to_element(self, driver, element):
        """Move the mouse to a specific element."""
        try:
            ActionChains(driver).move_to_element(element).perform()
            time.sleep(random.uniform(0.2, 0.8))
            return True
        except Exception as e:
            logger.error(f"Error moving mouse to element: {e}")
            return False

    def move_mouse_randomly(self, driver, moves=3):
        """Perform a few small random mouse movements."""
        try:
            chain = ActionChains(driver)
            for _ in range(moves):
                x = random.randint(-100, 100)
                y = random.randint(-50, 50)
                chain.move_by_offset(x, y).perform()
                time.sleep(random.uniform(0.1, 0.3))
            return True
        except Exception as e:
            logger.error(f"Error moving mouse randomly: {e}")
            return False

    def press_key(self, driver, key):
        """Press a specific keyboard key."""
        try:
            ActionChains(driver).send_keys(key).perform()
            time.sleep(random.uniform(0.1, 0.5))
            return True
        except Exception as e:
            logger.error(f"Error pressing key: {e}")
            return False

    # ===== Screenshot and Debugging =====
    def take_screenshot(self, driver, filename="screenshot.png"):
        """Save a screenshot to the given filename."""
        try:
            driver.save_screenshot(filename)
            logger.info(f"Screenshot saved as {filename}")
            return True
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return False

    def get_console_logs(self, driver):
        """Return browser console logs if available for this driver."""
        try:
            return driver.get_log("browser")
        except Exception:
            return []

    # ===== Waiting and Timing =====
    def random_delay(self, min_seconds=1.0, max_seconds=3.0):
        """Sleep for a random duration within the given bounds."""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
        return True

    def wait_for_element(self, driver, by, value, timeout=10):
        """Wait for an element to be present in the DOM."""
        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return True
        except TimeoutException:
            return False

    def wait_for_element_visible(self, driver, by, value, timeout=10):
        """Wait for an element to be visible on the page."""
        try:
            WebDriverWait(driver, timeout).until(
                EC.visibility_of_element_located((by, value))
            )
            return True
        except TimeoutException:
            return False

    def type_text(self, driver, text):
        """Type text into the search bar - handles multiple search box types"""
        try:
            # Try to find the search box using multiple selectors
            search_selectors = [
                "textarea[name='q']",          # Primary Google selector
                "input[name='search_query']",  # Primary YouTube selector  
                "textarea.gLFyf",              # Google class-based
                "input.ytSearchboxComponentInput",  # YouTube class-based
                "div.a4bIc textarea",          # Google container-based
                "yt-searchbox input",          # YouTube custom element
                "textarea#APjFqb",             # Google ID-based (specific)
                "input[name='q']",             # Legacy Google input
                "input#input",                           # ID-based (short & stable)
                "#input",                                # Shorthand for the same ID
                "input.truncate",                        # Class-based
                "#inputWrapper > input",                 # Parent-child structure
                "input[type='search']",                  # Attribute-based
                "input[placeholder='Search Google or type a URL']",
            ]
            
            main_selector = None
            search_box = None

            
            for selector in search_selectors:
                try:
                    logger.info(f"�� Trying selector: {selector}")
                    search_box = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    logger.info(f"✅ Found search box with selector: {selector}")
                    main_selector = selector
                    break
                except Exception as e:
                    logger.info(f"❌ Selector {selector} failed: {e}")
                    continue
            
            if search_box is None:
                logger.error("❌ Could not find search box with any selector")
                return False
            
            # Clear and type text
            logger.info("🧹 Clearing search box...")
            ok = enter_text(
                driver,
                main_selector,
                text,
                button=False,
                timeout=30
            )
            logger.info(f"✅ Successfully typed: {text}")
            return bool(ok)
            
        except Exception as e:
            logger.error(f"❌ Error typing text: {e}")
            return False




    def like_video(self, driver):
        """Like the current video"""
        try:
            like_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label*='Like']"))
            )
            
            # Check if already liked
            aria_label = like_button.get_attribute("aria-label")
            if "Unlike" in aria_label:
                logger.info("Video already liked")
                return True
            
            # Scroll to button and click
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", like_button)
            time.sleep(random.uniform(0.5, 1.0))
            like_button.click()
            logger.info("Liked video")
            time.sleep(random.uniform(1.0, 2.0))
            return True
        except Exception as e:
            logger.error(f"Error liking video: {e}")
            return False

    def dislike_video(self, driver):
        """Dislike the current video"""
        try:
            dislike_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label*='Dislike']"))
            )
            
            # Check if already disliked
            aria_label = dislike_button.get_attribute("aria-label")
            if "Undo" in aria_label:
                logger.info("Video already disliked")
                return True
            
            # Scroll to button and click
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", dislike_button)
            time.sleep(random.uniform(0.5, 1.0))
            dislike_button.click()
            logger.info("Disliked video")
            time.sleep(random.uniform(1.0, 2.0))
            return True
        except Exception as e:
            logger.error(f"Error disliking video: {e}")
            return False

    def subscribe_channel(self, driver):
        """Subscribe to the current channel"""
        try:
            subscribe_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label*='Subscribe']"))
            )
            
            # Check if already subscribed
            aria_label = subscribe_button.get_attribute("aria-label")
            if "Unsubscribe" in aria_label:
                logger.info("Already subscribed to channel")
                return True
            
            # Scroll to button and click
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", subscribe_button)
            time.sleep(random.uniform(0.5, 1.0))
            subscribe_button.click()
            logger.info("Subscribed to channel")
            time.sleep(random.uniform(1.0, 2.0))
            return True
        except Exception as e:
            logger.error(f"Error subscribing to channel: {e}")
            return False

    def mute_video(self, driver):
        """Mute the current video"""
        try:
            mute_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.ytp-mute-button"))
            )
            
            # Check if already muted
            aria_label = mute_button.get_attribute("aria-label")
            if "Unmute" in aria_label:
                logger.info("Video already muted")
                return True
            
            # Click to mute
            mute_button.click()
            logger.info("Muted video")
            time.sleep(random.uniform(1.0, 2.0))
            return True
        except Exception as e:
            logger.error(f"Error muting video: {e}")
            return False

    def skip_ad(self, driver):
        """Skip ad if skip button is available"""
        try:
            skip_button = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.ytp-skip-ad-button"))
            )
            if skip_button.is_displayed():
                time.sleep(random.uniform(0.8, 2.0))
                skip_button.click()
                logger.info("Skipped ad")
                time.sleep(random.uniform(1.0, 2.5))
                return True
        except:
            pass
        return False

    def fast_forward(self, driver, duration=1.0):
        """Fast forward video by pressing right arrow key"""
        try:
            ActionChains(driver).key_down(Keys.ARROW_RIGHT).key_up(Keys.ARROW_RIGHT).perform()
            time.sleep(duration)
            return True
        except Exception as e:
            logger.error(f"Error fast forwarding: {e}")
            return False

    def rewind(self, driver, duration=1.0):
        """Rewind video by pressing left arrow key"""
        try:
            ActionChains(driver).key_down(Keys.ARROW_LEFT).key_up(Keys.ARROW_LEFT).perform()
            time.sleep(duration)
            return True
        except Exception as e:
            logger.error(f"Error rewinding: {e}")
            return False

    def pause_video(self, driver):
        """Pause the current video"""
        try:
            video_element = driver.find_element(By.CSS_SELECTOR, "video.html5-main-video")
            video_element.click()
            logger.info("Paused video")
            time.sleep(random.uniform(1.0, 2.0))
            return True
        except Exception as e:
            logger.error(f"Error pausing video: {e}")
            return False

    def resume_video(self, driver):
        """Resume the current video"""
        try:
            video_element = driver.find_element(By.CSS_SELECTOR, "video.html5-main-video")
            video_element.click()
            logger.info("Resumed video")
            time.sleep(random.uniform(1.0, 2.0))
            return True
        except Exception as e:
            logger.error(f"Error resuming video: {e}")
            return False

    def scroll_to_comments(self, driver):
        """Scroll to the comment section"""
        try:
            comment_section = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-comments"))
            )
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'start'});", comment_section)
            time.sleep(random.uniform(1.5, 3.0))
            return True
        except Exception as e:
            logger.error(f"Error scrolling to comments: {e}")
            return False


    
    def extract_video_id(self, url):
        """Extracts YouTube video ID from various URL formats including Shorts"""
        if not url:
            return None
            
        # Handle URL encoding
        decoded_url = unquote(url)
        
        # Regular expression pattern for YouTube video IDs
        patterns = [
            r"youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})",  # Standard watch URL
            r"youtu\.be/([a-zA-Z0-9_-]{11})",               # Short URL
            r"youtube\.com/embed/([a-zA-Z0-9_-]{11})",      # Embed URL
            r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",     # Shorts URL
            r"youtube\.com/live/([a-zA-Z0-9_-]{11})",       # Live stream URL
            r"v=([a-zA-Z0-9_-]{11})",                       # Fallback for v parameter
            r"/([a-zA-Z0-9_-]{11})"                         # Fallback for 11-character ID
        ]
        
        for pattern in patterns:
            match = re.search(pattern, decoded_url)
            if match:
                return match.group(1)
                
        # Parse URL and extract video ID as fallback
        try:
            parsed = urlparse(decoded_url)
            if 'youtube.com' in parsed.netloc or 'youtu.be' in parsed.netloc:
                # Handle shorts URLs
                if parsed.path.startswith('/shorts/'):
                    return parsed.path.split('/')[2]
                
                # Handle standard watch URLs
                if parsed.path == '/watch' and 'v' in parse_qs(parsed.query):
                    return parse_qs(parsed.query)['v'][0]
                
                # Handle embed URLs
                if parsed.path.startswith('/embed/'):
                    return parsed.path.split('/')[2]
                
                # Handle youtu.be short URLs
                if parsed.netloc == 'youtu.be':
                    return parsed.path[1:]
        except:
            pass
            
        return None

    def click_video_link(self, driver, video_element):
        """Click on a video link in search results"""
        try:
            video_link_elem = video_element.find_element(By.CSS_SELECTOR, 'a#video-title')
            
            # Ensure element is in view and clickable
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", video_link_elem)
            time.sleep(random.uniform(0.5, 1.0))
            
            # Wait for element to be clickable
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'a#video-title'))
            )
            
            video_link_elem.click()
            logger.info("Clicked on video link")
            time.sleep(random.uniform(1.5, 3.5))
            return True
        except Exception as e:
            logger.error(f"Error clicking video link: {e}")
            return False

    def wait_for_video_player(self, driver, timeout=20):
        """Wait for video player to load"""
        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "video.html5-main-video"))
            )
            logger.info("Video player loaded")
            return True
        except Exception as e:
            logger.error(f"Error waiting for video player: {e}")
            return False

    def wait_for_search_results(self, driver, timeout=30):
        """Wait for search results to load"""
        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div#search, div[data-ved], h3"))
            )
            logger.info("Search results loaded")
            return True
        except Exception as e:
            logger.error(f"Error waiting for search results: {e}")
            return False

    def watch_video(self, driver, duration=30):
        """Watch video for specified duration"""
        try:
            logger.info(f"Watching video for {duration} seconds")
            time.sleep(duration)
            return True
        except Exception as e:
            logger.error(f"Error watching video: {e}")
            return False

    def scroll_comment_section(self, driver):
        """Scroll through the comment section"""
        try:
            logger.info("Scrolling through comment section")
            # Scroll to comments area
            comments_section = driver.find_element(By.CSS_SELECTOR, "ytd-comments")
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", comments_section)
            time.sleep(random.uniform(1.0, 2.0))
            
            # Scroll within comments
            for _ in range(3):
                driver.execute_script("window.scrollBy(0, 300);")
                time.sleep(random.uniform(0.5, 1.5))
            
            logger.info("Successfully scrolled comment section")
            return True
        except Exception as e:
            logger.error(f"Error scrolling comment section: {e}")
            return False

