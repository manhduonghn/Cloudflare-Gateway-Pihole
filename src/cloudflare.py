import requests
from src import CF_API_TOKEN, CF_IDENTIFIER, session
from tenacity import retry, stop_never, wait_random_exponential, retry_if_exception_type
from requests.exceptions import HTTPError, RequestException
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Tenacity settings
tenacity_settings = {
    'stop': stop_never,
    'wait': wait_random_exponential(multiplier=1, max=10),
    'retry': retry_if_exception_type((HTTPError, RequestException)),
    'after': lambda retry_state: logger.info(f"Retrying ({retry_state.attempt_number}): {retry_state.outcome.exception()}"),
    'before_sleep': lambda retry_state: logger.info(f"Sleeping before next retry ({retry_state.attempt_number})")
}

@retry(**tenacity_settings)
def get_lists(name_prefix: str):
    r = session.get(
        f"https://api.cloudflare.com/client/v4/accounts/{CF_IDENTIFIER}/gateway/lists",
    )
    if r.status_code != 200:
        raise Exception("Failed to get Cloudflare lists")
    lists = r.json()["result"] or []
    return [l for l in lists if l["name"].startswith(name_prefix)]

@retry(**tenacity_settings)
def create_list(name: str, domains: list[str]):
    r = session.post(
        f"https://api.cloudflare.com/client/v4/accounts/{CF_IDENTIFIER}/gateway/lists",
        json={
            "name": name,
            "description": "Ads & Tracking Domains",
            "type": "DOMAIN",
            "items": [{"value": domain} for domain in domains],
        },
    )
    if r.status_code != 200:
        raise Exception("Failed to create Cloudflare list")
    return r.json()["result"]

@retry(**tenacity_settings)
def delete_list(name: str, list_id: str):
    r = session.delete(
        f"https://api.cloudflare.com/client/v4/accounts/{CF_IDENTIFIER}/gateway/lists/{list_id}",
    )
    if r.status_code != 200:
        raise Exception("Failed to delete Cloudflare list")
    return r.json()["result"]

@retry(**tenacity_settings)
def get_firewall_policies(name_prefix: str):
    r = session.get(
        f"https://api.cloudflare.com/client/v4/accounts/{CF_IDENTIFIER}/gateway/rules",
    )
    if r.status_code != 200:
        raise Exception("Failed to get Cloudflare firewall policies")
    lists = r.json()["result"] or []
    return [l for l in lists if l["name"].startswith(name_prefix)]

@retry(**tenacity_settings)
def create_gateway_policy(name: str, list_ids: list[str]):
    r = session.post(
        f"https://api.cloudflare.com/client/v4/accounts/{CF_IDENTIFIER}/gateway/rules",
        json={
            "name": name,
            "description": "Block Ads & Tracking",
            "action": "block",
            "enabled": True,
            "filters": ["dns"],
            "traffic": "or".join([f"any(dns.domains[*] in ${l})" for l in list_ids]),
            "rule_settings": {
                "block_page_enabled": False,
            },
        },
    )
    if r.status_code != 200:
        raise Exception("Failed to create Cloudflare firewall policy")
    return r.json()["result"]

@retry(**tenacity_settings)
def update_gateway_policy(name: str, policy_id: str, list_ids: list[str]):
    r = session.put(
        f"https://api.cloudflare.com/client/v4/accounts/{CF_IDENTIFIER}/gateway/rules/{policy_id}",
        json={
            "name": name,
            "description": "Block Ads & Tracking",
            "action": "block",
            "enabled": True,
            "filters": ["dns"],
            "traffic": "or".join([f"any(dns.domains[*] in ${l})" for l in list_ids]),
            "rule_settings": {
                "block_page_enabled": False,
            },
        },
    )
    if r.status_code != 200:
        raise Exception("Failed to update Cloudflare firewall policy")
    return r.json()["result"]

@retry(**tenacity_settings)
def delete_gateway_policy(policy_id: str):    
    r = session.delete(
        f"https://api.cloudflare.com/client/v4/accounts/{CF_IDENTIFIER}/gateway/rules/{policy_id}",
    )
    if r.status_code != 200:
        raise Exception("Failed to delete Cloudflare gateway firewall policy")
    return r.json()["result"]
