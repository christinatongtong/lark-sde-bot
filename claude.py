import tempfile
import os
import subprocess
import asyncio
from dotenv import load_dotenv
from datetime import datetime
from github import Github

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


def git_push(PM_prompt: str):
    try:
        # Get environment variables
        github_token = os.getenv('GITHUB_TOKEN')
        git_repo_url = os.getenv('GIT_REPO_URL')
        git_repo_url_auth = git_repo_url.replace(
                'https://github.com/',
                f'https://{github_token}@github.com/'
            )

        if not github_token:
            return {"error": "GITHUB_TOKEN not set"}

        # git clone to temporary space
        temp_dir = tempfile.mkdtemp()
        repo_path = os.path.join(temp_dir, "repo")

        subprocess.run([
            "git", "clone",
            git_repo_url_auth,
            repo_path
        ])

        ### CALLING CLAUDE CODE SDK ###
        asyncio.run(call_claude(repo_path, PM_prompt))
        ### CALLING CLAUDE CODE SDK ###


        os.chdir(repo_path)
        print("repo_path: ", repo_path)

        # Create a new branch
        branch = f"pm-thru-claude-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}"
        result = subprocess.run(["git", "branch", "--list", branch], check=True, capture_output=True, text=True)
        if result.stdout.strip():
            subprocess.run(["git", "checkout", branch], check=True)
        else:
            subprocess.run(["git", "checkout", "-b", branch], check=True)

        # # check status, commit & push
        subprocess.run(["git", "add", "."], check=True)
        result = subprocess.run(["git", "status", "--porcelain"], check=True, capture_output=True, text=True)
        if result.stdout.strip():
            print("git status: ", result.stdout.strip())
        else:
            return {"error": "No changes to commit"}

        subprocess.run(
            ["git", "commit", "-m", f"PM:{PM_prompt}"], check=True
        )
        subprocess.run(
            ["git", "push", "-u", "origin", branch],
            check=True
        )

        # 3. Create PR
        gh = Github(github_token)
        # Extract owner and repo name from URL
        repo_url = git_repo_url.rstrip(".git")
        owner, name = repo_url.split("/")[-2:]
        repo = gh.get_repo(f"{owner}/{name}")
        pr = repo.create_pull(
            title=PM_prompt,
            body=f"Automated changes per instruction: {PM_prompt}",
            head=branch,
            base="main"
        )

        return pr.html_url

    except Exception as e:
        print(f"Error creating PR: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    # Properly run the async function
    pm_message = """
    Can you make the submit button smaller?
    """
    pr_url = git_push(pm_message)
    print(pr_url)
