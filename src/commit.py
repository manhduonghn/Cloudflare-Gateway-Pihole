import os
import base64
import requests

from loguru import logger 
from datetime import datetime, timedelta

github_token = os.getenv("GITHUB_TOKEN")
repo_owner = os.getenv("GITHUB_REPOSITORY_OWNER")
repo_name = os.getenv("GITHUB_REPOSITORY_NAME")

def auto_commit():
    try:
        response = requests.get(f'https://api.github.com/repos/{repo_owner}/{repo_name}/commits', headers={"Authorization": f"token {github_token}"})
        last_commit_date = datetime.strptime(response.json()[0]['commit']['author']['date'], "%Y-%m-%dT%H:%M:%SZ")
        current_date = datetime.utcnow()

        if current_date - last_commit_date > timedelta(days=30):
            commit_date = datetime.utcnow().strftime("%Y-%m-%d")
            commit_content = f"Commit date: {commit_date}"
            
            encoded_content = base64.b64encode(commit_content.encode('utf-8')).decode('utf-8')

            commit_message = "Auto commit"
            author_name = "Auto Commit Bot"
            author_email = "bot@example.com"

            response = requests.get(f'https://api.github.com/repos/{repo_owner}/{repo_name}/contents/keep-alive', headers={"Authorization": f"token {github_token}"})
            current_file_sha = response.json()['sha']

            data = {
                "message": commit_message,
                "content": encoded_content,
                "committer": {
                    "name": author_name,
                    "email": author_email
                },
                "sha": current_file_sha 
            }

            headers = {
                "Authorization": f"token {github_token}",
                "Content-Type": "application/json",
                "Accept": "application/vnd.github.v3+json"
            }

            response = requests.put(f'https://api.github.com/repos/{repo_owner}/{repo_name}/contents/keep-alive', headers=headers, json=data)

            if response.status_code == 200:
                logger.success("Auto commit successful")
            else:
                logger.error(f"Failed to create commit. Status code: {response.status_code}, Message: {response.text}")
        else:
            logger.warning("No need commit")

    except Exception as e:
        logger.error(f"Error: {e.__class__.__name__} - {str(e)}")
