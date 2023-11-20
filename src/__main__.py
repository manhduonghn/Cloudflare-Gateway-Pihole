from src.utils import App
from configparser import ConfigParser

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


if __name__ == "__main__":
    adlist_urls = read_urls_from_file("./lists/adlist.ini")
    whitelist_urls = read_urls_from_file("./lists/whitelist.ini")
    adlist_name = "DNS-Filters"
    app = App(adlist_name, adlist_urls, whitelist_urls)
    # app.delete()  # Leave script 
    app.run()
