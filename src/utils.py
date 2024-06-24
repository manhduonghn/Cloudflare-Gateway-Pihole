import requests
from src.colorlog import logger
from configparser import ConfigParser

def download_file(url: str):
    logger.success(f"Downloading file from {url}")
    r = requests.get(url, allow_redirects=True)
    logger.success(f"File size: {len(r.content)}")
    return r.content.decode("utf-8")

def chunk_list(_list: list[str], n: int):
    for i in range(0, len(_list), n):
        yield _list[i : i + n]

def read_urls_from_file(filename):
    urls = []
    try:
        config = ConfigParser()
        config.read(filename)
        for section in config.sections():
            for key in config.options(section):
                if not key.startswith("#"):
                    urls.append(config.get(section, key))
    except Exception:
        with open(filename, "r") as file:
            urls = [url.strip() for url in file if not url.startswith("#") and url.strip()]
    return urls
