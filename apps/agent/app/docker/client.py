import subprocess
import json
import logging
from typing import List, Dict, Any

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
            return []

        if self._sdk:
            try:
                containers = []
                for c in self._sdk.containers.list(all=True):
                    ports_list = []
                    port_bindings = (c.attrs.get("NetworkSettings", {}).get("Ports") or {})
                    for internal_port, host_bindings in port_bindings.items():
                        internal_num = internal_port.split("/")[0]
                        proto = internal_port.split("/")[1] if "/" in internal_port else "tcp"
                        if host_bindings:
                            for hb in host_bindings:
                                ports_list.append({
                                    "internal": int(internal_num) if internal_num.isdigit() else internal_num,
                                    "external": int(hb.get("HostPort", internal_num)) if str(hb.get("HostPort", "")).isdigit() else internal_num,
                                    "protocol": proto,
                                })
                        else:
                            ports_list.append({
                                "internal": int(internal_num) if internal_num.isdigit() else internal_num,
                                "external": int(internal_num) if internal_num.isdigit() else internal_num,
                                "protocol": proto,
                            })
                    image_tags = c.image.tags if c.image and c.image.tags else [c.attrs.get("Config", {}).get("Image", "unknown")]
                    containers.append({
                        "docker_id": c.short_id,
                        "name": c.name,
                        "image": image_tags[0] if image_tags else "unknown",
                        "status": "running" if c.status == "running" else "stopped",
                        "state": c.status,
                        "ports": ports_list,
                    })
                return containers
            except Exception as e:
                logger.warning(f"SDK list_containers failed, trying CLI: {e}")

        try:
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
                        "state": item.get("State", "exited"),
                        "ports": [],
                    })
            return containers
        except Exception as e:
            logger.error(f"Error listing containers: {e}")
            return []

    def list_images(self) -> List[Dict[str, Any]]:
        if not self.is_available():
            return []
        try:
            cmd = ["docker", "images", "--format", "{{json .}}"]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
            images = []
            for line in res.stdout.strip().split("\n"):
                if line.strip():
                    item = json.loads(line)
                    images.append({
                        "id": item.get("ID", ""),
                        "repository": item.get("Repository", "<none>"),
                        "tag": item.get("Tag", "latest"),
                        "size": item.get("Size", "0 MB"),
                        "created": item.get("CreatedSince", "recently"),
                    })
            return images
        except Exception:
            return []

    def list_volumes(self) -> List[Dict[str, Any]]:
        if not self.is_available():
            return []
        try:
            cmd = ["docker", "volume", "ls", "--format", "{{json .}}"]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
            volumes = []
            for line in res.stdout.strip().split("\n"):
                if line.strip():
                    item = json.loads(line)
                    volumes.append({
                        "name": item.get("Name", ""),
                        "driver": item.get("Driver", "local"),
                        "mountpoint": item.get("Mountpoint", f"/var/lib/docker/volumes/{item.get('Name', '')}/_data"),
                    })
            return volumes
        except Exception:
            return []

    def list_networks(self) -> List[Dict[str, Any]]:
        if not self.is_available():
            return []
        try:
            cmd = ["docker", "network", "ls", "--format", "{{json .}}"]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
            networks = []
            for line in res.stdout.strip().split("\n"):
                if line.strip():
                    item = json.loads(line)
                    networks.append({
                        "name": item.get("Name", ""),
                        "driver": item.get("Driver", "bridge"),
                        "scope": item.get("Scope", "local"),
                    })
            return networks
        except Exception:
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
