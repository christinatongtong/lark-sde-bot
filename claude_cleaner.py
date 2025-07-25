import tempfile
import os
import subprocess
import asyncio
from dotenv import load_dotenv
from datetime import datetime
from github import Github
import traceback
import logging

# Get logger
logger = logging.getLogger(__name__)

load_dotenv()

from claude_code_sdk import (
    AssistantMessage,
    ClaudeCodeOptions,
    ResultMessage,
    UserMessage,
    TextBlock,
    ToolResultBlock,
    query,
)

SYSTEM_PROMPT = """
You are a codebase engineer. Product manager gives you a natural-language description of their desired changes to the UI. You will:

1. explore the codebase to understand the current structure
2. Make the necessary changes to implement the requested modification

"""

async def call_claude(repo_path, PM_prompt: str):

    options=ClaudeCodeOptions(
        system_prompt=SYSTEM_PROMPT,
        cwd=repo_path,
        allowed_tools=["Bash", "Edit", "Glob", "Grep", "LS", "MultiEdit"],
        permission_mode="acceptEdits",  # This skips all permission checks
        max_turns=6
    )

    TextBlock_msg = []
    # claude code's response
    async for message in query(
        prompt=PM_prompt,
        options=options,
    ):
        if isinstance(message, UserMessage):
            # ToolResultBlock
            for block in message.content:
                # TextBlock
                if isinstance(block, TextBlock):
                    print(block.text)

        else:
            print("OTHER MESSAGE: ", message)


class GitProcessor:
    """
    GitProcessor is a class that handles the git operations for the project.
    """

    def __init__(self, PM_prompt):
        self.PM_prompt = PM_prompt
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.git_repo_url = os.getenv('GIT_REPO_URL')

    def actions(self):
        self.git_clone()
        asyncio.run(call_claude(self.repo_path, self.PM_prompt))
        self.commit()
        return self.create_pr()

    def git_clone(self):
        # Fix: use self.github_token instead of github_toke
        git_repo_url_auth = self.git_repo_url.replace(
            'https://github.com/',
            f'https://{self.github_token}@github.com/'  # Add self.
        )

        if not self.github_token:
            logger.error("GITHUB_TOKEN not set")
            return {"error": "GITHUB_TOKEN not set"}

        # git clone to temporary space
        temp_dir = tempfile.mkdtemp()
        self.repo_path = os.path.join(temp_dir, "repo")

        if not os.path.exists(temp_dir):
            logger.error(f"temp dir does not exist: {temp_dir}")
            return {"error": f"temp dir does not exist: {temp_dir}"}

        subprocess.run([
            "git", "clone",
            git_repo_url_auth,
            self.repo_path
        ])

    def commit(self):

        # Create a new branch
        try:
            os.chdir(self.repo_path)
            self.branch = f"pm-thru-claude-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}"
            result = subprocess.run(["git", "branch", "--list", self.branch], check=True, capture_output=True, text=True)
            if result.stdout.strip():
                subprocess.run(["git", "checkout", self.branch], check=True)
            else:
                subprocess.run(["git", "checkout", "-b", self.branch], check=True)

        except Exception as e:
            logger.error(f"Error in git checkout: {e}")
            return {"error": str(e)}

        # check status, commit & push
        try:
            subprocess.run(["git", "add", "."], check=True)
            result = subprocess.run(["git", "status", "--porcelain"], check=True, capture_output=True, text=True)
            if result.stdout.strip():
                print("git status: ", result.stdout.strip())
            else:
                return {"error": "No changes to commit"}

        except Exception as e:
            logger.error(f"Error in git add and status: {e}")
            return {"error": str(e)}

        # commit and push
        try:
            subprocess.run(
                ["git", "commit", "-m", f"PM:{self.PM_prompt}"], check=True
            )
            subprocess.run(
                ["git", "push", "-u", "origin", self.branch],
                check=True
            )
        except Exception as e:
            logger.error(f"Error in commit and push: {e}")
            return {"error": str(e)}

    def create_pr(self):
        gh = Github(self.github_token)
        # Extract owner and repo name from URL
        repo_url = self.git_repo_url.rstrip(".git")
        owner, name = repo_url.split("/")[-2:]
        repo = gh.get_repo(f"{owner}/{name}")
        pr = repo.create_pull(
            title=self.PM_prompt,
            body=f"Automated changes per instruction: {self.PM_prompt}",
            head=self.branch,
            base="main"
        )

        return pr.html_url


if __name__ == "__main__":
    # Properly run the async function
    pm_message = """
    Can you make the submit button smaller?
    """
    prl_url = GitProcessor(pm_message).actions()
    print(prl_url)
