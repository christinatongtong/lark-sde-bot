from dotenv import load_dotenv
import os
load_dotenv()

HOOK_URL = os.getenv("HOOK_URL")
APP_SECRET = os.getenv("APP_SECRET")
APP_ID = os.getenv("APP_ID")
GIT_REPO_URL = os.getenv("GIT_REPO_URL")
