import json
from src.requests import (
    rate_limited_request, retry, cloudflare_gateway_request, retry_config
)
from src.colorlog import logger

@retry(**retry_config)
def get_lists(name_prefix: str):
    status, response = cloudflare_gateway_request("GET", "/lists")
    lists = response["result"] or []
    return [l for l in lists if l["name"].startswith(name_prefix)]

@retry(**retry_config)
@rate_limited_request
def create_list(name: str, domains: list[str]):
    body = json.dumps({
        "name": name,
        "description": "Ads & Tracking Domains",
        "type": "DOMAIN",
        "items": [{"value": domain} for domain in domains],
    })
    status, response = cloudflare_gateway_request("POST", "/lists", body)
    return response["result"]

@retry(**retry_config)
@rate_limited_request
def delete_list(name: str, list_id: str):
    status, response = cloudflare_gateway_request("DELETE", f"/lists/{list_id}")
    return response["result"]

@retry(**retry_config)
def get_list_items(list_id: str):
    status, response = cloudflare_gateway_request("GET", f"/lists/{list_id}/items")
    return response["result"]

@retry(**retry_config)
@rate_limited_request
def patch_list(list_id: str, domains: list[str]):
    body = json.dumps({
        "items": [{"value": domain} for domain in domains],
    })
    status, response = cloudflare_gateway_request("PATCH", f"/lists/{list_id}", body)
    return response["result"]

@retry(**retry_config)
def get_firewall_policies(name_prefix: str):
    status, response = cloudflare_gateway_request("GET", "/rules")
    policies = response["result"] or []
    return [p for p in policies if p["name"].startswith(name_prefix)]

@retry(**retry_config)
def create_gateway_policy(name: str, list_ids: list[str]):
    body = json.dumps({
        "name": name,
        "description": "Block Ads & Tracking",
        "action": "block",
        "enabled": True,
        "filters": ["dns"],
        "traffic": "or".join([f"any(dns.domains[*] in ${l})" for l in list_ids]),
        "rule_settings": {
            "block_page_enabled": False,
        },
    })
    status, response = cloudflare_gateway_request("POST", "/rules", body)
    return response["result"]

@retry(**retry_config)
def update_gateway_policy(name: str, policy_id: str, list_ids: list[str]):
    body = json.dumps({
        "name": name,
        "description": "Block Ads & Tracking",
        "action": "block",
        "enabled": True,
        "filters": ["dns"],
        "traffic": "or".join([f"any(dns.domains[*] in ${l})" for l in list_ids]),
        "rule_settings": {
            "block_page_enabled": False,
        },
    })
    status, response = cloudflare_gateway_request("PUT", f"/rules/{policy_id}", body)
    return response["result"]

@retry(**retry_config)
def delete_gateway_policy(policy_id: str):
    status, response = cloudflare_gateway_request("DELETE", f"/rules/{policy_id}")
    return response["result"]
