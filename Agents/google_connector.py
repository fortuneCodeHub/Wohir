#!/usr/bin/python3
"""
    Google Connector - High-level YouTube behaviors
    Author: Fortune Nwohiri
"""
import time
import random
import json
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
from urllib.parse import urlparse, parse_qs, unquote
import re
from logging_config.logger import get_logger
from .agent import Agent
from .google_actions import GoogleActions
from selenium.webdriver.common.keys import Keys
from seleniumbase.fixtures import js_utils

logger = get_logger("GoogleConnector")


class GoogleConnector(Agent):
    """
    The bridge between the Brain and Google.
    This is where high-level behaviors are defined.
    A Connector decides which low-level actions to use from google_actions.py.
    """

    def __init__(self, target_url=None):
        super().__init__()
        self.actions = GoogleActions()
        self.target_url = target_url

    def search(self, driver, keyword: str):
        """
        High-level search behavior: focuses search bar → types text → presses enter
        """
        try:
            logger.info(f"Searching for: {keyword}")
            
            # Step 1: Focus the search bar
            # if not self.actions.focus_search_bar(driver):
            #     logger.error("Failed to focus search bar")
            #     return False
            
            # Step 2: Type the search keyword
            if not self.actions.type_text(driver, keyword):
                logger.error("Failed to type search keyword")
                return False
            
            # Step 3: Press enter to search
            if not self.actions.press_enter(driver):
                logger.error("Failed to press enter")
                return False
            
            # Step 4: Wait for search results
            if not self.actions.wait_for_search_results(driver):
                logger.error("Failed to load search results")
                return False
            
            logger.info(f"Successfully searched for: {keyword}")
            return True
            
        except Exception as e:
            logger.error(f"Error in search: {e}")
            return False
        
    def explore_account(self, driver, max_actions=3):
        """
        Simulate natural exploration of Google account page
        with random actions to appear more human-like
        """
        logger.info("🔍 Exploring Google account page")
        
        # Define what constitutes being on the account page
        def is_on_account_page(url):
            # Check if we're on the main account page or a sub-page
            return ("myaccount.google.com" in url and 
                    "/signin/" not in url and 
                    "/ServiceLogin" not in url and
                    "accounts.google.com/v3/signin" not in url)
        
        try:
            # Store the original URL to detect navigation away from account page
            original_url = driver.current_url
            
            # Check if we're starting from a valid account page
            if not is_on_account_page(original_url):
                logger.warning("⚠️ Not starting from a valid account page, redirecting")
                driver.get("https://myaccount.google.com/")
                time.sleep(2)
            
            # Set a timeout to prevent infinite exploration
            start_time = time.time()
            max_exploration_time = 30  # seconds
            
            # Randomly decide how many actions to perform (1-3)
            num_actions = random.randint(1, max_actions)
            logger.info(f"🔍 Will perform {num_actions} exploration actions")
            
            # List of possible exploration actions with weights
            exploration_actions = [
                (self.actions._click_navbar_item, 0.4),
                (self.actions._click_main_content_button, 0.3),
                (self.actions._use_search_bar, 0.2),
                (self.actions._scroll_account_page, 0.1)
            ]
            
            # Perform random actions
            for i in range(num_actions):
                # Check timeout
                if time.time() - start_time > max_exploration_time:
                    logger.info("⏰ Exploration time limit reached")
                    break
                    
                # Check if we're still on the account page
                if not is_on_account_page(driver.current_url):
                    logger.info("🚪 Left account page - ending exploration early")
                    break
                    
                # Choose a random action based on weights
                action_func = random.choices(
                    [action[0] for action in exploration_actions],
                    weights=[action[1] for action in exploration_actions],
                    k=1
                )[0]
                
                # Execute the action
                logger.info(f"🔍 Performing exploration action {i+1}/{num_actions}")
                
                # Store URL before action to detect navigation
                url_before_action = driver.current_url
                success = action_func(driver)
                
                if not success:
                    logger.warning("⚠️ Action failed, trying next action")
                    continue
                    
                # Check if the action caused navigation away from account page
                if not is_on_account_page(driver.current_url):
                    logger.info("🚪 Action navigated away from account page")
                    break
                    
                # If we're still on account page but URL changed, we might be in a sub-section
                # In this case, we can continue but might need to adjust our element selectors
                if driver.current_url != url_before_action:
                    logger.info("🔍 Navigated to account sub-section, continuing exploration")
                
                # Random delay between actions
                delay = random.uniform(1.5, 4.0)
                logger.info(f"⏳ Waiting {delay:.1f}s before next action")
                time.sleep(delay)
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Error exploring account: {e}")
            # Try to navigate back to the account page if we encountered an error
            try:
                if not is_on_account_page(driver.current_url):
                    driver.open("https://myaccount.google.com/")
                    logger.info("🔁 Navigated back to account homepage after error")
            except:
                pass
            return False

    def _click_main_content_button(self, driver):
        """Click a random button in the main content area, avoiding security-sensitive areas"""
        try:
            # Avoid security-sensitive areas that might trigger authentication
            avoid_selectors = [
                '[href*="security"]',
                '[href*="signin"]',
                '[href*="password"]',
                '[href*="2step"]',
                '[href*="recovery"]',
                '[data-identifier*="security"]',
                'button[aria-label*="security"]',
                'button[aria-label*="password"]',
                'button[aria-label*="sign in"]',
                'button[aria-label*="verification"]'
            ]
            
            # Find all clickable elements excluding security-sensitive ones
            all_elements = driver.find_elements(By.CSS_SELECTOR, "a, button, div[role='button'], span[role='button']")
            safe_elements = []
            
            for element in all_elements:
                # Skip elements that match any of the avoid selectors
                is_unsafe = False
                for selector in avoid_selectors:
                    try:
                        if driver.execute_script(
                            "return arguments[0].matches(arguments[1]);", 
                            element, selector
                        ):
                            is_unsafe = True
                            break
                    except:
                        # If JavaScript execution fails, check attributes manually
                        href = element.get_attribute("href") or ""
                        aria_label = element.get_attribute("aria-label") or ""
                        data_id = element.get_attribute("data-identifier") or ""
                        
                        if ("security" in href or "signin" in href or "password" in href or
                            "security" in aria_label.lower() or "password" in aria_label.lower() or
                            "security" in data_id.lower()):
                            is_unsafe = True
                            break
                
                if is_unsafe:
                    continue
                    
                # Only include visible, clickable elements
                if element.is_displayed() and element.is_enabled():
                    safe_elements.append(element)
            
            if not safe_elements:
                logger.warning("No safe elements found to click")
                return False
                
            # Choose a random safe element
            element = random.choice(safe_elements)
            element_text = element.text.strip() or element.get_attribute("aria-label") or "unknown"
            logger.info(f"🔘 Clicking element: {element_text}")
            
            # Scroll to element and click
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.3)
            
            # Try multiple click methods
            try:
                element.click()
            except:
                try:
                    ActionChains(driver).move_to_element(element).click().perform()
                except:
                    driver.execute_script("arguments[0].click();", element)
            
            time.sleep(1)  # Wait for any navigation
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error clicking main content element: {e}")
            return False

    def _element_matches_selector(self, element, selector):
        """Check if an element matches a CSS selector"""
        try:
            # Use JavaScript to check if element matches selector
            return self.driver.execute_script(
                "return arguments[0].matches(arguments[1]);", 
                element, selector
            )
        except:
            return False
        
    

    def click_web_result(self, driver):
        """
            This function helps with clicking a web results
        """
        logger.info("🔍 Clicking a web result")
        # Locate search result elements using a more specific CSS selector
        results = driver.find_elements(By.CSS_SELECTOR, "h3.LC20lb.MBeuO.DKV0Md")
        # logger.debug("Now entering the scroll down function")
        if results:
            # Select a random result from the top 5
            result = random.choice(results)
            self.actions.scroll_down(driver, max_scrolls=3, scroll_duration=3)
            # logger.debug("Now done with scroll down and entering clicking element")
            self.actions.click_element(driver, result, "web result")
            return True
        return False



    def go_back(self, driver):
        """Go back to previous page"""
        try:
            logger.info("Going back to previous page")
            driver.back()
            time.sleep(random.uniform(1.0, 2.0))
            return True
        except Exception as e:
            logger.error(f"Error going back: {e}")
            return False


    def navigate_to_search_results(self, driver, search_keyword=None, search_results_url=None):
        """
        Robust function to navigate to search results page.
        Priority order:
        1. Try browser back navigation first
        2. Use direct URL if available
        3. Extract keyword and perform search
        4. Use provided keyword for fresh search
        5. Navigate to Google homepage as last resort
        
        Args:
            driver: Selenium WebDriver instance
            search_keyword (str, optional): Keyword to search for
            search_results_url (str, optional): Direct URL to search results
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("Navigating to search results page")
            initial_url = driver.current_url
            
            # Store the initial state for comparison
            navigation_successful = False
            
            # Priority 1: Try browser back navigation first
            # This is fastest and preserves the exact search state
            logger.info("Attempting browser back navigation")
            try:
                # Store where we are before going back
                before_back_url = driver.current_url
                
                # Try going back
                driver.back()
                time.sleep(random.uniform(1.5, 2.5))
                
                # Check if we moved and if we're on a search page
                after_back_url = driver.current_url
                
                if after_back_url != before_back_url:
                    # We successfully navigated somewhere
                    if "google.com/search" in after_back_url and "q=" in after_back_url:
                        logger.info("Successfully returned to search results via browser back")
                        return True
                    elif "google.com" in after_back_url:
                        # We're on Google but not search results
                        logger.info("Browser back led to Google homepage, will perform search")
                        # Continue to search strategies below
                    else:
                        # We're somewhere else, need to continue with other strategies
                        logger.info("Browser back didn't lead to search results, trying other methods")
                else:
                    logger.info("Browser back had no effect, trying other methods")
                    
            except Exception as e:
                logger.debug(f"Browser back navigation failed: {e}")
            
            # Priority 2: Check current URL - we might already be on search results
            current_url = driver.current_url
            if "google.com/search" in current_url and "q=" in current_url:
                logger.info("Already on a search results page")
                return True
            
            # Priority 3: Use provided search results URL if available
            if search_results_url and search_results_url != current_url:
                logger.info(f"Using provided search results URL: {search_results_url}")
                try:
                    driver.get(search_results_url)
                    time.sleep(random.uniform(*self.timing_params["search_processing_time"]))
                    
                    # Verify we're on the correct page
                    new_url = driver.current_url
                    if new_url == search_results_url or ("google.com/search" in new_url and "q=" in new_url):
                        logger.info("Successfully navigated to search results via direct URL")
                        return True
                    else:
                        logger.warning("Direct URL navigation didn't land on search results page")
                except Exception as e:
                    logger.warning(f"Direct URL navigation failed: {e}")
            
            # Priority 4: Check if we're on Google and can search
            current_url = driver.current_url
            if "google.com" in current_url:
                logger.info("On Google domain, attempting search")
                
                # First try to extract keyword from current URL (might have partial search info)
                extracted_keyword = self._extract_search_keyword(current_url)
                
                # Use extracted keyword, or fall back to provided keyword
                keyword_to_search = extracted_keyword or search_keyword
                
                if keyword_to_search:
                    logger.info(f"Performing search with keyword: {keyword_to_search}")
                    search_result = self.search(driver, keyword_to_search)
                    if search_result:
                        return True
                    else:
                        logger.warning("Search failed, will try navigation to Google")
                else:
                    logger.info("No keyword available, need to navigate to Google first")
            
            # Priority 5: Try to extract keyword from the provided URL if we haven't already
            if not navigation_successful and search_results_url and not search_keyword:
                extracted_from_url = self._extract_search_keyword(search_results_url)
                if extracted_from_url:
                    logger.info(f"Extracted keyword from provided URL: {extracted_from_url}")
                    
                    # Navigate to Google first if not there
                    if "google.com" not in driver.current_url:
                        logger.info("Navigating to Google first")
                        driver.get("https://www.google.com")
                        time.sleep(random.uniform(2.0, 4.0))
                    
                    # Now perform the search
                    if "google.com" in driver.current_url:
                        search_result = self.search(driver, extracted_from_url)
                        if search_result:
                            return True
            
            # Priority 6: Use provided search keyword for fresh search
            if search_keyword and not navigation_successful:
                logger.info(f"Performing fresh search with provided keyword: {search_keyword}")
                
                # Navigate to Google first if not there
                if "google.com" not in driver.current_url:
                    logger.info("Navigating to Google first")
                    driver.get("https://www.google.com")
                    time.sleep(random.uniform(2.0, 4.0))
                
                # Perform the search
                if "google.com" in driver.current_url:
                    return self.search(driver, search_keyword)
            
            # Priority 7: Last resort - navigate to Google homepage
            logger.info("All strategies exhausted, navigating to Google homepage as last resort")
            driver.get("https://www.google.com")
            time.sleep(random.uniform(2.0, 4.0))
            
            # Final check
            if "google.com" in driver.current_url:
                logger.info("Successfully navigated to Google homepage")
                
                # If we have any keyword, try one more search
                final_keyword = search_keyword or self._extract_search_keyword(search_results_url) if search_results_url else None
                if final_keyword:
                    logger.info(f"Final search attempt with keyword: {final_keyword}")
                    return self.search(driver, final_keyword)
                
                return True
            else:
                logger.error("Failed to navigate to Google")
                return False
                
        except Exception as e:
            logger.error(f"Critical error in navigate_to_search_results: {e}")
            
            # Emergency fallback
            try:
                logger.info("Attempting emergency fallback to Google")
                driver.get("https://www.google.com")
                time.sleep(random.uniform(2.0, 4.0))
                return "google.com" in driver.current_url
            except:
                return False

    def navigate_to_search_results_smart(self, driver, context=None):
        """
        Smarter version that uses context to determine best navigation approach.
        
        Args:
            driver: Selenium WebDriver instance
            context (dict): Context containing search history, current state, etc.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not context:
                context = {}
            
            # Priority 1: Use stored search results URL from context
            stored_url = context.get('last_search_results_url')
            if stored_url:
                logger.info("Using stored search results URL from context")
                driver.get(stored_url)
                time.sleep(random.uniform(*self.timing_params["search_processing_time"]))
                
                if "google.com/search" in driver.current_url:
                    logger.info("Successfully navigated using stored URL")
                    return True
            
            # Priority 2: Use search keyword from context
            search_keyword = context.get('search_keyword')
            if search_keyword:
                logger.info(f"Using stored search keyword: {search_keyword}")
                return self.search(driver, search_keyword)
            
            # Priority 3: Extract from current page if we're on a search results page
            current_url = driver.current_url
            if "google.com/search" in current_url:
                logger.info("Already on search results page")
                return True
            
            # Priority 4: Use the generic navigation approach
            return self.navigate_to_search_results(driver)
            
        except Exception as e:
            logger.error(f"Error in smart navigation: {e}")
            return self.navigate_to_search_results(driver)  # Fallback to basic version

    def _extract_search_keyword(self, search_results_url):
        """Extract search keyword from search results URL"""
        try:
            if "search_query=" not in search_results_url:
                return None
            
            patterns = [
                r'search_query=([^&]+)',
                r'search_query=([^#]+)',
                r'q=([^&]+)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, search_results_url)
                if match:
                    return unquote(match.group(1))
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting search keyword: {e}")
            return None
        

    def click_target_site(self, driver, target_url=None):
        """
        Click on the target website in search results.
        
        Args:
            driver: Selenium WebDriver instance
        
        Returns:
            bool: True if successful, False otherwise
        """
        logger.info("🎯 Attempting to click target website")
        try:
            # Extract domain from target URL
            target_domain = urlparse(target_url).netloc

            # Find all result links
            results = driver.find_elements(By.CSS_SELECTOR, "h3.LC20lb.MBeuO.DKV0Md")
            target_results = []

            for result in results:
                try:
                    parent = result.find_element(By.XPATH, "./ancestor::a")
                    href = parent.get_attribute('href')
                    if href and target_domain in href:
                        target_results.append(parent)
                except Exception:
                    continue

            if target_results:
                # Click the first target result
                target = target_results[0]
                self.actions.scroll_to_element(driver, target)
                self.actions.click_element(driver, target, "target website")
                logger.info("✅ Successfully clicked target website")
                return True

            logger.warning("❌ Target website not found in current results")
            return False

        except Exception as e:
            logger.error(f"❌ Error clicking target website: {e}")
            return False

    def click_competitor_site(self, driver, competitors=None):
        """
        Click on a competitor website from search results.
        
        Args:
            driver: Selenium WebDriver instance
            competitors: Optional list of competitor domains
            
        Returns:
            bool: True if successful, False otherwise
        """
        logger.info("🎯 Attempting to click competitor website")
        try:
            if not competitors:
                # Load competitors from configuration
                try:
                    with open('competitors_urls.json', 'r') as f:
                        competitors_json = json.load(f)
                        competitor_urls = competitors_json.get('competitors', [])
                        competitors = [url for url in competitor_urls]
                        logger.info(f"📋 Loaded {len(competitors)} competitors from JSON")
                        for i, comp in enumerate(competitors):
                            logger.info(f"   {i+1}. {comp}")
                except Exception as e:
                    logger.error(f"❌ Failed to load competitors: {e}")
                    return False
            
            # Find all result links
            results = driver.find_elements(By.CSS_SELECTOR, "h3.LC20lb.MBeuO.DKV0Md")
            logger.info(f"🔍 Found {len(results)} search result elements")
            
            competitor_results = []
            
            for i, result in enumerate(results):
                try:
                    parent = result.find_element(By.XPATH, "./ancestor::a")
                    href = parent.get_attribute('href')
                    logger.info(f"📎 Result {i+1} URL: {href}")
                    
                    # Check if this URL matches any competitor URL
                    for comp_url in competitors:
                        # Compare the full URLs more intelligently
                        if self._urls_match(href, comp_url):
                            logger.info(f"✅ MATCH FOUND! Result URL matches competitor: {comp_url}")
                            competitor_results.append(parent)
                            break
                    else:
                        logger.info(f"❌ No match found for result {i+1}")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Error processing result {i+1}: {e}")
                    continue
            
            logger.info(f"🎯 Found {len(competitor_results)} matching competitor results")
            
            if competitor_results:
                # Click a random competitor result
                target = random.choice(competitor_results)
                target_url = target.get_attribute('href')
                logger.info(f"🎲 Randomly selected competitor URL: {target_url}")
                
                self.actions.scroll_to_element(driver, target)
                self.actions.click_element(driver, target, "competitor website")
                logger.info("✅ Successfully clicked competitor website")
                return True
            
            logger.warning("❌ No competitor websites found in current results")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error clicking competitor website: {e}")
            return False
        

    def _urls_match(self, search_result_url, competitor_url):
        """
        Compare URLs to determine if they match, handling various URL formats.
        
        Args:
            search_result_url: URL from search results
            competitor_url: URL from competitors JSON
            
        Returns:
            bool: True if URLs match, False otherwise
        """
        try:
            from urllib.parse import urlparse, parse_qs
            
            # Parse both URLs
            search_parsed = urlparse(search_result_url.lower())
            comp_parsed = urlparse(competitor_url.lower())
            
            
            # 1. Check if domains match exactly
            if search_parsed.netloc == comp_parsed.netloc:
                logger.info("✅ Domain match found")
                
                # 2. Check if paths match (considering trailing slashes)
                search_path = search_parsed.path.rstrip('/')
                comp_path = comp_parsed.path.rstrip('/')
                
                if search_path == comp_path:
                    # logger.info("✅ Path match found - URLs are identical")
                    return True
                elif search_path.startswith(comp_path) or comp_path.startswith(search_path):
                    # logger.info("✅ Path partial match found")
                    return True
                else:
                    logger.info(f"❌ Paths don't match: '{search_path}' vs '{comp_path}'")
            else:
                pass
                # logger.info(f"❌ Domains don't match: '{search_parsed.netloc}' vs '{comp_parsed.netloc}'")
            
            # 3. Fallback: Check if competitor domain is contained in search URL
            # This handles cases where search results might have additional parameters or redirects
            comp_domain = comp_parsed.netloc.replace('www.', '')
            search_domain = search_parsed.netloc.replace('www.', '')
            
            if comp_domain in search_domain or search_domain in comp_domain:
                logger.info(f"✅ Domain substring match found: '{comp_domain}' <-> '{search_domain}'")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"❌ Error comparing URLs: {e}")
            return False

    def click_random_result(self, driver, exclude_domains=None):
        """
        Click on a random organic result, excluding specified domains.
        
        Args:
            driver: Selenium WebDriver instance
            exclude_domains: List of domains to exclude
            
        Returns:
            bool: True if successful, False otherwise
        """
        logger.info("🎯 Attempting to click random organic result")
        try:
            exclude_domains = exclude_domains or []
            if self.target_url:
                exclude_domains.append(self.target_url)
            
            results = driver.find_elements(By.CSS_SELECTOR, "h3.LC20lb.MBeuO.DKV0Md")
            valid_results = []
            
            for result in results:
                try:
                    parent = result.find_element(By.XPATH, "./ancestor::a")
                    href = parent.get_attribute('href')
                    domain = self.actions.extract_domain(href)
                    
                    if not any(excluded in domain for excluded in exclude_domains):
                        valid_results.append(parent)
                except Exception:
                    continue
                    
            if valid_results:
                target = random.choice(valid_results)
                self.actions.scroll_to_element(driver, target)
                self.actions.click_element(driver, target, "organic result")
                logger.info("✅ Successfully clicked organic result")
                return True
            
            logger.warning("❌ No valid organic results found")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error clicking organic result: {e}")
            return False
        


    def go_to_next_page(self, driver, max_wait=10, scroll_before_click=True, retry_attempts=3):
        """
        Navigate to the next page in Google search results.
        
        Args:
            driver: Selenium WebDriver or SeleniumBase driver instance
            max_wait: Maximum time to wait for elements (seconds)
            scroll_before_click: Whether to scroll to the element before clicking
            retry_attempts: Number of retry attempts if navigation fails
            
        Returns:
            bool: True if successfully navigated to next page, False otherwise
        """
        
        for attempt in range(retry_attempts):
            try:
                logger.info(f"Attempting to go to next page (attempt {attempt + 1}/{retry_attempts})")
                
                # Store initial URL to verify navigation
                initial_url = driver.current_url
                
                # Strategy 1: Try to find and click the "Next" button using ID (most reliable)
                try:
                    wait = WebDriverWait(driver, max_wait)
                    
                    # Find next button by ID
                    next_button = wait.until(
                        EC.element_to_be_clickable((By.ID, "pnnext"))
                    )
                    
                    if next_button:
                        logger.info("Found 'Next' button by ID")
                        
                        # Scroll to element if needed
                        if scroll_before_click:
                            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", next_button)
                            time.sleep(random.uniform(0.5, 1.0))
                        
                        # Click the next button
                        try:
                            next_button.click()
                        except:
                            # Fallback to JavaScript click if regular click fails
                            driver.execute_script("arguments[0].click();", next_button)
                        
                        # Wait for page to load
                        time.sleep(random.uniform(2.0, 3.0))
                        
                        # Verify navigation occurred
                        if driver.current_url != initial_url:
                            logger.info("Successfully navigated to next page using ID selector")
                            return True
                            
                except TimeoutException:
                    logger.debug("Next button by ID not found, trying alternative methods")
                
                # Strategy 2: Find by aria-label
                try:
                    next_links = driver.find_elements(By.CSS_SELECTOR, "a[aria-label*='Next'], a[id='pnnext']")
                    
                    for link in next_links:
                        if link.is_displayed() and link.is_enabled():
                            href = link.get_attribute('href')
                            if href and 'start=' in href:
                                logger.info("Found next link by aria-label/CSS selector")
                                
                                if scroll_before_click:
                                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", link)
                                    time.sleep(random.uniform(0.5, 1.0))
                                
                                try:
                                    link.click()
                                except:
                                    driver.execute_script("arguments[0].click();", link)
                                
                                time.sleep(random.uniform(2.0, 3.0))
                                
                                if driver.current_url != initial_url:
                                    logger.info("Successfully navigated to next page using aria-label")
                                    return True
                                    
                except NoSuchElementException:
                    logger.debug("No next links found by aria-label")
                
                # Strategy 3: Find by text content
                try:
                    # Look for elements containing "Next" text
                    xpath_patterns = [
                        "//a[contains(., 'Next')]",
                        "//span[contains(text(), 'Next')]/parent::a",
                        "//a[contains(@class, 'fl') and contains(@href, 'start=')]"
                    ]
                    
                    for xpath in xpath_patterns:
                        try:
                            elements = driver.find_elements(By.XPATH, xpath)
                            
                            for element in elements:
                                if element.is_displayed():
                                    # Check if this is likely the pagination next button
                                    href = element.get_attribute('href')
                                    if href and 'start=' in href:
                                        current_start = self._extract_start_param(initial_url)
                                        next_start = self._extract_start_param(href)
                                        
                                        # Verify this goes to next page (start param should increase)
                                        if next_start > current_start:
                                            logger.info(f"Found next link with start={next_start}")
                                            
                                            if scroll_before_click:
                                                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                                                time.sleep(random.uniform(0.5, 1.0))
                                            
                                            try:
                                                element.click()
                                            except:
                                                driver.execute_script("arguments[0].click();", element)
                                            
                                            time.sleep(random.uniform(2.0, 3.0))
                                            
                                            if driver.current_url != initial_url:
                                                logger.info("Successfully navigated using text search")
                                                return True
                                                
                        except NoSuchElementException:
                            continue
                            
                except Exception as e:
                    logger.debug(f"Error searching by text: {e}")
                
                # Strategy 4: Find in navigation table structure
                try:
                    # Find the navigation table
                    nav_table = driver.find_element(By.CSS_SELECTOR, "table.AaVjTc, div[role='navigation'] table")
                    
                    if nav_table:
                        # Get all links in the navigation
                        nav_links = nav_table.find_elements(By.TAG_NAME, "a")
                        
                        # Find current page and next page
                        current_page = self._get_current_page_number(driver)
                        
                        for link in nav_links:
                            aria_label = link.get_attribute('aria-label')
                            if aria_label and f"Page {current_page + 1}" in aria_label:
                                logger.info(f"Found page {current_page + 1} link")
                                
                                if scroll_before_click:
                                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", link)
                                    time.sleep(random.uniform(0.5, 1.0))
                                
                                try:
                                    link.click()
                                except:
                                    driver.execute_script("arguments[0].click();", link)
                                
                                time.sleep(random.uniform(2.0, 3.0))
                                
                                if driver.current_url != initial_url:
                                    logger.info("Successfully navigated using page number")
                                    return True
                                    
                except NoSuchElementException:
                    logger.debug("Navigation table not found")
                
                # Strategy 5: Direct URL manipulation (last resort)
                if attempt == retry_attempts - 1:
                    try:
                        current_url = driver.current_url
                        current_start = self._extract_start_param(current_url)
                        
                        # Calculate next page start (Google typically uses 10 results per page)
                        next_start = current_start + 10
                        
                        # Build new URL
                        if 'start=' in current_url:
                            new_url = current_url.replace(f'start={current_start}', f'start={next_start}')
                        elif '?' in current_url:
                            new_url = f"{current_url}&start={next_start}"
                        else:
                            new_url = f"{current_url}?start={next_start}"
                        
                        logger.info(f"Attempting direct navigation to start={next_start}")
                        driver.get(new_url)
                        time.sleep(random.uniform(2.0, 3.0))
                        
                        if driver.current_url != initial_url:
                            logger.info("Successfully navigated using URL manipulation")
                            return True
                            
                    except Exception as e:
                        logger.error(f"Error in URL manipulation: {e}")
                
                # If we haven't returned by now, wait before retry
                if attempt < retry_attempts - 1:
                    logger.warning(f"Attempt {attempt + 1} failed, retrying...")
                    time.sleep(random.uniform(1.0, 2.0))
                    
            except Exception as e:
                logger.error(f"Unexpected error in go_to_next_page: {e}")
                if attempt < retry_attempts - 1:
                    time.sleep(random.uniform(1.0, 2.0))
                continue
        
        logger.error("Failed to navigate to next page after all attempts")
        return False


    def _extract_start_param(self, url):
        """Extract the 'start' parameter value from URL"""
        try:
            import re
            match = re.search(r'start=(\d+)', url)
            if match:
                return int(match.group(1))
            return 0  # First page if no start param
        except:
            return 0


    def _get_current_page_number(self, driver):
        """Get the current page number from the navigation"""
        try:
            # Look for the current page indicator (usually not a link)
            current_indicators = [
                "//td[@class='YyVfkd NKTSme']",  # Current page cell
                "//td[contains(@class, 'YyVfkd')]",
                "//span[@class='SJajHc' and not(parent::a)]/../.."
            ]
            
            for xpath in current_indicators:
                try:
                    elements = driver.find_elements(By.XPATH, xpath)
                    for element in elements:
                        text = element.text.strip()
                        if text.isdigit():
                            return int(text)
                except:
                    continue
            
            # Fallback: extract from URL
            url = driver.current_url
            start = self._extract_start_param(url)
            return (start // 10) + 1  # Assuming 10 results per page
            
        except Exception as e:
            logger.debug(f"Could not determine current page: {e}")
            return 1
        


    # Main exploration function
    def explore_site(self, driver, duration_range, action_type):
        """
        Enhanced explore_site function that dynamically enforces different action types
        using existing action methods.
        """
        try:
            duration = random.uniform(duration_range[0], duration_range[1])
            logger.info(f"🕒 Exploring site for {duration:.1f}s with action type: {action_type}")
            
            start_time = time.time()
            elapsed_time = 0
            
            while elapsed_time < duration:
                remaining_time = duration - elapsed_time
                
                # Dynamic behavior routing
                behavior_handlers = {
                    "browse_moderately": self._moderate_browsing,
                    "browse_pages": self._engaged_browsing,
                    "click_internal_links": self._internal_link_clicking,
                    "stay_on_page": self._stay_on_page,
                    "click_ads": self._ad_clicking,
                    "leave_immediately": self._quick_exit
                }
                
                handler = behavior_handlers.get(action_type, self._moderate_browsing)
                handler(driver, remaining_time)
                
                # Update timing
                elapsed_time = time.time() - start_time
                if elapsed_time >= duration:
                    break
                    
                time.sleep(random.uniform(1, 3))
            
            logger.info(f"✅ Completed {action_type} exploration in {elapsed_time:.1f}s")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error during {action_type} exploration: {e}")
            return False

    # Behavior type handlers
    def _moderate_browsing(self, driver, remaining_time):
        actions = [("scroll", 0.4), ("read", 0.3), ("click_link", 0.2), ("scroll_slow", 0.1)]
        self._execute_weighted_action(driver, actions, remaining_time)

    def _engaged_browsing(self, driver, remaining_time):
        actions = [("click_link", 0.5), ("scroll", 0.3), ("navigate_pages", 0.2)]
        self._execute_weighted_action(driver, actions, remaining_time)

    def _internal_link_clicking(self, driver, remaining_time):
        actions = [("click_internal_link", 0.6), ("scroll", 0.2), ("read", 0.2)]
        self._execute_weighted_action(driver, actions, remaining_time)

    def _stay_on_page(self, driver, remaining_time):
        actions = [("read", 0.5), ("scroll_slow", 0.4), ("minimal_interaction", 0.1)]
        self._execute_weighted_action(driver, actions, remaining_time)

    def _ad_clicking(self, driver, remaining_time):
        actions = [("click_ads", 0.7), ("scroll", 0.2), ("read", 0.1)]
        self._execute_weighted_action(driver, actions, remaining_time)

    def _quick_exit(self, driver, remaining_time):
        actions = [("scroll_quick", 0.6), ("minimal_interaction", 0.3), ("read_brief", 0.1)]
        self._execute_weighted_action(driver, actions, remaining_time)

    # Core action executor
    def _execute_weighted_action(self, driver, actions, remaining_time):
        """Execute weighted random action using existing action methods"""
        actions_list, weights = zip(*actions)
        chosen_action = random.choices(actions_list, weights=weights)[0]
        
        max_action_time = min(remaining_time * 0.3, 10)
        action_duration = random.uniform(2, max_action_time)
        
        logger.debug(f"🔄 Executing {chosen_action} for {action_duration:.1f}s")
        
        # Map actions to existing method calls
        action_dispatcher = {
            "scroll": lambda: self._scroll_action(driver, action_duration),
            "scroll_slow": lambda: self._slow_scroll_action(driver, action_duration),
            "scroll_quick": lambda: self._quick_scroll_action(driver, action_duration),
            "read": lambda: self._reading_action(driver, action_duration),
            "read_brief": lambda: self._brief_reading_action(driver, action_duration),
            "click_link": lambda: self._click_random_link(driver),
            "click_internal_link": lambda: self._click_internal_navigation(driver),
            "navigate_pages": lambda: self._navigate_to_subpage(driver),
            "click_ads": lambda: self._find_and_click_ads(driver),
            "minimal_interaction": lambda: self._minimal_interaction(driver, action_duration)
        }
        
        if chosen_action in action_dispatcher:
            action_dispatcher[chosen_action]()
        else:
            self._moderate_browsing(driver, action_duration)

    # Concrete action implementations using your existing methods
    def _scroll_action(self, driver, duration):
        max_scrolls = max(1, int(duration / 3))
        self.actions.scroll_down(driver, max_scrolls=max_scrolls, scroll_duration=duration)

    def _slow_scroll_action(self, driver, duration):
        max_scrolls = max(1, int(duration / 5))
        self.actions.scroll_down(driver, max_scrolls=max_scrolls, scroll_duration=duration)

    def _quick_scroll_action(self, driver, duration):
        self.actions.scroll_down(driver, max_scrolls=2, scroll_duration=min(duration, 3))

    def _reading_action(self, driver, duration):
        read_intervals = int(duration / 3)
        for i in range(read_intervals):
            time.sleep(random.uniform(2, 4))
            if random.random() < 0.3:
                current_pos = js_utils.execute_script(driver, "return window.scrollY")
                self.actions._human_like_scroll(driver, current_pos, current_pos + 100, "down")

    def _brief_reading_action(self, driver, duration):
        time.sleep(min(duration, 3))

    def _click_random_link(self, driver):
        try:
            links = driver.find_elements(By.TAG_NAME, "a")
            clickable_links = [
                link for link in links 
                if self._is_clickable_link(link)
            ]
            if clickable_links:
                link = random.choice(clickable_links)
                return self.actions.click_element(driver, link, "random link")
        except Exception as e:
            logger.debug(f"Could not click random link: {e}")
        return False

    def _click_internal_navigation(self, driver):
        internal_selectors = ["nav a", ".menu a", ".navigation a", ".breadcrumb a", ".pagination a", ".next", ".prev", "button"]
        for selector in internal_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if self._is_clickable_link(element):
                        self.actions.scroll_to_element(driver, element)
                        return self.actions.click_element(driver, element, "internal navigation")
            except:
                continue
        return False

    def _navigate_to_subpage(self, driver):
        if self._click_random_link(driver):
            time.sleep(random.uniform(3, 6))
            return True
        return False

    def _find_and_click_ads(self, driver):
        ad_selectors = ["[class*='ad']", "[id*='ad']", ".advertisement", ".banner", ".sponsor", "ins.adsbygoogle"]
        for selector in ad_selectors:
            try:
                ads = driver.find_elements(By.CSS_SELECTOR, selector)
                for ad in ads:
                    if self._is_clickable_link(ad):
                        self.actions.scroll_to_element(driver, ad)
                        return self.actions.click_element(driver, ad, "advertisement")
            except:
                continue
        return False

    def _minimal_interaction(self, driver, duration):
        time.sleep(min(duration, 5))

    # Helper method for link validation
    def _is_clickable_link(self, element):
        """Check if element is clickable"""
        try:
            return (element.is_displayed() and 
                    element.is_enabled() and 
                    element.get_attribute('href') and 
                    not element.get_attribute('href').startswith('javascript:'))
        except:
            return False
        
    
    def _extract_related_searches(self, driver, keyword):
        """
        Extract related searches from Google's search results page.
        
        Args:
            driver: WebDriver instance
            
        Returns:
            List of related search terms or empty list if none found
        """
        related_searches = []
        
        try:
            # Wait for related searches to load
            time.sleep(2)
            
            # Multiple selectors to catch different Google layouts
            selectors = [
                "a.ngTNl.ggLgoc .dg6jd.JGD2rd",  # Primary selector from your HTML
                "div.aypzVd",  # Alternative selector for related searches
                "div.s75CSd",  # Another common selector
                "div[aria-label='Related searches'] a",  # Aria-label approach
            ]
            
            for selector in selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        for element in elements:
                            text = element.text.strip()
                            if text and text not in related_searches:
                                related_searches.append(text)
                        break  # Stop at first successful selector
                except Exception:
                    continue
                    
            # If we found related searches, filter and return them
            if related_searches:
                # Filter out any that are too similar to our current keyword
                filtered_searches = [
                    search for search in related_searches 
                    if search.lower() != keyword.lower()
                ]
                
                return filtered_searches if filtered_searches else related_searches
                
        except Exception as e:
            logger.warning(f"Failed to extract related searches: {e}")
        
        return []