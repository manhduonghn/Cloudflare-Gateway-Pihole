import os
import json 
from src import (
    error,
    session,
    make_domains,
    silent_error,
    PREFIX,
    BASE_URL,
    MAX_LISTS,
    MAX_LIST_SIZE,
)

class App:
    def run(self):
        
        # Process domains lists
        converter = make_domains.DomainConverter()
        converter.process_urls()

        # Check if the file has changed
        if os.system("git diff --exit-code domains_ads.txt > /dev/null") == 0:
            silent_error("The domains list has not changed")

        # Ensure the file is not empty
        if os.path.getsize("domains_ads.txt") == 0:
            error("The domains list is empty")

        # Calculate the number of lines in the file
        with open("domains_ads.txt") as file:
            total_lines = len(file.readlines())

        # Ensure the file is not over the maximum allowed lines
        if total_lines > MAX_LIST_SIZE * MAX_LISTS:
            error(f"The domains list has more than {MAX_LIST_SIZE * MAX_LISTS} lines")

        # Calculate the number of lists required
        total_lists = total_lines // MAX_LIST_SIZE
        if total_lines % MAX_LIST_SIZE != 0:
            total_lists += 1
        
        response = session.get(f"{BASE_URL}/lists")
        if response.status_code == 200:
            current_lists = response.json()
        else:
            error("Failed to get current lists from Cloudflare")

        # Get current policies from Cloudflare
        response = session.get(f"{BASE_URL}/rules")
        if response.status_code == 200:
            current_policies = response.json()
        else:
            error("Failed to get current policies from Cloudflare")

        # Calculate the number of lists that have PREFIX in name
        try:
            current_lists_count = len([list_item for list_item in current_lists["result"] if PREFIX in list_item["name"]])
        except TypeError:
            current_lists_count = 0

        # Calculate the number of lists that don't have PREFIX in name
        try:
            current_lists_count_without_prefix = len([list_item for list_item in current_lists["result"] if PREFIX not in list_item["name"]])
        except TypeError:
            current_lists_count_without_prefix = 0

        # Ensure total_lists name is less than or equal to MAX_LISTS - current_lists_count_without_prefix
        if total_lists > MAX_LISTS - current_lists_count_without_prefix:
            error(f"The number of lists required ({total_lists}) is greater than the maximum allowed ({MAX_LISTS - current_lists_count_without_prefix})")

        # Split lists into chunks of MAX_LIST_SIZE
        os.system(f"split -l {MAX_LIST_SIZE} domains_ads.txt domains_ads.txt.")

        # Create array of chunked lists
        chunked_lists = [file for file in os.listdir() if file.startswith("domains_ads.txt.")]

        # Create array of used list IDs
        used_list_ids = []

        # Create array of excess list IDs
        excess_list_ids = []

        # Create list counter
        list_counter = current_lists_count + 1

        # Update existing lists
        if current_lists_count > 0:
            for list_item in current_lists["result"]:
                if PREFIX in list_item["name"]:
                    # If there are no more chunked lists, mark the list ID for deletion
                    if not chunked_lists:
                        print(f"Marking list {list_item['id']} for deletion...")
                        excess_list_ids.append(list_item['id'])
                        continue

                    print(f"Updating list {list_item['id']}...")

                    # Get list contents
                    response = session.get(
                        f"{BASE_URL}/lists/{list_item['id']}/items?limit={MAX_LIST_SIZE}"
                    )
                    if response.status_code == 200:
                        list_items = response.json()
                    else:
                        error(f"Failed to get list {list_item['id']} contents")

                    # Create list item values for removal
                    list_items_values = [item['value'] for item in list_items["result"] if item["value"] is not None]

                    # Create list item array for appending from the first chunked list
                    with open(chunked_lists[0]) as file:
                        list_items_array = [{"value": line.strip()} for line in file if line.strip()]

                    # Create payload
                    payload = {
                        "append": list_items_array,
                        "remove": list_items_values
                    }

                    # Patch list
                    response = session.patch(
                        f"{BASE_URL}/lists/{list_item['id']}",
                        json=payload
                    )
                    if response.status_code == 200:
                        list = response.json()
                    else:
                        error(f"Failed to patch list {list_item['id']}")

                    # Store the list ID
                    used_list_ids.append(list_item['id'])

                    # Delete the first chunked file
                    os.remove(chunked_lists[0])
                    chunked_lists.pop(0)

                    # Increment list counter
                    list_counter += 1

        # Create extra lists if required
        for file in chunked_lists:
            print("Creating list...")

            # Format list counter
            formatted_counter = f"{list_counter:03d}"

            # Create payload
            with open(file) as list_file:
                list_items = [{"value": line.strip()} for line in list_file if line.strip()]

            payload = {
                "name": f"{PREFIX} - {formatted_counter}",
                "type": "DOMAIN",
                "items": list_items
            }

            # Create list
            response = session.post(
                f"{BASE_URL}/lists",
                json=payload
            )
            if response.status_code == 200:
                list = response.json()
            else:
                error("Failed to create list")

            # Store the list ID
            used_list_ids.append(list["result"]["id"])

            # Delete the file
            os.remove(file)

            # Increment list counter
            list_counter += 1

        # Ensure policy called exactly PREFIX exists, else create it
        policy_id = None
        for policy_item in current_policies["result"]:
            if policy_item["name"] == PREFIX:
                policy_id = policy_item["id"]

        # Initialize an empty list to store conditions
        conditions = []

        # Loop through the used_list_ids and build the "conditions" array dynamically
        if len(used_list_ids) == 1:
            conditions = {
                "any": {
                    "in": {
                        "lhs": {
                            "splat": "dns.domains"
                        },
                        "rhs": f"${used_list_ids[0]}"
                    }
                }
            }
        else:
            for list_id in used_list_ids:
                conditions.append({
                    "any": {
                        "in": {
                            "lhs": {
                                "splat": "dns.domains"
                            },
                            "rhs": f"${list_id}"
                        }
                    }
                })

            conditions = {
                "or": conditions
            }

        # Create the JSON data dynamically
        json_data = {
            "name": PREFIX,
            "conditions": [
                {
                    "type": "traffic",
                    "expression": conditions
                }
            ],
            "action": "block",
            "enabled": True,
            "description": "",
            "rule_settings": {
                "block_page_enabled": False,
                "block_reason": "",
                "biso_admin_controls": {
                    "dcp": False,
                    "dcr": False,
                    "dd": False,
                    "dk": False,
                    "dp": False,
                    "du": False
                },
                "add_headers": {},
                "ip_categories": False,
                "override_host": "",
                "override_ips": None,
                "l4override": None,
                "check_session": None
            },
            "filters": ["dns"]
        }

        if not policy_id or policy_id == "null":
            # Create the policy
            print("Creating policy...")
            response = session.post(
                f"{BASE_URL}/rules",
                json=json_data
            )
            if response.status_code != 200:
                error("Failed to create policy")
        else:
            # Update the policy
            print(f"Updating policy {policy_id}...")
            response = session.put(
                f"{BASE_URL}/rules/{policy_id}",
                json=json_data
            )
            if response.status_code != 200:
                error("Failed to update policy")

        # Delete excess lists in excess_list_ids
        for list_id in excess_list_ids:
            print(f"Deleting list {list_id}...")
            response = session.delete(
                f"{BASE_URL}/lists/{list_id}"
            )
            if response.status_code != 200:
                error(f"Failed to delete list {list_id}")

        # Add, commit and push the file
        os.system("git config --global user.email \"{GITHUB_ACTOR_ID}+{GITHUB_ACTOR}@users.noreply.github.com\"")
        os.system("git config --global user.name \"$(gh api /users/${GITHUB_ACTOR} | jq .name -r)\"")
        os.system("git add domains_ads.txt")
        os.system("git commit -m \"Update domains list\" --author=.")
        os.system("git push origin main")


    def leave(self):

        # Get current lists from Cloudflare

        response = session.get(
            f"{BASE_URL}/lists"
        )
        current_lists = response.json()
        if response.status_code != 200:
            error(f"Failed to get current list")

        # Get current policies from Cloudflare
        response = session.get(
            f"{BASE_URL}/rules"
        )
        current_policies = response.json()
        if response.status_code != 200:
            error(f"Failed to get current policies")

        # Delete policy with PREFIX as name
        print("Deleting policy...")
        policy_id = next((policy["id"] for policy in current_policies["result"] if policy["name"] == PREFIX), None)
        if policy_id:
            session.delete(
                f"{BASE_URL}/rules/{policy_id}"
            )
            if response.status_code != 200:
                error(f"Failed to delete policy")

        # Delete all lists with PREFIX in name
        print("Deleting lists...")
        for lst in current_lists["result"]:
            if PREFIX in lst["name"]:
                print(f"Deleting list: {lst['name']}")
                session.delete(
                    f"{BASE_URL}/lists/{lst['id']}"
                )
                if response.status_code != 200:
                    error(f"Failed to delete list {lst['name']}")
