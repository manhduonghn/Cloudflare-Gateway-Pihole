import logging
import requests
from src import cloudflare, convert

class App:
    def __init__(self, adlist_name: str, adlist_urls: list[str],whitelist_urls: list[str]):
        self.adlist_name = adlist_name
        self.adlist_urls = adlist_urls
        self.whitelist_urls = whitelist_urls
        self.name_prefix = f"[AdBlock-{adlist_name}]"

    def run(self):
        block_content = ""
        white_content = ""
        for url in self.adlist_urls:
            block_content += self.download_file(url) 
        for url in self.whitelist_urls:
            white_content += self.download_file(url)

        
        with open("dynamic_blacklist.txt", "r") as black_file:
            blacklist_content = black_file.read()
            block_content += blacklist_content
        
        with open("dynamic_whitelist.txt", "r") as white_file:
            whitelist_content = white_file.read()
            white_content += whitelist_content
        
        domains = convert.convert_to_domain_list(block_content, white_content)

        # check if number of domains exceeds the limit
        if len(domains) == 0:
            logging.warning("No domains found in the adlist file. Exiting script.")
            return 
        
        # stop script if the number of final domains exceeds the limit
        if len(domains) > 300000:
            logging.warning("The number of final domains exceeds the limit. Exiting script.")
            return
        
        # check if the list is already in Cloudflare
        cf_lists = cloudflare.get_lists(self.name_prefix)
        logging.info(f"Number of lists in Cloudflare: {len(cf_lists)}")

        # compare the lists size
        if len(domains) == sum([l["count"] for l in cf_lists]):
            logging.warning("Lists are the same size, checking policy")
            cf_policies = cloudflare.get_firewall_policies(self.name_prefix)

            if len(cf_policies) == 0:
                logging.info("No firewall policy found, creating new policy")
                cf_policies = cloudflare.create_gateway_policy(
                    f"{self.name_prefix} Block Ads", [l["id"] for l in cf_lists]
                )
            else:
                logging.warning("Firewall policy already exists, exiting script")
                return
                
            return 

        # Delete existing policy created by script
        policy_prefix = f"{self.name_prefix} Block Ads"
        deleted_policies = cloudflare.delete_gateway_policy(policy_prefix)
        logging.info(f"Deleted {deleted_policies} gateway policies")

        # delete the lists
        for l in cf_lists:
            logging.info(f"Deleting list {l['name']} - ID:{l['id']} ")
            cloudflare.delete_list(l["name"], l["id"])
        cf_lists = []

        # chunk the domains into lists of 1000 and create them
        for chunk in self.chunk_list(domains, 1000):
            list_name = f"{self.name_prefix} {len(cf_lists) + 1}"
            logging.info(f"Creating list {list_name}")
            _list = cloudflare.create_list(list_name, chunk)
            cf_lists.append(_list)

        # get the gateway policies
        cf_policies = cloudflare.get_firewall_policies(self.name_prefix)
        logging.info(f"Number of policies in Cloudflare: {len(cf_policies)}")

        # setup the gateway policy
        if len(cf_policies) == 0:
            logging.info("Creating firewall policy")
            cf_policies = cloudflare.create_gateway_policy(
                f"{self.name_prefix} Block Ads", [l["id"] for l in cf_lists]
            )

        elif len(cf_policies) != 1:
            logging.error("More than one firewall policy found")
            raise Exception("More than one firewall policy found")

        else:
            logging.info("Updating firewall policy")
            cloudflare.update_gateway_policy(
                f"{self.name_prefix} Block Ads", cf_policies[0]["id"], [l["id"] for l in cf_lists]
            )
        logging.info("Done")
        
    def download_file(self, url: str):
        logging.info(f"Downloading file from {url}")
        r = requests.get(url, allow_redirects=True)
        logging.info(f"File size: {len(r.content)}")
        return r.content.decode("utf-8")

    def chunk_list(self, _list: list[str], n: int):
        for i in range(0, len(_list), n):
            yield _list[i : i + n]

    def delete(self):
        # Delete gateway policy
        policy_prefix = f"{self.name_prefix} Block Ads"
        deleted_policies = cloudflare.delete_gateway_policy(policy_prefix)
        logging.info(f"Deleted {deleted_policies} gateway policies")

        # Delete lists
        cf_lists = cloudflare.get_lists(self.name_prefix)
        for l in cf_lists:
            logging.info(f"Deleting list {l['name']} - ID:{l['id']} ")
            cloudflare.delete_list(l["name"], l["id"])
        logging.info("Deletion completed")
                          
