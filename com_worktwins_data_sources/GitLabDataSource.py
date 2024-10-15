# GitLabDataSource.py

import os
import requests
import subprocess
import logging
from com_worktwins_data_sources.WorkTwinsDataSource import WorkTwinsDataSource


class GitLabBatchCloner:
    def __init__(self, token=None):
        self.token = token  # Optional: GitLab token for authenticated requests

    def get_gitlab_repos(self, usernames):
        """
        Fetches repository URLs for the given GitLab usernames.
        Returns a tuple of (repo_count, clone_urls).
        """
        clone_urls = []
        for username in usernames:
            try:
                url = f"https://gitlab.com/api/v4/users/{username}/projects"
                headers = {}
                if self.token:
                    headers['Authorization'] = f"Bearer {self.token}"
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    repos = response.json()
                    for repo in repos:
                        clone_url = repo.get('http_url_to_repo')
                        if clone_url:
                            clone_urls.append(clone_url)
                else:
                    logging.warning(f"Failed to fetch repos for {username}: {response.status_code}")
            except Exception as e:
                logging.error(f"Error fetching repos for {username}: {e}")

        return len(clone_urls), clone_urls

    def clone_repos(self, clone_urls, destination_dir):
        """
        Clones the given repository URLs into the destination directory.
        """
        os.makedirs(destination_dir, exist_ok=True)
        for url in clone_urls:
            try:
                subprocess.run(['git', 'clone', url, destination_dir], check=True)
                logging.info(f"Cloned repository: {url}")
            except subprocess.CalledProcessError as e:
                logging.error(f"Failed to clone {url}: {e}")






class GitLabDataSource(WorkTwinsDataSource):
    def __init__(self, usernames, source_code_dir, progress_callback=None):
        super().__init__(source_code_dir, progress_callback)
        self.usernames = usernames
        self.total_repos = 0
        self.cloned_repos = 0
        self.data_source_name = 'gitlab'  # Set data source name

    def fetch_data(self):
        repo_count, clone_urls = self._get_gitlab_repos(self.usernames)
        self.total_repos = repo_count
        self.cloned_repos = 0
        if repo_count > 0:
            self._clone_repos(clone_urls, self.source_code_dir)
        else:
            logging.warning("No repositories found for the given GitLab usernames.")
            print("No repositories found for the given GitLab usernames.")

    def _get_gitlab_repos(self, usernames):
        repos = self._get_list_of_repositories_for_usernames(usernames)
        clone_urls = [repo['http_url_to_repo'] for repo in repos]
        total_repos = len(clone_urls)
        logging.info(f"Total GitLab repositories to process: {total_repos}")
        return total_repos, clone_urls

    def _get_list_of_repositories_for_usernames(self, usernames):
        all_repos = []
        for username in usernames:
            user_id = self._get_user_id(username)
            if user_id:
                page = 1
                while True:
                    url = f"https://gitlab.com/api/v4/users/{user_id}/projects?page={page}&per_page=100"
                    response = requests.get(url)
                    if response.status_code != 200:
                        logging.error(f"Failed to fetch repositories for user {username}. HTTP Status code: {response.status_code}")
                        print(f"Failed to fetch repositories for user {username}. HTTP Status code: {response.status_code}")
                        break
                    page_repos = response.json()
                    if not page_repos:
                        break
                    all_repos.extend(page_repos)
                    page += 1
                logging.info(f"Fetched {len(page_repos)} repositories for user {username}")
            else:
                logging.warning(f"Skipping user {username} due to missing user ID.")
                print(f"Skipping user {username} due to missing user ID.")
        return all_repos

    def _get_user_id(self, username):
        url = f"https://gitlab.com/api/v4/users?username={username}"
        response = requests.get(url)
        if response.status_code == 200:
            users = response.json()
            if users:
                return users[0]['id']
        logging.error(f"User {username} not found on GitLab.")
        print(f"User {username} not found on GitLab.")
        return None

    def _clone_or_update_repo(self, repo_url, dest_dir):
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        repo_path = os.path.join(dest_dir, repo_name)
        if not os.path.exists(repo_path):
            logging.info(f"Cloning {repo_url} into {repo_path}...")
            print(f"Cloning {repo_url} into {repo_path}...")
            result = subprocess.run(['git', 'clone', repo_url, repo_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                logging.error(f"Failed to clone {repo_url}: {result.stderr.decode()}")
                print(f"Failed to clone {repo_url}: {result.stderr.decode()}")
                return
        else:
            logging.info(f"Repository {repo_name} already exists. Pulling updates in {repo_path}...")
            print(f"Repository {repo_name} already exists. Pulling updates in {repo_path}...")
            # Fetch all branches
            result = subprocess.run(['git', '-C', repo_path, 'fetch', '--all'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                logging.error(f"Failed to fetch all branches for {repo_name}: {result.stderr.decode()}")
                print(f"Failed to fetch all branches for {repo_name}: {result.stderr.decode()}")
                return

            # Try to get the default branch
            result = subprocess.run(['git', '-C', repo_path, 'symbolic-ref', 'refs/remotes/origin/HEAD'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode == 0:
                default_branch = result.stdout.decode().strip().split('/')[-1]
            else:
                # Attempt to default to 'master'
                logging.warning(f"Failed to determine default branch for {repo_name}. Attempting to checkout 'master'.")
                print(f"Failed to determine default branch for {repo_name}. Attempting to checkout 'master'.")
                default_branch = 'master'

            # Checkout to the default branch and pull
            result = subprocess.run(['git', '-C', repo_path, 'checkout', default_branch], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                logging.error(f"Failed to checkout to {default_branch} for {repo_name}: {result.stderr.decode()}")
                print(f"Failed to checkout to {default_branch} for {repo_name}: {result.stderr.decode()}")
                return

            result = subprocess.run(['git', '-C', repo_path, 'pull', 'origin', default_branch], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                logging.error(f"Failed to pull latest changes for {repo_name} on branch {default_branch}: {result.stderr.decode()}")
                print(f"Failed to pull latest changes for {repo_name} on branch {default_branch}: {result.stderr.decode()}")
                return

        self.cloned_repos += 1
        logging.info(f"Successfully cloned/updated repository {repo_name}")
        if self.progress_callback:
            progress_value = int((self.cloned_repos / self.total_repos) * 100)
            self.progress_callback(progress_value)

    def _clone_repos(self, clone_urls, dest_dir):
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
            logging.info(f"Created directory {dest_dir}")
        for url in clone_urls:
            self._clone_or_update_repo(url, dest_dir)
