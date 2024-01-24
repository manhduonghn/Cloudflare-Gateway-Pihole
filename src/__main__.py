from loguru import logger
from src import (
    utils,
    convert, 
    cloudflare
)

class CloudflareManager:    
    def __init__(self, adlist_name: str, adlist_urls: list[str],whitelist_urls: list[str]):
        self.adlist_name = adlist_name
        self.adlist_urls = adlist_urls
        self.whitelist_urls = whitelist_urls
        self.name_prefix = f"[AdBlock-{adlist_name}]"

    def run(self):
        
        # Download block and white content 
        block_content = ""
        white_content = ""
        for url in self.adlist_urls:
            block_content += utils.download_file(url) 
        for url in self.whitelist_urls:
            white_content += utils.download_file(url)

        # Add dynamic black list
        with open("./lists/dynamic_blacklist.txt", "r") as black_file:
            blacklist_content = black_file.read()
            block_content += blacklist_content
        
        # Add dynamic white list 
        with open("./lists/dynamic_whitelist.txt", "r") as white_file:
            whitelist_content = white_file.read()
            white_content += whitelist_content
        
        domains = convert.convert_to_domain_list(block_content, white_content)

        # check if number of domains exceeds the limit
        if len(domains) == 0:
            logger.warning("No domains found in the adlist file. Exiting script.")
            return 
        
        # stop script if the number of final domains exceeds the limit
        if len(domains) > 300000:
            logger.warning("The number of final domains exceeds the limit. Exiting script.")
            return
        
        # check if the list is already in Cloudflare
        cf_lists = cloudflare.get_lists(self.name_prefix)
        logger.info(f"Number of lists in Cloudflare: {len(cf_lists)}")

        # compare the lists size
        if len(domains) == sum([l["count"] for l in cf_lists]):
            logger.warning("Lists are the same size, checking policy")
            cf_policies = cloudflare.get_firewall_policies(self.name_prefix)

            if len(cf_policies) == 0:
                logger.info("No firewall policy found, creating new policy")
                cf_policies = cloudflare.create_gateway_policy(
                    f"{self.name_prefix} Block Ads", [l["id"] for l in cf_lists]
                )
            else:
                logger.warning("Firewall policy already exists, exiting script")
                return
                
            return 

        # Delete existing policy created by script
        policy_prefix = f"{self.name_prefix} Block Ads"
        firewall_policies = cloudflare.get_firewall_policies(policy_prefix)
        for policy in firewall_policies:
            cloudflare.delete_gateway_policy(policy["id"])
        logger.info(f"Deleted gateway policies")

        # delete the lists
        for l in cf_lists:
            logger.info(f"Deleting list {l['name']} - ID:{l['id']} ")
            cloudflare.delete_list(l["name"], l["id"])
        cf_lists = []

        # chunk the domains into lists of 1000 and create them
        for chunk in utils.chunk_list(domains, 1000):
            list_name = f"{self.name_prefix} - {len(cf_lists) + 1:03d}"
            logger.info(f"Creating list {list_name}")
            _list = cloudflare.create_list(list_name, chunk)
            cf_lists.append(_list)

        # get the gateway policies
        cf_policies = cloudflare.get_firewall_policies(self.name_prefix)
        logger.info(f"Number of policies in Cloudflare: {len(cf_policies)}")

        # setup the gateway policy
        if len(cf_policies) == 0:
            logger.info("Creating firewall policy")
            cf_policies = cloudflare.create_gateway_policy(
                f"{self.name_prefix} Block Ads", [l["id"] for l in cf_lists]
            )

        elif len(cf_policies) != 1:
            logger.error("More than one firewall policy found")
            raise Exception("More than one firewall policy found")

        else:
            logger.info("Updating firewall policy")
            cloudflare.update_gateway_policy(
                f"{self.name_prefix} Block Ads", cf_policies[0]["id"], [l["id"] for l in cf_lists]
            )
        logger.info("Done")

    def leave(self):
        # Delete gateway policy
        policy_prefix = f"{self.name_prefix} Block Ads"
        firewall_policies = cloudflare.get_firewall_policies(policy_prefix)

        for policy in firewall_policies:
            cloudflare.delete_gateway_policy(policy["id"])
        logger.info(f"Deleted gateway policies")

        # Delete lists
        cf_lists = cloudflare.get_lists(self.name_prefix)
        for l in cf_lists:
            logger.info(f"Deleting list {l['name']} - ID:{l['id']} ")
            cloudflare.delete_list(l["name"], l["id"])
        logger.info("Deletion completed")

if __name__ == "__main__":
    adlist_urls = utils.read_urls_from_file("./lists/adlist.ini")
    whitelist_urls = utils.read_urls_from_file("./lists/whitelist.ini")
    adlist_name = "DNS-Filters"
    cloudflaremanager = CloudflareManager(adlist_name, adlist_urls, whitelist_urls)
    cloudflaremanager.leave()  # Leave script 
    # cloudflaremanager.run()
