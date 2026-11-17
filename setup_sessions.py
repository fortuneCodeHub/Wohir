#!/usr/bin/python3
"""
    Session Setup Script
    Run once per platform to save a logged-in session.
    Step 1: Signs into Gmail manually in the bot's browser.
    Step 2: Signs into the platform using Continue with Google.
    Author: Fortune Nwohiri
"""
from login_gmail_selenium.util.profiles.google_profile import GoogleProfile
from logging_config.logger import get_logger
import os
import login_gmail_selenium.common.constant as Constant

logger = get_logger("SessionSetup")


def open_browser_for_login(platform_name: str, login_url: str, profile_dir: str, device: str = "iphone_15_pro_max"):
    logger.info(f"Opening browser for {platform_name}")
    logger.info(f"Device: {device}")
    logger.info(f"Profile will be saved to: {os.path.join(Constant.PROFILE_GOOGLE_FOLDER, profile_dir)}")

    profile = GoogleProfile(
        email=None,
        password=None,
        backup_email=None,
        skip_login=True,
        auth_type="backup_code",
        device=device,
        path=profile_dir,
    )

    # retrieve_driver() only — do NOT call profile.start()
    # profile.start() triggers check_login_status() which has
    # time.sleep(10000) in the skip_login branch. Freezes the browser.
    driver = profile.retrieve_driver()

    # ── Step 1: Sign into Gmail first ────────────────────────────────────────
    driver.uc_open_with_reconnect("https://google.com")

    logger.info("=" * 60)
    logger.info("STEP 1: SIGN INTO GMAIL")
    logger.info("Sign into your Gmail account in the browser window.")
    logger.info("Click your profile icon at the top right.")
    logger.info("Sign in with your Gmail credentials.")
    logger.info("Take your time. Do it naturally.")
    logger.info("=" * 60)

    input("Press Enter once you are fully signed into Gmail...")

    # ── Step 2: Navigate to the platform ─────────────────────────────────────
    driver.uc_open_with_reconnect(login_url)

    logger.info("=" * 60)
    logger.info(f"STEP 2: SIGN INTO {platform_name.upper()}")
    logger.info(f"Browser is now open at {login_url}")
    logger.info("Click Continue with Google.")
    logger.info("Your Gmail account will appear — click on it.")
    logger.info("Click Continue on the next screen.")
    logger.info("Wait until you can see your full dashboard.")
    logger.info("Take your time. Do it naturally.")
    logger.info("=" * 60)

    input("Press Enter once you can see your dashboard...")

    driver.quit()

    # ── Confirm session saved ─────────────────────────────────────────────────
    saved_path = os.path.join(Constant.PROFILE_GOOGLE_FOLDER, profile_dir)
    if os.path.exists(saved_path):
        logger.info(f"Session confirmed saved at: {saved_path}")
        logger.info(f"Gmail session and {platform_name} session both saved.")
    else:
        logger.warning(f"Session directory not found at: {saved_path}")
        logger.warning("The google_profile.py fix may not have been applied.")

    logger.info(f"Session setup complete for {platform_name}.")
    logger.info("-" * 60)


if __name__ == "__main__":
    print("\nWhich platform do you want to log into?")
    print("1. Wellfound")
    print("2. Contra")
    print("3. Workable")
    print("4. All three")

    choice = input("\nEnter number: ").strip()

    platforms = {
        "1": ("Wellfound", "https://wellfound.com/login", "wellfound_session", "iphone_15_pro_max"),
        "2": ("Contra", "https://contra.com/login", "contra_session", "Samsung Galaxy S23"),
        "3": ("Workable", "https://jobs.workable.com", "workable_session", "Windows 11 - Chrome"),
    }

    if choice == "4":
        for key in platforms:
            name, url, path, device = platforms[key]
            open_browser_for_login(name, url, path, device)
    elif choice in platforms:
        name, url, path, device = platforms[choice]
        open_browser_for_login(name, url, path, device)
    else:
        print("Invalid choice.")