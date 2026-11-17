#!/usr/bin/python3
"""
    Application Actions — Mechanical form filling layer.
    Receives the field map from page_intelligence_agent.py and fills
    every field using the correct source. No AI inside this file.
    All AI calls happen through application_brain.py before this runs.
    Author: Fortune Nwohiri
"""
import os
import time
import random
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException,
    ElementClickInterceptedException, StaleElementReferenceException,
    JavascriptException,
)
from selenium.webdriver.common.keys import Keys
from logging_config.logger import get_logger

logger = get_logger("ApplicationActions")


# ── STATIC FIELD VALUE MAP ────────────────────────────────────────────────────
# Maps field type to the key in agent_profile.json that holds its value.

STATIC_FIELD_PROFILE_MAP = {
    "first_name": lambda profile: profile.get("first_name", "").split()[0],
    "last_name": lambda profile: profile.get("last_name", "").split()[-1],
    "full_name": lambda profile: profile.get("name", ""),
    "email": lambda profile: profile.get("email", ""),
    "phone": lambda profile: profile.get("phone", ""),
    "linkedin": lambda profile: profile.get("linkedin", ""),
    "github": lambda profile: profile.get("github", ""),
    "portfolio": lambda profile: profile.get("portfolio", ""),
    "location": lambda profile: profile.get("location", "Lagos State, Nigeria"),
}


def pre_click_hesitation():
    """
    Pause before interacting with any field.
    Simulates a human reading the field label before typing.
    """
    time.sleep(random.uniform(0.3, 1.5))


def scroll_to_field(driver, element):
    """
    Scroll the page until the field is visible in the viewport.
    A human always scrolls to see a field before typing into it.
    """
    try:
        driver.execute_script(
            "arguments[0].scrollIntoViewIfNeeded(true);", element
        )
        time.sleep(random.uniform(0.2, 0.6))
    except Exception as e:
        logger.debug(f"Scroll to field failed (non-fatal): {e}")


def fill_text_field(driver, element, value: str) -> bool:
    """
    Type a value into a single line text input.
    Clears the field first. Types character by character with
    random delays between 40 and 120 milliseconds per character.
    Simulates human typing speed.

    Used for: name, email, phone, LinkedIn, GitHub, portfolio,
    location, years of experience, salary, and any short text input.
    """
    if not value:
        logger.debug("fill_text_field called with empty value, skipping")
        return False

    try:
        scroll_to_field(driver, element)
        pre_click_hesitation()

        # Click to focus
        element.click()
        time.sleep(random.uniform(0.1, 0.3))

        # Clear existing content
        element.send_keys(Keys.CONTROL + "a")
        time.sleep(random.uniform(0.05, 0.15))
        element.send_keys(Keys.DELETE)
        time.sleep(random.uniform(0.1, 0.3))

        # Type character by character
        for char in value:
            element.send_keys(char)
            time.sleep(random.uniform(0.04, 0.12))

        logger.info(f"Filled text field: '{value[:30]}{'...' if len(value) > 30 else ''}'")
        return True

    except StaleElementReferenceException:
        logger.warning("fill_text_field: stale element, skipping")
        return False
    except Exception as e:
        logger.error(f"fill_text_field failed: {e}")
        return False


def fill_textarea(driver, element, text: str) -> bool:
    """
    Type a value into a multi-line textarea.
    Types in chunks of 20 to 50 characters with pauses between chunks.
    Chunked because typing 500 characters one by one is slower than
    a human would actually type a long passage.

    Used for: cover letter, custom question answers, additional info.
    """
    if not text:
        logger.debug("fill_textarea called with empty text, skipping")
        return False

    try:
        scroll_to_field(driver, element)
        pre_click_hesitation()

        element.click()
        time.sleep(random.uniform(0.2, 0.5))

        # Clear existing content
        element.send_keys(Keys.CONTROL + "a")
        time.sleep(random.uniform(0.05, 0.15))
        element.send_keys(Keys.DELETE)
        time.sleep(random.uniform(0.2, 0.4))

        # Type in chunks
        chunk_size = random.randint(20, 50)
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i + chunk_size]
            element.send_keys(chunk)
            time.sleep(random.uniform(0.05, 0.20))

        word_count = len(text.split())
        logger.info(f"Filled textarea: {word_count} words")
        return True

    except StaleElementReferenceException:
        logger.warning("fill_textarea: stale element, skipping")
        return False
    except Exception as e:
        logger.error(f"fill_textarea failed: {e}")
        return False


def upload_file(driver, element, file_path: str) -> bool:
    """
    Upload a file to a file input field.
    File inputs are often hidden in the DOM so makes the element
    visible first using JavaScript before sending the file path.

    Used for: resume PDF upload.
    """
    abs_path = str(Path(file_path).resolve())

    if not os.path.exists(abs_path):
        logger.error(f"File not found for upload: {abs_path}")
        return False

    try:
        scroll_to_field(driver, element)
        pre_click_hesitation()

        # Make file input visible and interactable
        driver.execute_script("""
            arguments[0].style.display = 'block';
            arguments[0].style.visibility = 'visible';
            arguments[0].style.opacity = '1';
            arguments[0].style.width = '200px';
            arguments[0].style.height = '30px';
        """, element)
        time.sleep(random.uniform(0.3, 0.7))

        element.send_keys(abs_path)
        time.sleep(random.uniform(1.0, 2.5))

        logger.info(f"Uploaded file: {os.path.basename(abs_path)}")
        return True

    except Exception as e:
        logger.error(f"upload_file failed: {e}")
        return False


def select_dropdown(driver, element, value: str) -> bool:
    """
    Select an option from a select dropdown element.
    Tries to match by visible text first then by value attribute.

    Used for: country dropdowns, years of experience dropdowns,
    work authorization dropdowns.
    """
    if not value:
        logger.debug("select_dropdown called with empty value, skipping")
        return False

    try:
        scroll_to_field(driver, element)
        pre_click_hesitation()

        select = Select(element)

        # Try visible text match first
        try:
            select.select_by_visible_text(value)
            logger.info(f"Dropdown selected by text: '{value}'")
            return True
        except Exception:
            pass

        # Try value attribute match
        try:
            select.select_by_value(value)
            logger.info(f"Dropdown selected by value: '{value}'")
            return True
        except Exception:
            pass

        # Try partial text match
        for option in select.options:
            if value.lower() in option.text.lower():
                select.select_by_visible_text(option.text)
                logger.info(f"Dropdown selected by partial match: '{option.text}'")
                return True

        logger.warning(f"Dropdown value not found: '{value}'")
        return False

    except Exception as e:
        logger.error(f"select_dropdown failed: {e}")
        return False


def handle_checkbox(driver, element, should_check: bool = True) -> bool:
    """
    Check or uncheck a checkbox.
    Checks current state before clicking to avoid double-clicking
    a checkbox that is already in the right state.

    Used for: terms agreement, work authorization checkboxes.
    """
    try:
        scroll_to_field(driver, element)
        pre_click_hesitation()

        is_checked = element.is_selected()

        if should_check and not is_checked:
            element.click()
            logger.info("Checkbox checked")
            return True
        elif not should_check and is_checked:
            element.click()
            logger.info("Checkbox unchecked")
            return True
        else:
            logger.info(f"Checkbox already in correct state: {'checked' if should_check else 'unchecked'}")
            return True

    except Exception as e:
        logger.error(f"handle_checkbox failed: {e}")
        return False


def handle_radio(driver, element, value: str) -> bool:
    """
    Select a radio button option by finding all radio buttons in the
    same group by name attribute and clicking the one matching value.

    Used for: Yes/No questions like visa sponsorship, work authorization.
    """
    try:
        field_name = element.get_attribute("name")
        if not field_name:
            scroll_to_field(driver, element)
            pre_click_hesitation()
            element.click()
            return True

        # Find all radios in this group
        radio_group = driver.find_elements(
            By.CSS_SELECTOR, f"input[type='radio'][name='{field_name}']"
        )

        for radio in radio_group:
            radio_value = (radio.get_attribute("value") or "").lower()
            radio_label = ""

            # Try to get label text
            radio_id = radio.get_attribute("id")
            if radio_id:
                try:
                    label_el = driver.find_element(
                        By.CSS_SELECTOR, f"label[for='{radio_id}']"
                    )
                    radio_label = label_el.text.lower()
                except Exception:
                    pass

            if value.lower() in radio_value or value.lower() in radio_label:
                scroll_to_field(driver, radio)
                pre_click_hesitation()
                radio.click()
                logger.info(f"Radio selected: '{value}'")
                return True

        logger.warning(f"Radio value not found: '{value}'")
        return False

    except Exception as e:
        logger.error(f"handle_radio failed: {e}")
        return False


def click_element(driver, element) -> bool:
    """
    Click any clickable element.
    Scrolls to it first, hesitates, then clicks.

    Used for: submit button, Next step buttons, Apply button.
    """
    try:
        scroll_to_field(driver, element)
        pre_click_hesitation()

        # Try normal click first
        try:
            element.click()
            logger.info("Element clicked")
            return True
        except ElementClickInterceptedException:
            # Fallback: JavaScript click
            driver.execute_script("arguments[0].click();", element)
            logger.info("Element clicked via JavaScript fallback")
            return True

    except Exception as e:
        logger.error(f"click_element failed: {e}")
        return False


def wait_for_next_step(driver, timeout: int = 10) -> bool:
    """
    After clicking Next on a multi-step form, wait for the next
    set of fields to appear in the DOM before interacting.
    Prevents the bot from trying to fill fields that have not loaded.
    """
    try:
        time.sleep(random.uniform(1.5, 3.0))
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )
        time.sleep(random.uniform(0.5, 1.5))
        logger.info("Next step loaded")
        return True
    except TimeoutException:
        logger.warning("wait_for_next_step timed out")
        return False


def detect_submission_confirmation(driver, timeout: int = 15) -> bool:
    """
    After clicking Submit, wait for a confirmation signal that the
    application was submitted successfully.

    Checks for:
    - Confirmation text patterns in page content
    - Thank you page URL patterns
    - Success element selectors
    - URL change away from /apply path
    """
    success_text_patterns = [
        "thank you", "thanks for applying", "application received",
        "application submitted", "successfully submitted",
        "we have received", "we'll be in touch", "we will be in touch",
        "your application has been", "application complete",
        "submission received", "successfully applied",
    ]

    success_selectors = [
        "div.confirmation", "div[class*='confirmation']",
        "div[class*='success']", "h1[class*='confirmation']",
        "h2[class*='confirmation']", ".success-message",
        "[data-testid='confirmation']", "[data-testid='success']",
        "div[class*='thank']", "h1[class*='thank']",
    ]

    success_url_patterns = [
        "confirmation", "success", "thank", "submitted", "complete",
    ]

    skip_url_patterns = [
        "/apply", "/application", "/apply/", "/application/",
    ]

    try:
        time.sleep(random.uniform(2.0, 4.0))

        # Check URL for confirmation signals
        current_url = driver.current_url.lower()

        # If still on apply page, not confirmed yet
        still_on_apply = any(p in current_url for p in skip_url_patterns)

        # Check for success URL patterns
        url_confirmed = any(p in current_url for p in success_url_patterns)
        if url_confirmed:
            logger.info(f"Submission confirmed via URL: {current_url}")
            return True

        # Check for success elements
        for selector in success_selectors:
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                logger.info(f"Submission confirmed via element: {selector}")
                return True
            except TimeoutException:
                continue

        # Check page text for confirmation patterns
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
            for pattern in success_text_patterns:
                if pattern in body_text:
                    logger.info(f"Submission confirmed via text: '{pattern}'")
                    return True
        except Exception:
            pass

        # If URL changed away from apply page that is a soft confirmation
        if not still_on_apply:
            logger.info("Submission likely confirmed — URL changed away from apply path")
            return True

        logger.warning("No submission confirmation detected")
        return False

    except Exception as e:
        logger.error(f"detect_submission_confirmation failed: {e}")
        return False


def find_submit_button(driver) -> object:
    """
    Find the submit button on the current form step.
    Returns the element or None if not found.
    """
    submit_selectors = [
        "button[type='submit']",
        "input[type='submit']",
        "button[id*='submit']",
        "button[class*='submit']",
        "//button[contains(., 'Submit')]",
        "//button[contains(., 'Submit application')]",
        "//button[contains(., 'Submit Application')]",
        "//button[contains(., 'Apply')]",
        "//button[contains(., 'Send application')]",
        "//input[@type='submit']",
        "[data-testid='submit-application']",
        "[data-testid='apply-button']",
    ]

    for selector in submit_selectors:
        try:
            by = By.XPATH if selector.startswith("//") else By.CSS_SELECTOR
            element = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((by, selector))
            )
            if element.is_displayed():
                logger.info(f"Submit button found: {selector}")
                return element
        except (TimeoutException, Exception):
            continue

    logger.warning("Submit button not found")
    return None


def find_next_button(driver) -> object:
    """
    Find the Next or Continue button on a multi-step form.
    Returns the element or None if not found.
    """
    next_selectors = [
        "//button[contains(., 'Next')]",
        "//button[contains(., 'Continue')]",
        "//button[contains(., 'Next step')]",
        "//button[contains(., 'Next Step')]",
        "button[id*='next']",
        "button[class*='next']",
        "[data-testid='next-button']",
        "[data-testid='continue-button']",
    ]

    for selector in next_selectors:
        try:
            by = By.XPATH if selector.startswith("//") else By.CSS_SELECTOR
            element = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((by, selector))
            )
            if element.is_displayed():
                logger.info(f"Next button found: {selector}")
                return element
        except (TimeoutException, Exception):
            continue

    return None


def get_static_value(field_type: str, agent_profile: dict) -> str:
    """
    Get the static value for a field type from agent_profile.json.
    Returns empty string if field type is not in the static map.
    """
    resolver = STATIC_FIELD_PROFILE_MAP.get(field_type)
    if resolver:
        try:
            return resolver(agent_profile)
        except Exception as e:
            logger.warning(f"Static value resolution failed for {field_type}: {e}")
            return ""
    return ""


def fill_form(
    driver,
    field_map: list,
    agent_profile: dict,
    jd_extraction: dict,
    cv_path: str,
    brain,
    cv_text: str = "",
) -> dict:
    """
    Master form filling function. Processes every field in the field map.

    For each field:
    - static          → get value from agent_profile.json
    - cv_pdf          → upload Fortune_Nwohiri_CV.pdf
    - ai_agent_5      → call brain.generate_cover_letter()
    - ai_agent_6      → call brain.answer_custom_question(label)
    - ai_agent_8      → call brain.get_salary_expectation()
    - skip            → do nothing

    Returns:
    {
        "fields_filled": int,
        "fields_skipped": int,
        "fields_failed": int,
        "honeypots_avoided": int,
        "cover_letter_generated": bool,
        "custom_questions_answered": int,
        "salary_answered": bool,
        "resume_uploaded": bool,
    }
    """
    result = {
        "fields_filled": 0,
        "fields_skipped": 0,
        "fields_failed": 0,
        "honeypots_avoided": 0,
        "cover_letter_generated": False,
        "custom_questions_answered": 0,
        "salary_answered": False,
        "resume_uploaded": False,
    }

    # Cache AI-generated content so the same field type is not
    # generated multiple times in one form
    cover_letter_cache = ""
    salary_cache = ""

    logger.info(f"Filling form: {len(field_map)} fields in map")

    for field in field_map:
        field_type = field.get("type", "unknown")
        value_source = field.get("value_source", "skip")
        element = field.get("element")
        label = field.get("label", "")

        if not element:
            logger.warning(f"No element for field [{field_type}], skipping")
            result["fields_skipped"] += 1
            continue

        # Verify element is still in DOM
        try:
            element.is_displayed()
        except StaleElementReferenceException:
            logger.warning(f"Stale element for field [{field_type}], skipping")
            result["fields_skipped"] += 1
            continue

        logger.info(f"Processing field: [{field_type}] source={value_source} label='{label}'")

        # ── SKIP HONEYPOTS ────────────────────────────────────────────────────
        if value_source == "skip" or field_type == "honeypot":
            logger.info(f"Skipping honeypot or flagged field: [{field_type}]")
            result["honeypots_avoided"] += 1
            result["fields_skipped"] += 1
            continue

        # ── STATIC FIELDS ─────────────────────────────────────────────────────
        if value_source == "static":
            value = get_static_value(field_type, agent_profile)
            if not value:
                logger.warning(f"No static value found for [{field_type}]")
                result["fields_skipped"] += 1
                continue

            tag = ""
            try:
                tag = element.tag_name.lower()
            except Exception:
                pass

            success = False
            if tag == "select":
                success = select_dropdown(driver, element, value)
            elif tag == "textarea":
                success = fill_textarea(driver, element, value)
            else:
                success = fill_text_field(driver, element, value)

            if success:
                result["fields_filled"] += 1
            else:
                result["fields_failed"] += 1
            continue

        # ── RESUME UPLOAD ─────────────────────────────────────────────────────
        if value_source == "cv_pdf":
            if not cv_path or not os.path.exists(cv_path):
                logger.warning("CV PDF not found, trying fallback resume")
                fallback = agent_profile.get("fallback_resume_path", "")
                if fallback and os.path.exists(fallback):
                    cv_path = fallback
                else:
                    logger.error("No resume file available for upload")
                    result["fields_failed"] += 1
                    continue

            success = upload_file(driver, element, cv_path)
            if success:
                result["fields_filled"] += 1
                result["resume_uploaded"] = True
            else:
                result["fields_failed"] += 1
            continue

        # ── COVER LETTER — AGENT 5 ────────────────────────────────────────────
        if value_source == "ai_agent_5":
            if not cover_letter_cache:
                logger.info("Generating cover letter via Agent 5")
                cover_letter_cache = brain.generate_cover_letter(
                    jd_extraction=jd_extraction,
                    cv_text=cv_text,
                )

            if cover_letter_cache:
                success = fill_textarea(driver, element, cover_letter_cache)
                if success:
                    result["fields_filled"] += 1
                    result["cover_letter_generated"] = True
                else:
                    result["fields_failed"] += 1
            else:
                logger.warning("Cover letter generation returned empty, skipping field")
                result["fields_skipped"] += 1
            continue

        # ── COVER LETTER FILE UPLOAD — AGENT 5 PDF ───────────────────────────
        if value_source == "ai_agent_5_pdf":
            if not cover_letter_cache:
                logger.info("Generating cover letter via Agent 5 for file upload")
                cover_letter_cache = brain.generate_cover_letter(
                    jd_extraction=jd_extraction,
                    cv_text=cv_text,
                )

            if cover_letter_cache:
                from job_agent.cv_builder import build_cover_letter_pdf
                cl_pdf_path = build_cover_letter_pdf(cover_letter_cache)

                if cl_pdf_path:
                    success = upload_file(driver, element, cl_pdf_path)
                    if success:
                        result["fields_filled"] += 1
                        result["cover_letter_generated"] = True
                    else:
                        result["fields_failed"] += 1
                else:
                    logger.error("Cover letter PDF generation failed")
                    result["fields_failed"] += 1
            else:
                logger.warning("Cover letter generation returned empty, skipping upload")
                result["fields_skipped"] += 1
            continue

        # ── SALARY — AGENT 8 ──────────────────────────────────────────────────
        if value_source == "ai_agent_8":
            if not salary_cache:
                logger.info("Getting salary answer via Agent 8")
                salary_cache = brain.get_salary_expectation(
                    jd_extraction=jd_extraction,
                    agent_profile=agent_profile,
                    field_label=label,
                )

            if salary_cache and salary_cache.upper() != "SKIP":
                tag = ""
                try:
                    tag = element.tag_name.lower()
                except Exception:
                    pass

                success = False
                if tag == "select":
                    success = select_dropdown(driver, element, salary_cache)
                else:
                    success = fill_text_field(driver, element, salary_cache)

                if success:
                    result["fields_filled"] += 1
                    result["salary_answered"] = True
                else:
                    result["fields_failed"] += 1
            else:
                logger.info("Salary field flagged as SKIP by Agent 8")
                result["fields_skipped"] += 1
            continue

        # ── CUSTOM QUESTIONS — AGENT 6 ────────────────────────────────────────
        if value_source == "ai_agent_6":
            if not label:
                logger.warning("Custom question has no label, skipping")
                result["fields_skipped"] += 1
                continue

            logger.info(f"Answering custom question via Agent 6: '{label[:60]}'")
            answer = brain.answer_custom_question(
                question=label,
                jd_extraction=jd_extraction,
                agent_profile=agent_profile,
                cv_text=cv_text,
            )

            if answer:
                tag = ""
                try:
                    tag = element.tag_name.lower()
                except Exception:
                    pass

                success = False
                if tag == "textarea":
                    success = fill_textarea(driver, element, answer)
                elif tag == "select":
                    success = select_dropdown(driver, element, answer)
                else:
                    success = fill_text_field(driver, element, answer)

                if success:
                    result["fields_filled"] += 1
                    result["custom_questions_answered"] += 1
                else:
                    result["fields_failed"] += 1
            else:
                logger.warning(f"Agent 6 returned empty answer for: '{label}'")
                result["fields_skipped"] += 1
            continue

        # ── UNKNOWN VALUE SOURCE ───────────────────────────────────────────────
        logger.warning(f"Unknown value_source '{value_source}' for field [{field_type}], skipping")
        result["fields_skipped"] += 1

    logger.info(
        f"Form fill complete: "
        f"{result['fields_filled']} filled, "
        f"{result['fields_skipped']} skipped, "
        f"{result['fields_failed']} failed, "
        f"{result['honeypots_avoided']} honeypots avoided"
    )

    return result


def handle_multi_step_form(
    driver,
    field_map: list,
    agent_profile: dict,
    jd_extraction: dict,
    cv_path: str,
    brain,
    cv_text: str = "",
    max_steps: int = 8,
) -> dict:
    """
    Handle multi-step forms where fields are spread across multiple pages.

    Fills whatever fields are visible on the current step, clicks Next,
    waits for the next step to load, then fills the next set of fields.
    Repeats until Submit button is found and clicked.

    Returns the combined fill result across all steps plus submission status.
    """
    combined_result = {
        "fields_filled": 0,
        "fields_skipped": 0,
        "fields_failed": 0,
        "honeypots_avoided": 0,
        "cover_letter_generated": False,
        "custom_questions_answered": 0,
        "salary_answered": False,
        "resume_uploaded": False,
        "submitted": False,
        "confirmed": False,
        "steps_completed": 0,
    }

    for step in range(max_steps):
        logger.info(f"Multi-step form: processing step {step + 1}")

        # Get visible fields on this step only
        visible_fields = []
        for field in field_map:
            element = field.get("element")
            if not element:
                continue
            try:
                if element.is_displayed() and element.is_enabled():
                    visible_fields.append(field)
            except StaleElementReferenceException:
                continue
            except Exception:
                continue

        logger.info(f"Step {step + 1}: {len(visible_fields)} visible fields")

        # Fill visible fields
        if visible_fields:
            step_result = fill_form(
                driver=driver,
                field_map=visible_fields,
                agent_profile=agent_profile,
                jd_extraction=jd_extraction,
                cv_path=cv_path,
                brain=brain,
                cv_text=cv_text,
            )

            # Accumulate results
            combined_result["fields_filled"] += step_result["fields_filled"]
            combined_result["fields_skipped"] += step_result["fields_skipped"]
            combined_result["fields_failed"] += step_result["fields_failed"]
            combined_result["honeypots_avoided"] += step_result["honeypots_avoided"]
            if step_result["cover_letter_generated"]:
                combined_result["cover_letter_generated"] = True
            combined_result["custom_questions_answered"] += step_result["custom_questions_answered"]
            if step_result["salary_answered"]:
                combined_result["salary_answered"] = True
            if step_result["resume_uploaded"]:
                combined_result["resume_uploaded"] = True

        combined_result["steps_completed"] += 1

        # Look for Submit button first
        submit_btn = find_submit_button(driver)
        if submit_btn:
            logger.info(f"Submit button found on step {step + 1}. Submitting.")
            success = click_element(driver, submit_btn)
            if success:
                combined_result["submitted"] = True
                time.sleep(random.uniform(2, 4))
                combined_result["confirmed"] = detect_submission_confirmation(driver)
            return combined_result

        # Look for Next button to advance to next step
        next_btn = find_next_button(driver)
        if next_btn:
            logger.info(f"Next button found on step {step + 1}. Advancing.")
            click_element(driver, next_btn)
            wait_for_next_step(driver)
            continue

        # Neither Submit nor Next found — form may be complete or stuck
        logger.warning(f"No Submit or Next button found on step {step + 1}")
        break

    logger.warning(f"Multi-step form ended without submission after {max_steps} steps")
    return combined_result