import argparse
from sys import exit
from src.colorlog import logger
from src import utils, domains, cloudflare

class CloudflareManager:
    def __init__(self, adlist_name: str):
        self.adlist_name = adlist_name
        self.name_prefix = f"[AdBlock-{adlist_name}]"

    def run(self):
        converter = domains.DomainConverter()
        domain_list = converter.process_urls()

        if len(domain_list) == 0:
            logger.warning("No domains found in the adlist file. Exiting script.")
            return

        if len(domain_list) > 300000:
            logger.warning("The number of final domains exceeds the limit. Exiting script.")
            return

        cf_lists = cloudflare.get_lists(self.name_prefix)
        logger.info(f"Number of lists in Cloudflare: {len(cf_lists)}")

        list_ids = []

        for i, lst in enumerate(cf_lists):
            items = cloudflare.get_list_items(lst['id'])
            existing_domains = [item['value'] for item in items]

            if set(domain_list) != set(existing_domains):
                logger.info(f"Updating list {lst['name']}")
                cloudflare.patch_list(lst['id'], domain_list)
            else:
                logger.info(f"No changes detected in the list {lst['name']}")
            
            list_ids.append(lst['id'])

        # Create new list if no existing lists match
        if not cf_lists:
            list_name = f"{self.name_prefix} - 001"
            logger.info(f"Creating list {list_name}")
            new_list = cloudflare.create_list(list_name, domain_list)
            list_ids.append(new_list['id'])

        # Create or update policy with the current list of IDs
        cf_policies = cloudflare.get_firewall_policies(self.name_prefix)
        logger.info(f"Number of policies in Cloudflare: {len(cf_policies)}")

        if len(cf_policies) == 0:
            logger.info("Creating firewall policy")
            cloudflare.create_gateway_policy(
                f"{self.name_prefix} Block Ads", list_ids
            )
        elif len(cf_policies) != 1:
            logger.error("More than one firewall policy found")
            raise Exception("More than one firewall policy found")
        else:
            logger.info("Updating firewall policy")
            cloudflare.update_gateway_policy(
                f"{self.name_prefix} Block Ads", cf_policies[0]["id"], list_ids
            )

        logger.info("Done")

    def leave(self):
        policy_prefix = f"{self.name_prefix} Block Ads"
        firewall_policies = cloudflare.get_firewall_policies(policy_prefix)

        for policy in firewall_policies:
            cloudflare.delete_gateway_policy(policy["id"])
        logger.info(f"Deleted gateway policies")

        cf_lists = cloudflare.get_lists(self.name_prefix)
        for l in cf_lists:
            logger.info(f"Deleting list {l['name']}")
            cloudflare.delete_list(l["name"], l["id"])
        logger.info("Deletion completed")

def main():
    parser = argparse.ArgumentParser(description="Cloudflare Manager Script")
    parser.add_argument("action", choices=["run", "leave"], help="Choose action: run or leave")
    args = parser.parse_args()
    adlist_name = "DNS-Filters"
    cloudflare_manager = CloudflareManager(adlist_name)
    if args.action == "run":
        cloudflare_manager.run()
    elif args.action == "leave":
        cloudflare_manager.leave()
    else:
        logger.error("Invalid action. Please choose either 'run' or 'leave'.")
        exit(1)

if __name__ == "__main__":
    main()
