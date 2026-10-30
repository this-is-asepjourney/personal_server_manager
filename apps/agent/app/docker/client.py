import subprocess
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class DockerManager:
    def __init__(self):
        self._sdk = None
        try:
            import docker
            self._sdk = docker.from_env()
        except Exception as e:
            logger.info(f"Docker SDK not available or daemon not running: {e}. Falling back to CLI.")

    def is_available(self) -> bool:
        if self._sdk:
            try:
                self._sdk.ping()
                return True
            except Exception:
                pass
        try:
            res = subprocess.run(["docker", "info"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
            return res.returncode == 0
        except Exception:
            return False

    def list_containers(self) -> List[Dict[str, Any]]:
        if not self.is_available():
            # Return empty or fallback
            return []

        try:
            # Query via docker CLI formatted json
            cmd = ["docker", "ps", "-a", "--format", "{{json .}}"]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
            containers = []
            for line in res.stdout.strip().split("\n"):
                if line.strip():
                    item = json.loads(line)
                    containers.append({
                        "docker_id": item.get("ID", ""),
                        "name": item.get("Names", "").replace("/", ""),
                        "image": item.get("Image", ""),
                        "status": "running" if "Up" in item.get("Status", "") else "stopped",
                        "state": item.get("State", ""),
                        "created": item.get("CreatedAt", ""),
                        "ports": item.get("Ports", "")
                    })
            return containers
        except Exception as e:
            logger.error(f"Error listing containers: {e}")
            return []

    def start_container(self, container_id: str) -> bool:
        try:
            res = subprocess.run(["docker", "start", container_id], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            return res.returncode == 0
        except Exception:
            return False

    def stop_container(self, container_id: str) -> bool:
        try:
            res = subprocess.run(["docker", "stop", container_id], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
            return res.returncode == 0
        except Exception:
            return False

    def restart_container(self, container_id: str) -> bool:
        try:
            res = subprocess.run(["docker", "restart", container_id], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
            return res.returncode == 0
        except Exception:
            return False

    def remove_container(self, container_id: str, force: bool = False) -> bool:
        try:
            args = ["docker", "rm"]
            if force:
                args.append("-f")
            args.append(container_id)
            res = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            return res.returncode == 0
        except Exception:
            return False

    def get_container_logs(self, container_id: str, tail: int = 100) -> str:
        try:
            res = subprocess.run(["docker", "logs", "--tail", str(tail), container_id], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
            return res.stdout or res.stderr
        except Exception as e:
            return f"Error reading logs: {e}"

docker_manager = DockerManager()

