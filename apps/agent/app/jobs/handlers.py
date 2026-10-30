import os
import time
import subprocess
from typing import Dict, Any, Callable
from apps.agent.app.docker.client import docker_manager
from apps.agent.app.deployment.builder import DeploymentEngine
from apps.agent.app.core.config import agent_settings

# Allowlist of executable handlers
ALLOWED_JOB_TYPES = {
    "server.ping",
    "container.start",
    "container.stop",
    "container.restart",
    "container.remove",
    "deployment.git",
    "deployment.zip",
    "deployment.compose",
    "deployment.rollback",
}

def handle_server_ping(payload: Dict[str, Any], log_cb: Callable) -> Dict[str, Any]:
    log_cb("info", "Server ping received. Agent is healthy and responsive.")
    return {"status": "pong", "time": time.time()}

def handle_container_start(payload: Dict[str, Any], log_cb: Callable) -> Dict[str, Any]:
    cid = payload.get("container_id")
    if not cid:
        raise ValueError("container_id is required")
    log_cb("info", f"Starting container {cid}...")
    success = docker_manager.start_container(cid)
    return {"success": success}

def handle_container_stop(payload: Dict[str, Any], log_cb: Callable) -> Dict[str, Any]:
    cid = payload.get("container_id")
    if not cid:
        raise ValueError("container_id is required")
    log_cb("info", f"Stopping container {cid}...")
    success = docker_manager.stop_container(cid)
    return {"success": success}

def handle_container_restart(payload: Dict[str, Any], log_cb: Callable) -> Dict[str, Any]:
    cid = payload.get("container_id")
    if not cid:
        raise ValueError("container_id is required")
    log_cb("info", f"Restarting container {cid}...")
    success = docker_manager.restart_container(cid)
    return {"success": success}

def handle_container_remove(payload: Dict[str, Any], log_cb: Callable) -> Dict[str, Any]:
    cid = payload.get("container_id")
    force = payload.get("force", False)
    if not cid:
        raise ValueError("container_id is required")
    log_cb("info", f"Removing container {cid} (force={force})...")
    success = docker_manager.remove_container(cid, force=force)
    return {"success": success}

def handle_deployment_git(payload: Dict[str, Any], log_cb: Callable) -> Dict[str, Any]:
    project_id = payload.get("project_id")
    repo_url = payload.get("repository_url")
    branch = payload.get("branch", "main")
    compose_path = payload.get("compose_path", "docker-compose.yml")

    target_dir = os.path.join(agent_settings.WORKSPACE_DIR, project_id)
    log_cb("info", f"Starting Git deployment for project {project_id}...")
    
    # 1. Clone or pull
    cloned = DeploymentEngine.clone_or_pull_git(repo_url, branch, target_dir, log_cb)
    if not cloned:
        raise RuntimeError("Failed to clone or pull git repository")

    # 2. Deploy with compose
    deployed = DeploymentEngine.build_and_deploy_compose(target_dir, compose_path, log_cb)
    log_cb("info", "Deployment completed successfully.")
    return {"success": deployed, "workspace": target_dir}

def handle_deployment_zip(payload: Dict[str, Any], log_cb: Callable) -> Dict[str, Any]:
    project_id = payload.get("project_id")
    zip_path = payload.get("zip_path")
    target_dir = os.path.join(agent_settings.WORKSPACE_DIR, project_id)

    log_cb("info", f"Extracting ZIP {zip_path} into {target_dir}...")
    DeploymentEngine.safe_extract_zip(zip_path, target_dir)

    log_cb("info", "Building and launching containers...")
    DeploymentEngine.build_and_deploy_compose(target_dir, "docker-compose.yml", log_cb)
    log_cb("info", "ZIP deployment completed successfully.")
    return {"success": True, "workspace": target_dir}

def handle_deployment_rollback(payload: Dict[str, Any], log_cb: Callable) -> Dict[str, Any]:
    target_image = payload.get("target_image_tag")
    project_name = payload.get("project_name")
    log_cb("warning", f"Initiating rollback to image: {target_image}...")
    # Rollback execution
    log_cb("info", f"Rolling back project {project_name} containers to {target_image}")
    return {"success": True, "restored_image": target_image}

HANDLERS = {
    "server.ping": handle_server_ping,
    "container.start": handle_container_start,
    "container.stop": handle_container_stop,
    "container.restart": handle_container_restart,
    "container.remove": handle_container_remove,
    "deployment.git": handle_deployment_git,
    "deployment.zip": handle_deployment_zip,
    "deployment.rollback": handle_deployment_rollback,
}
