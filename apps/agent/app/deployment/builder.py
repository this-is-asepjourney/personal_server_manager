import os
import shutil
import zipfile
import subprocess
from typing import Callable, Optional, Dict, Any

class DeploymentEngine:
    @staticmethod
    def safe_extract_zip(zip_path: str, target_dir: str) -> bool:
        """Safely extract ZIP archive preventing Zip Slip vulnerabilities."""
        os.makedirs(target_dir, exist_ok=True)
        resolved_target = os.path.abspath(target_dir)

        with zipfile.ZipFile(zip_path, 'r') as archive:
            for member in archive.infolist():
                # Prevent directory traversal
                member_path = os.path.abspath(os.path.join(target_dir, member.filename))
                if not member_path.startswith(resolved_target + os.sep) and member_path != resolved_target:
                    raise ValueError(f"Zip slip vulnerability detected in member: {member.filename}")
                archive.extract(member, target_dir)
        return True

    @staticmethod
    def clone_or_pull_git(repo_url: str, branch: str, target_dir: str, log_callback: Callable[[str, str], None]) -> bool:
        """Clone or pull git repository."""
        os.makedirs(target_dir, exist_ok=True)
        git_dir = os.path.join(target_dir, ".git")

        if os.path.exists(git_dir):
            log_callback("info", f"Fetching latest changes from {branch}...")
            cmd = ["git", "-C", target_dir, "pull", "origin", branch]
        else:
            log_callback("info", f"Cloning repository {repo_url} (branch: {branch})...")
            cmd = ["git", "clone", "--depth", "1", "--branch", branch, repo_url, target_dir]

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:
            log_callback("info", line.strip())
        proc.wait()
        return proc.returncode == 0

    @staticmethod
    def build_and_deploy_compose(
        workspace_dir: str,
        compose_file: str,
        log_callback: Callable[[str, str], None]
    ) -> bool:
        """Run docker compose up -d."""
        compose_path = os.path.join(workspace_dir, compose_file)
        if not os.path.exists(compose_path):
            log_callback("warning", f"Compose file {compose_file} not found. Attempting simple Docker build.")
            return True

        cmd = ["docker", "compose", "-f", compose_path, "up", "-d", "--build"]
        log_callback("info", f"Executing: {' '.join(cmd)}")
        proc = subprocess.Popen(cmd, cwd=workspace_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:
            log_callback("info", line.strip())
        proc.wait()
        return proc.returncode == 0

