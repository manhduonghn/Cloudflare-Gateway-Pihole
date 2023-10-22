import os
import re
import logging
from libs import requests
from libs.dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from src.colorlogs import ColoredLevelFormatter


# Regex Pattern
replace_pattern = re.compile(
    r"(^([0-9.]+|[0-9a-fA-F:.]+)\s+|^(\|\||@@\|\||\*\.|\*))"
)
domain_pattern = re.compile(
    r"^([a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?\.?)+[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?$"
)
ip_pattern = re.compile(
    r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
)


# Logging Level Color 
logging.getLogger().setLevel(logging.INFO)
formatter = ColoredLevelFormatter("%(levelname)s: %(message)s")
console = logging.StreamHandler()
console.setFormatter(ColoredLevelFormatter("%(levelname)s: %(message)s"))
logger = logging.getLogger()
logger.addHandler(console)


# load env
load_dotenv()
CF_API_TOKEN = os.getenv("CF_API_TOKEN") or os.environ.get("CF_API_TOKEN")
CF_IDENTIFIER = os.getenv("CF_IDENTIFIER") or os.environ.get("CF_IDENTIFIER")
if not CF_API_TOKEN or not CF_IDENTIFIER:
    raise Exception("Missing Cloudflare credentials")


# Session 
session = requests.Session()
session.headers.update({"Authorization": f"Bearer {CF_API_TOKEN}"})

# Enable keep-alive
adapter = HTTPAdapter(pool_connections=10, pool_maxsize=10, max_retries=3)
session.mount('http://', adapter)
session.mount('https://', adapter)
