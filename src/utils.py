import http.client
from src.colorlog import logger
from configparser import ConfigParser

def download_file(url: str):
    logger.info(f"Downloading file from {url}")

    # Parse the URL
    if url.startswith("https://"):
        url = url[8:]
    elif url.startswith("http://"):
        url = url[7:]
    
    host, path = url.split("/", 1)
    path = "/" + path

    conn = http.client.HTTPSConnection(host)
    conn.request("GET", path)
    response = conn.getresponse()
    
    if response.status != 200:
        raise Exception(f"Failed to download file with status code {response.status}")

    content = response.read()
    logger.info(f"File size: {len(content)}")
    return content.decode("utf-8")

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
