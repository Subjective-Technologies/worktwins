# com_worktwins_data_sources/GitHubDataSource.py

from com_worktwins_data_sources.WorkTwinsDataSource import WorkTwinsDataSource
import logging
import requests
import logging
import os
import subprocess

class GitHubBatchCloner:
    def __init__(self, token=None):
        self.token = token  # Optional: GitHub token for authenticated requests

    def get_github_repos(self, usernames):
        """
        Fetches repository URLs for the given GitHub usernames.
        Returns a tuple of (repo_count, clone_urls).
        """
        clone_urls = []
        for username in usernames:
            try:
                url = f"https://api.github.com/users/{username}/repos"
                headers = {}
                if self.token:
                    headers['Authorization'] = f"token {self.token}"
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    repos = response.json()
                    for repo in repos:
                        clone_url = repo.get('clone_url')
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




class GitHubDataSource(WorkTwinsDataSource):
    def __init__(self, usernames, source_code_dir, progress_callback=None, compress=0, amount_of_chunks=0, size_of_chunk=0):
        super().__init__(source_code_dir, progress_callback)
        self.usernames = usernames  # List of GitHub usernames
        self.data_source_name = 'github'
        self.compress = compress
        self.amount_of_chunks = amount_of_chunks
        self.size_of_chunk = size_of_chunk

    def fetch_data(self):
        """
        Fetches data from GitHub by cloning repositories for the provided usernames.
        """
        try:
            clone_client = GitHubBatchCloner()
            repo_count, clone_urls = clone_client.get_github_repos(self.usernames)
            logging.info(f"Found {repo_count} repositories for GitHub usernames: {', '.join(self.usernames)}")

            if repo_count > 0:
                clone_client.clone_repos(clone_urls, self.source_code_dir)
                logging.info(f"Cloned {repo_count} repositories into {self.source_code_dir}")
            else:
                logging.warning("No repositories found to clone.")
        except Exception as e:
            logging.error(f"Failed to fetch GitHub data: {e}")

    def get_github_username(self):
        """
        Returns the GitHub username(s) associated with this data source.
        If multiple usernames are provided, returns them joined by commas.
        """
        return ", ".join(self.usernames)
