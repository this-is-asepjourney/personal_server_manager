import os
import shutil
import zipfile
import subprocess
import re
from typing import Callable, Optional, Dict, Any

class DeploymentEngine:
    @staticmethod
    def safe_extract_zip(zip_path: str, target_dir: str) -> bool:
        """Safely extract ZIP archive preventing Zip Slip vulnerabilities."""
        os.makedirs(target_dir, exist_ok=True)
        resolved_target = os.path.abspath(target_dir)

        with zipfile.ZipFile(zip_path, 'r') as archive:
            for member in archive.infolist():
                member_path = os.path.abspath(os.path.join(target_dir, member.filename))
                if not member_path.startswith(resolved_target + os.sep) and member_path != resolved_target:
                    raise ValueError(f"Zip slip vulnerability detected in member: {member.filename}")
                archive.extract(member, target_dir)
        return True

    @staticmethod
    def write_env_file(workspace_dir: str, env_vars: Optional[Dict[str, str]] = None) -> None:
        """Write decrypted environment variables to .env in workspace."""
        if not env_vars:
            return
        env_path = os.path.join(workspace_dir, ".env")
        lines = []
        for k, v in env_vars.items():
            clean_k = str(k).strip()
            clean_v = str(v).replace("\n", "\\n")
            lines.append(f"{clean_k}={clean_v}")
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    @staticmethod
    def clone_or_pull_git(
        repo_url: str,
        branch: str,
        target_dir: str,
        log_callback: Callable[[str, str], None],
        commit_hash: Optional[str] = None
    ) -> bool:
        """Clone or pull git repository."""
        os.makedirs(target_dir, exist_ok=True)
        git_dir = os.path.join(target_dir, ".git")

        if os.path.exists(git_dir):
            log_callback("info", f"[Git] Fetching latest changes from branch '{branch}'...")
            cmd = ["git", "-C", target_dir, "pull", "origin", branch]
        else:
            log_callback("info", f"[Git] Cloning repository {repo_url} (branch: {branch})...")
            cmd = ["git", "clone", "--depth", "1", "--branch", branch, repo_url, target_dir]

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:
            log_callback("info", line.strip())
        proc.wait()

        if proc.returncode != 0:
            return False

        if commit_hash and commit_hash != "HEAD":
            log_callback("info", f"[Git] Checking out commit {commit_hash}...")
            c_proc = subprocess.run(
                ["git", "-C", target_dir, "checkout", commit_hash],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            for line in c_proc.stdout.strip().split("\n"):
                if line.strip():
                    log_callback("info", line.strip())

        return True

    @staticmethod
    def build_and_deploy_compose(
        workspace_dir: str,
        compose_file: str,
        log_callback: Callable[[str, str], None]
    ) -> bool:
        """Execute docker compose up -d --build."""
        compose_path = os.path.join(workspace_dir, compose_file)
        if not os.path.exists(compose_path):
            return False

        cmd = ["docker", "compose", "-f", compose_file, "up", "-d", "--build", "--remove-orphans"]
        log_callback("info", f"[Compose] Launching stack: {' '.join(cmd)}")
        proc = subprocess.Popen(cmd, cwd=workspace_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:
            log_callback("info", line.strip())
        proc.wait()
        return proc.returncode == 0

    @staticmethod
    def build_and_run_dockerfile(
        workspace_dir: str,
        dockerfile_path: str,
        image_tag: str,
        container_name: str,
        log_callback: Callable[[str, str], None]
    ) -> bool:
        """Build image using Dockerfile and launch container directly."""
        full_df_path = os.path.join(workspace_dir, dockerfile_path)
        if not os.path.exists(full_df_path):
            log_callback("error", f"[Docker] Dockerfile not found at {full_df_path}")
            return False

        # 1. Build image
        log_callback("info", f"[Docker] Building image '{image_tag}' from {dockerfile_path}...")
        build_cmd = ["docker", "build", "-t", image_tag, "-f", dockerfile_path, "."]
        build_proc = subprocess.Popen(build_cmd, cwd=workspace_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in build_proc.stdout:
            log_callback("info", line.strip())
        build_proc.wait()

        if build_proc.returncode != 0:
            log_callback("error", f"[Docker] Image build failed with exit code {build_proc.returncode}")
            return False

        log_callback("info", f"[Docker] Image '{image_tag}' built successfully.")

        # 2. Stop and remove existing container if running
        sanitized_name = re.sub(r"[^a-zA-Z0-9_.-]", "-", container_name.lower())
        log_callback("info", f"[Docker] Checking for existing container '{sanitized_name}'...")
        subprocess.run(["docker", "stop", sanitized_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["docker", "rm", "-f", sanitized_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 3. Detect exposed ports from Dockerfile
        port_args = []
        try:
            with open(full_df_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                matches = re.findall(r"EXPOSE\s+(\d+)", content, re.IGNORECASE)
                for port in matches:
                    port_args.extend(["-p", f"{port}:{port}"])
                    log_callback("info", f"[Docker] Detected EXPOSE {port}, mapping to host port {port}")
        except Exception:
            pass

        # 4. Run new container
        run_cmd = ["docker", "run", "-d", "--restart", "unless-stopped", "--name", sanitized_name]
        env_file_path = os.path.join(workspace_dir, ".env")
        if os.path.exists(env_file_path):
            run_cmd.extend(["--env-file", ".env"])
        run_cmd.extend(port_args)
        run_cmd.append(image_tag)

        log_callback("info", f"[Docker] Running container: {' '.join(run_cmd)}")
        run_proc = subprocess.Popen(run_cmd, cwd=workspace_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in run_proc.stdout:
            log_callback("info", line.strip())
        run_proc.wait()

        if run_proc.returncode != 0:
            log_callback("error", f"[Docker] Container run failed with exit code {run_proc.returncode}")
            return False

        log_callback("info", f"[Docker] Container '{sanitized_name}' is now running!")
        return True
