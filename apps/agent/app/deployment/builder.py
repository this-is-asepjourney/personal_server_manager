import os
import shutil
import zipfile
import subprocess
import re
from typing import Callable, Optional, Dict, Any, List

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
        """Clone or pull git repository with clean workspace reset."""
        os.makedirs(target_dir, exist_ok=True)
        git_dir = os.path.join(target_dir, ".git")

        if os.path.exists(git_dir):
            log_callback("info", f"[Git] Fetching latest changes from branch '{branch}'...")
            subprocess.run(["git", "-C", target_dir, "fetch", "origin", branch], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            cmd = ["git", "-C", target_dir, "reset", "--hard", f"origin/{branch}"]
        else:
            # If target dir exists but is not a clean git repo, clean it first
            if os.path.exists(target_dir) and os.listdir(target_dir):
                shutil.rmtree(target_dir, ignore_errors=True)
                os.makedirs(target_dir, exist_ok=True)
            log_callback("info", f"[Git] Cloning repository {repo_url} (branch: {branch})...")
            cmd = ["git", "clone", "--depth", "1", "--branch", branch, repo_url, target_dir]

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:
            clean = line.strip()
            if clean:
                log_callback("info", clean)
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
    def _get_compose_cmd() -> Optional[List[str]]:
        """Detect available Docker Compose executable (V2 plugin or standalone)."""
        docker_bin = shutil.which("docker") or "/usr/bin/docker"
        if os.path.exists(docker_bin) or shutil.which("docker"):
            try:
                res = subprocess.run([docker_bin, "compose", "version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=4)
                if res.returncode == 0:
                    return [docker_bin, "compose"]
            except Exception:
                pass

        dc_bin = shutil.which("docker-compose") or "/usr/local/bin/docker-compose"
        if os.path.exists(dc_bin) or shutil.which("docker-compose"):
            return [dc_bin]

        return None

    @staticmethod
    def build_and_deploy_compose(
        workspace_dir: str,
        compose_file: str,
        log_callback: Callable[[str, str], None]
    ) -> bool:
        """Execute docker compose up -d --build."""
        compose_path = os.path.join(workspace_dir, compose_file)
        if not os.path.exists(compose_path):
            log_callback("error", f"[Compose] Compose specification not found at {compose_path}")
            return False

        compose_cmd = DeploymentEngine._get_compose_cmd()
        if not compose_cmd:
            log_callback("error", "[Compose] Neither 'docker compose' (V2 plugin) nor 'docker-compose' was found in PATH.")
            return False

        cmd = [*compose_cmd, "-f", compose_file, "up", "-d", "--build", "--remove-orphans"]
        log_callback("info", f"[Compose] Launching stack: {' '.join(cmd)}")
        try:
            proc = subprocess.Popen(cmd, cwd=workspace_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in proc.stdout:
                clean = line.strip()
                if clean:
                    log_callback("info", clean)
            proc.wait()
            if proc.returncode != 0:
                log_callback("error", f"[Compose] Stack deployment failed with exit code {proc.returncode}")
                return False

            log_callback("info", f"[Compose] Stack deployed successfully!")
            return True
        except Exception as e:
            log_callback("error", f"[Compose] Process execution error: {e}")
            return False

    @staticmethod
    def _extract_port_args(full_df_path: str, workspace_dir: str, log_callback: Callable[[str, str], None]) -> List[str]:
        port_args: List[str] = []
        env_dict = DeploymentEngine._load_env_dict(workspace_dir)
        explicit_port = env_dict.get("PORT") or env_dict.get("HOST_PORT")
        if explicit_port and explicit_port.isdigit():
            port_args.extend(["-p", f"{explicit_port}:{explicit_port}"])
            log_callback("info", f"[Docker] Mapping port {explicit_port}:{explicit_port} from environment configuration")
            return port_args

        try:
            with open(full_df_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                matches = re.findall(r"EXPOSE\s+(\d+)", content, re.IGNORECASE)
                for port in matches:
                    port_args.extend(["-p", f"{port}:{port}"])
                    log_callback("info", f"[Docker] Detected EXPOSE {port}, mapping to host port {port}")
        except Exception:
            pass
        return port_args

    @staticmethod
    def _extract_ports_dict(full_df_path: str, workspace_dir: str, log_callback: Callable[[str, str], None]) -> Dict[str, int]:
        ports: Dict[str, int] = {}
        env_dict = DeploymentEngine._load_env_dict(workspace_dir)
        explicit_port = env_dict.get("PORT") or env_dict.get("HOST_PORT")
        if explicit_port and explicit_port.isdigit():
            p = int(explicit_port)
            ports[f"{p}/tcp"] = p
            log_callback("info", f"[Docker-SDK] Mapping container port {p} from environment")
            return ports

        try:
            with open(full_df_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                matches = re.findall(r"EXPOSE\s+(\d+)", content, re.IGNORECASE)
                for port in matches:
                    p = int(port)
                    ports[f"{p}/tcp"] = p
                    log_callback("info", f"[Docker-SDK] Detected EXPOSE {p}, mapping port")
        except Exception:
            pass
        return ports

    @staticmethod
    def _load_env_dict(workspace_dir: str) -> Dict[str, str]:
        env_dict: Dict[str, str] = {}
        env_file_path = os.path.join(workspace_dir, ".env")
        if os.path.exists(env_file_path):
            try:
                with open(env_file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            env_dict[k.strip()] = v.strip()
            except Exception:
                pass
        return env_dict

    @staticmethod
    def build_and_run_dockerfile(
        workspace_dir: str,
        dockerfile_path: str,
        image_tag: str,
        container_name: str,
        log_callback: Callable[[str, str], None]
    ) -> bool:
        """Build image using Dockerfile and launch container directly.
        Supports both Docker CLI and Python Docker SDK fallback via /var/run/docker.sock.
        """
        full_df_path = os.path.join(workspace_dir, dockerfile_path)
        if not os.path.exists(full_df_path):
            log_callback("error", f"[Docker] Dockerfile not found at {full_df_path}")
            return False

        sanitized_tag = re.sub(r"[^a-z0-9_.:-]", "-", image_tag.lower())
        sanitized_name = re.sub(r"[^a-zA-Z0-9_.-]", "-", container_name.lower())

        # 1. Check if Docker CLI is available
        docker_bin = shutil.which("docker") or "/usr/bin/docker"
        cli_available = False
        if os.path.exists(docker_bin) or shutil.which("docker"):
            try:
                chk = subprocess.run([docker_bin, "info"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=4)
                cli_available = (chk.returncode == 0)
            except Exception:
                cli_available = False

        if cli_available:
            log_callback("info", f"[Docker-CLI] Building image '{sanitized_tag}' from {dockerfile_path}...")
            build_cmd = [docker_bin, "build", "-t", sanitized_tag, "-f", dockerfile_path, "."]
            try:
                build_proc = subprocess.Popen(build_cmd, cwd=workspace_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                for line in build_proc.stdout:
                    clean = line.strip()
                    if clean:
                        log_callback("info", clean)
                build_proc.wait()
                if build_proc.returncode != 0:
                    log_callback("error", f"[Docker-CLI] Build failed with exit code {build_proc.returncode}")
                    return False
            except Exception as e:
                log_callback("error", f"[Docker-CLI] Build execution error: {e}")
                return False

            log_callback("info", f"[Docker-CLI] Image '{sanitized_tag}' built successfully.")

            # Stop & remove existing container
            log_callback("info", f"[Docker-CLI] Removing existing container '{sanitized_name}'...")
            subprocess.run([docker_bin, "stop", sanitized_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run([docker_bin, "rm", "-f", sanitized_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Ports & Run
            port_args = DeploymentEngine._extract_port_args(full_df_path, workspace_dir, log_callback)
            run_cmd = [docker_bin, "run", "-d", "--restart", "unless-stopped", "--name", sanitized_name]
            env_file_path = os.path.join(workspace_dir, ".env")
            if os.path.exists(env_file_path):
                run_cmd.extend(["--env-file", ".env"])
            run_cmd.extend(port_args)
            run_cmd.append(sanitized_tag)

            log_callback("info", f"[Docker-CLI] Running container: {' '.join(run_cmd)}")
            try:
                run_proc = subprocess.Popen(run_cmd, cwd=workspace_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                for line in run_proc.stdout:
                    clean = line.strip()
                    if clean:
                        log_callback("info", clean)
                run_proc.wait()
                if run_proc.returncode != 0:
                    log_callback("error", f"[Docker-CLI] Container launch failed with exit code {run_proc.returncode}")
                    return False

                log_callback("info", f"[Docker-CLI] Container '{sanitized_name}' is now running successfully!")
                return True
            except Exception as e:
                log_callback("error", f"[Docker-CLI] Launch execution error: {e}")
                return False

        # 2. FALLBACK: Use Python Docker SDK directly through /var/run/docker.sock
        log_callback("info", f"[Docker-SDK] CLI binary not in PATH. Utilizing Docker daemon socket connection...")
        try:
            import docker
            client = docker.from_env()
            client.ping()

            log_callback("info", f"[Docker-SDK] Building image '{sanitized_tag}' from {dockerfile_path}...")
            build_logs = client.api.build(
                path=workspace_dir,
                dockerfile=dockerfile_path,
                tag=sanitized_tag,
                rm=True,
                decode=True
            )
            for chunk in build_logs:
                if "stream" in chunk:
                    for line in chunk["stream"].splitlines():
                        clean = line.strip()
                        if clean:
                            log_callback("info", clean)
                elif "error" in chunk:
                    log_callback("error", chunk["error"].strip())
                    return False

            log_callback("info", f"[Docker-SDK] Image '{sanitized_tag}' built successfully.")

            # Stop & remove existing container
            try:
                existing = client.containers.get(sanitized_name)
                log_callback("info", f"[Docker-SDK] Removing existing container '{sanitized_name}'...")
                existing.stop(timeout=5)
                existing.remove(force=True)
            except Exception:
                pass

            # Extract ports & environment variables
            ports_mapping = DeploymentEngine._extract_ports_dict(full_df_path, workspace_dir, log_callback)
            env_dict = DeploymentEngine._load_env_dict(workspace_dir)

            log_callback("info", f"[Docker-SDK] Launching container '{sanitized_name}'...")
            c = client.containers.run(
                image=sanitized_tag,
                name=sanitized_name,
                detach=True,
                restart_policy={"Name": "unless-stopped"},
                ports=ports_mapping if ports_mapping else None,
                environment=env_dict if env_dict else None
            )
            log_callback("info", f"[Docker-SDK] Container '{sanitized_name}' ({c.short_id}) launched and operational!")
            return True
        except Exception as sdk_err:
            log_callback("error", f"[Docker-SDK] Failure via Docker daemon socket: {sdk_err}")
            return False
