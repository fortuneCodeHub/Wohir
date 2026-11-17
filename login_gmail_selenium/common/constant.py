import os
import dotenv


# NOTE: Global constants
RETRY = 3
LOADING_TIMEOUT = 10
LONG_LOADING_TIMEOUT = 30
STAND_BY_TIMEOUT = 15
TRANSITION_TIMEOUT = 5
SHORT_TIMEOUT = 2
MEDIUM_WAIT = [10, 20]
SHORT_WAIT = [2, 5]
VERY_SHORT_WAIT = [0, 1]
LONG_WAIT = [20, 40]
WIDE_WAIT = [1, 10]
PASTE_PERCENTAGE = 50
DISK_SPACE = 80.0
CHANGED_PASSWORD_SEPARATOR = '::::'
PASSWORD_LENGTH = 25
ACCOUNT_DISABLED_MESSAGE = 'Account disabled'
ACCOUNT_VERIFICATION_MESSAGE = 'Account required verification steps'
ACCOUNT_REQUIRED_CAPTCHA_MESSAGE = 'Account required captcha'
ACCOUNT_REJECTED_MESSAGE = 'Account rejected because of suspicious action'
ACCOUNT_PASSWORD_CHANGED_MESSAGE = 'Password changed'


def resource_path(relative_path):
    # Get the project root programmatically
    # Get the directory where this script is located (login_gmail_selenium/common/)
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up two levels to reach the project root (Google Adsense BOT/)
    project_root = os.path.dirname(os.path.dirname(current_file_dir))
    return os.path.join(project_root, relative_path)


# NOTE: Configuration
CWD = resource_path("")
TEMP_FOLDER = resource_path("temp")

# Print all paths for verification
# print(f"Project Root: {CWD}")
# print(f"Temp Folder: {TEMP_FOLDER}")
# print(f"Project Root exists: {os.path.exists(CWD)}")
# print(f"Temp Folder exists: {os.path.exists(TEMP_FOLDER)}")

# Create temp folder
os.makedirs(TEMP_FOLDER, exist_ok=True)

# Define all file and folder paths
LOG_FILE = os.path.join(TEMP_FOLDER, 'output.log')
PROFILE_GOOGLE_FOLDER = os.path.join(TEMP_FOLDER, 'profiles')
BLANK_PROFILE_FOLDER = os.path.join(TEMP_FOLDER, 'blank_profiles')
PATCHED_DRIVER = os.path.join(TEMP_FOLDER, 'chromedriver.exe')
CHANGED_EMAILS_FILE = os.path.join(TEMP_FOLDER, 'changed_emails.log')
FALSE_EMAIL_FILE = os.path.join(TEMP_FOLDER, 'false_email.log')
PROXY_FOLDER = os.path.join(TEMP_FOLDER, 'proxy')

# Print all paths for verification
# print(f"Log File: {LOG_FILE}")
# print(f"Profile Google Folder: {PROFILE_GOOGLE_FOLDER}")
# print(f"Blank Profile Folder: {BLANK_PROFILE_FOLDER}")
# print(f"Patched Driver: {PATCHED_DRIVER}")
# print(f"Changed Emails File: {CHANGED_EMAILS_FILE}")
# print(f"False Email File: {FALSE_EMAIL_FILE}")
# print(f"Proxy Folder: {PROXY_FOLDER}")

# Create all necessary directories
# os.makedirs(PROFILE_GOOGLE_FOLDER, exist_ok=True)
# os.makedirs(BLANK_PROFILE_FOLDER, exist_ok=True)
# os.makedirs(PROXY_FOLDER, exist_ok=True)
