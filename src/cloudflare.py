import json
from src import (
    CF_API_TOKEN, CF_IDENTIFIER, rate_limited_request, send_request, retry_config
)
from src.colorlog import logger 

@retry(**retry_config)
def get_lists(name_prefix: str):
    response = send_request("GET", "gateway/lists")
    lists = response["result"] or []
    return [l for l in lists if l["name"].startswith(name_prefix)]

@retry(**retry_config)
@rate_limited_request
def create_list(name: str, domains: list[str]):
    body = {
        "name": name,
        "description": "Ads & Tracking Domains",
        "type": "DOMAIN",
        "items": [{"value": domain} for domain in domains],
    }
    response = send_request("POST", "gateway/lists", body)
    return response["result"]

@retry(**retry_config)
@rate_limited_request
def delete_list(name: str, list_id: str):
    response = send_request("DELETE", f"gateway/lists/{list_id}")
    return response["result"]

@retry(**retry_config)
def get_firewall_policies(name_prefix: str):
    response = send_request("GET", "gateway/rules")
    lists = response["result"] or []
    return [l for l in lists if l["name"].startswith(name_prefix)]

@retry(**retry_config)
def create_gateway_policy(name: str, list_ids: list[str]):
    body = {
        "name": name,
        "description": "Block Ads & Tracking",
        "action": "block",
        "enabled": True,
        "filters": ["dns"],
        "traffic": "or".join([f"any(dns.domains[*] in ${l})" for l in list_ids]),
        "rule_settings": {
            "block_page_enabled": False,
        },
    }
    response = send_request("POST", "gateway/rules", body)
    return response["result"]

@retry(**retry_config)
def update_gateway_policy(name: str, policy_id: str, list_ids: list[str]):
    body = {
        "name": name,
        "description": "Block Ads & Tracking",
        "action": "block",
        "enabled": True,
        "filters": ["dns"],
        "traffic": "or".join([f"any(dns.domains[*] in ${l})" for l in list_ids]),
        "rule_settings": {
            "block_page_enabled": False,
        },
    }
    response = send_request("PUT", f"gateway/rules/{policy_id}", body)
    return response["result"]

@retry(**retry_config)
def delete_gateway_policy(policy_id: str):    
    response = send_request("DELETE", f"gateway/rules/{policy_id}")
    return response["result"]
