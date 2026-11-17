#!/usr/bin/python3
"""
    Job Application Agent - Entry Point
    Author: Fortune Nwohiri
"""
import time
import json
import random
import os
import sys
import uuid
import shutil
from logging_config.logger import get_logger
from login_gmail_selenium.util.profiles.google_profile import GoogleProfile
from Agents.google_connector import GoogleConnector
from Agents.google_actions import GoogleActions
from Agents.utils import nigerian_websites
from Brain.enhanced_google_brain import EnhancedGoogleBrain
from login_gmail_selenium.common.constant import PROFILE_GOOGLE_FOLDER
from between_app_searches import BETWEEN_APPLICATION_SEARCHES
from job_agent.job_discovery import discover_jobs
from job_agent.job_connector import run_application_loop

logger = get_logger("AgentMain")


JOB_WARMUP_KEYWORDS = [
    "best backend frameworks 2026",
    "typescript vs javascript performance",
    "nestjs tutorial beginners",
    "postgresql vs mysql 2026",
    "remote work tips developers",
    "redis caching strategies",
    "docker best practices",
    "api design patterns rest",
    "how to negotiate salary software engineer",
    "open source projects contribute",
]

WARMUP_POOL = nigerian_websites + JOB_WARMUP_KEYWORDS

# Device rotation — each application gets a different device.
# Looks like a different person on a different device every time.
DEVICE_ROTATION = [
    "iphone_15_pro_max",
    "iphone_14_pro_max",
    "iphone_13",
    "Samsung Galaxy S23",
    "Samsung Galaxy S23 Ultra",
    "Google Pixel 8",
    "Windows 11 - Chrome",
    "Windows 11 - Edge",
    "Windows 10 - Chrome",
    "macOS Sonoma - Chrome",
    "macOS Ventura - Safari",
]

# Platforms that require a saved login session.
# These use their own profile directories and are never deleted.
LOGIN_REQUIRED_PLATFORMS = ["wellfound", "contra", "workable"]


def load_config(path: str) -> dict:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Config file not found: {path}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {path}: {e}")
        return {}


def load_state(path: str = "./state/applied_jobs.json") -> dict:
    if not os.path.exists(path):
        logger.info("No state file found, starting fresh")
        return {"applied": [], "skipped": [], "failed": [], "manual_queue": []}
    with open(path, "r") as f:
        return json.load(f)


def save_state(state: dict, path: str = "./state/applied_jobs.json"):
    with open(path, "w") as f:
        json.dump(state, f, indent=2)


def setup_main_driver():
    """
    Boots the main job_agent_default browser.
    Stays open the entire run.
    Used for warmup and job discovery on Google only.
    Fixed device — iphone_15_pro_max.
    """
    try:
        profile = GoogleProfile(
            email=None,
            password=None,
            backup_email=None,
            skip_login=True,
            auth_type="backup_code",
            device="iphone_15_pro_max",
            path="job_agent_default",
        )
        driver = profile.retrieve_driver()
        logger.info("Main driver booted — profile: job_agent_default")
        return driver, profile
    except Exception as e:
        logger.error(f"Main driver setup failed: {e}")
        return None, None


def setup_application_driver(device_name: str = None):
    """
    Boots a fresh browser for a single application.
    Random device from DEVICE_ROTATION.
    Unique profile directory — deleted after the application closes.
    Used for no-login platforms only.
    """
    if device_name is None:
        device_name = random.choice(DEVICE_ROTATION)

    unique_id = str(uuid.uuid4())[:8]
    profile_dir = f"job_app_{unique_id}"

    try:
        profile = GoogleProfile(
            email=None,
            password=None,
            backup_email=None,
            skip_login=True,
            auth_type="backup_code",
            device=device_name,
            path=profile_dir,
        )
        driver = profile.retrieve_driver()
        logger.info(f"Application driver booted — device: {device_name}, profile: {profile_dir}")
        return driver, profile, profile_dir, device_name
    except Exception as e:
        logger.error(f"Application driver setup failed: {e}")
        return None, None, None, None


def setup_session_driver(platform_key: str, platform_sessions: dict):
    """
    Boots a browser using a saved login session for Wellfound, Contra, Workable.
    Uses the fixed profile directory for that platform.
    Profile directory is NEVER deleted — session must be preserved.
    """
    platform_data = platform_sessions.get(platform_key)
    if not platform_data:
        logger.error(f"No session config found for {platform_key}")
        return None, None, None

    profile_dir = platform_data["profile_dir"]

    try:
        profile = GoogleProfile(
            email=None,
            password=None,
            backup_email=None,
            skip_login=True,
            auth_type="backup_code",
            device="iphone_15_pro_max",
            path=profile_dir,
        )
        driver = profile.retrieve_driver()
        logger.info(f"Session driver booted — platform: {platform_key}, profile: {profile_dir}")
        return driver, profile, profile_dir
    except Exception as e:
        logger.error(f"Session driver setup failed for {platform_key}: {e}")
        return None, None, None


def cleanup_application_driver(driver, profile, profile_dir: str, is_session: bool = False):
    """
    Closes the driver and cleans up.
    For no-login platforms: deletes the temporary profile directory.
    For session platforms: keeps the profile directory intact.
    """
    try:
        driver.quit()
        logger.info("Application driver closed")
    except Exception:
        pass

    try:
        profile.stop()
    except Exception:
        pass

    # Only delete temporary per-application profiles.
    # Never delete session profiles for Wellfound, Contra, Workable.
    if not is_session and profile_dir and profile_dir.startswith("job_app_"):
        full_path = os.path.join(PROFILE_GOOGLE_FOLDER, profile_dir)
        if os.path.exists(full_path):
            shutil.rmtree(full_path, ignore_errors=True)
            logger.info(f"Temporary profile deleted: {profile_dir}")


def check_platform_sessions(platform_sessions: dict) -> dict:
    status = {}
    for platform_key, platform_data in platform_sessions.items():
        profile_path = os.path.join(
            PROFILE_GOOGLE_FOLDER,
            platform_data["profile_dir"]
        )
        exists = os.path.exists(profile_path)
        status[platform_key] = exists

        if not exists:
            logger.warning(
                f"No saved session for {platform_key}. "
                f"Run setup_sessions.py and log in manually at {platform_data['login_url']}"
            )
        else:
            logger.info(f"Session found for {platform_key}")

    return status


def detect_platform(url: str) -> str:
    """
    Detect which platform a job URL belongs to.
    Returns platform key for session platforms.
    Returns 'guest' for no-login platforms.
    Returns 'skip' for unsupported platforms.
    """
    url_lower = url.lower()

    if "wellfound.com" in url_lower:
        return "wellfound"
    if "contra.com" in url_lower:
        return "contra"
    if "apply.workable.com" in url_lower or "jobs.workable.com" in url_lower:
        return "workable"
    if "boards.greenhouse.io" in url_lower:
        return "greenhouse"
    if "jobs.lever.co" in url_lower:
        return "lever"
    if "jobs.ashbyhq.com" in url_lower:
        return "ashby"
    if "smartrecruiters.com" in url_lower:
        return "smartrecruiters"
    if "remoteok.com" in url_lower:
        return "remoteok"
    if "himalayas.app" in url_lower:
        return "himalayas"
    if "remotive.com" in url_lower:
        return "remotive"
    if "weworkremotely.com" in url_lower:
        return "weworkremotely"
    if "jobgether.com" in url_lower:
        return "jobgether"
    if "4dayweek.io" in url_lower:
        return "4dayweek"

    # Platforms to skip
    if any(x in url_lower for x in [
        "linkedin.com", "indeed.com", "workday.com",
        "myworkdayjobs.com", "taleo.net", "icims.com",
        "successfactors.com"
    ]):
        return "skip"

    # Unknown platform — treat as guest and attempt
    return "guest"


def micro_warmup(driver):
    """
    Quick 30 to 60 second warmup for per-application browsers.
    Visits one random site before touching any job platform or Google.
    Prevents cold-start detection on fresh browser profiles.
    """
    sites = [s for s in nigerian_websites if not s.startswith("naijabulletin")]
    site = random.choice(sites)

    if not site.startswith("http"):
        site = f"https://{site}"

    try:
        logger.info(f"Micro-warmup: visiting {site}")
        driver.uc_open_with_reconnect(site)
        time.sleep(random.uniform(5, 10))

        actions = GoogleActions()
        actions.scroll_down(driver, max_scrolls=2, scroll_duration=random.uniform(15, 30))

        time.sleep(random.uniform(10, 20))
        logger.info("Micro-warmup complete")

    except Exception as e:
        logger.warning(f"Micro-warmup failed (non-fatal): {e}")
        time.sleep(random.uniform(20, 40))


def run_warmup(driver, duration_minutes: int = 4):
    """
    Full warmup on the main driver at the start of the run.
    Runs once only. Uses EnhancedGoogleBrain exploratory session.
    """
    logger.info("=" * 70)
    logger.info("WARMUP: Building session history before job hunt")
    logger.info(f"Duration: {duration_minutes} minutes")
    logger.info("=" * 70)

    try:
        connector = GoogleConnector()
        warmup_keyword = random.choice(WARMUP_POOL)
        logger.info(f"Warmup seed keyword: '{warmup_keyword}'")

        brain = EnhancedGoogleBrain(
            driver=driver,
            google_connector=connector,
            target_url="https://stackoverflow.com",
            keyword=warmup_keyword,
        )

        brain.run_session("exploratory", duration_minutes=duration_minutes)
        logger.info(f"Warmup complete — domains visited: {len(brain.visited_domains)}, keywords used: {len(brain.used_keywords)}")
        return True

    except Exception as e:
        logger.error(f"Warmup failed: {e}", exc_info=True)
        return False


def browse_between_applications(driver, agent_profile: dict):
    """
    Between applications the bot searches a random question and browses
    naturally for the configured gap duration on the application browser
    before it closes. Looks like a person who just submitted a job form
    and kept browsing afterward.
    """
    min_gap = agent_profile.get("min_seconds_between_applications", 180)
    max_gap = agent_profile.get("max_seconds_between_applications", 420)
    gap_seconds = random.uniform(min_gap, max_gap)
    gap_minutes = gap_seconds / 60

    search_query = random.choice(BETWEEN_APPLICATION_SEARCHES)

    logger.info("=" * 70)
    logger.info(f"BETWEEN APPLICATIONS: Browsing for {gap_minutes:.1f} minutes")
    logger.info(f"Search query: '{search_query}'")
    logger.info("=" * 70)

    try:
        connector = GoogleConnector()

        brain = EnhancedGoogleBrain(
            driver=driver,
            google_connector=connector,
            target_url="https://stackoverflow.com",
            keyword=search_query,
        )

        brain.run_session("exploratory", duration_minutes=gap_minutes)
        logger.info("Between-application browse complete")

    except Exception as e:
        logger.error(f"Between-application browse failed: {e}")
        logger.info(f"Falling back to plain sleep for {gap_seconds:.0f}s")
        time.sleep(gap_seconds)


def get_application_duration(agent_profile: dict) -> float:
    """
    Returns a random target duration in seconds for one application.
    The bot paces itself to this duration before submitting.
    """
    min_time = agent_profile.get("min_time_per_application_seconds", 120)
    max_time = agent_profile.get("max_time_per_application_seconds", 480)
    duration = random.uniform(min_time, max_time)
    logger.info(f"Application time target: {duration:.0f}s ({duration/60:.1f} minutes)")
    return duration


def wait_to_human_pace(driver, start_time: float, target_duration: float, connector):
    """
    If the form filled faster than the target duration,
    spend the remaining time scrolling and pausing naturally
    before submitting. Simulates a person reviewing their answers.
    """
    elapsed = time.time() - start_time
    remaining = target_duration - elapsed

    if remaining <= 0:
        logger.info(f"Application took {elapsed:.0f}s — at target, proceeding to submit")
        return

    logger.info(f"Form filled in {elapsed:.0f}s. Reading for {remaining:.0f}s before submit.")

    while time.time() - start_time < target_duration:
        try:
            connector.actions.scroll_down(driver, max_scrolls=1, scroll_duration=2)
            time.sleep(random.uniform(3, 8))
        except Exception:
            time.sleep(random.uniform(3, 6))


def run_job_session(
    main_driver,
    platform_sessions: dict,
    session_status: dict,
    job_sources: dict,
    agent_profile: dict,
    state: dict
):
    """
    Job discovery and application pipeline entry point.
    job_discovery.py and job_connector.py wire in here as they are built.

    main_driver: used for job discovery on Google only.
    platform_sessions: config for Wellfound, Contra, Workable.
    session_status: which platform sessions are available.

    For each listing:
    - detect_platform() decides which browser type to open
    - no-login platforms get a fresh per-application browser
    - session platforms get their saved session browser
    - micro_warmup() runs on every application browser before touching the platform
    - browse_between_applications() runs after every application
    - cleanup_application_driver() closes and cleans up after each application
    """
    logger.info("=" * 70)
    logger.info("JOB HUNT: Discovery and application pipeline starting")
    logger.info(f"Max applications this run: {agent_profile.get('max_applications_per_run', 20)}")
    logger.info(f"Time per application: {agent_profile.get('min_time_per_application_seconds', 120)}s to {agent_profile.get('max_time_per_application_seconds', 480)}s")
    logger.info(f"Gap between applications: {agent_profile.get('min_seconds_between_applications', 180)}s to {agent_profile.get('max_seconds_between_applications', 420)}s")
    logger.info("=" * 70)

    # This is where job_discovery.py wires in.
    # It uses main_driver to search Google and returns a list of job URLs.
    # Then for each URL:
    #
    # platform = detect_platform(url)
    #
    # if platform == "skip":
    #     log and continue
    #
    # elif platform in LOGIN_REQUIRED_PLATFORMS:
    #     if not session_status.get(platform):
    #         log as skipped, continue
    #     driver, profile, profile_dir = setup_session_driver(platform, platform_sessions)
    #     micro_warmup(driver)
    #     target_duration = get_application_duration(agent_profile)
    #     start_time = time.time()
    #     ... job_connector fills form ...
    #     wait_to_human_pace(driver, start_time, target_duration, connector)
    #     ... submit ...
    #     browse_between_applications(driver, agent_profile)
    #     cleanup_application_driver(driver, profile, profile_dir, is_session=True)
    #
    # else:
    #     driver, profile, profile_dir, device = setup_application_driver()
    #     micro_warmup(driver)
    #     target_duration = get_application_duration(agent_profile)
    #     start_time = time.time()
    #     ... job_connector fills form ...
    #     wait_to_human_pace(driver, start_time, target_duration, connector)
    #     ... submit ...
    #     browse_between_applications(driver, agent_profile)
    #     cleanup_application_driver(driver, profile, profile_dir, is_session=False)

    logger.info("Job discovery module: not yet built — standing by")
    logger.info(f"Agent: {agent_profile.get('name', 'unknown')}")
    logger.info(f"Queries loaded: {len(job_sources.get('queries', []))}")
    logger.info(f"Previously applied: {len(state.get('applied', []))}")

    # Discover job URLs from Google
    discovered_jobs = discover_jobs(
        driver=main_driver,
        job_sources=job_sources,
        agent_profile=agent_profile,
        state_path="./state/applied_jobs.json",
    )

    if not discovered_jobs:
        logger.info("No new jobs discovered this run")
        return

    # Run the application loop
    session_summary = run_application_loop(
        main_driver=main_driver,
        discovered_jobs=discovered_jobs,
        agent_profile=agent_profile,
        platform_sessions=platform_sessions,
        state_path="./state/applied_jobs.json",
    )

    logger.info(
        f"Session complete: "
        f"{session_summary.get('applied_count', 0)} applied, "
        f"{session_summary.get('skipped_count', 0)} skipped, "
        f"{session_summary.get('failed_count', 0)} failed, "
        f"{session_summary.get('manual_queue_count', 0)} manual queue"
    )

def main():
    logger.info("=" * 70)
    logger.info("JOB APPLICATION AGENT — STARTING")
    logger.info("=" * 70)

    agent_profile = load_config("./config/agent_profile.json")
    job_sources = load_config("./config/job_sources.json")
    platform_sessions = load_config("./config/platform_sessions.json")
    state = load_state("./state/applied_jobs.json")

    if not agent_profile:
        logger.error("agent_profile.json missing. Cannot run.")
        sys.exit(1)

    if not job_sources:
        logger.error("job_sources.json missing. Cannot run.")
        sys.exit(1)

    logger.info(f"Agent: {agent_profile.get('name', 'unknown')}")
    logger.info(f"Min score threshold: {agent_profile.get('min_score_threshold', 72)}")
    logger.info(f"Max applications: {agent_profile.get('max_applications_per_run', 20)}")
    logger.info(f"Previously applied: {len(state.get('applied', []))}")

    session_status = check_platform_sessions(platform_sessions)
    available = [k for k, v in session_status.items() if v]
    missing = [k for k, v in session_status.items() if not v]

    if available:
        logger.info(f"Platforms ready: {', '.join(available)}")
    if missing:
        logger.info(f"Platforms skipped (no session): {', '.join(missing)}")

    # Boot the main driver — stays open the whole run
    main_driver, main_profile = setup_main_driver()

    if not main_driver:
        logger.error("Main driver failed to boot. Exiting.")
        sys.exit(1)

    if main_profile:
        try:
            main_profile.start()
            logger.info("Main profile started")
        except Exception as e:
            logger.warning(f"Main profile start failed (non-fatal): {e}")

    session_summary = None

    try:
        # Warmup — runs once only on the main driver
        warmup_minutes = agent_profile.get("warmup_minutes", 4)
        warmup_success = run_warmup(main_driver, duration_minutes=warmup_minutes)

        if not warmup_success:
            logger.warning("Warmup failed — continuing anyway")

        pause = random.uniform(30, 90)
        logger.info(f"Pause before job hunt: {pause:.1f}s")
        time.sleep(pause)

        # Job hunt — main_driver is passed in for Google discovery only
        session_summary = run_job_session(
            main_driver=main_driver,
            platform_sessions=platform_sessions,
            session_status=session_status,
            job_sources=job_sources,
            agent_profile=agent_profile,
            state=state,
        )

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Agent crashed: {e}", exc_info=True)
    finally:
        logger.info("Cleaning up main driver")
        try:
            main_driver.quit()
            logger.info("Main driver closed")
        except Exception:
            pass
        if main_profile:
            try:
                main_profile.stop()
            except Exception:
                pass

        # Generate report and dashboard at end of every run
        try:
            from job_agent.report_generator import generate as generate_report
            from job_agent.email_sender import EmailSender

            logger.info("Generating session report and dashboard")
            report_result = generate_report(session_summary=session_summary)

            logger.info(f"Report saved: {report_result['report_path']}")
            logger.info(f"Dashboard saved: {report_result['dashboard_path']}")

            metrics = report_result.get("metrics", {})
            logger.info(
                f"Session summary: "
                f"{metrics.get('total_applied', 0)} applied, "
                f"{metrics.get('total_skipped', 0)} skipped, "
                f"{metrics.get('total_failed', 0)} failed, "
                f"{metrics.get('total_manual_queue', 0)} manual queue"
            )

            # Email the morning report to yourself
            email_sender = EmailSender()
            email_sender.send_morning_report(report_result["report_path"])

        except Exception as e:
            logger.error(f"Report generation failed (non-fatal): {e}", exc_info=True)

        logger.info("=" * 70)
        logger.info("JOB APPLICATION AGENT — SESSION COMPLETE")
        logger.info("=" * 70)

if __name__ == "__main__":
    main()