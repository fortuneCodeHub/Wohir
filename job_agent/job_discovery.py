#!/usr/bin/python3
"""
    Job Discovery — Searches Google for job listing URLs using existing
    GoogleConnector and EnhancedGoogleBrain infrastructure.
    Returns deduplicated list of job URLs to run_job_session() in agent_main.py.
    Author: Fortune Nwohiri
"""
import time
import random
import hashlib
import json
import os
import re
import requests
from urllib.parse import urlparse, parse_qs, unquote
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from logging_config.logger import get_logger
from Agents.google_connector import GoogleConnector
from Agents.google_actions import GoogleActions
from job_agent.ai_client import call_ai_safe

logger = get_logger("JobDiscovery")


DIRECT_PLATFORMS = [
    "boards.greenhouse.io",
    "job-boards.greenhouse.io",
    "jobs.lever.co",
    "jobs.ashbyhq.com",
    "smartrecruiters.com",
    "remoteok.com",
    "himalayas.app",
    "remotive.com",
    "weworkremotely.com",
    "jobgether.com",
    "4dayweek.io",
    "apply.workable.com",
]

SESSION_PLATFORMS = [
    "wellfound.com",
    "contra.com",
    "jobs.workable.com",
]

SKIP_PLATFORMS = [
    "linkedin.com",
    "indeed.com",
    "myworkdayjobs.com",
    "workday.com",
    "taleo.net",
    "icims.com",
    "successfactors.com",
]

MANUAL_QUEUE_PLATFORMS = [
    "workday.com",
    "myworkdayjobs.com",
    "taleo.net",
    "icims.com",
]

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

# URL path patterns that strongly indicate a single job description
# rather than a category or list page
JOB_DESCRIPTION_PATH_PATTERNS = [
    r"/jobs/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+/\d+",   # greenhouse: /nortal/jobs/5287641007
    r"/jobs/\d+",                                    # generic: /jobs/12345
    r"/job/[a-zA-Z0-9_-]+-\d+",                     # lever, ashby
    r"/job/[a-zA-Z0-9_-]{8,}",                      # 4dayweek slugs with hash
    r"/apply/[a-zA-Z0-9_-]+",                        # workable apply paths
    r"/o/[a-zA-Z0-9_-]+/details",                   # smartrecruiters
    r"/posting/[a-zA-Z0-9_-]+",                     # various ATS
    r"/careers/[a-zA-Z0-9_-]+/\d+",                 # generic career pages
    r"/position/[a-zA-Z0-9_-]+",
    r"/vacancy/[a-zA-Z0-9_-]+",
    r"/opening/[a-zA-Z0-9_-]+",
]

# URL path patterns that strongly indicate a category or list page
JOB_LIST_PATH_PATTERNS = [
    r"/jobs/countries/",
    r"/jobs/worldwide/",
    r"/jobs/remote/",
    r"/jobs/[a-z-]+$",             # ends at a word with no ID
    r"/remote-jobs/",
    r"/engineering-jobs",
    r"/developer-jobs",
    r"/search\?",
    r"/jobs\?",
    r"\?page=\d+$",                # pagination
    r"/jobs/$",
]


def make_url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:16]


def load_applied_state(state_path: str = "./state/applied_jobs.json") -> set:
    if not os.path.exists(state_path):
        return set()

    try:
        with open(state_path, "r") as f:
            state = json.load(f)

        seen = set()
        for entry in state.get("applied", []):
            seen.add(entry.get("job_id", ""))
        for entry in state.get("skipped", []):
            seen.add(entry.get("job_id", ""))
        for entry in state.get("manual_queue", []):
            seen.add(entry.get("job_id", ""))
        seen.discard("")
        return seen

    except Exception as e:
        logger.error(f"Failed to load state: {e}")
        return set()


def classify_url(url: str) -> str:
    url_lower = url.lower()

    for platform in SKIP_PLATFORMS:
        if platform in url_lower:
            return "skip"

    for platform in MANUAL_QUEUE_PLATFORMS:
        if platform in url_lower:
            return "manual_queue"

    for platform in SESSION_PLATFORMS:
        if platform in url_lower:
            return "session"

    for platform in DIRECT_PLATFORMS:
        if platform in url_lower:
            return "direct"

    return "unknown"


def is_valid_job_url(url: str) -> bool:
    if not url or not url.startswith("http"):
        return False

    parsed = urlparse(url)
    skip_domains = [
        "googleapis.com",
        "gstatic.com",
        "youtube.com",
        "facebook.com",
        "twitter.com",
        "reddit.com",
        "quora.com",
    ]
    for domain in skip_domains:
        if domain in parsed.netloc:
            return False

    if len(parsed.path) < 5:
        return False

    return True


def is_error_url(url: str) -> bool:
    """
    Catch obvious error pages before wasting an AI call or navigation on them.
    """
    url_lower = url.lower()
    error_signals = ["error=true", "error=1", "/404", "/not-found", "?error=", "#error"]
    return any(signal in url_lower for signal in error_signals)


def is_job_description_url(url: str) -> str:
    """
    Layer 1: URL-only analysis.
    Uses regex patterns first for zero-cost fast path.
    Falls back to AI for ambiguous URLs.
    Returns: 'description' | 'list' | 'unknown'
    """
    parsed = urlparse(url)
    path = parsed.path.lower()
    full = url.lower()

    # Fast path: unambiguous regex matches
    for pattern in JOB_DESCRIPTION_PATH_PATTERNS:
        if re.search(pattern, path):
            return "description"

    for pattern in JOB_LIST_PATH_PATTERNS:
        if re.search(pattern, full):
            return "list"

    # Ambiguous — ask AI
    try:

        prompt = f"""You are helping a job application bot classify a URL.

URL: {url}

Based on this URL alone, classify it as one of:
- "description" — this URL points to a single job listing (one specific role at one company)
- "list" — this URL points to a page listing multiple jobs (category page, search results, company jobs page)
- "unknown" — cannot tell from the URL alone

Consider:
- URLs with numeric IDs or long unique slugs at the end are usually single job descriptions
- URLs with words like /jobs/, /remote/, /engineering/, /search, or pagination are usually list pages
- URLs with a company name followed by a job slug are usually descriptions

Return ONLY one word: description, list, or unknown. Nothing else."""

        result = call_ai_safe(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            agent_type="classifier",
        ).strip().lower()

        if result in ["description", "list", "unknown"]:
            return result
        return "unknown"

    except Exception as e:
        logger.debug(f"Layer 1 AI fallback failed: {e}")
        return "unknown"

def classify_page_lightweight(driver, url: str) -> str:
    """
    Layer 2: Full page content analysis via AI.
    Reads title, body text, forms, inputs, buttons, h1s, and all anchor texts.
    Sends everything to AI for classification.
    Returns: job_form | job_description | job_listing | not_a_job |
             cloudflare | captcha | login_wall | unknown
    """
    try:

        # Collect page signals
        page_title = driver.title or ""

        try:
            visible_text = driver.find_element(By.TAG_NAME, "body").text[:3000]
        except Exception:
            visible_text = ""

        # Check for Cloudflare before anything else
        if any(signal in page_title.lower() for signal in CLOUDFLARE_TITLE_SIGNALS):
            return "cloudflare"

        forms = driver.find_elements(By.TAG_NAME, "form")
        inputs = driver.find_elements(By.TAG_NAME, "input")
        textareas = driver.find_elements(By.TAG_NAME, "textarea")
        buttons = driver.find_elements(By.TAG_NAME, "button")
        h1_elements = driver.find_elements(By.TAG_NAME, "h1")
        h2_elements = driver.find_elements(By.TAG_NAME, "h2")

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

        h2_texts = []
        for h2 in h2_elements[:8]:
            try:
                text = h2.text.strip()
                if text:
                    h2_texts.append(text)
            except Exception:
                continue

        # Collect anchor texts to detect list patterns
        anchors = driver.find_elements(By.CSS_SELECTOR, "a[href]")
        anchor_texts = []
        for a in anchors[:30]:
            try:
                text = a.text.strip()
                if text and len(text) > 2:
                    anchor_texts.append(text)
            except Exception:
                continue

        prompt = f"""You are helping a job application bot classify a webpage.

URL: {url}
PAGE TITLE: {page_title}

PAGE TEXT (first 3000 chars):
{visible_text}

PAGE STRUCTURE:
- Forms on page: {len(forms)}
- Input fields: {len(inputs)}
- Textareas: {len(textareas)}
- H1 headings: {h1_texts}
- H2 headings: {h2_texts[:5]}
- Button texts: {button_texts}
- Link texts (sample): {anchor_texts[:20]}

Classify this page as exactly one of these labels:

- "job_description" — a single job listing page showing one specific role with its requirements, responsibilities, and qualifications. No application form present yet.
- "job_form" — a job application form page where the candidate fills in their details and submits. Has input fields for name, email, resume upload etc.
- "job_listing" — a page showing multiple job openings. Could be a company jobs page, a job board category, or search results with multiple roles listed.
- "not_a_job" — not related to job applications at all. Could be a homepage, blog post, news article, product page etc.
- "cloudflare" — a Cloudflare challenge or bot detection page.
- "captcha" — a CAPTCHA challenge page.
- "login_wall" — a page requiring login before showing job content.
- "unknown" — genuinely cannot tell.

Return ONLY the label. Nothing else."""

        result = call_ai_safe(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            agent_type="classifier",
        ).strip().lower()

        valid_labels = [
            "job_description", "job_form", "job_listing",
            "not_a_job", "cloudflare", "captcha", "login_wall", "unknown"
        ]

        if result in valid_labels:
            logger.info(f"Agent 1 during discovery: {result} (confidence: 100) obstruction: none — {url[:60]}")
            return result

        # AI returned something unexpected — try to map it
        if "form" in result:
            return "job_form"
        if "listing" in result or "list" in result or "multiple" in result:
            return "job_listing"
        if "description" in result or "single" in result:
            return "job_description"
        if "cloudflare" in result or "challenge" in result:
            return "cloudflare"
        if "login" in result or "sign in" in result:
            return "login_wall"
        if "not" in result or "none" in result:
            return "not_a_job"

        return "unknown"

    except Exception as e:
        logger.warning(f"Layer 2 AI classification failed: {e}")
        return "unknown"

def is_cloudflare_page(driver) -> bool:
    """
    Pure DOM check for Cloudflare challenge. No AI call. Zero cost.
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


def human_wander(duration_seconds: float):
    """
    Move the OS cursor organically for duration_seconds.
    Builds cursor entropy that Cloudflare measures before the click.
    """
    import pyautogui
    import screeninfo

    try:
        screen = screeninfo.get_monitors()[0]
        screen_w = screen.width
        screen_h = screen.height
    except Exception:
        screen_w = 1920
        screen_h = 1080

    x = random.randint(screen_w // 4, screen_w * 3 // 4)
    y = random.randint(screen_h // 4, screen_h * 3 // 4)
    pyautogui.moveTo(x, y, duration=random.uniform(0.4, 0.8))

    deadline = time.time() + duration_seconds
    while time.time() < deadline:
        dx = random.randint(-180, 180)
        dy = random.randint(-120, 120)
        new_x = max(50, min(screen_w - 50, x + dx))
        new_y = max(50, min(screen_h - 50, y + dy))
        duration = random.uniform(0.3, 1.4)
        pyautogui.moveTo(new_x, new_y, duration=duration)
        x, y = new_x, new_y
        if random.random() < 0.3:
            time.sleep(random.uniform(0.5, 2.0))
        else:
            time.sleep(random.uniform(0.05, 0.3))


def drift_toward_checkbox(steps: int = 6):
    """
    Drift the OS cursor toward where the Turnstile checkbox typically sits
    over several moves so the approach is not a straight line.
    """
    import pyautogui

    target_x = random.randint(200, 350)
    target_y = random.randint(400, 550)
    current_x, current_y = pyautogui.position()

    for i in range(steps):
        progress = (i + 1) / steps
        next_x = int(current_x + (target_x - current_x) * progress + random.randint(-30, 30))
        next_y = int(current_y + (target_y - current_y) * progress + random.randint(-20, 20))
        duration = random.uniform(0.3, 0.8) + (progress * 0.4)
        pyautogui.moveTo(next_x, next_y, duration=duration)
        time.sleep(random.uniform(0.2, 0.6))

    time.sleep(random.uniform(0.8, 1.5))


def try_cloudflare_bypass(driver) -> bool:
    """
    Attempt Cloudflare Turnstile bypass using uc_gui_click_captcha().
    6-phase sequence: iframe wait, Selenium body move, OS cursor wander,
    drift toward checkbox, pre-click pause, click.
    One attempt only. Returns True if challenge cleared.
    """
    logger.info("Cloudflare wall detected — attempting bypass via uc_gui_click_captcha")

    try:
        # Phase 1: wait for Turnstile iframe to fully render
        wait_secs = random.uniform(8.0, 14.0)
        logger.info(f"  Phase 1: waiting {wait_secs:.1f}s for iframe to render...")
        time.sleep(wait_secs)

        # Phase 2: move Selenium mouse to body — establishes cursor presence on the page
        try:
            body = driver.find_element(By.TAG_NAME, "body")
            ActionChains(driver).move_to_element(body).perform()
            logger.info("  Phase 2: Selenium cursor moved to body.")
            time.sleep(random.uniform(1.0, 2.0))
        except Exception as e:
            logger.warning(f"  Body move failed: {e}")

        # Phase 3: organic OS-level cursor wander — builds entropy Cloudflare measures
        wander_secs = random.uniform(20.0, 35.0)
        logger.info(f"  Phase 3: organic cursor wander for {wander_secs:.1f}s...")
        try:
            human_wander(wander_secs)
        except Exception as e:
            logger.warning(f"  Wander failed: {e}")

        # Phase 4: drift toward where the Turnstile checkbox usually sits
        logger.info("  Phase 4: drifting toward checkbox area...")
        try:
            drift_toward_checkbox(steps=random.randint(5, 8))
        except Exception as e:
            logger.warning(f"  Drift failed: {e}")

        # Phase 5: final pause before the click
        pre_click_pause = random.uniform(1.2, 2.5)
        logger.info(f"  Phase 5: pre-click pause {pre_click_pause:.1f}s...")
        time.sleep(pre_click_pause)

        # Phase 6: real OS cursor click on the Turnstile checkbox
        logger.info("  Phase 6: calling driver.uc_gui_click_captcha()...")
        driver.uc_gui_click_captcha()

        post_sleep = random.uniform(4.0, 7.0)
        logger.info(f"  Sleeping {post_sleep:.1f}s after captcha click...")
        time.sleep(post_sleep)

        if is_cloudflare_page(driver):
            logger.warning("Still on Cloudflare challenge after bypass attempt")
            return False

        logger.info(f"Cloudflare bypass succeeded — now on: {driver.current_url[:80]}")
        return True

    except Exception as e:
        logger.error(f"Cloudflare bypass failed: {e}")
        return False



def crawl_listing_page(driver, list_url: str, seen_urls: set, max_jobs: int = 8) -> list:
    """
    Navigate to a job list page and extract individual job description URLs.
    Uses AI to read the full page and identify clickable job links.
    """
    logger.info(f"Crawling list page for individual jobs: {list_url[:80]}")
    found_jobs = []
    page_url = driver.current_url

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(random.uniform(2.0, 3.5))

        # Scroll to load lazy content
        try:
            actions = GoogleActions()
            actions.scroll_down(driver, max_scrolls=3, scroll_duration=random.uniform(4, 8))
            time.sleep(random.uniform(1.5, 2.5))
        except Exception:
            pass

        # Dump full page text
        try:
            page_text = driver.find_element(By.TAG_NAME, "body").text[:6000]
        except Exception:
            logger.warning("Could not read page body")
            return []

        # Collect all anchor tags with hrefs
        all_anchors = driver.find_elements(By.CSS_SELECTOR, "a[href]")
        anchor_data = []
        for a in all_anchors:
            try:
                href = a.get_attribute("href") or ""
                text = a.text.strip()
                if href and len(text) > 2:
                    anchor_data.append({"href": href, "text": text})
            except Exception:
                continue

        if not anchor_data:
            logger.warning("No anchor tags found on page")
            return []

        anchor_summary = "\n".join(
            f"- TEXT: {a['text'][:80]} | HREF: {a['href'][:120]}"
            for a in anchor_data[:80]
        )

        prompt = f"""You are helping a job application bot identify individual job listing links on a webpage.

PAGE URL: {list_url}

PAGE TEXT (first 2000 chars):
{page_text[:2000]}

ANCHOR TAGS ON PAGE (text | href):
{anchor_summary}

Your task: identify which of these anchor tags are links to individual job listings (single job descriptions, not category pages, not pagination, not navigation).

Return ONLY a JSON array of href strings for the job listing links. Maximum {max_jobs} items. If none qualify, return an empty array [].

Example output format:
["https://jobs.lever.co/company/abc123", "https://boards.greenhouse.io/company/jobs/456"]

Return only the JSON array, nothing else."""

        raw = call_ai_safe(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            json_response=False,
            agent_type="classifier",
        )

        if not raw:
            logger.warning("AI returned empty response for crawl classification")
            return []

        # Parse the JSON array
        job_urls = []
        try:
            clean = re.sub(r"```[a-z]*\n?", "", raw).strip()
            job_urls = json.loads(clean)
            if not isinstance(job_urls, list):
                job_urls = []
        except Exception as parse_err:
            logger.warning(f"AI response parse failed: {parse_err} — raw: {raw[:200]}")
            return []

        logger.info(f"AI identified {len(job_urls)} job links on list page")

        # Click each AI-identified link, read the final URL, go back
        for href in job_urls[:max_jobs]:
            if len(found_jobs) >= max_jobs:
                break

            if not href or not is_valid_job_url(href):
                continue

            url_hash = make_url_hash(href)
            if url_hash in seen_urls:
                logger.debug(f"  Already seen: {href[:60]}")
                continue

            # Find the matching anchor element
            target_el = None
            for a in all_anchors:
                try:
                    el_href = a.get_attribute("href") or ""
                    if el_href == href or el_href.rstrip("/") == href.rstrip("/"):
                        target_el = a
                        break
                except Exception:
                    continue

            try:
                if target_el:
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'});", target_el
                    )
                    time.sleep(random.uniform(0.5, 1.2))
                    target_el.click()
                else:
                    driver.get(href)

                time.sleep(random.uniform(2.5, 4.0))

                if is_cloudflare_page(driver):
                    bypass_ok = try_cloudflare_bypass(driver)
                    if not bypass_ok:
                        logger.debug(f"  Cloudflare on job page, skipping: {href[:60]}")
                        driver.back()
                        time.sleep(random.uniform(1.5, 2.5))
                        continue
                    time.sleep(random.uniform(1.5, 2.5))

                final_url = driver.current_url

                if is_error_url(final_url):
                    logger.info(f"  Error page, skipping: {final_url[:60]}")
                else:
                    found_jobs.append(final_url)
                    seen_urls.add(make_url_hash(final_url))
                    logger.info(f"  Found job description: {final_url[:80]}")

            except Exception as e:
                logger.debug(f"  Crawl click failed: {e}")

            finally:
                try:
                    driver.back()
                    time.sleep(random.uniform(1.5, 2.5))

                    if driver.current_url != page_url and "google.com" not in driver.current_url:
                        driver.get(page_url)
                        time.sleep(random.uniform(2.0, 3.0))

                    WebDriverWait(driver, 8).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                except Exception:
                    try:
                        driver.get(page_url)
                        time.sleep(random.uniform(2.0, 3.0))
                    except Exception:
                        pass

    except Exception as e:
        logger.error(f"crawl_listing_page failed: {e}")

    logger.info(f"Crawl complete: {len(found_jobs)} job descriptions extracted from {list_url[:60]}")
    return found_jobs


def resolve_google_redirect(href: str) -> str:
    if not href:
        return href

    parsed = urlparse(href)

    if "google.com" in parsed.netloc:
        qs = parse_qs(parsed.query)
        if "q" in qs:
            return unquote(qs["q"][0])
        if "url" in qs:
            return unquote(qs["url"][0])

    return href


def extract_urls_from_search_results(
    driver,
    max_results: int = 10,
    seen_this_run: set = None,
) -> list:
    """
    Click each h3 on the Google results page, read the destination URL,
    classify it, and if it is a list page crawl it for individual job
    description URLs before returning.
    """
    if seen_this_run is None:
        seen_this_run = set()

    urls = []

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div#search"))
        )
        time.sleep(random.uniform(1.5, 3.0))

        search_results_url = driver.current_url
        result_links = driver.find_elements(By.CSS_SELECTOR, "h3")
        logger.info(f"Found {len(result_links)} result titles on page")

        for link in result_links:
            if len(urls) >= max_results:
                break

            try:
                title_text = link.text.strip().lower()
                if not title_text:
                    continue

                skip = False
                for platform in SKIP_PLATFORMS:
                    platform_name = platform.split(".")[0]
                    if platform_name in title_text:
                        logger.debug(f"  Pre-click skip: {title_text[:50]}")
                        skip = True
                        break
                if skip:
                    continue

                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", link
                )
                time.sleep(random.uniform(0.5, 1.2))
                link.click()
                time.sleep(random.uniform(2.5, 4.0))

                # Handle Cloudflare immediately after landing
                if is_cloudflare_page(driver):
                    bypass_ok = try_cloudflare_bypass(driver)
                    if not bypass_ok:
                        logger.info(f"  Cloudflare bypass failed — skipping")
                        continue
                    time.sleep(random.uniform(1.5, 2.5))

                final_url = driver.current_url

                # Hard skip: error pages
                if is_error_url(final_url):
                    logger.info(f"  Error page, skipping: {final_url[:60]}")
                    continue

                if "google.com" not in final_url and is_valid_job_url(final_url):
                    platform_type = classify_url(final_url)

                    if platform_type == "skip":
                        logger.debug(f"  Skip platform: {final_url[:60]}")
                        continue

                    # Determine if this is a description or a list
                    url_type = is_job_description_url(final_url)

                    if url_type == "description":
                        # Single job description — accept directly
                        if final_url not in urls:
                            urls.append(final_url)
                            seen_this_run.add(make_url_hash(final_url))
                            logger.info(f"  Accepted [description]: {final_url[:80]}")

                    elif url_type == "list":
                        # Category page — crawl it for individual jobs
                        logger.info(f"  List page detected — crawling: {final_url[:80]}")
                        crawled = crawl_listing_page(
                            driver=driver,
                            list_url=final_url,
                            seen_urls=seen_this_run,
                            max_jobs=min(8, max_results - len(urls)),
                        )
                        for job_url in crawled:
                            if len(urls) >= max_results:
                                break
                            if job_url not in urls:
                                urls.append(job_url)
                                logger.info(f"  Accepted [crawled]: {job_url[:80]}")

                        # After crawling we are still on the list page —
                        # the finally block will handle going back to Google

                    else:
                        # Unknown from URL alone — ask Agent 1
                        page_type = classify_page_lightweight(driver, final_url)

                        if page_type in ["job_form", "job_description"]:
                            # Single job page — accept directly
                            if final_url not in urls:
                                urls.append(final_url)
                                seen_this_run.add(make_url_hash(final_url))
                                logger.info(f"  Accepted [agent1 confirmed]: {final_url[:80]}")

                        elif page_type == "job_listing":
                            # List page confirmed by Agent 1 — crawl it
                            logger.info(f"  Agent 1: list page — crawling: {final_url[:60]}")
                            crawled = crawl_listing_page(
                                driver=driver,
                                list_url=final_url,
                                seen_urls=seen_this_run,
                                max_jobs=min(8, max_results - len(urls)),
                            )
                            for job_url in crawled:
                                if len(urls) >= max_results:
                                    break
                                if job_url not in urls:
                                    urls.append(job_url)
                                    logger.info(f"  Accepted [crawled]: {job_url[:80]}")

                        elif page_type == "not_a_job":
                            logger.info(f"  Agent 1: not a job page — skipping: {final_url[:60]}")

                        elif page_type in ["cloudflare", "captcha"]:
                            logger.info(f"  Agent 1: blocked ({page_type}) — skipping")

                        else:
                            # unknown — crawl and let crawl_listing_page sort it out
                            logger.info(f"  Agent 1: unknown ({page_type}) — crawling: {final_url[:60]}")
                            crawled = crawl_listing_page(
                                driver=driver,
                                list_url=final_url,
                                seen_urls=seen_this_run,
                                max_jobs=min(8, max_results - len(urls)),
                            )
                            for job_url in crawled:
                                if len(urls) >= max_results:
                                    break
                                if job_url not in urls:
                                    urls.append(job_url)
                                    logger.info(f"  Accepted [crawled]: {job_url[:80]}")

                else:
                    logger.info(f"  Rejected: {final_url[:60]}")

            except Exception as e:
                logger.debug(f"  Click failed: {e}")

            finally:
                try:
                    driver.back()
                    time.sleep(random.uniform(1.5, 2.5))

                    if "google.com/search" not in driver.current_url:
                        logger.debug("Back did not return to results, navigating directly")
                        driver.get(search_results_url)
                        time.sleep(random.uniform(2.0, 3.0))

                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div#search"))
                    )
                except Exception:
                    try:
                        driver.get(search_results_url)
                        time.sleep(random.uniform(2.0, 3.0))
                    except Exception:
                        pass

    except TimeoutException:
        logger.warning("Search results did not load in time")
    except Exception as e:
        logger.error(f"URL extraction failed: {e}")

    return urls


def human_read_results(driver, connector: GoogleConnector):
    try:
        actions = GoogleActions()
        actions.scroll_down(driver, max_scrolls=2, scroll_duration=random.uniform(8, 15))
        time.sleep(random.uniform(2, 5))
        actions.scroll_up(driver, max_scrolls=1, scroll_duration=random.uniform(3, 6))
        time.sleep(random.uniform(1, 3))
    except Exception as e:
        logger.debug(f"human_read_results failed (non-fatal): {e}")


def safe_navigate(driver, url: str, retries: int = 3) -> bool:
    for attempt in range(retries):
        try:
            driver.uc_open_with_reconnect(url)
            return True
        except Exception as e:
            logger.warning(f"Navigation attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(random.uniform(5, 15))

    logger.error(f"Navigation failed after {retries} attempts: {url}")
    return False


def search_google_for_jobs(
    driver,
    query: str,
    connector: GoogleConnector,
    max_results: int = 10,
    seen_this_run: set = None,
) -> list:
    logger.info(f"Searching: '{query}'")

    if seen_this_run is None:
        seen_this_run = set()

    try:
        connector.search(driver, query)
        time.sleep(random.uniform(2, 4))

        human_read_results(driver, connector)

        urls = extract_urls_from_search_results(
            driver,
            max_results=max_results,
            seen_this_run=seen_this_run,
        )
        logger.info(f"Found {len(urls)} URLs for query: '{query}'")

        return urls

    except Exception as e:
        logger.error(f"Google search failed for query '{query}': {e}")
        return []


def discover_jobs(
    driver,
    job_sources: dict,
    agent_profile: dict,
    state_path: str = "./state/applied_jobs.json",
) -> list:
    logger.info("=" * 70)
    logger.info("JOB DISCOVERY: Starting Google search")
    logger.info("=" * 70)

    connector = GoogleConnector()
    seen_hashes = load_applied_state(state_path)
    queries = job_sources.get("queries", [])
    max_per_run = agent_profile.get("max_applications_per_run", 20)

    if not queries:
        logger.error("No queries found in job_sources.json")
        return []

    logger.info(f"Queries to run: {len(queries)}")
    logger.info(f"Max applications this run: {max_per_run}")
    logger.info(f"Previously seen URLs: {len(seen_hashes)}")

    all_jobs = []
    seen_this_run = seen_hashes.copy()

    shuffled_queries = queries.copy()
    random.shuffle(shuffled_queries)

    for query in shuffled_queries:
        if len(all_jobs) >= max_per_run:
            logger.info(f"Reached max {max_per_run} listings. Stopping discovery.")
            break

        urls = search_google_for_jobs(
            driver=driver,
            query=query,
            connector=connector,
            max_results=10,
            seen_this_run=seen_this_run,
        )

        for url in urls:
            if len(all_jobs) >= max_per_run:
                break

            url_hash = make_url_hash(url)

            if url_hash in seen_hashes:
                logger.debug(f"Already seen: {url}")
                continue

            if url_hash in seen_this_run and url_hash not in seen_hashes:
                # already added this run but not yet in all_jobs — skip duplicate
                already_in_jobs = any(j["job_id"] == url_hash for j in all_jobs)
                if already_in_jobs:
                    continue

            platform_type = classify_url(url)

            if platform_type == "skip":
                logger.debug(f"Skipping platform: {url}")
                continue

            seen_this_run.add(url_hash)
            all_jobs.append({
                "job_id": url_hash,
                "url": url,
                "platform_type": platform_type,
                "query": query,
            })

            logger.info(f"Added [{platform_type}]: {url}")

        pause = random.uniform(8, 20)
        logger.info(f"Pause between queries: {pause:.1f}s")
        time.sleep(pause)

    priority_order = {"direct": 0, "session": 1, "unknown": 2, "manual_queue": 3}
    all_jobs.sort(key=lambda j: priority_order.get(j["platform_type"], 99))

    logger.info("=" * 70)
    logger.info(f"DISCOVERY COMPLETE: {len(all_jobs)} listings found")
    direct = sum(1 for j in all_jobs if j["platform_type"] == "direct")
    session = sum(1 for j in all_jobs if j["platform_type"] == "session")
    manual = sum(1 for j in all_jobs if j["platform_type"] == "manual_queue")
    unknown = sum(1 for j in all_jobs if j["platform_type"] == "unknown")
    logger.info(f"Direct (no login): {direct}")
    logger.info(f"Session (saved login): {session}")
    logger.info(f"Manual queue: {manual}")
    logger.info(f"Unknown platform: {unknown}")
    logger.info("=" * 70)

    return all_jobs