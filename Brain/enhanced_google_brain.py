#!/usr/bin/python3
"""
    Enhanced Human Brain for Google Search Automation
    Fixed version with anti-detection features
    Author: Fortune Nwohiri
"""
import time
import json
import random
from urllib.parse import urlparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    JavascriptException, TimeoutException, ElementClickInterceptedException,
    NoSuchElementException, StaleElementReferenceException
)
from logging_config.logger import get_logger
from Agents.agent import Agent
from Agents.google_connector import GoogleConnector

logger = get_logger("EnhancedHumanBrain")





review_query_templates = [
    "{brand} reviews",
    "{brand} review",
    "{brand} customer feedback",
    "{brand} customer reviews",
    "{brand} user reviews",
    "{brand} ratings",
    "{brand} rating",
    "{brand} testimonial",
    "{brand} testimonials",
    "{brand} positive reviews",
    "{brand} negative reviews",
    "complaints about {brand}",
    "{brand} pros and cons",
    "{brand} problems",
    "{brand} issues",
    "{brand} best features",
    "{brand} worst features",
    "is {brand} worth it",
    "should i buy {brand}",
    "buy {brand} online",
    "where to buy {brand}",
    "{brand} price",
    "{brand} cost",
    "{brand} price in",
    "{brand} discount coupon",
    "{brand} deals",
    "alternatives to {brand}",
    "best alternatives to {brand}",
    "{brand} compared to",
    "{brand} not working",
    "{brand} broken",
    "{brand} error",
    "how to fix {brand}",
    "{brand} customer support",
    "{brand} warranty",
    "{brand} return policy",
    "{brand} troubleshooting",
    "{brand} reviews",
    "{brand} near me",
    "{brand} for",
    "how long does {brand} last",
    "{brand} battery life",
    "{brand} durability review",
    "{brand} performance review",
    "{brand} unboxing",
    "{brand} hands-on review",
    "{brand} demonstration",
    "{brand} comparison video",
    "what do people say about {brand}",
    "are {brand} good",
    "are {brand} worth the money",
    "how good is {brand}",
    "where to get reviews for {brand}",
    "who makes {brand}",
    "{brand} reviews Amazon",
    "{brand} reviews Google Shopping",
    "{brand} reviews eBay",
    "{brand} reviews Reddit",
    "{brand} reviews Trustpilot",
    "{brand} reviews",
    "latest reviews of {brand}",
    "{brand} review",
    "{brand} review 2025",
    "{brand} demo",
    "request demo {brand}",
    "{brand} free trial",
    "book a demo {brand}",
    "{brand} pricing plan",
    "{brand} subscription cost",
    "{brand} coupon code",
    "{brand} promo code",
    "{brand} scam",
    "{brand} legit or scam",
    "{brand} refund",
    "{brand} return policy"
]


class EnhancedGoogleBrain:
    def __init__(self, driver, google_connector, target_url, keyword):
        logger.info(f"Initializing EnhancedHumanBrain with target: {target_url}, keyword: {keyword}")
        
        self.driver = driver
        self.google = google_connector
        self.target_url = target_url
        self.initial_keyword = keyword  # Store original keyword
        self.current_keyword = keyword
        self.phase = "exploratory"
        
        # Tracking metrics
        self.visited_domains = {}  # {domain: visit_count}
        self.current_page = 1
        self.max_pages = 3
        self.max_visits_per_domain = 2
        self.used_keywords = set([keyword])
        self.pagination_attempts = 0
        self.max_pagination_attempts = 3
        self.search_refinement_count = 0
        self.max_search_refinements = 4
        
        # Session timing
        self.session_start_time = None
        self.actions_taken = []

        # percieving target
        self.target_seen_during_exploration = False
        self.target_page_number = None
        
        logger.info("EnhancedHumanBrain initialized successfully")
    
    def run_session(self, session_type="exploratory", duration_minutes=30):
        """Main entry point - choose session type"""
        try:
            logger.info(f"=" * 80)
            logger.info(f"Starting {session_type.upper()} session (duration: {duration_minutes} min)")
            logger.info(f"=" * 80)
            
            self.session_start_time = time.time()
            self.phase = session_type
            
            if session_type == "exploratory":
                self._run_exploratory_session(duration_minutes)
            else:
                self._run_goal_oriented_session()
            
            logger.info(f"=" * 80)
            logger.info(f"Session complete. Total actions: {len(self.actions_taken)}")
            logger.info(f"Domains visited: {len(self.visited_domains)}")
            logger.info(f"=" * 80)

        except JavascriptException as e:
            logger.error(f"JavaScript error in session: {e}")
            self._recover_from_failure()
        except TimeoutException as e:
            logger.error(f"Timeout in session: {e}")
            self._recover_from_failure()
        except Exception as e:
            logger.error(f"Critical session error: {e}", exc_info=True)
            try:
                self._emergency_cleanup()
            except Exception:
                logger.error("Emergency cleanup failed")
    
    def _run_exploratory_session(self, duration_minutes):
        """Exploratory phase: build browsing history with varied keywords"""
        logger.info("EXPLORATORY MODE: Building browsing history and cookie data")
        logger.info(f"Strategy: Use keyword variations, visit diverse sites, natural patterns")
        
        end_time = time.time() + (duration_minutes * 60)
        search_count = 0
        
        while time.time() < end_time:
            search_count += 1
            logger.info(f"\n--- Exploratory Search Cycle {search_count} ---")
            
            # Choose keyword strategy for this cycle
            if search_count == 1:
                # First search always uses initial keyword
                self.current_keyword = self.initial_keyword
                logger.info(f"Using INITIAL keyword: '{self.current_keyword}'")
            else:
                # Subsequent searches use extracted related terms
                self._choose_related_keyword()
            
            # Perform search
            if not self._perform_search_with_natural_timing():
                logger.error("Search failed, attempting recovery")
                if not self._recover_from_failure():
                    logger.error("Recovery failed, ending session")
                    break
                continue
            
            # Choose exploration pattern for this cycle
            pattern = self._choose_exploration_pattern()
            logger.info(f"Selected pattern: {pattern}")
            
            # Execute pattern
            if pattern == "quick_scan":
                self._quick_scan_pattern()
            # elif pattern == "deep_dive":
            #     self._deep_dive_pattern()
            elif pattern == "pagination_explore":
                self._pagination_explore_pattern()
            elif pattern == "competitor_check":
                self._competitor_check_pattern()
            
            # Reset for next cycle
            self._reset_cycle_state()
            
            # Natural breaks between searches
            if random.random() < 0.3:  # 30% chance of break
                break_duration = random.uniform(30, 90)
                logger.info(f"Taking natural break: {break_duration:.1f}s")
                time.sleep(break_duration)
            
            # Check if we should continue
            if self.search_refinement_count >= self.max_search_refinements:
                logger.info("Reached max search refinements, ending exploratory phase")
                self._navigate_to_google()
                logger.info("Returning to Google Results page")
                break
        
        logger.info("Exploratory session completed")
    
    def _run_goal_oriented_session(self):
        """Goal-oriented phase: Focus on finding and engaging with target"""
        logger.info("GOAL-ORIENTED MODE: Focused search for target site")
        logger.info(f"Target: {self.target_url}")
        logger.info(f"Strategy: Use ONLY initial keyword, prioritize target detection")
        
        # CRITICAL: Always use initial keyword in goal-oriented mode
        self.current_keyword = self.initial_keyword
        logger.info(f"Using INITIAL keyword only: '{self.current_keyword}'")
        
        if self.target_seen_during_exploration:
            logger.info(f"🎯 Target already spotted on page {self.target_page_number} during exploration")
            logger.info("Navigating directly to that page...")
            
            # Navigate to the page we know has the target
            if not self._perform_search_with_natural_timing():
                return
            
            # Go to the page we know has target
            for _ in range(self.target_page_number - 1):
                if not self._go_to_next_page_safe():
                    break
            
            # Click target
            if self._scan_and_click_target():
                self._engage_with_target()
                return
        

        # Perform search
        if not self._perform_search_with_natural_timing():
            logger.error("Initial search failed")
            if not self._recover_from_failure():
                logger.error("Recovery failed, ending session")
            return
        
        # Scan first page for target
        if self._scan_and_click_target():
            logger.info("Target found on first page! Engaging...")
            self._engage_with_target()
            return
        
        # Try pagination if target not on first page
        for page_num in range(2, self.max_pages + 1):
            logger.info(f"Target not on page {page_num - 1}, trying page {page_num}")
            
            if not self._go_to_next_page_safe():
                logger.info("No more pages available")
                break
            
            if self._scan_and_click_target():
                logger.info(f"Target found on page {page_num}! Engaging...")
                self._engage_with_target()
                return
        
        # Fallback: Visit some organic results then try refined search
        logger.info("Target not found through pagination, trying organic exploration")
        self._visit_organic_results(count=2)
        
        # One final attempt with site-specific search
        logger.info("Final attempt: Using site-specific search")
        self._try_site_specific_search()


    def _check_for_target_silently(self):
        """Silently check if target is on current page without clicking"""
        try:
            if not self._is_on_google_results():
                return False
            
            # Use your existing click_target_site logic but just for detection
            results = self.driver.find_elements(By.CSS_SELECTOR, "div.g a, h3")
            target_domain = urlparse(self.target_url).netloc.lower()
            
            for result in results:
                href = result.get_attribute('href')
                if href and target_domain in href.lower():
                    self.target_seen_during_exploration = True
                    self.target_page_number = self.current_page
                    logger.info(f"🎯 TARGET SPOTTED during exploration on page {self.current_page} (not clicking yet)")
                    return True
            return False
        except:
            return False
    
    def _choose_related_keyword(self):
        """Extract and choose related keyword from Google (exploratory only)"""
        logger.info("Extracting related keywords from current page")
        
        if not self._is_on_google_results():
            logger.warning("Not on Google results page, navigating back")
            self._navigate_to_google()
            time.sleep(self._human_pause())
        
        # Extract related searches
        related = self.google._extract_related_searches(self.driver, self.current_keyword)
        
        if related and len(related) > 0:
            # Filter out already used keywords
            available = [k for k in related if k not in self.used_keywords]
            
            if available:
                self.current_keyword = random.choice(available)
                self.used_keywords.add(self.current_keyword)
                self.search_refinement_count += 1
                logger.info(f"Selected related keyword: '{self.current_keyword}'")
                logger.info(f"Search refinement count: {self.search_refinement_count}/{self.max_search_refinements}")
            else:
                logger.info("All related keywords already used, keeping current")
        else:
            # Fallback: Add variation to current keyword
            variations = [
                f"{self.initial_keyword} requirements",
                f"{self.initial_keyword} online",
                f"best {self.initial_keyword}",
                f"{self.initial_keyword} Nigeria",
                f"how to get {self.initial_keyword}"
            ]
            unused_variations = [v for v in variations if v not in self.used_keywords]
            
            if unused_variations:
                self.current_keyword = random.choice(unused_variations)
                self.used_keywords.add(self.current_keyword)
                self.search_refinement_count += 1
                logger.info(f"No related terms found, using variation: '{self.current_keyword}'")
            else:
                logger.info("No new keywords available, keeping current")
    
    def _perform_search_with_natural_timing(self):
        """Perform search with human-like timing and behaviors"""
        logger.info(f"Performing search for: '{self.current_keyword}'")
        
        # Human reads/thinks before typing (1-3 seconds)
        thinking_pause = random.uniform(1, 3)
        logger.info(f"Pre-search pause (thinking): {thinking_pause:.1f}s")
        time.sleep(thinking_pause)
        
        # Perform search
        success = self.google.search(self.driver, self.current_keyword)
        
        if success:
            # Handle popups immediately after search loads
            time.sleep(random.uniform(1, 2))
            self._handle_popups_and_cookies()
            
            # Human scans results before clicking (2-8 seconds)
            scan_pause = random.uniform(2, 8)
            logger.info(f"Scanning search results: {scan_pause:.1f}s")
            time.sleep(scan_pause)
            
            self._log_action("search", self.current_keyword)
            return True
        else:
            logger.error("Search execution failed")
            return False
    
    def _choose_exploration_pattern(self):
        """Choose exploration pattern with realistic distribution"""
        logger.info("Choosing exploration pattern")
        
        patterns = [
            ("quick_scan", 0.35),        # 35% - most common
            # ("deep_dive", 0.20),         # 20% - occasional deep reading
            ("pagination_explore", 0.25), # 25% - check multiple pages
            ("competitor_check", 0.20)    # 20% - comparison shopping
        ]
        
        pattern_names = [p[0] for p in patterns]
        weights = [p[1] for p in patterns]
        
        chosen = random.choices(pattern_names, weights=weights)[0]
        logger.info(f"Pattern selected: {chosen}")
        return chosen
    
    def _quick_scan_pattern(self):
        """Quick scan: Visit 2-4 sites briefly (mimics recognizing irrelevant results)"""
        sites_to_visit = random.randint(2, 4)
        logger.info(f"QUICK SCAN: Planning to visit {sites_to_visit} sites briefly")
        
        visited = 0
        attempts = 0
        max_attempts = sites_to_visit * 2  # Prevent infinite loops
        
        while visited < sites_to_visit and attempts < max_attempts:
            attempts += 1
            
            if not self._is_on_google_results():
                logger.warning("Not on search results, going back")
                self.driver.back()
                time.sleep(self._human_pause())
                continue
            
            # Get available results
            results = self._get_available_results()
            if not results:
                logger.info("No more available results on this page")
                break
            
            # Pick random result (humans don't click sequentially)
            result = random.choice(results)
            domain = self._extract_domain_from_result(result)
            
            if self._should_skip_domain(domain):
                logger.info(f"Skipping {domain} (visited {self.visited_domains.get(domain, 0)} times)")
                continue
            
            # Click and engage briefly
            if self._click_result_safe(result):
                self._track_domain_visit(domain)
                visited += 1
                
                # Brief engagement (5-15 seconds) - quick exit
                duration = random.uniform(5, 15)
                logger.info(f"Quick visit to {domain}: {duration:.1f}s")
                self._minimal_browsing(duration)
                
                # Handle popups
                self._handle_popups_and_cookies()
                
                # Back to results
                logger.info("Returning to search results (quick exit)")
                self.driver.back()
                time.sleep(self._human_pause())
                
                self._log_action("quick_visit", domain)
        
        logger.info(f"Quick scan complete: visited {visited}/{sites_to_visit} sites")
    
    def _deep_dive_pattern(self):
        """Deep dive: Visit 1-2 sites with extended engagement"""
        sites_to_visit = random.randint(1, 2)
        logger.info(f"DEEP DIVE: Planning {sites_to_visit} site(s) with extended engagement")
        
        visited = 0
        attempts = 0
        
        while visited < sites_to_visit and attempts < 4:
            attempts += 1
            
            if not self._is_on_google_results():
                self.driver.back()
                time.sleep(self._human_pause())
                continue
            
            results = self._get_available_results()
            if not results:
                break
            
            result = random.choice(results)
            domain = self._extract_domain_from_result(result)
            
            if self._should_skip_domain(domain):
                logger.info(f"Skipping {domain}")
                continue
            
            if self._click_result_safe(result):
                self._track_domain_visit(domain)
                visited += 1
                
                # Extended engagement (60-180 seconds)
                duration = random.uniform(60, 180)
                logger.info(f"Deep engagement with {domain}: {duration:.1f}s")
                self._moderate_browsing(duration)
                
                self._handle_popups_and_cookies()
                
                logger.info("Returning to search results after deep engagement")
                self.driver.back()
                time.sleep(self._human_pause())
                
                self._log_action("deep_visit", domain)
        
        logger.info(f"Deep dive complete: {visited} site(s) explored")
    
    def _pagination_explore_pattern(self):
        """Pagination: Visit results across multiple pages"""
        logger.info("PAGINATION EXPLORE: Checking multiple result pages")
        
        # Only attempt if on Google results
        if not self._is_on_google_results():
            logger.warning("Not on Google results, cannot paginate")
            return
        
        pages_to_check = random.randint(2, 3)
        logger.info(f"Planning to check {pages_to_check} pages")
        
        for page_num in range(1, pages_to_check + 1):
            if page_num > 1:
                logger.info(f"Attempting to go to page {page_num}")
                if not self._go_to_next_page_safe():
                    logger.info(f"Could not reach page {page_num}, stopping pagination")
                    break
                
                # Natural pause after page load
                time.sleep(random.uniform(2, 4))
            
            logger.info(f"On page {page_num}, running silent target check")
            # Call _check_for_target_silently() on each page
            try:
                found = self._check_for_target_silently()
                if found:
                    logger.info(f"[Pagination] Target was spotted on page {page_num} (not clicking)")
                else:
                    logger.info(f"[Pagination] Target not on page {page_num}")
            except Exception as e:
                logger.debug(f"Silent target check error during pagination: {e}")

            logger.info(f"On page {page_num}, selecting result to visit")
            
            # Visit 1 result per page
            results = self._get_available_results()
            if not results:
                logger.info(f"No results found on page {page_num}")
                break
            
            result = random.choice(results)
            domain = self._extract_domain_from_result(result)
            
            if not self._should_skip_domain(domain):
                if self._click_result_safe(result):
                    # Ensure page loaded before engagement
                    if not self._wait_for_page_ready():
                        logger.warning("Page not ready after click, returning to results")
                        try:
                            self.driver.back()
                        except:
                            pass
                        continue

                    self._track_domain_visit(domain)
                    
                    # Medium engagement (30-90 seconds)
                    duration = random.uniform(30, 90)
                    logger.info(f"Medium engagement with {domain}: {duration:.1f}s")
                    self._minimal_browsing(duration)
                    
                    self._handle_popups_and_cookies()
                    
                    self.driver.back()
                    time.sleep(self._human_pause())
                    
                    self._log_action("paginated_visit", domain)
        
        logger.info("Pagination exploration complete")
    
    def _competitor_check_pattern(self):
        """Competitor check: Brief visits to competitor sites (high bounce)"""
        logger.info("COMPETITOR CHECK: Visiting competitor sites briefly")
        
        if not self._is_on_google_results():
            logger.warning("Not on Google results")
            return
        
        competitors = self._get_competitor_domains()
        if not competitors:
            logger.info("No competitor domains configured")
            return
        
        # Visit only 1 competitor per pattern execution
        logger.info("Attempting to click competitor site")
        if self.google.click_competitor_site(self.driver, competitors):
            domain = self._extract_current_domain()
            self._track_domain_visit(domain)
            
            self._handle_popups_and_cookies()
            
            # Very brief visit (5-15 seconds) - high bounce rate
            duration = random.uniform(5, 15)
            logger.info(f"Brief competitor visit to {domain}: {duration:.1f}s (high bounce)")
            time.sleep(duration)
            
            # Maybe one scroll to appear human
            if random.random() < 0.3:
                self.google.actions.scroll_down(self.driver, max_scrolls=1, scroll_duration=1)
            
            logger.info("Quick exit from competitor (increasing their bounce rate)")
            self.driver.back()
            time.sleep(self._human_pause())
            
            self._log_action("competitor_bounce", domain)
        else:
            logger.info("No competitor sites found on current page")
    
    def _scan_and_click_target(self):
        """Scan current page for target and click if found"""
        logger.info("Scanning page for target site")
        
        if not self._is_on_google_results():
            logger.warning("Not on search results page")
            return False
        
        # Try to click target
        if self.google.click_target_site(self.driver, self.target_url):
            logger.info("TARGET FOUND AND CLICKED!")
            self._log_action("target_found", self.target_url)
            return True
        else:
            logger.info("Target not found on this page")
            return False
    
    def _engage_with_target(self):
        """Deep engagement with target site (5-15 minutes)"""
        logger.info("=" * 80)
        logger.info("ENGAGING WITH TARGET SITE")
        logger.info("=" * 80)
        
        # Handle popups immediately
        time.sleep(random.uniform(1, 2))
        self._handle_popups_and_cookies()
        
        # Extended engagement (5-15 minutes)
        total_duration = random.uniform(300, 900)
        logger.info(f"Target engagement duration: {total_duration/60:.1f} minutes")
        
        start_time = time.time()
        action_count = 0
        
        while time.time() - start_time < total_duration:
            action_count += 1
            
            # Varied actions
            actions = ["scroll_read", "click_internal", "pause", "click_ads"]
            weights = [0.4, 0.2, 0.1, 0.3]  # 40% scroll, 20% click, 10% pause, 30% click ads
            
            action = random.choices(actions, weights=weights)[0]
            logger.info(f"Target engagement action {action_count}: {action}")
            
            if action == "scroll_read":
                self._scroll_and_read()
            elif action == "click_internal":
                if self._click_internal_links():
                    logger.info("Navigated to internal page, exploring")
                    time.sleep(random.uniform(10, 30))
                else:
                    logger.info("No internal links found, scrolling instead")
                    self._scroll_and_read()
            else:
                pause_duration = random.uniform(5, 15)
                logger.info(f"Natural pause: {pause_duration:.1f}s")
                time.sleep(pause_duration)
        
        logger.info(f"Target engagement complete: {action_count} actions in {total_duration/60:.1f} minutes")
        self._log_action("target_engaged", f"{total_duration:.0f}s")
    
    def _visit_organic_results(self, count=2):
        """Visit organic results as fallback"""
        logger.info(f"Visiting {count} organic results as fallback")
        
        for i in range(count):
            if self.google.click_random_result(self.driver):
                domain = self._extract_current_domain()
                self._track_domain_visit(domain)
                
                duration = random.uniform(20, 60)
                logger.info(f"Organic visit {i+1} to {domain}: {duration:.1f}s")
                self._minimal_browsing(duration)
                
                self.driver.back()
                time.sleep(self._human_pause())
    
    def _try_site_specific_search(self):
        """Try site-specific search as last resort"""
        logger.info("Attempting site-specific search")
        
        target_domain = urlparse(self.target_url).netloc
        site_search = f"site:{target_domain} {self.initial_keyword}"
        
        logger.info(f"Site search query: '{site_search}'")
        if self.google.search(self.driver, site_search):
            time.sleep(random.uniform(2, 5))
            if self._scan_and_click_target():
                self._engage_with_target()
    
    def _is_on_google_results(self):
        """Check if currently on Google search results page"""
        try:
            current_url = self.driver.current_url
            is_results = "google.com/search" in current_url
            logger.info(f"URL check: {current_url[:80]}... - Is Google results: {is_results}")
            return is_results
        except:
            return False
    
    def _go_to_next_page_safe(self):
        """Safely go to next page with validation"""
        logger.info("Checking if next page is available")
        
        # Validate we're on Google results
        if not self._is_on_google_results():
            logger.error("Cannot paginate: not on Google results page")
            return False
        
        # Check pagination attempts
        if self.pagination_attempts >= self.max_pagination_attempts:
            logger.info(f"Reached max pagination attempts ({self.max_pagination_attempts})")
            return False
        
        # Check if next page button exists
        try:
            next_button = self.driver.find_element(By.ID, "pnnext")
            if not next_button.is_displayed():
                logger.info("Next button not visible")
                return False
        except NoSuchElementException:
            logger.info("Next button not found")
            return False
        
        # Attempt pagination
        logger.info(f"Next page available, attempting navigation (attempt {self.pagination_attempts + 1})")
        success = self.google.go_to_next_page(self.driver)
        
        if success:
            self.pagination_attempts += 1
            self.current_page += 1
            logger.info(f"Successfully moved to page {self.current_page}")
            
            # Handle popups on new page
            time.sleep(random.uniform(1, 2))
            self._handle_popups_and_cookies()
            
            self._log_action("pagination", f"page_{self.current_page}")
            return True
        else:
            logger.info("Pagination failed")
            return False
    
    def _get_available_results(self):
        """Get clickable results that haven't been over-visited"""
        logger.info("Scanning for available results")
        
        try:
            # Multiple selectors for robustness
            selectors = [
                "h3.LC20lb.MBeuO.DKV0Md",
                "div.yuRUbf a",
                "div.g a h3"
            ]
            
            all_results = []
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        all_results.extend(elements)
                        break
                except:
                    continue
            
            # Filter by domain visit count
            available = []
            for result in all_results:
                try:
                    parent = result.find_element(By.XPATH, "./ancestor::a") if result.tag_name != "a" else result
                    href = parent.get_attribute('href')
                    
                    if not href or 'google.com' in href:
                        continue
                    
                    domain = self._extract_domain(href)
                    if not self._should_skip_domain(domain):
                        available.append(parent)
                except:
                    continue
            
            logger.info(f"Found {len(available)} available results (from {len(all_results)} total)")
            return available
            
        except Exception as e:
            logger.error(f"Error getting results: {e}")
            return []
    
    def _should_skip_domain(self, domain):
        """Check if domain should be skipped"""
        if not domain:
            return True
        visit_count = self.visited_domains.get(domain, 0)
        should_skip = visit_count >= self.max_visits_per_domain
        if should_skip:
            logger.info(f"Skipping {domain}: visited {visit_count} times")
        return should_skip
    
    def _track_domain_visit(self, domain):
        """Track domain visits"""
        if domain:
            self.visited_domains[domain] = self.visited_domains.get(domain, 0) + 1
            logger.info(f"Domain tracking: {domain} - {self.visited_domains[domain]} visit(s)")
    
    def _extract_domain_from_result(self, result_element):
        """Extract domain from result element"""
        try:
            href = result_element.get_attribute('href')
            return self._extract_domain(href)
        except:
            return None
    
    def _extract_current_domain(self):
        """Extract domain from current URL"""
        try:
            return self._extract_domain(self.driver.current_url)
        except:
            return None
    
    def _extract_domain(self, url):
        """Extract clean domain from URL"""
        try:
            parsed = urlparse(url)
            return parsed.netloc.replace("www.", "").lower()
        except:
            return ""
    
    def _click_result_safe(self, result_element):
        """Safely click result with error handling"""
        try:
            logger.info("Clicking search result")
            self.google.actions.scroll_to_element(self.driver, result_element)
            time.sleep(random.uniform(0.5, 1.5))  # Pause before clicking
            self.google.actions.click_element(self.driver, result_element, "search result")
            time.sleep(random.uniform(1, 3))  # Wait for page load
            return True
        except Exception as e:
            logger.error(f"Click failed: {e}")
            return False
    
    def _handle_popups_and_cookies(self):
        """Handle popups and cookie banners"""
        logger.info("Checking for popups and cookie banners")
        
        try:
            # Cookie acceptance selectors
            cookie_selectors = [
                "button[id*='accept']",
                "button[class*='accept']",
                "button[class*='cookie']",
                ".cookie-accept",
                "#acceptCookies",
                "button:contains('Accept')",
                "button:contains('Allow')",
                "button:contains('Agree')"
            ]
            
            for selector in cookie_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            element.click()
                            logger.info("Accepted cookies")
                            time.sleep(1)
                            return
                except:
                    continue
            
            # Popup close selectors
            popup_selectors = [
                "button[aria-label*='close']",
                "button[class*='close']",
                ".modal-close",
                ".popup-close"
            ]
            
            for selector in popup_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            element.click()
                            logger.info("Closed popup")
                            time.sleep(1)
                            return
                except:
                    continue
                    
        except Exception as e:
            logger.debug(f"No popups/cookies to handle: {e}")
    
    def _minimal_browsing(self, duration):
        """Minimal browsing with error handling"""
        logger.info(f"Minimal browsing for {duration:.1f}s")
        end_time = time.time() + duration
        scroll_count = 0

        while time.time() < end_time:
            scroll_count += 1
            logger.info(f"Scroll {scroll_count}")
            try:
                self.google.actions.scroll_down(self.driver, max_scrolls=1, scroll_duration=2)
                time.sleep(random.uniform(2, 5))
            except JavascriptException as e:
                logger.warning(f"Scroll error (page may not be ready): {e}")
                time.sleep(2)
                continue
            except Exception as e:
                logger.error(f"Browsing error: {e}")
                break
    
    def _moderate_browsing(self, duration):
        """Moderate browsing - scrolling and some clicks"""
        logger.info(f"Moderate browsing for {duration:.1f}s")
        
        end_time = time.time() + duration
        action_count = 0
        
        while time.time() < end_time:
            action_count += 1
            
            # 30% chance to click internal links, 70% scroll
            if random.random() < 0.3:
                logger.info(f"Action {action_count}: Attempting internal link click")
                if not self._click_internal_links():
                    logger.info("No internal links, scrolling instead")
                    self.google.actions.scroll_down(self.driver, max_scrolls=2, scroll_duration=3)
            else:
                logger.info(f"Action {action_count}: Scrolling")
                self.google.actions.scroll_down(self.driver, max_scrolls=2, scroll_duration=3)
            
            time.sleep(random.uniform(3, 8))
    
    def _scroll_and_read(self):
        """Natural reading behavior with scrolling"""
        logger.info("Scroll and read pattern")
        
        scroll_count = random.randint(2, 5)
        for i in range(scroll_count):
            logger.info(f"Reading scroll {i+1}/{scroll_count}")
            try:
                self.google.actions.scroll_down(self.driver, max_scrolls=1, scroll_duration=random.randint(3, 6))
            except Exception as e:
                logger.warning(f"Scroll during read failed: {e}")
                break
            
            # Reading pause
            read_pause = random.uniform(5, 12)
            logger.info(f"Reading pause: {read_pause:.1f}s")
            time.sleep(read_pause)
    
    def _click_internal_links(self):
        """Click internal navigation links"""
        logger.info("Searching for internal links")
        
        try:
            links = self.driver.find_elements(By.CSS_SELECTOR, "a[href]")
            current_domain = self._extract_current_domain()
            
            internal_links = []
            for link in links:
                try:
                    href = link.get_attribute('href')
                    if not href:
                        continue
                    
                    link_domain = self._extract_domain(href)
                    
                    # Check if internal and visible
                    if (link_domain == current_domain and 
                        link.is_displayed() and 
                        link.is_enabled() and
                        link.text.strip()):
                        internal_links.append(link)
                except:
                    continue
            
            if internal_links:
                link = random.choice(internal_links)
                link_text = link.text.strip()[:50]
                logger.info(f"Clicking internal link: '{link_text}'")
                
                self.google.actions.scroll_to_element(self.driver, link)
                time.sleep(random.uniform(0.5, 1.5))
                self.google.actions.click_element(self.driver, link, "internal link")
                
                # Wait for page load
                time.sleep(random.uniform(2, 4))
                logger.info("Successfully navigated to internal page")
                return True
            else:
                logger.info("No internal links found")
                return False
                
        except Exception as e:
            logger.error(f"Error clicking internal link: {e}")
            return False

    def _wait_for_page_ready(self, timeout=10):
        """Wait for page to be fully loaded"""
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            time.sleep(1)
            return True
        except TimeoutException:
            logger.warning("Page load timeout")
            return False

    def _click_result_safe(self, result_element):
        """Enhanced safe clicking with retry"""
        max_retries = 2
        for attempt in range(max_retries):
            try:
                logger.info(f"Clicking search result (attempt {attempt+1})")
                self.google.actions.scroll_to_element(self.driver, result_element)
                time.sleep(random.uniform(0.5, 1.5))
                self.google.actions.click_element(self.driver, result_element, "search result")
                time.sleep(random.uniform(1, 3))
                return True
            except (ElementClickInterceptedException, StaleElementReferenceException) as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Click failed (attempt {attempt+1}), retrying...")
                    time.sleep(2)
                    continue
                logger.error(f"Click failed after {max_retries} attempts: {e}")
                return False
            except Exception as e:
                logger.error(f"Unexpected click error: {e}")
                return False

    def _post_target_behavior(self):
        """Natural behavior after target site visit"""
        logger.info("Post-target behavior: deciding next action")
        behaviors = [
            ("end_session", 0.70),
            ("search_brand_reviews", 0.10),
            ("compare_options", 0.15),
            ("return_reflect", 0.05)
        ]
        chosen = random.choices([b[0] for b in behaviors], weights=[b[1] for b in behaviors])[0]

        if chosen == "search_brand_reviews":
            brand = urlparse(self.target_url).netloc.split('.')[0]
            review_queries = review_query_templates
            query = random.choice(review_queries)
            logger.info(f"Post-target: searching for brand reviews using '{query}'")
            self.google.search(self.driver, query)
            time.sleep(random.uniform(10, 20))

        elif chosen == "compare_options":
            logger.info("Post-target: comparison shopping - returning to results and visiting competitors")
            try:
                self.driver.back()
                time.sleep(random.uniform(2, 4))
            except:
                pass
            competitors = self._get_competitor_domains()
            if competitors and self.google.click_competitor_site(self.driver, competitors):
                time.sleep(random.uniform(15, 30))

        elif chosen == "return_reflect":
            logger.info("Post-target: returning to search results to reflect")
            try:
                self.driver.back()
                time.sleep(random.uniform(5, 10))
            except:
                pass
        else:
            logger.info("Post-target: ending session naturally (closing or navigating away)")

    def _emergency_cleanup(self):
        """Emergency cleanup on critical errors"""
        logger.info("Running emergency cleanup")
        try:
            if not self._is_on_google_results():
                self.driver.get("https://www.google.com")
                time.sleep(3)
        except Exception as e:
            logger.error(f"Emergency cleanup failed: {e}")
    
    def _get_competitor_domains(self):
        """Load competitor domains from JSON"""
        try:
            with open('competitors_urls.json', 'r') as f:
                data = json.load(f)
                competitors = data.get('competitors', [])
                logger.info(f"Loaded {len(competitors)} competitor domains")
                return competitors
        except Exception as e:
            logger.warning(f"Could not load competitors: {e}")
            return []
    
    def _navigate_to_google(self):
        """Navigate back to Google homepage"""
        logger.info("Navigating to Google homepage")
        try:
            self.google.navigate_to_search_results(self.driver, search_keyword=None, search_results_url=None)
            #self.driver.get("https://www.google.com")
            time.sleep(random.uniform(2, 4))
            logger.info("Successfully navigated to Google")
            return True
        except:
            logger.error("Failed to navigate to Google")
            return False
    
    def _recover_from_failure(self):
        """Attempt to recover from failures"""
        logger.info("Attempting recovery")
        
        try:
            # Try going back first
            logger.info("Trying to go back")
            self.driver.back()
            time.sleep(random.uniform(2, 4))
            
            if self._is_on_google_results():
                logger.info("Recovery successful - back on search results")
                return True
            
            # Try navigating to Google
            logger.info("Trying to navigate to Google")
            return self._navigate_to_google()
            
        except Exception as e:
            logger.error(f"Recovery failed: {e}")
            return False
    
    def _reset_cycle_state(self):
        """Reset state for new search cycle"""
        logger.info("Resetting cycle state")
        self.current_page = 1
        self.pagination_attempts = 0
        logger.info("State reset complete")
    
    def _human_pause(self):
        """Generate human-like pause duration"""
        return random.uniform(2.55, 5.67)
    
    def _log_action(self, action_type, details):
        """Log action for tracking"""
        action = {
            'timestamp': time.time(),
            'type': action_type,
            'details': details
        }
        self.actions_taken.append(action)
        logger.info(f"Action logged: {action_type} - {details}")

