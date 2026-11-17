#!/usr/bin/python3
"""
    This Module Contains the base Agent class for the YouTube Bot
    Author: Fortune Nwohiri
"""
import time
import concurrent.futures
import pyperclip
import csv
from csv import reader
import json
from login_gmail_selenium.util.profiles.google_profile import GoogleProfile
from login_gmail_selenium.util.profiles.profile import Profile
from login_gmail_selenium.util.helper import enter_text
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.common.exceptions import JavascriptException, TimeoutException, ElementClickInterceptedException
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
from logging_config.logger import get_logger
from abc import ABC, abstractmethod
from Agents.utils import nigerian_websites

# Get logger
logger = get_logger("YouTubeBot")


class Agent(ABC):

    nigerian_websites = nigerian_websites
    """ 
    The Agent class is the abstract base class that defines what all connectors should be able to do.
    It provides utility methods and defines the interface for environment interactions.
    """



    GOOGLE_SEARCH_XPATH = "/html/body/div[1]/div[3]/form/div[1]/div[1]/div[1]/div[1]/div[2]/textarea"

    def pick_random_websites(self, websites, num_pick=None):
        """
        Pick a random selection of websites from a list.
        
        Args:
            websites (list): List of website URLs to choose from
            num_pick (int, optional): Number of websites to pick. If None, picks 1-5 randomly
            
        Returns:
            list: Random selection of websites
            
        Raises:
            ValueError: If num_pick is greater than available websites
        """
        if num_pick is None:
            num_pick = random.randint(1, 5)
        elif num_pick > len(websites):
            raise ValueError("num_pick must be less than or equal to the number of websites.")
        
        return random.sample(websites, num_pick)
        
    
    def launch_profile(self, email, password, backup_email):
        """
        Launch a Google profile with the provided credentials.
        
        Args:
            email (str): Primary email address for the profile
            password (str): Password for the email account
            backup_email (str): Backup email address for recovery
            
        Returns:
            tuple: (driver, profile) where driver is the WebDriver instance and profile is the GoogleProfile instance
            
        Raises:
            Exception: If email or password is empty
        """
        if email != "" and password != "":
            profile = GoogleProfile(email, password, backup_email)
            driver = profile.retrieve_driver()
            profile.start()
            return driver, profile
        else:
            raise(f"Error: No Email or Password was Passed for {email} with password: {password}")
        



    def set_browser_size(self, driver, size_name="desktop"):
        """Set browser window size based on common device presets"""
        size_presets = {
            "mobile": (375, 667),      # iPhone 6/7/8
            "tablet": (768, 1024),     # iPad
            "desktop": (1280, 800),    # Small desktop
            "large": (1920, 1080),     # HD desktop
            "fullscreen": (0, 0)       # Full screen
        }
        
        width, height = size_presets.get(size_name, (1280, 800))
        
        if width == 0 and height == 0:
            driver.maximize_window()
        else:
            driver.set_window_size(width, height)


    def extract_video_id(self, url):
        """
        Extract YouTube video ID from various URL formats including Shorts.
        
        Args:
            url (str): YouTube URL to extract video ID from
            
        Returns:
            str or None: The 11-character video ID if found, None otherwise
        """
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


    


    def find_correct_link(self, driver, website, results):
        """
        # This function takes the website we are searching for and the list of search results,
        # and finds the correct link for the website among the results.
        """
        target_domain = website.replace("www.", "").strip().lower()

        found_match = False
        for i, result in enumerate(results[:10], 1):
            try:
                url = result.get_attribute("href")
                if not url:
                    continue

                selector = driver.execute_script("""
                                    function getSelector(el) {
                                        if (!el) return '';
                                        const path = [];
                                        while (el && el.nodeType === Node.ELEMENT_NODE) {
                                            let selector = el.nodeName.toLowerCase();
                                            
                                            if (el.id) {
                                                selector += `#${el.id}`;
                                                path.unshift(selector);
                                                break;
                                            }
                                            else if (el.name) {
                                                selector += `[name="${el.name}"]`;
                                                path.unshift(selector);
                                                break;
                                            }
                                            else if (el.title) {
                                                selector += `[title="${el.title}"]`;
                                                path.unshift(selector);
                                                break;
                                            }
                                            else if (el.ariaLabel) {
                                                selector += `[aria-label="${el.ariaLabel}"]`;
                                                path.unshift(selector);
                                                break;
                                            }
                                            else {
                                                let sib = el, nth = 1;
                                                while (sib = sib.previousElementSibling) {
                                                    if (sib.nodeName.toLowerCase() === selector) nth++;
                                                }
                                                if (nth !== 1) selector += `:nth-of-type(${nth})`;
                                                path.unshift(selector);
                                            }
                                            el = el.parentNode;
                                        }
                                        return path.join(' > ');
                                    }
                                    return getSelector(arguments[0]);
                                """, result)
                    
                # Parse URL to get domain
                parsed = urlparse(url)
                result_domain = parsed.netloc.replace("www.", "").lower()
                
                # Check if domain matches exactly
                if result_domain == target_domain:
                    logger.info(f"\nExact match found for {website}:")
                    logger.info(f"URL: {url}")
                    logger.info(f"Selector: {selector}")
                    found_match = True
                    break  # Stop after first exact match
            
            except Exception as e:
                logger.error(f"Error processing result #{i}: {str(e)}")
                continue

        if not found_match:
            logger.info(f"No exact match found for domain: {website}")

        return url, selector
    
    def warmup_accounts(self, email, password, backup_email):
        """
        Warms up accounts to evade bot detection with improved network resilience
        """
        random_websites = self.pick_random_websites(self.nigerian_websites)
        driver = self.launch_profile(email, password, backup_email)
        logger.info("Warming up Google accounts - network-optimized version")

        # Navigate to Google with extended timeout
        driver.uc_open_with_tab("https://google.com/ncr")
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.NAME, "q"))
            )
        except TimeoutException:
            logger.warning("Google didn't load in 30s. Refreshing...")
            driver.refresh()
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.NAME, "q"))
            )

        for i, website in enumerate(random_websites):
            logger.info(f"{email} accessing {website} [{i+1}/{len(random_websites)}]")
            
            # SEARCH PHASE (with recovery)
            try:
                # Always use same search method
                search_success = enter_text(
                    driver, 
                    'q', 
                    website, 
                    button=True, 
                    by=By.NAME, 
                    timeout=25  # Extended timeout for slow networks
                )
                if not search_success:
                    logger.warning(f"Search failed for {website}. Skipping...")
                    continue
            except Exception as e:
                logger.error(f"Critical search error: {str(e)}. Re-initializing Google...")
                driver.get("https://www.google.com")
                continue

            # RESULTS HANDLING
            try:
                # Wait for results with extended timeout
                WebDriverWait(driver, 25).until(
                    EC.visibility_of_element_located((By.ID, "search"))
                )
                
                # Get results with freshness check
                results = WebDriverWait(driver, 15).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'a[jsname="UWckNb"]'))
                )
                
                # Find target link
                url, selector = self.find_correct_link(driver, website, results)
                result = driver.find_element(By.CSS_SELECTOR, selector)

                # Scroll and click
                self.scroll(driver, result)
                result.click()
                
                # Verify site loaded
                WebDriverWait(driver, 30).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                
                # Browse target site
                self.scroll(driver)
                wait_time = random.uniform(3, 7)
                time.sleep(wait_time)
                
            except Exception as e:
                logger.error(f"Results processing failed: {str(e)}. Continuing...")
                driver.back()
                continue
            
            # RETURN TO GOOGLE (with verification)
            try:
                driver.back()
                # Wait for Google to reload
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.NAME, "q"))
                )
                logger.info(f"Returned to Google after {wait_time:.1f}s on site")
            except Exception as e:
                logger.warning(f"Return failed: {str(e)}. Reloading Google...")
                driver.open("https://www.google.com")
            
            # Randomized break between actions
            sleep_duration = random.uniform(2, 5)
            logger.info(f"Cycle complete. Sleeping {sleep_duration:.1f}s...")
            time.sleep(sleep_duration)
        
        return driver


            

    def extract_accounts(self, account_file):
        """
        Extracts a list of email, password, and backup email tuples from the specified file.

        Args:
            account_file (str): Path to the file containing account information.

        Returns:
            list: A list of tuples containing (email, password, backup_email).
        """
        with open('accounts.json', 'r') as f:
            retrieved_email_data = json.load(f)
        return retrieved_email_data

    def navigate_to_google(self, driver):
        logger.info("Navigating to Google")
        choice = random.choice(["same_tab", "new_tab"])

        if choice == "same_tab":
            # Open Google in current tab
            driver.open("https://www.google.com/ncr")
        else:
            # Open Google in a new tab
            driver.open_new_window("https://www.google.com/ncr")
            driver.switch_to_newest_window()
            driver.open("https://www.google.com/ncr")
        return True
    
    # def navigate_to_youtube(self, driver):
    #     driver.open("https://www.google.com/ncr")
    #     driver.find_element(By.ID, "APjFqb").send_keys("youtube.com")
    #     driver.find_element(By.ID, "APjFqb").send_keys(Keys.ENTER)
    #     return True

    # # Abstract methods that must be implemented by concrete agents
    # @abstractmethod
    # def search(self, driver, keyword: str):
    #     """Search for content in the environment"""
    #     pass

    # @abstractmethod
    # def engage_with_video(self, driver, target=False):
    #     """Engage with video content"""
    #     pass


if __name__=="__main__":
    logger.info("DO NOT RUN THIS DIRECTLY")
    pass
    