#!/usr/bin/python3
"""
    OAuth Handler — Handles Continue with Google flow for session re-authentication.
    Uses existing GoogleActions click behavior for human-like timing.
    Never types credentials. Only clicks what a logged-in human would click.
    Author: Fortune Nwohiri
"""
import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from logging_config.logger import get_logger
from Agents.google_actions import GoogleActions

logger = get_logger("OAuthHandler")


class OAuthHandler:
    """
    Handles Google OAuth re-authentication for platforms that use
    Continue with Google as their login method.

    Flow:
    1. Detect if the platform is showing a login wall
    2. Find and click Continue with Google
    3. Find and click the Gmail account in the picker
    4. Click Continue/Allow on the consent screen if it appears
    5. Confirm dashboard loaded successfully

    Every click goes through GoogleActions.click_element() which has
    pre-click hesitation, scroll-to-element, and post-click pause.
    Nothing is clicked instantly. Nothing is typed.
    """

    def __init__(self):
        self.actions = GoogleActions()

        # Selectors for Continue with Google buttons across platforms.
        # Wellfound, Contra, and Workable all use variations of these.
        self.CONTINUE_WITH_GOOGLE_SELECTORS = [
            "a[href*='google'][class*='social']",
            "button[class*='google']",
            "a[href*='auth/google']",
            "a[href*='oauth/google']",
            "a[href*='google_oauth']",
            "button[data-provider='google']",
            "a[data-provider='google']",
            "[class*='google-login']",
            "[class*='google-signin']",
            "[class*='google-auth']",
            "button[class*='GoogleLogin']",
            # Text-based fallbacks
            "//button[contains(., 'Continue with Google')]",
            "//a[contains(., 'Continue with Google')]",
            "//button[contains(., 'Sign in with Google')]",
            "//a[contains(., 'Sign in with Google')]",
            "//button[contains(., 'Log in with Google')]",
            "//a[contains(., 'Log in with Google')]",
        ]

        # Google account picker selectors.
        # These appear on accounts.google.com after clicking Continue with Google.
        self.GOOGLE_ACCOUNT_SELECTORS = [
            "div[data-identifier]",          # Account container with email
            "div[data-email]",               # Direct email attribute
            "div.jMFfSd",                    # Google's account picker card
            "div[jsname='s3Eaab']",          # Google account list item
            "li[data-identifier]",
            "div[role='link'][data-email]",
        ]

        # Google OAuth consent/continue button selectors.
        # Appears after picking the account.
        self.OAUTH_CONTINUE_SELECTORS = [
            "button[id='submit_approve_access']",
            "button[id='continue']",
            "#submit_approve_access",
            "//button[contains(., 'Continue')]",
            "//button[contains(., 'Allow')]",
            "//button[contains(., 'Allow access')]",
        ]

        # Dashboard confirmation selectors per platform.
        # If any of these appear, the login was successful.
        self.DASHBOARD_INDICATORS = {
            "wellfound": [
                "a[href*='/jobs']",
                "nav[class*='navbar']",
                "div[class*='dashboard']",
                "[class*='job-feed']",
                "a[href*='/profile']",
            ],
            "contra": [
                "div[class*='dashboard']",
                "a[href*='/projects']",
                "nav[class*='nav']",
                "[class*='opportunity']",
            ],
            "workable": [
                "div[class*='job-list']",
                "h1[class*='jobs']",
                "[class*='search-results']",
                "div[class*='careers']",
            ],
        }

    def is_session_expired(self, driver, platform_key: str) -> bool:
        """
        Check if the current page is showing a login wall.
        Called before every job scrape attempt on login-required platforms.

        Args:
            driver: Active SeleniumBase driver
            platform_key: 'wellfound', 'contra', or 'workable'

        Returns:
            bool: True if login wall detected, False if still logged in
        """
        try:
            current_url = driver.current_url.lower()

            # URL-based detection — most reliable
            login_url_patterns = [
                "login", "signin", "sign-in",
                "auth", "authenticate", "session"
            ]
            for pattern in login_url_patterns:
                if pattern in current_url:
                    logger.info(f"Session expired on {platform_key} — login URL detected: {current_url}")
                    return True

            # Check for Continue with Google button on the page
            for selector in self.CONTINUE_WITH_GOOGLE_SELECTORS[:6]:
                try:
                    by = By.XPATH if selector.startswith("//") else By.CSS_SELECTOR
                    elements = driver.find_elements(by, selector)
                    if elements and any(el.is_displayed() for el in elements):
                        logger.info(f"Session expired on {platform_key} — login button detected")
                        return True
                except Exception:
                    continue

            return False

        except Exception as e:
            logger.error(f"Error checking session status: {e}")
            return False

    def reauthenticate(self, driver, platform_key: str, gmail_account: str) -> bool:
        """
        Full Google OAuth re-authentication flow.
        Every click is human-timed via GoogleActions.click_element().

        Args:
            driver: Active SeleniumBase driver
            platform_key: 'wellfound', 'contra', or 'workable'
            gmail_account: The Gmail address to look for in the account picker.
                           Used to identify the correct account if multiple exist.

        Returns:
            bool: True if re-authentication succeeded, False if failed
        """
        logger.info(f"Starting OAuth re-authentication for {platform_key}")

        try:
            # Step 1: Find and click Continue with Google
            if not self._click_continue_with_google(driver, platform_key):
                logger.error("Could not find Continue with Google button")
                return False

            # Step 2: Wait for Google account picker to load
            # Google's OAuth page takes 2-5 seconds to load
            logger.info("Waiting for Google account picker...")
            time.sleep(random.uniform(2.5, 5.0))

            # Step 3: Click the Gmail account in the picker
            if not self._click_gmail_account(driver, gmail_account):
                logger.error("Could not find Gmail account in picker")
                return False

            # Step 4: Handle consent screen if it appears
            # Not always shown — only on first auth or when permissions change
            time.sleep(random.uniform(1.5, 3.0))
            self._handle_consent_screen(driver)

            # Step 5: Wait for platform dashboard to load
            time.sleep(random.uniform(2.0, 4.0))

            # Step 6: Confirm login succeeded
            if self._confirm_dashboard_loaded(driver, platform_key):
                logger.info(f"Re-authentication successful for {platform_key}")
                return True
            else:
                logger.warning(f"Dashboard not confirmed for {platform_key} — may have failed")
                return False

        except Exception as e:
            logger.error(f"OAuth re-authentication failed: {e}", exc_info=True)
            return False

    def _click_continue_with_google(self, driver, platform_key: str) -> bool:
        """
        Find and click the Continue with Google button.
        Tries CSS selectors first, then XPath text-based selectors.
        """
        logger.info("Looking for Continue with Google button")

        # Natural pause before looking — simulates reading the page
        time.sleep(random.uniform(1.0, 2.5))

        for selector in self.CONTINUE_WITH_GOOGLE_SELECTORS:
            try:
                by = By.XPATH if selector.startswith("//") else By.CSS_SELECTOR

                element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((by, selector))
                )

                if not element.is_displayed():
                    continue

                logger.info(f"Found Continue with Google button: {selector}")

                # Use existing click_element from GoogleActions —
                # has scroll-to-element, pre-click hesitation, post-click pause
                self.actions.click_element(driver, element, "Continue with Google")
                return True

            except (TimeoutException, NoSuchElementException):
                continue
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue

        logger.error("Continue with Google button not found with any selector")
        return False

    def _click_gmail_account(self, driver, gmail_account: str) -> bool:
        """
        Find and click the Gmail account in Google's account picker.
        Looks for the account by email address first, then falls back
        to clicking the first visible account if only one exists.
        """
        logger.info(f"Looking for Gmail account: {gmail_account}")

        # Natural reading pause — simulates looking at the account options
        time.sleep(random.uniform(1.2, 3.0))

        # Try to find account by email address
        for selector in self.GOOGLE_ACCOUNT_SELECTORS:
            try:
                by = By.XPATH if selector.startswith("//") else By.CSS_SELECTOR
                elements = driver.find_elements(by, selector)

                for element in elements:
                    if not element.is_displayed():
                        continue

                    # Check if this element contains the Gmail address
                    element_text = element.text.lower()
                    element_data = (
                        element.get_attribute("data-identifier") or
                        element.get_attribute("data-email") or
                        ""
                    ).lower()

                    if (gmail_account.lower() in element_text or
                            gmail_account.lower() in element_data):
                        logger.info(f"Found matching Gmail account")
                        self.actions.click_element(driver, element, "Gmail account")
                        return True

            except Exception as e:
                logger.debug(f"Account selector {selector} failed: {e}")
                continue

        # Fallback: if only one account is visible, click it
        logger.info("Exact match not found, trying fallback to first visible account")
        for selector in self.GOOGLE_ACCOUNT_SELECTORS:
            try:
                by = By.XPATH if selector.startswith("//") else By.CSS_SELECTOR
                elements = driver.find_elements(by, selector)
                visible = [el for el in elements if el.is_displayed()]

                if len(visible) == 1:
                    logger.info("One account visible, clicking it")
                    self.actions.click_element(driver, visible[0], "Gmail account")
                    return True

            except Exception:
                continue

        logger.error("Could not find Gmail account in picker")
        return False

    def _handle_consent_screen(self, driver) -> bool:
        """
        Handle the Google OAuth consent screen if it appears.
        Not always shown. Clicks Continue or Allow if present.
        Returns True if consent screen was handled, False if not present.
        """
        logger.info("Checking for OAuth consent screen")

        for selector in self.OAUTH_CONTINUE_SELECTORS:
            try:
                by = By.XPATH if selector.startswith("//") else By.CSS_SELECTOR

                element = WebDriverWait(driver, 4).until(
                    EC.element_to_be_clickable((by, selector))
                )

                if element.is_displayed():
                    logger.info("Consent screen detected, clicking Continue")
                    # Extra pause here — Google watches timing on consent clicks
                    time.sleep(random.uniform(1.5, 3.0))
                    self.actions.click_element(driver, element, "OAuth consent Continue")
                    return True

            except TimeoutException:
                continue
            except Exception as e:
                logger.debug(f"Consent selector failed: {e}")
                continue

        logger.info("No consent screen detected — not required this time")
        return False

    def _confirm_dashboard_loaded(self, driver, platform_key: str) -> bool:
        """
        Confirm the platform dashboard loaded successfully after OAuth.
        Checks platform-specific indicators.
        """
        indicators = self.DASHBOARD_INDICATORS.get(platform_key, [])

        for selector in indicators:
            try:
                by = By.XPATH if selector.startswith("//") else By.CSS_SELECTOR
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((by, selector))
                )
                logger.info(f"Dashboard confirmed for {platform_key}")
                return True
            except TimeoutException:
                continue

        # Fallback: check URL is not a login page
        current_url = driver.current_url.lower()
        is_not_login = not any(
            p in current_url for p in ["login", "signin", "auth", "oauth"]
        )
        if is_not_login:
            logger.info(f"Dashboard URL check passed for {platform_key}")
            return True

        return False