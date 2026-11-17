#!/usr/bin/python3
"""
    Job Connector — Navigation and routing layer.
    Takes one job URL from job_discovery.py, navigates to it,
    understands what it is looking at via page_intelligence_agent.py,
    routes it through the correct application flow, and logs the result.
    Central hub that owns all other components.
    Author: Fortune Nwohiri
"""
import time
import random
import json
import os
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from logging_config.logger import get_logger
from job_agent.application_brain import ApplicationBrain
from job_agent.cv_builder import build_cv, get_fallback_resume_path
from job_agent.page_intelligence_agent import read_page, update_jd_extraction_from_page
from job_agent.application_actions import fill_form, handle_multi_step_form
from job_agent.email_sender import EmailSender
from job_agent.oauth_handler import OAuthHandler

logger = get_logger("JobConnector")


# ── JOB DESCRIPTION SELECTORS ─────────────────────────────────────────────────
# Tried in order. First match with meaningful content wins.

JD_SELECTORS = [
    # Greenhouse
    "div#content",
    "div.content",
    "div[class*='job-description']",
    "div[class*='jobDescription']",
    "div[id*='job-description']",
    # Lever
    "div.section-wrapper",
    "div[class*='section']",
    # Ashby
    "div[class*='job-posting']",
    "div[class*='jobPosting']",
    # Wellfound
    "div[class*='job-details']",
    "div[class*='jobDetails']",
    # Workable
    "section[class*='job-description']",
    "div[class*='description']",
    # Generic
    "article",
    "main",
    "div[class*='posting']",
    "div[class*='vacancy']",
    "div[class*='role']",
    "div[class*='position']",
    "div[class*='opportunity']",
    "div[class*='details']",
    "div.job",
    "#job",
    ".job",
]

# ── JOB TITLE SELECTORS ───────────────────────────────────────────────────────

TITLE_SELECTORS = [
    "h1[class*='title']", "h1[class*='job']",
    "h1[class*='position']", "h1[class*='role']",
    "h1", "h2[class*='title']",
    "[data-testid='job-title']",
    "[class*='job-title']", "[class*='jobTitle']",
    "[class*='posting-title']",
]

# ── COMPANY NAME SELECTORS ────────────────────────────────────────────────────

COMPANY_SELECTORS = [
    "[class*='company-name']", "[class*='companyName']",
    "[class*='employer']", "[class*='organization']",
    "[data-testid='company-name']",
    "a[class*='company']",
]

# ── EMAIL DETECTION SELECTORS ─────────────────────────────────────────────────

EMAIL_SELECTORS = [
    "a[href^='mailto:']",
    "a[href*='mailto']",
]


def safe_navigate(driver, url: str, retries: int = 3) -> bool:
    """
    Navigate to a URL with retry logic for network issues.
    Every navigation in the system goes through this method.
    Returns True if navigation succeeded.
    """
    for attempt in range(retries):
        try:
            driver.uc_open_with_reconnect(url)
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(random.uniform(1.5, 3.0))
            logger.info(f"Navigated to: {url}")
            return True
        except Exception as e:
            logger.warning(f"Navigation attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(random.uniform(5, 15))

    logger.error(f"Navigation failed after {retries} attempts: {url}")
    return False


def extract_job_description(driver) -> str:
    """
    Extract the full job description text from the current page.
    Tries multiple CSS selectors covering Greenhouse, Lever, Ashby,
    Wellfound, Workable, and general job boards.
    Returns the longest meaningful text found.
    """
    candidates = []

    for selector in JD_SELECTORS:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for el in elements:
                text = el.text.strip()
                if len(text) > 200:
                    candidates.append(text)
        except Exception:
            continue

    if not candidates:
        # Fallback: get all body text
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text.strip()
            if len(body_text) > 200:
                return body_text[:5000]
        except Exception:
            pass
        return ""

    # Return the longest candidate as it is most likely the full JD
    best = max(candidates, key=len)
    logger.info(f"Job description extracted: {len(best)} characters")
    return best[:5000]


def extract_job_metadata(driver, url: str) -> dict:
    """
    Extract job title and company name from the current page.
    Returns dict with 'title' and 'company' keys.
    Falls back to URL parsing if selectors fail.
    """
    title = ""
    company = ""

    # Try title selectors
    for selector in TITLE_SELECTORS:
        try:
            el = driver.find_element(By.CSS_SELECTOR, selector)
            text = el.text.strip()
            if text and len(text) > 2:
                title = text
                break
        except NoSuchElementException:
            continue
        except Exception:
            continue

    # Try company selectors
    for selector in COMPANY_SELECTORS:
        try:
            el = driver.find_element(By.CSS_SELECTOR, selector)
            text = el.text.strip()
            if text and len(text) > 1:
                company = text
                break
        except NoSuchElementException:
            continue
        except Exception:
            continue

    # Fallback: parse title from page title
    if not title:
        try:
            page_title = driver.title or ""
            if " at " in page_title:
                parts = page_title.split(" at ")
                title = parts[0].strip()
                if not company and len(parts) > 1:
                    company = parts[1].strip().split("|")[0].strip()
            elif " - " in page_title:
                parts = page_title.split(" - ")
                title = parts[0].strip()
                if not company and len(parts) > 1:
                    company = parts[1].strip()
            else:
                title = page_title.split("|")[0].strip()
        except Exception:
            pass

    # Fallback: parse company from URL
    if not company:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            netloc = parsed.netloc.replace("www.", "")
            path_parts = parsed.path.strip("/").split("/")
            if "greenhouse.io" in netloc and path_parts:
                company = path_parts[0].replace("-", " ").title()
            elif "lever.co" in netloc and path_parts:
                company = path_parts[0].replace("-", " ").title()
            elif "ashbyhq.com" in netloc and path_parts:
                company = path_parts[0].replace("-", " ").title()
            else:
                company = netloc.split(".")[0].title()
        except Exception:
            pass

    logger.info(f"Metadata extracted: title='{title}' company='{company}'")
    return {"title": title, "company": company}


def extract_contact_email(driver) -> str:
    """
    Extract the contact email address from an email-only job listing.
    Returns the email address string or empty string if not found.
    """
    for selector in EMAIL_SELECTORS:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for el in elements:
                href = el.get_attribute("href") or ""
                if "mailto:" in href:
                    email = href.replace("mailto:", "").split("?")[0].strip()
                    if "@" in email:
                        logger.info(f"Contact email found: {email}")
                        return email
        except Exception:
            continue

    # Fallback: search body text for email pattern
    try:
        import re
        body_text = driver.find_element(By.TAG_NAME, "body").text
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        matches = re.findall(email_pattern, body_text)
        # Filter out generic emails and prefer careers/jobs emails
        for match in matches:
            lower = match.lower()
            if any(kw in lower for kw in ["career", "job", "hire", "recruit", "apply", "hr", "talent"]):
                logger.info(f"Contact email found via pattern: {match}")
                return match
        if matches:
            logger.info(f"Contact email found via pattern: {matches[0]}")
            return matches[0]
    except Exception:
        pass

    logger.warning("No contact email found on page")
    return ""


def check_and_handle_session(
    driver,
    platform_key: str,
    platform_sessions: dict,
    agent_profile: dict,
) -> bool:
    """
    For session-required platforms check if the session is still alive.
    If expired calls OAuthHandler.reauthenticate() to handle
    Continue with Google automatically.
    Returns True if session is active or restored, False if failed.
    """
    oauth_handler = OAuthHandler()
    gmail_account = agent_profile.get("gmail_account", "")

    if oauth_handler.is_session_expired(driver, platform_key):
        logger.info(f"Session expired for {platform_key}. Attempting reauth.")
        success = oauth_handler.reauthenticate(driver, platform_key, gmail_account)
        if success:
            logger.info(f"Session restored for {platform_key}")
            return True
        else:
            logger.error(f"Session reauth failed for {platform_key}")
            return False

    logger.info(f"Session active for {platform_key}")
    return True


def handle_email_application(
    job: dict,
    jd_extraction: dict,
    cv_result: dict,
    agent_profile: dict,
    brain: ApplicationBrain,
) -> dict:
    """
    Handle email-only job applications.
    Generates subject and body via Agent 7, attaches the targeted CV PDF,
    sends via SMTP.

    Returns dict with success bool and method used.
    """
    logger.info(f"Email application: {job.get('url')}")

    contact_email = job.get("contact_email", "")
    if not contact_email:
        logger.error("No contact email available for email application")
        return {"success": False, "method": "email", "reason": "no_contact_email"}

    # Generate email subject and body via Agent 7
    email_content = brain.generate_email_body(
        jd_extraction=jd_extraction,
        cv_text=cv_result.get("cv_text", ""),
    )

    subject = email_content.get("subject", "")
    body = email_content.get("body", "")

    if not subject or not body:
        logger.error("Email body generation failed")
        return {"success": False, "method": "email", "reason": "email_generation_failed"}

    # Get CV path — always use targeted CV for emails, never fallback
    cv_path = cv_result.get("cv_path", "")
    if not cv_path or not os.path.exists(cv_path):
        logger.error("No CV PDF available for email attachment")
        return {"success": False, "method": "email", "reason": "no_cv_pdf"}

    # Send via SMTP
    email_sender = EmailSender()
    success = email_sender.send_application(
        to_email=contact_email,
        subject=subject,
        body=body,
        resume_path=cv_path,
    )

    if success:
        logger.info(f"Email application sent to {contact_email}: '{subject}'")
        return {"success": True, "method": "email"}
    else:
        logger.error(f"Email send failed to {contact_email}")
        return {"success": False, "method": "email", "reason": "smtp_failed"}


def handle_form_application(
    driver,
    job: dict,
    page_result: dict,
    jd_extraction: dict,
    cv_result: dict,
    agent_profile: dict,
    brain: ApplicationBrain,
) -> dict:
    """
    Handle job applications that go through a web form.
    Receives the page intelligence result which already has the field map.
    Routes to handle_multi_step_form() with all required context.

    Returns dict with success bool, method, and fill statistics.
    """
    logger.info(f"Form application: {job.get('url')}")

    field_map = page_result.get("field_map", [])
    cv_path = cv_result.get("cv_path", "")
    cv_text = cv_result.get("cv_text", "")

    if not field_map:
        logger.warning("Empty field map — cannot fill form")
        return {"success": False, "method": "form", "reason": "empty_field_map"}

    if not cv_path or not os.path.exists(cv_path):
        logger.warning("No CV PDF, using fallback resume")
        cv_path = get_fallback_resume_path(agent_profile)

    if not cv_path:
        logger.error("No resume available — cannot apply")
        return {"success": False, "method": "form", "reason": "no_resume"}

    # Run the form fill
    fill_result = handle_multi_step_form(
        driver=driver,
        field_map=field_map,
        agent_profile=agent_profile,
        jd_extraction=jd_extraction,
        cv_path=cv_path,
        brain=brain,
        cv_text=cv_text,
        max_steps=8,
    )

    success = fill_result.get("submitted", False)
    confirmed = fill_result.get("confirmed", False)

    logger.info(
        f"Form application {'submitted' if success else 'failed'}: "
        f"confirmed={confirmed}, "
        f"fields_filled={fill_result.get('fields_filled', 0)}, "
        f"honeypots_avoided={fill_result.get('honeypots_avoided', 0)}"
    )

    return {
        "success": success,
        "confirmed": confirmed,
        "method": "form",
        "fill_result": fill_result,
    }


def process_job_url(
    driver,
    job: dict,
    agent_profile: dict,
    platform_sessions: dict,
    brain: ApplicationBrain,
    state_path: str = "./state/applied_jobs.json",
) -> dict:
    """
    Master method. Takes one job dict from job_discovery.py and runs
    the complete pipeline for that listing.

    Flow:
    1. Navigate to URL
    2. read_page() — classify and map fields
    3. Extract JD and metadata
    4. application_brain.process_listing() — score and extract
    5. cv_builder.build_cv() — generate targeted PDF
    6. Route to email or form application
    7. Log result

    Returns:
    {
        "job_id": str,
        "url": str,
        "success": bool,
        "method": str,
        "score": int,
        "skip_reason": str,
        "cv_gap_report": str,
        "honeypots_detected": int,
    }
    """
    url = job.get("url", "")
    job_id = job.get("job_id", "")
    platform_type = job.get("platform_type", "unknown")

    logger.info("=" * 70)
    logger.info(f"Processing: {url}")
    logger.info(f"Platform type: {platform_type}")
    logger.info("=" * 70)

    result = {
        "job_id": job_id,
        "url": url,
        "success": False,
        "method": "",
        "score": 0,
        "skip_reason": "",
        "cv_gap_report": "",
        "honeypots_detected": 0,
    }

    # ── STEP 1: Navigate ──────────────────────────────────────────────────────
    if not safe_navigate(driver, url):
        result["skip_reason"] = "navigation_failed"
        brain.record_failed(job, 0, "navigation_failed")
        return result

    # ── STEP 2: Session check for login-required platforms ────────────────────
    if platform_type == "session":
        # Detect which platform from URL
        url_lower = url.lower()
        platform_key = None
        for key in platform_sessions:
            platform_data = platform_sessions.get(key, {})
            login_url = platform_data.get("login_url", "")
            if any(
                domain in url_lower
                for domain in [key, login_url.split("//")[-1].split("/")[0]]
            ):
                platform_key = key
                break

        if platform_key:
            session_ok = check_and_handle_session(
                driver, platform_key, platform_sessions, agent_profile
            )
            if not session_ok:
                result["skip_reason"] = f"session_expired_{platform_key}"
                brain.record_manual_queue(job, 0, {}, "", f"session_expired_{platform_key}")
                return result

    # ── STEP 3: Read and classify the page ───────────────────────────────────
    page_result = read_page(driver, url)
    skip_reason = page_result.get("skip_reason", "")
    honeypots = page_result.get("honeypots_detected", 0)
    result["honeypots_detected"] = honeypots

    if skip_reason:
        logger.warning(f"Page intelligence skip: {skip_reason}")

        # Cloudflare and captcha go to manual queue with pre-generated CV
        if skip_reason in ["cloudflare_wall", "captcha_detected", "login_wall"]:
            result["skip_reason"] = skip_reason
            brain.record_manual_queue(job, 0, {}, "", skip_reason)
            return result

        # Everything else is a hard skip
        result["skip_reason"] = skip_reason
        brain._record(job, "skipped", 0, {}, {}, skip_reason)
        return result

    if not page_result.get("ready_to_fill") and page_result.get("page_type") != "job_listing":
        logger.warning("Page not ready to fill and not a listing page")
        result["skip_reason"] = "page_not_ready"
        brain._record(job, "skipped", 0, {}, {}, "page_not_ready")
        return result

    # ── STEP 4: Extract job description and metadata ──────────────────────────
    description = extract_job_description(driver)
    metadata = extract_job_metadata(driver, url)

    # Enrich the job dict with extracted metadata
    job["title"] = job.get("title") or metadata.get("title", "Unknown")
    job["company"] = job.get("company") or metadata.get("company", "Unknown")

    logger.info(f"Job: '{job['title']}' @ {job['company']}")

    # ── STEP 5: Score and extract JD via ApplicationBrain ────────────────────
    # Sleep before scorer to prevent back-to-back AI calls from dropping
    time.sleep(random.uniform(4.0, 7.0))
    listing_result = brain.process_listing(
        job=job,
        description=description,
    )

    score = listing_result.get("score", 0)
    result["score"] = score

    if not listing_result.get("proceed"):
        result["skip_reason"] = listing_result.get("skip_reason", "low_score")
        return result

    jd_extraction = listing_result.get("jd_extraction", {})

    # Update JD extraction with what page intelligence found on the actual form
    jd_extraction = update_jd_extraction_from_page(page_result, jd_extraction)

    # ── STEP 6: Detect email-only application ────────────────────────────────
    is_email_only = jd_extraction.get("application_method") == "email"
    contact_email = jd_extraction.get("contact_email", "")

    # Try to extract email from page if JD extraction missed it
    if not contact_email:
        contact_email = extract_contact_email(driver)
        if contact_email:
            jd_extraction["contact_email"] = contact_email
            if not is_email_only:
                is_email_only = True

    # ── STEP 7: Build targeted CV ─────────────────────────────────────────────
    logger.info("Building targeted CV")
    cv_result = build_cv(
        jd_extraction=jd_extraction,
        job_id=job_id,
        max_retries=2,
    )

    result["cv_gap_report"] = cv_result.get("gap_report", "")

    if not cv_result.get("success"):
        logger.warning("CV build failed — using fallback resume")
        fallback = get_fallback_resume_path(agent_profile)
        cv_result = {
            "success": bool(fallback),
            "cv_text": "",
            "cv_path": fallback,
            "gap_report": "CV builder failed",
            "warnings": [],
            "word_count": 0,
        }

        if not fallback:
            result["skip_reason"] = "cv_build_failed_no_fallback"
            brain.record_failed(job, score, "cv_build_failed_no_fallback")
            return result

    # ── STEP 8: Route to correct application method ───────────────────────────
    if is_email_only and contact_email:
        logger.info(f"Routing to email application: {contact_email}")
        job["contact_email"] = contact_email
        app_result = handle_email_application(
            job=job,
            jd_extraction=jd_extraction,
            cv_result=cv_result,
            agent_profile=agent_profile,
            brain=brain,
        )
    else:
        logger.info("Routing to form application")
        app_result = handle_form_application(
            driver=driver,
            job=job,
            page_result=page_result,
            jd_extraction=jd_extraction,
            cv_result=cv_result,
            agent_profile=agent_profile,
            brain=brain,
        )

    # ── STEP 9: Log result ────────────────────────────────────────────────────
    success = app_result.get("success", False)
    method = app_result.get("method", "unknown")
    result["success"] = success
    result["method"] = method

    fill_result = app_result.get("fill_result", {})

    if success:
        brain.record_applied(
            job=job,
            score=score,
            score_data=listing_result.get("score_data", {}),
            jd_extraction=jd_extraction,
            apply_method=method,
            cv_gap_report=cv_result.get("gap_report", ""),
            had_cover_letter=fill_result.get("cover_letter_generated", False),
            had_custom_questions=fill_result.get("custom_questions_answered", 0) > 0,
            honeypots_detected=honeypots,
        )
        logger.info(f"Application SUCCESS: '{job['title']}' @ {job['company']}")
    else:
        skip_reason = app_result.get("reason", "application_failed")
        result["skip_reason"] = skip_reason
        brain.record_failed(job, score, skip_reason)
        logger.warning(f"Application FAILED: '{job['title']}' @ {job['company']} — {skip_reason}")

    return result


def run_application_loop(
    main_driver,
    discovered_jobs: list,
    agent_profile: dict,
    platform_sessions: dict,
    state_path: str = "./state/applied_jobs.json",
):
    """
    Outer loop called from run_job_session() in agent_main.py.

    Iterates through every job URL from job_discovery.py.
    For each job:
    - Decides which driver to use (per-application or session)
    - Calls micro_warmup() on the application driver
    - Calls process_job_url()
    - Calls wait_to_human_pace() before submit
    - Calls browse_between_applications() after submit
    - Calls cleanup_application_driver() after the application closes
    - Enforces max_applications_per_run limit

    Returns session summary dict from ApplicationBrain.
    """
    from agent_main import (
        setup_application_driver,
        setup_session_driver,
        cleanup_application_driver,
        micro_warmup,
        browse_between_applications,
        get_application_duration,
        wait_to_human_pace,
        detect_platform,
        LOGIN_REQUIRED_PLATFORMS,
    )
    from Agents.google_connector import GoogleConnector

    brain = ApplicationBrain(agent_profile)
    max_applications = agent_profile.get("max_applications_per_run", 20)
    applications_this_run = 0
    connector = GoogleConnector()

    logger.info("=" * 70)
    logger.info(f"APPLICATION LOOP: {len(discovered_jobs)} jobs to process")
    logger.info(f"Max applications this run: {max_applications}")
    logger.info("=" * 70)

    for job in discovered_jobs:
        if applications_this_run >= max_applications:
            logger.info(f"Reached max applications ({max_applications}). Stopping.")
            break

        url = job.get("url", "")
        platform_type = job.get("platform_type", "unknown")
        job_id = job.get("job_id", "")

        # Skip already seen jobs
        if brain.already_seen(job_id):
            logger.info(f"Already seen: {url}")
            continue

        logger.info(f"Application {applications_this_run + 1}/{max_applications}: {url}")

        app_driver = None
        app_profile = None
        app_profile_dir = None
        is_session = False

        try:
            # ── Boot application driver ───────────────────────────────────────
            if platform_type == "session":
                platform_key = detect_platform(url)
                if platform_key not in platform_sessions:
                    logger.warning(f"No session config for platform: {platform_key}")
                    brain._record(job, "skipped", 0, {}, {}, f"no_session_{platform_key}")
                    continue

                app_driver, app_profile, app_profile_dir = setup_session_driver(
                    platform_key, platform_sessions
                )
                is_session = True
            else:
                app_driver, app_profile, app_profile_dir, device = setup_application_driver()
                is_session = False

            if not app_driver:
                logger.error("Failed to boot application driver")
                brain.record_failed(job, 0, "driver_boot_failed")
                continue

            # ── Micro warmup ──────────────────────────────────────────────────
            micro_warmup(app_driver)

            # ── Set application time target ───────────────────────────────────
            target_duration = get_application_duration(agent_profile)
            start_time = time.time()

            # ── Process the job ───────────────────────────────────────────────
            result = process_job_url(
                driver=app_driver,
                job=job,
                agent_profile=agent_profile,
                platform_sessions=platform_sessions,
                brain=brain,
                state_path=state_path,
            )

            # ── Human pace before submit ──────────────────────────────────────
            # wait_to_human_pace scrolls the page naturally until the
            # target duration is reached before the form submits.
            # It is called here after process_job_url returns because
            # the submission happens inside process_job_url.
            # For next iteration timing we still enforce the gap.
            wait_to_human_pace(
                app_driver,
                start_time,
                target_duration,
                connector,
            )

            if result.get("success") or result.get("score", 0) >= agent_profile.get("min_score_threshold", 72):
                applications_this_run += 1

            # ── Between application browse ────────────────────────────────────
            browse_between_applications(app_driver, agent_profile)

        except Exception as e:
            logger.error(f"Application loop error for {url}: {e}", exc_info=True)
            brain.record_failed(job, 0, f"loop_error: {str(e)[:100]}")

        finally:
            # ── Cleanup application driver ────────────────────────────────────
            if app_driver:
                cleanup_application_driver(
                    app_driver,
                    app_profile,
                    app_profile_dir,
                    is_session=is_session,
                )

    logger.info("=" * 70)
    logger.info(f"APPLICATION LOOP COMPLETE: {applications_this_run} applications submitted")
    logger.info("=" * 70)

    return brain.get_session_summary()