#!/usr/bin/python3
"""
    Page Intelligence Agent — Reads the full page DOM before any form
    interaction. Returns a structured field map telling application_actions.py
    exactly what to fill, what to skip, and what to send to AI.
    Uses Agent 1 from SKILL.md for page classification.
    Author: Fortune Nwohiri
"""
import json
import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from logging_config.logger import get_logger
from job_agent.application_brain import classify_page

logger = get_logger("PageIntelligenceAgent")


# ── CLOUDFLARE SIGNALS ────────────────────────────────────────────────────────

CLOUDFLARE_TITLE_SIGNALS = [
    "just a moment",
    "attention required",
    "checking your browser",
    "please wait",
    "ddos-guard",
    "cloudflare",
    "enable javascript",
    "one moment please",
]


# ── STATIC FIELD SIGNATURES ───────────────────────────────────────────────────

STATIC_FIELD_SIGNATURES = [
    {
        "type": "first_name",
        "value_source": "static",
        "selectors": [
            "input#first_name", "input[name='first_name']",
            "input[name='firstName']", "input[id*='first']",
            "input[placeholder*='First name']",
            "input[placeholder*='first name']",
            "input[aria-label*='First name']",
            "input[autocomplete='given-name']",
        ],
        "label_patterns": ["first name", "first"],
    },
    {
        "type": "last_name",
        "value_source": "static",
        "selectors": [
            "input#last_name", "input[name='last_name']",
            "input[name='lastName']", "input[id*='last']",
            "input[placeholder*='Last name']",
            "input[placeholder*='last name']",
            "input[aria-label*='Last name']",
            "input[autocomplete='family-name']",
        ],
        "label_patterns": ["last name", "surname", "family name"],
    },
    {
        "type": "full_name",
        "value_source": "static",
        "selectors": [
            "input[name='name']", "input#name",
            "input[id*='full_name']", "input[name='full_name']",
            "input[placeholder*='Full name']",
            "input[placeholder*='Your name']",
            "input[aria-label*='Full name']",
            "input[autocomplete='name']",
        ],
        "label_patterns": ["full name", "your name", "name"],
    },
    {
        "type": "email",
        "value_source": "static",
        "selectors": [
            "input[type='email']", "input#email",
            "input[name='email']", "input[id*='email']",
            "input[placeholder*='Email']",
            "input[aria-label*='Email']",
            "input[autocomplete='email']",
        ],
        "label_patterns": ["email", "email address"],
    },
    {
        "type": "phone",
        "value_source": "static",
        "selectors": [
            "input[type='tel']", "input#phone",
            "input[name='phone']", "input[id*='phone']",
            "input[placeholder*='Phone']",
            "input[aria-label*='Phone']",
            "input[autocomplete='tel']",
        ],
        "label_patterns": ["phone", "telephone", "mobile", "phone number"],
    },
    {
        "type": "linkedin",
        "value_source": "static",
        "selectors": [
            "input[name*='linkedin']", "input[id*='linkedin']",
            "input[placeholder*='LinkedIn']",
            "input[aria-label*='LinkedIn']",
            "input[name*='LinkedIn']",
        ],
        "label_patterns": ["linkedin", "linkedin url", "linkedin profile"],
    },
    {
        "type": "github",
        "value_source": "static",
        "selectors": [
            "input[name*='github']", "input[id*='github']",
            "input[placeholder*='GitHub']",
            "input[aria-label*='GitHub']",
        ],
        "label_patterns": ["github", "github url", "github profile"],
    },
    {
        "type": "portfolio",
        "value_source": "static",
        "selectors": [
            "input[name*='portfolio']", "input[id*='portfolio']",
            "input[placeholder*='Portfolio']",
            "input[name*='website']", "input[id*='website']",
            "input[placeholder*='Website']",
            "input[aria-label*='Portfolio']",
            "input[aria-label*='Website']",
            "input[autocomplete='url']",
        ],
        "label_patterns": ["portfolio", "website", "personal website", "portfolio url"],
    },
    {
        "type": "location",
        "value_source": "static",
        "selectors": [
            "input[name*='location']", "input[id*='location']",
            "input[name*='city']", "input[id*='city']",
            "input[name*='address']", "input[id*='address']",
            "input[placeholder*='Location']",
            "input[placeholder*='City']",
            "input[autocomplete='address-level2']",
        ],
        "label_patterns": ["location", "city", "address", "where are you based"],
    },
    {
        "type": "resume",
        "value_source": "cv_pdf",
        "selectors": [
            "input[type='file']",
            "input[name*='resume']",
            "input[name*='cv']",
            "input[id*='resume']",
            "input[id*='cv']",
            "input[accept*='pdf']",
            "input[accept*='.doc']",
        ],
        "label_patterns": ["resume", "cv", "upload resume", "attach resume", "upload cv"],
    },
]

# ── DYNAMIC FIELD SIGNATURES ──────────────────────────────────────────────────

COVER_LETTER_SIGNATURES = {
    "selectors": [
        "textarea[name*='cover']", "textarea[id*='cover']",
        "textarea[placeholder*='cover letter']",
        "textarea[aria-label*='cover letter']",
        "textarea[name*='letter']", "textarea[id*='letter']",
    ],
    "label_patterns": [
        "cover letter", "covering letter", "letter of interest",
        "motivation letter", "why do you want",
    ],
}

COVER_LETTER_FILE_SIGNATURES = {
    "selectors": [
        "input[type='file'][name*='cover']",
        "input[type='file'][id*='cover']",
        "input[type='file'][name*='letter']",
        "input[type='file'][id*='letter']",
        "input[accept*='pdf'][name*='cover']",
        "input[accept*='pdf'][id*='cover']",
    ],
    "label_patterns": [
        "upload cover letter", "attach cover letter",
        "cover letter file", "cover letter upload",
        "upload covering letter", "attach covering letter",
        "upload letter", "motivation letter file",
    ],
}

SALARY_SIGNATURES = {
    "selectors": [
        "input[name*='salary']", "input[id*='salary']",
        "input[placeholder*='salary']",
        "input[aria-label*='salary']",
        "input[name*='compensation']", "input[id*='compensation']",
        "input[name*='pay']", "input[id*='pay']",
    ],
    "label_patterns": [
        "salary", "expected salary", "desired salary", "salary expectation",
        "salary requirement", "compensation", "current salary",
        "annual salary", "monthly salary",
    ],
}

# ── HONEYPOT DETECTION ────────────────────────────────────────────────────────

HONEYPOT_NAME_PATTERNS = [
    "website", "url", "company2", "phone2", "address2",
    "fax", "hp", "honeypot", "trap", "bot", "spam",
    "winnie", "confirm_email", "email2", "email_confirm",
]

# ── MODAL SELECTORS ───────────────────────────────────────────────────────────
# Used to detect if clicking the apply button opened a modal overlay.

MODAL_SELECTORS = [
    "[role='dialog']",
    "[aria-modal='true']",
    "[class*='modal']:not([class*='modal-backdrop'])",
    "[class*='overlay'][style*='display']",
    "[class*='popup']",
    "[class*='drawer']",
    "[id*='modal']",
    "[id*='dialog']",
    ".ReactModal__Content",
    "[data-testid*='modal']",
    "[data-testid*='dialog']",
]


# ── CLOUDFLARE BYPASS ─────────────────────────────────────────────────────────

def _is_cloudflare_page(driver) -> bool:
    """
    Pure DOM check for Cloudflare challenge. No AI call. Zero cost.
    Checks page title and known challenge element selectors.
    """
    try:
        title = (driver.title or "").lower()
        if any(signal in title for signal in CLOUDFLARE_TITLE_SIGNALS):
            return True

        challenge_elements = driver.find_elements(
            By.CSS_SELECTOR,
            "div#challenge-stage, "
            "iframe[src*='challenges.cloudflare.com'], "
            "iframe[src*='cf-chl'], "
            "#cf-wrapper, "
            ".cf-browser-verification"
        )
        if challenge_elements and any(el.is_displayed() for el in challenge_elements):
            return True

        return False

    except Exception:
        return False


def try_cloudflare_bypass(driver) -> bool:
    """
    Attempt to bypass a Cloudflare Turnstile challenge.
    Uses SeleniumBase's uc_gui_click_captcha() which moves the real OS
    cursor rather than Selenium-generated mouse events. Cloudflare cannot
    distinguish real OS cursor movement from a human.

    Requirements:
    - Machine must have a display (Windows desktop, Linux with X11)
    - Browser window must be visible and in the foreground

    One attempt only. Returns True if challenge cleared.
    """
    logger.info("Attempting Cloudflare bypass via uc_gui_click_captcha")

    try:
        # Give the challenge time to fully render
        time.sleep(random.uniform(2.5, 4.5))

        # Move mouse to body first — simulates human hesitation
        try:
            body = driver.find_element(By.TAG_NAME, "body")
            ActionChains(driver).move_to_element(body).perform()
            time.sleep(random.uniform(0.8, 1.8))
        except Exception:
            pass

        # Real OS cursor click on the Turnstile checkbox
        driver.uc_gui_click_captcha()

        # Wait for page transition after the click
        time.sleep(random.uniform(3.0, 5.0))

        # Verify challenge is gone
        if _is_cloudflare_page(driver):
            logger.warning("Still on Cloudflare challenge after bypass attempt")
            return False

        logger.info(f"Cloudflare bypass succeeded — now on: {driver.current_url[:80]}")
        return True

    except Exception as e:
        logger.error(f"uc_gui_click_captcha failed: {e}")
        return False


# ── HONEYPOT CHECK ────────────────────────────────────────────────────────────

def is_honeypot(driver, element) -> tuple:
    """
    Check if a form field is a honeypot trap.
    Returns (bool, str) — is_honeypot, reason.
    """
    try:
        display = driver.execute_script(
            "return window.getComputedStyle(arguments[0]).display;", element
        )
        if display == "none":
            return True, "display:none"

        visibility = driver.execute_script(
            "return window.getComputedStyle(arguments[0]).visibility;", element
        )
        if visibility == "hidden":
            return True, "visibility:hidden"

        opacity = driver.execute_script(
            "return window.getComputedStyle(arguments[0]).opacity;", element
        )
        if float(opacity) == 0:
            return True, "opacity:0"

        tabindex = element.get_attribute("tabindex")
        if tabindex and int(tabindex) < 0:
            return True, "tabindex=-1"

        size = element.size
        if size["width"] == 0 or size["height"] == 0:
            return True, "zero dimensions"

        location = element.location
        if location["x"] < -100 or location["y"] < -100:
            return True, "off-screen position"

        field_name = (element.get_attribute("name") or "").lower()
        field_id = (element.get_attribute("id") or "").lower()
        for pattern in HONEYPOT_NAME_PATTERNS:
            if pattern in field_name or pattern in field_id:
                return True, f"suspicious name pattern: {pattern}"

        return False, ""

    except Exception as e:
        logger.debug(f"Honeypot check error (non-fatal): {e}")
        return False, ""


# ── LABEL DETECTION ───────────────────────────────────────────────────────────

def get_field_label(driver, element) -> str:
    try:
        aria_label = element.get_attribute("aria-label")
        if aria_label:
            return aria_label.lower().strip()

        placeholder = element.get_attribute("placeholder")
        if placeholder:
            return placeholder.lower().strip()

        field_id = element.get_attribute("id")
        if field_id:
            try:
                label_el = driver.find_element(
                    By.CSS_SELECTOR, f"label[for='{field_id}']"
                )
                return label_el.text.lower().strip()
            except NoSuchElementException:
                pass

        try:
            parent = driver.execute_script(
                "return arguments[0].closest('label');", element
            )
            if parent:
                return parent.text.lower().strip()
        except Exception:
            pass

        try:
            label_text = driver.execute_script("""
                var el = arguments[0];
                var parent = el.parentElement;
                if (!parent) return '';
                var labels = parent.querySelectorAll('label, span, p');
                for (var i = 0; i < labels.length; i++) {
                    if (labels[i].textContent.trim().length > 0) {
                        return labels[i].textContent.trim();
                    }
                }
                return parent.textContent.trim().substring(0, 100);
            """, element)
            if label_text:
                return label_text.lower().strip()
        except Exception:
            pass

        title = element.get_attribute("title")
        if title:
            return title.lower().strip()

        return ""

    except Exception as e:
        logger.debug(f"Label detection error (non-fatal): {e}")
        return ""


# ── FIELD CLASSIFIER ──────────────────────────────────────────────────────────

def classify_field(driver, element, tag: str) -> dict:
    try:
        honeypot, reason = is_honeypot(driver, element)
        if honeypot:
            selector = element.get_attribute("id") or element.get_attribute("name") or "unknown"
            logger.debug(f"Honeypot detected: {selector} — {reason}")
            return {
                "type": "honeypot",
                "value_source": "skip",
                "selector": selector,
                "label": "",
                "honeypot_reason": reason,
                "element": element,
            }

        label = get_field_label(driver, element)
        field_name = (element.get_attribute("name") or "").lower()
        field_id = (element.get_attribute("id") or "").lower()
        input_type = (element.get_attribute("type") or "text").lower()
        combined = f"{label} {field_name} {field_id}"

        if input_type in ["submit", "button", "image", "reset"]:
            return None

        if input_type == "hidden":
            return {
                "type": "honeypot",
                "value_source": "skip",
                "selector": field_id or field_name or "hidden",
                "label": label,
                "honeypot_reason": "hidden input type",
                "element": element,
            }

        if input_type == "file" or tag == "file":
            for pattern in COVER_LETTER_FILE_SIGNATURES["label_patterns"]:
                if pattern in combined:
                    return {
                        "type": "cover_letter_file",
                        "value_source": "ai_agent_5_pdf",
                        "selector": f"input[id='{field_id}']" if field_id else "input[type='file']",
                        "label": label,
                        "element": element,
                    }
            for selector in COVER_LETTER_FILE_SIGNATURES["selectors"]:
                try:
                    matched = driver.find_elements(By.CSS_SELECTOR, selector)
                    if element in matched:
                        return {
                            "type": "cover_letter_file",
                            "value_source": "ai_agent_5_pdf",
                            "selector": selector,
                            "label": label,
                            "element": element,
                        }
                except Exception:
                    continue

            return {
                "type": "resume",
                "value_source": "cv_pdf",
                "selector": f"input[id='{field_id}']" if field_id else "input[type='file']",
                "label": label,
                "element": element,
            }

        if tag == "textarea":
            for pattern in COVER_LETTER_SIGNATURES["label_patterns"]:
                if pattern in combined:
                    return {
                        "type": "cover_letter",
                        "value_source": "ai_agent_5",
                        "selector": f"textarea[id='{field_id}']" if field_id else "textarea",
                        "label": label,
                        "element": element,
                    }
            return {
                "type": "custom",
                "value_source": "ai_agent_6",
                "selector": f"textarea[id='{field_id}']" if field_id else "textarea",
                "label": label or "additional information",
                "element": element,
            }

        for pattern in SALARY_SIGNATURES["label_patterns"]:
            if pattern in combined:
                return {
                    "type": "salary",
                    "value_source": "ai_agent_8",
                    "selector": f"input[id='{field_id}']" if field_id else "input",
                    "label": label,
                    "element": element,
                }

        for sig in STATIC_FIELD_SIGNATURES:
            for selector in sig["selectors"]:
                try:
                    matched = driver.find_elements(By.CSS_SELECTOR, selector)
                    if element in matched:
                        return {
                            "type": sig["type"],
                            "value_source": sig["value_source"],
                            "selector": selector,
                            "label": label,
                            "element": element,
                        }
                except Exception:
                    continue

            for pattern in sig["label_patterns"]:
                if pattern in combined:
                    selector = f"input[id='{field_id}']" if field_id else f"input[name='{field_name}']"
                    return {
                        "type": sig["type"],
                        "value_source": sig["value_source"],
                        "selector": selector,
                        "label": label,
                        "element": element,
                    }

        selector = f"input[id='{field_id}']" if field_id else f"input[name='{field_name}']" if field_name else "input"
        return {
            "type": "custom",
            "value_source": "ai_agent_6",
            "selector": selector,
            "label": label or field_name or field_id or "unknown field",
            "element": element,
        }

    except Exception as e:
        logger.error(f"Field classification error: {e}")
        return None


# ── OBSTRUCTION HANDLER ───────────────────────────────────────────────────────

def handle_obstruction(driver, classification: dict) -> bool:
    obstruction_type = classification.get("obstruction_type", "none")
    obstruction_action = classification.get("obstruction_action", "none")

    if obstruction_type == "none" or obstruction_action == "none":
        return True

    logger.info(f"Clearing obstruction: {obstruction_type} via {obstruction_action}")

    accept_selectors = [
        "button[id*='accept']", "button[id*='cookie']",
        "button[class*='accept']", "button[class*='cookie']",
        "button[aria-label*='Accept']", "button[aria-label*='accept']",
        "//button[contains(., 'Accept')]",
        "//button[contains(., 'Accept all')]",
        "//button[contains(., 'Allow all')]",
        "//button[contains(., 'I agree')]",
        "//button[contains(., 'Got it')]",
        "//button[contains(., 'OK')]",
        "#cookieConsent button", ".cookie-banner button",
        "[data-testid='cookie-accept']",
    ]

    dismiss_selectors = [
        "button[aria-label='Close']", "button[aria-label='close']",
        "button[class*='close']", "button[id*='close']",
        "button[class*='dismiss']", "button[id*='dismiss']",
        "//button[contains(., 'No thanks')]",
        "//button[contains(., 'Reject')]",
        "//button[contains(., 'Decline')]",
        "[data-testid='modal-close']",
        ".modal-close", ".popup-close",
    ]

    selectors_to_try = []
    if obstruction_action == "click_accept":
        selectors_to_try = accept_selectors
    elif obstruction_action in ["click_dismiss", "click_close"]:
        selectors_to_try = dismiss_selectors
    else:
        selectors_to_try = accept_selectors + dismiss_selectors

    for selector in selectors_to_try:
        try:
            by = By.XPATH if selector.startswith("//") else By.CSS_SELECTOR
            el = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((by, selector))
            )
            if el.is_displayed():
                time.sleep(random.uniform(0.5, 1.5))
                el.click()
                time.sleep(random.uniform(1, 2))
                logger.info(f"Obstruction cleared via: {selector}")
                return True
        except (TimeoutException, Exception):
            continue

    try:
        from selenium.webdriver.common.keys import Keys
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        time.sleep(random.uniform(0.5, 1))
        logger.info("Obstruction cleared via Escape key")
        return True
    except Exception:
        pass

    logger.warning("Could not clear obstruction")
    return False


# ── APPLY BUTTON FINDER ───────────────────────────────────────────────────────

def find_and_click_apply_button(driver, classification: dict) -> bool:
    apply_button_text = classification.get("apply_button_text", "").lower()

    apply_selectors = [
        "//button[contains(., 'Apply now')]",
        "//button[contains(., 'Apply Now')]",
        "//a[contains(., 'Apply now')]",
        "//a[contains(., 'Apply Now')]",
        "//button[contains(., 'Apply')]",
        "//a[contains(., 'Apply')]",
        "button[data-automation='btn-apply']",
        "button[class*='apply']",
        "a[class*='apply']",
        "[data-testid='apply-button']",
        "#apply-button",
        ".apply-button",
        "button[id*='apply']",
        "a[id*='apply']",
    ]

    if apply_button_text:
        apply_selectors.insert(0, f"//button[contains(., '{apply_button_text}')]")
        apply_selectors.insert(1, f"//a[contains(., '{apply_button_text}')]")

    for selector in apply_selectors:
        try:
            by = By.XPATH if selector.startswith("//") else By.CSS_SELECTOR
            el = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((by, selector))
            )
            if el.is_displayed():
                driver.execute_script("arguments[0].scrollIntoViewIfNeeded(true);", el)
                time.sleep(random.uniform(0.8, 2.0))
                el.click()
                logger.info(f"Apply button clicked: {selector}")
                time.sleep(random.uniform(2, 4))
                return True
        except (TimeoutException, Exception):
            continue

    logger.warning("Apply button not found")
    return False


# ── MODAL DETECTOR ────────────────────────────────────────────────────────────

def _detect_modal(driver) -> tuple:
    """
    Check if a modal or overlay appeared after a click.
    Returns (bool, str) — modal_found, modal_text.
    Modal text is extracted from the modal's inner content, not the page body.
    This is what gets passed to classify_page() after clicking Apply.
    """
    # Short wait for modal animation to complete
    time.sleep(random.uniform(0.8, 1.5))

    for selector in MODAL_SELECTORS:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for el in elements:
                try:
                    if not el.is_displayed():
                        continue
                    size = el.size
                    if size["width"] < 50 or size["height"] < 50:
                        continue
                    text = el.text.strip()
                    if len(text) > 20:
                        logger.info(
                            f"Modal detected via selector: {selector} "
                            f"({size['width']}x{size['height']}px, {len(text)} chars)"
                        )
                        return True, text[:1000]
                except Exception:
                    continue
        except Exception:
            continue

    # Fallback: check if a new element with significant z-index appeared
    try:
        high_z = driver.execute_script("""
            var all = document.querySelectorAll('*');
            for (var i = 0; i < all.length; i++) {
                var style = window.getComputedStyle(all[i]);
                var z = parseInt(style.zIndex);
                if (z > 100 && style.display !== 'none' && style.visibility !== 'hidden') {
                    var rect = all[i].getBoundingClientRect();
                    if (rect.width > 100 && rect.height > 100) {
                        return all[i].innerText.substring(0, 500);
                    }
                }
            }
            return null;
        """)
        if high_z and len(high_z.strip()) > 20:
            logger.info(f"Modal detected via z-index scan ({len(high_z)} chars)")
            return True, high_z.strip()
    except Exception:
        pass

    return False, ""


# ── POST-CLICK OBSERVER ───────────────────────────────────────────────────────

def _observe_post_click(driver, pre_click_url: str) -> dict:
    """
    After clicking the Apply button, observe what happened.
    Checks three possible outcomes in order:
    1. URL changed — navigated to a new page
    2. Modal appeared — an overlay opened on the same page
    3. Nothing changed — click may have failed or is a redirect in disguise

    Returns a dict with:
        changed: bool
        change_type: "redirect" | "modal" | "none"
        new_url: str
        modal_text: str
        visible_text: str (for page re-classification)
        forms: int
        inputs: int
        button_texts: list
        h1_texts: list
    """
    observation = {
        "changed": False,
        "change_type": "none",
        "new_url": driver.current_url,
        "modal_text": "",
        "visible_text": "",
        "forms": 0,
        "inputs": 0,
        "button_texts": [],
        "h1_texts": [],
    }

    current_url = driver.current_url

    # Check 1: Did we navigate to a new page?
    if current_url != pre_click_url:
        logger.info(f"Post-click: URL changed to {current_url[:80]}")
        observation["changed"] = True
        observation["change_type"] = "redirect"
        observation["new_url"] = current_url

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(random.uniform(1.0, 2.0))
            observation["visible_text"] = driver.find_element(By.TAG_NAME, "body").text[:1000]
            observation["forms"] = len(driver.find_elements(By.TAG_NAME, "form"))
            observation["inputs"] = len(driver.find_elements(By.TAG_NAME, "input"))
            buttons = driver.find_elements(By.TAG_NAME, "button")
            observation["button_texts"] = [
                btn.text.strip() for btn in buttons[:15] if btn.text.strip()
            ]
            h1s = driver.find_elements(By.TAG_NAME, "h1")
            observation["h1_texts"] = [
                h1.text.strip() for h1 in h1s[:5] if h1.text.strip()
            ]
        except Exception as e:
            logger.warning(f"Post-redirect page read failed: {e}")

        return observation

    # Check 2: Did a modal appear on the same page?
    modal_found, modal_text = _detect_modal(driver)
    if modal_found:
        logger.info(f"Post-click: Modal opened ({len(modal_text)} chars)")
        observation["changed"] = True
        observation["change_type"] = "modal"
        observation["modal_text"] = modal_text
        observation["visible_text"] = modal_text

        # Count inputs inside the modal specifically
        try:
            for selector in MODAL_SELECTORS:
                modal_els = driver.find_elements(By.CSS_SELECTOR, selector)
                for modal_el in modal_els:
                    if modal_el.is_displayed():
                        modal_inputs = modal_el.find_elements(
                            By.CSS_SELECTOR, "input, textarea, select"
                        )
                        modal_forms = modal_el.find_elements(By.TAG_NAME, "form")
                        modal_buttons = modal_el.find_elements(By.TAG_NAME, "button")
                        modal_h1s = modal_el.find_elements(By.TAG_NAME, "h1")

                        if modal_inputs:
                            observation["inputs"] = len(modal_inputs)
                            observation["forms"] = len(modal_forms)
                            observation["button_texts"] = [
                                btn.text.strip() for btn in modal_buttons[:15] if btn.text.strip()
                            ]
                            observation["h1_texts"] = [
                                h1.text.strip() for h1 in modal_h1s[:5] if h1.text.strip()
                            ]
                            logger.info(
                                f"Modal has {len(modal_inputs)} inputs, "
                                f"{len(modal_forms)} forms"
                            )
                            return observation
        except Exception as e:
            logger.debug(f"Modal input count failed (non-fatal): {e}")

        # Fallback: use full page counts but modal text
        try:
            observation["forms"] = len(driver.find_elements(By.TAG_NAME, "form"))
            observation["inputs"] = len(driver.find_elements(By.TAG_NAME, "input"))
            buttons = driver.find_elements(By.TAG_NAME, "button")
            observation["button_texts"] = [
                btn.text.strip() for btn in buttons[:15] if btn.text.strip()
            ]
        except Exception:
            pass

        return observation

    # Check 3: Nothing changed
    logger.info("Post-click: No URL change, no modal detected")
    observation["changed"] = False
    observation["change_type"] = "none"

    try:
        observation["visible_text"] = driver.find_element(By.TAG_NAME, "body").text[:1000]
        observation["forms"] = len(driver.find_elements(By.TAG_NAME, "form"))
        observation["inputs"] = len(driver.find_elements(By.TAG_NAME, "input"))
        buttons = driver.find_elements(By.TAG_NAME, "button")
        observation["button_texts"] = [
            btn.text.strip() for btn in buttons[:15] if btn.text.strip()
        ]
        h1s = driver.find_elements(By.TAG_NAME, "h1")
        observation["h1_texts"] = [
            h1.text.strip() for h1 in h1s[:5] if h1.text.strip()
        ]
    except Exception:
        pass

    return observation


# ── MAIN PAGE INTELLIGENCE FUNCTION ──────────────────────────────────────────

def read_page(driver, url: str) -> dict:
    """
    Master function. Reads the full page and returns a complete
    intelligence report including page classification and field map.
    Called by job_connector.py before any form interaction.
    """
    logger.info(f"Reading page: {url}")

    result = {
        "page_type": "unknown",
        "confidence": 0,
        "obstruction_cleared": False,
        "apply_button_clicked": False,
        "post_click_change_type": "none",
        "field_map": [],
        "honeypots_detected": 0,
        "total_fields": 0,
        "fillable_fields": 0,
        "has_cover_letter": False,
        "has_custom_questions": False,
        "has_salary_field": False,
        "has_resume_upload": False,
        "ready_to_fill": False,
        "skip_reason": "",
    }

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(random.uniform(1.5, 3.0))

        page_title = driver.title or ""
        try:
            visible_text = driver.find_element(By.TAG_NAME, "body").text[:1000]
        except Exception:
            visible_text = ""

        forms = driver.find_elements(By.TAG_NAME, "form")
        inputs = driver.find_elements(By.TAG_NAME, "input")
        buttons = driver.find_elements(By.TAG_NAME, "button")
        h1_elements = driver.find_elements(By.TAG_NAME, "h1")

        button_texts = []
        for btn in buttons[:15]:
            try:
                text = btn.text.strip()
                if text:
                    button_texts.append(text)
            except Exception:
                continue

        h1_texts = []
        for h1 in h1_elements[:5]:
            try:
                text = h1.text.strip()
                if text:
                    h1_texts.append(text)
            except Exception:
                continue

        # Agent 1: classify the page
        classification = classify_page(
            url=url,
            page_title=page_title,
            visible_text=visible_text,
            form_count=len(forms),
            input_count=len(inputs),
            button_texts=button_texts,
            h1_texts=h1_texts,
        )

        page_type = classification.get("page_type", "unknown")
        confidence = classification.get("confidence", 0)
        result["page_type"] = page_type
        result["confidence"] = confidence

        logger.info(
            f"Page type: {page_type} (confidence: {confidence}) "
            f"apply_button_exists: {classification.get('apply_button_exists')} "
            f"apply_opens_modal: {classification.get('apply_opens_modal')}"
        )

        # Handle obstructions first
        if classification.get("obstruction_detected"):
            cleared = handle_obstruction(driver, classification)
            result["obstruction_cleared"] = cleared
            if cleared:
                time.sleep(random.uniform(1, 2))
                try:
                    visible_text = driver.find_element(By.TAG_NAME, "body").text[:1000]
                    inputs = driver.find_elements(By.TAG_NAME, "input")
                    forms = driver.find_elements(By.TAG_NAME, "form")
                except Exception:
                    pass

        # ── CLOUDFLARE ────────────────────────────────────────────────────────
        if page_type == "cloudflare":
            logger.warning(f"Cloudflare wall on application driver — attempting bypass: {url}")
            bypassed = try_cloudflare_bypass(driver)

            if bypassed:
                try:
                    time.sleep(random.uniform(1.5, 2.5))
                    page_title = driver.title or ""
                    visible_text = driver.find_element(By.TAG_NAME, "body").text[:1000]
                    forms = driver.find_elements(By.TAG_NAME, "form")
                    inputs = driver.find_elements(By.TAG_NAME, "input")
                    buttons = driver.find_elements(By.TAG_NAME, "button")
                    button_texts = [btn.text.strip() for btn in buttons[:15] if btn.text.strip()]
                    h1_elements = driver.find_elements(By.TAG_NAME, "h1")
                    h1_texts = [h1.text.strip() for h1 in h1_elements[:5] if h1.text.strip()]

                    classification = classify_page(
                        url=driver.current_url,
                        page_title=page_title,
                        visible_text=visible_text,
                        form_count=len(forms),
                        input_count=len(inputs),
                        button_texts=button_texts,
                        h1_texts=h1_texts,
                    )
                    page_type = classification.get("page_type", "unknown")
                    result["page_type"] = page_type
                    result["confidence"] = classification.get("confidence", 0)
                    logger.info(f"Post-bypass page type: {page_type}")

                    if page_type == "cloudflare":
                        result["skip_reason"] = "cloudflare_bypass_failed"
                        logger.warning(f"Still on Cloudflare after bypass: {url}")
                        return result

                except Exception as e:
                    logger.warning(f"Re-read after Cloudflare bypass failed: {e}")
                    result["skip_reason"] = "cloudflare_bypass_failed"
                    return result
            else:
                result["skip_reason"] = "cloudflare_bypass_failed"
                logger.warning(f"Cloudflare bypass failed, skipping: {url}")
                return result

        # ── OTHER UNRECOVERABLE STATES ────────────────────────────────────────
        if page_type == "captcha":
            result["skip_reason"] = "captcha_detected"
            logger.warning(f"CAPTCHA detected: {url}")
            return result

        if page_type == "login_wall":
            result["skip_reason"] = "login_wall"
            logger.warning(f"Login wall detected: {url}")
            return result

        if page_type == "not_a_job":
            result["skip_reason"] = "not_a_job_page"
            logger.warning(f"Not a job page: {url}")
            return result

        # ── JOB LISTING — CLICK APPLY FIRST ──────────────────────────────────
        if page_type == "job_listing":
            if classification.get("apply_button_exists"):
                pre_click_url = driver.current_url

                clicked = find_and_click_apply_button(driver, classification)
                result["apply_button_clicked"] = clicked

                if not clicked:
                    result["skip_reason"] = "apply_button_not_found"
                    return result

                # ── POST-CLICK OBSERVATION ────────────────────────────────────
                # Observe what happened after clicking: redirect, modal, or nothing.
                # This is the awareness layer. The bot now knows what the click did.
                observation = _observe_post_click(driver, pre_click_url)
                result["post_click_change_type"] = observation["change_type"]

                logger.info(
                    f"Post-click observation: change_type={observation['change_type']} "
                    f"changed={observation['changed']} "
                    f"inputs={observation['inputs']} "
                    f"forms={observation['forms']}"
                )

                if not observation["changed"] and observation["inputs"] == 0:
                    # Click did nothing and no inputs appeared — give up
                    logger.warning("Apply button click produced no DOM change and no inputs")
                    result["skip_reason"] = "apply_click_no_effect"
                    return result

                # Re-classify using what the observation saw, not the stale page body.
                # For a modal, visible_text is the modal content.
                # For a redirect, visible_text is the new page body.
                classify_url = observation["new_url"] if observation["change_type"] == "redirect" else driver.current_url

                try:
                    classification = classify_page(
                        url=classify_url,
                        page_title=driver.title or "",
                        visible_text=observation["visible_text"],
                        form_count=observation["forms"],
                        input_count=observation["inputs"],
                        button_texts=observation["button_texts"],
                        h1_texts=observation["h1_texts"],
                    )
                    page_type = classification.get("page_type", "unknown")
                    result["page_type"] = page_type
                    result["confidence"] = classification.get("confidence", 0)
                    logger.info(
                        f"Post-click page type: {page_type} "
                        f"(change_type: {observation['change_type']})"
                    )
                except Exception as e:
                    logger.warning(f"Re-classification after Apply click failed: {e}")
                    # If the modal had inputs, trust the observation and treat as job_form
                    if observation["inputs"] > 0:
                        page_type = "job_form"
                        result["page_type"] = "job_form"
                        logger.info("Falling back to job_form based on input count after click")
                    else:
                        result["skip_reason"] = "post_click_classify_failed"
                        return result

            else:
                result["skip_reason"] = "no_apply_button_on_listing"
                return result

        # ── FIELD MAP ─────────────────────────────────────────────────────────
        if page_type not in ["job_form", "unknown"]:
            result["skip_reason"] = f"unexpected_page_type_{page_type}"
            return result

        all_inputs = driver.find_elements(By.CSS_SELECTOR, "input, textarea, select")
        field_map = []
        honeypot_count = 0

        for element in all_inputs:
            try:
                if not element.is_displayed() and not element.is_enabled():
                    honeypot, reason = is_honeypot(driver, element)
                    if honeypot:
                        honeypot_count += 1
                        field_map.append({
                            "type": "honeypot",
                            "value_source": "skip",
                            "selector": element.get_attribute("id") or element.get_attribute("name") or "unknown",
                            "label": "",
                            "honeypot_reason": reason,
                            "element": element,
                        })
                    continue

                tag = element.tag_name.lower()
                input_type = (element.get_attribute("type") or "text").lower()

                if tag == "textarea":
                    simplified_tag = "textarea"
                elif input_type == "file":
                    simplified_tag = "file"
                elif tag == "select":
                    simplified_tag = "select"
                else:
                    simplified_tag = "input"

                field = classify_field(driver, element, simplified_tag)

                if field is None:
                    continue

                if field["type"] == "honeypot":
                    honeypot_count += 1

                field_map.append(field)

            except Exception as e:
                logger.debug(f"Field processing error (non-fatal): {e}")
                continue

        # Deduplicate
        seen_selectors = set()
        deduplicated = []
        for field in field_map:
            selector = field.get("selector", "")
            if selector not in seen_selectors:
                seen_selectors.add(selector)
                deduplicated.append(field)

        field_map = deduplicated

        fillable = [f for f in field_map if f["value_source"] != "skip"]
        honeypots = [f for f in field_map if f["type"] == "honeypot"]
        has_cover_letter = any(
            f["type"] in ["cover_letter", "cover_letter_file"]
            for f in field_map
        )
        has_custom = any(f["type"] == "custom" for f in field_map)
        has_salary = any(f["type"] == "salary" for f in field_map)
        has_resume = any(f["type"] == "resume" for f in field_map)

        result["field_map"] = field_map
        result["honeypots_detected"] = len(honeypots)
        result["total_fields"] = len(field_map)
        result["fillable_fields"] = len(fillable)
        result["has_cover_letter"] = has_cover_letter
        result["has_custom_questions"] = has_custom
        result["has_salary_field"] = has_salary
        result["has_resume_upload"] = has_resume
        result["ready_to_fill"] = len(fillable) > 0

        logger.info(
            f"Field map built: {len(fillable)} fillable, "
            f"{len(honeypots)} honeypots, "
            f"cover_letter={has_cover_letter}, "
            f"custom_questions={has_custom}, "
            f"salary={has_salary}, "
            f"resume_upload={has_resume}"
        )

        for field in field_map:
            if field["type"] != "honeypot":
                logger.info(
                    f"  [{field['type']}] {field.get('label', '')} "
                    f"→ {field['value_source']}"
                )
            else:
                logger.info(
                    f"  [HONEYPOT SKIPPED] {field.get('selector', '')} "
                    f"— {field.get('honeypot_reason', '')}"
                )

        return result

    except Exception as e:
        logger.error(f"Page intelligence failed: {e}", exc_info=True)
        result["skip_reason"] = f"page_read_error: {str(e)}"
        return result


def update_jd_extraction_from_page(
    page_result: dict,
    jd_extraction: dict,
) -> dict:
    updated = jd_extraction.copy()
    updated["has_cover_letter_field"] = page_result.get("has_cover_letter", False)
    updated["has_custom_questions"] = page_result.get("has_custom_questions", False)
    return updated