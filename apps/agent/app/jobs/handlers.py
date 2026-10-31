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
    "system.prune",
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

def handle_system_prune(payload: Dict[str, Any], log_cb: Callable) -> Dict[str, Any]:
    all_images = payload.get("all_images", False)
    log_cb("info", f"Running Docker system prune (all_images={all_images})...")
    res = docker_manager.prune_system(all_images=all_images)
    log_cb("info", f"Prune completed. Output: {res.get('output', 'Success')}")
    return res

def handle_deployment_git(payload: Dict[str, Any], log_cb: Callable) -> Dict[str, Any]:
    project_id = payload.get("project_id")
    project_name = payload.get("project_name", f"proj-{project_id}")
    repo_url = payload.get("repository_url")
    branch = payload.get("branch", "main")
    commit_hash = payload.get("commit_hash")
    compose_path = payload.get("compose_path", "docker-compose.yml")
    dockerfile_path = payload.get("dockerfile_path", "Dockerfile")
    image_tag = payload.get("image_tag", f"{project_name}:latest")
    env_vars = payload.get("environment_variables", {})
    db_config = payload.get("database_config", {})

    target_dir = os.path.join(agent_settings.WORKSPACE_DIR, project_id)
    log_cb("info", f"[Deploy] Starting Git deployment for project '{project_name}'...")

    # 1. Clone or pull repository
    cloned = DeploymentEngine.clone_or_pull_git(repo_url, branch, target_dir, log_cb, commit_hash=commit_hash)
    if not cloned:
        raise RuntimeError("Failed to clone or pull git repository")

    # 2. Ensure PostgreSQL database exists & auto-connect environment secrets
    merged_env = DeploymentEngine.ensure_project_postgres_db(project_name, env_vars, db_config, log_cb)
    log_cb("info", f"[Deploy] Injecting {len(merged_env)} environment & PostgreSQL connection variable(s) into .env...")
    DeploymentEngine.write_env_file(target_dir, merged_env)

    # 3. Check for Compose vs Dockerfile
    deployed = False
    has_compose = os.path.exists(os.path.join(target_dir, compose_path))
    has_dockerfile = os.path.exists(os.path.join(target_dir, dockerfile_path))

    if has_compose:
        log_cb("info", f"[Deploy] Found Compose file '{compose_path}'. Building and launching stack...")
        deployed = DeploymentEngine.build_and_deploy_compose(target_dir, compose_path, log_cb)
    elif has_dockerfile:
        log_cb("info", f"[Deploy] Found Dockerfile '{dockerfile_path}'. Building image and running container...")
        deployed = DeploymentEngine.build_and_run_dockerfile(
            workspace_dir=target_dir,
            dockerfile_path=dockerfile_path,
            image_tag=image_tag,
            container_name=project_name,
            log_callback=log_cb
        )
    else:
        # Fallback check for any Dockerfile in root
        if os.path.exists(os.path.join(target_dir, "Dockerfile")):
            deployed = DeploymentEngine.build_and_run_dockerfile(
                workspace_dir=target_dir,
                dockerfile_path="Dockerfile",
                image_tag=image_tag,
                container_name=project_name,
                log_callback=log_cb
            )
        else:
            raise RuntimeError(f"Neither '{compose_path}' nor '{dockerfile_path}' was found in the repository root.")

    if not deployed:
        raise RuntimeError("Build or launch process failed. See deployment logs for details.")

    log_cb("info", f"[Deploy] Project '{project_name}' deployed successfully to Docker!")
    return {"success": True, "workspace": target_dir, "image_tag": image_tag}

def handle_deployment_zip(payload: Dict[str, Any], log_cb: Callable) -> Dict[str, Any]:
    project_id = payload.get("project_id")
    project_name = payload.get("project_name", f"proj-{project_id}")
    zip_path = payload.get("zip_path")
    image_tag = payload.get("image_tag", f"{project_name}:latest")
    dockerfile_path = payload.get("dockerfile_path", "Dockerfile")
    compose_path = payload.get("compose_path", "docker-compose.yml")
    env_vars = payload.get("environment_variables", {})
    db_config = payload.get("database_config", {})

    target_dir = os.path.join(agent_settings.WORKSPACE_DIR, project_id)

    log_cb("info", f"[Deploy] Extracting ZIP package into workspace {target_dir}...")
    DeploymentEngine.safe_extract_zip(zip_path, target_dir)

    merged_env = DeploymentEngine.ensure_project_postgres_db(project_name, env_vars, db_config, log_cb)
    log_cb("info", f"[Deploy] Injecting {len(merged_env)} environment & PostgreSQL connection variable(s) into .env...")
    DeploymentEngine.write_env_file(target_dir, merged_env)

    has_compose = os.path.exists(os.path.join(target_dir, compose_path))
    if has_compose:
        log_cb("info", f"[Deploy] Launching Docker Compose stack...")
        deployed = DeploymentEngine.build_and_deploy_compose(target_dir, compose_path, log_cb)
    else:
        log_cb("info", f"[Deploy] Launching Dockerfile build...")
        deployed = DeploymentEngine.build_and_run_dockerfile(
            workspace_dir=target_dir,
            dockerfile_path=dockerfile_path if os.path.exists(os.path.join(target_dir, dockerfile_path)) else "Dockerfile",
            image_tag=image_tag,
            container_name=project_name,
            log_callback=log_cb
        )

    if not deployed:
        raise RuntimeError("ZIP build or launch failed")

    log_cb("info", "[Deploy] ZIP deployment completed successfully.")
    return {"success": True, "workspace": target_dir}

def handle_deployment_rollback(payload: Dict[str, Any], log_cb: Callable) -> Dict[str, Any]:
    target_image = payload.get("target_image_tag")
    project_name = payload.get("project_name", "app")
    log_cb("warning", f"[Rollback] Initiating rollback to image: {target_image}...")
    sanitized_name = project_name.lower().replace(" ", "-")

    # Stop current container and run previous image tag
    subprocess.run(["docker", "stop", sanitized_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["docker", "rm", "-f", sanitized_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cmd = ["docker", "run", "-d", "--restart", "unless-stopped", "--name", sanitized_name, target_image]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    log_cb("info", proc.stdout.strip() if proc.stdout else "Container restarted with previous release image.")
    return {"success": True, "restored_image": target_image}

def handle_deployment_compose(payload: Dict[str, Any], log_cb: Callable) -> Dict[str, Any]:
    project_id = payload.get("project_id")
    project_name = payload.get("project_name", f"proj-{project_id}")
    compose_content = payload.get("compose_content", "")
    env_vars = payload.get("environment_variables", {})

    target_dir = os.path.join(agent_settings.WORKSPACE_DIR, project_id)
    os.makedirs(target_dir, exist_ok=True)

    log_cb("info", f"[Deploy] Writing docker-compose.yml for template project '{project_name}'...")
    compose_path = os.path.join(target_dir, "docker-compose.yml")
    with open(compose_path, "w", encoding="utf-8") as f:
        f.write(compose_content)

    if env_vars:
        log_cb("info", f"[Deploy] Injecting {len(env_vars)} environment configuration variables...")
        DeploymentEngine.write_env_file(target_dir, env_vars)

    log_cb("info", f"[Deploy] Starting containers via docker compose up -d...")
    deployed = DeploymentEngine.build_and_deploy_compose(target_dir, "docker-compose.yml", log_cb)
    if not deployed:
        raise RuntimeError(f"Failed to deploy compose stack '{project_name}'")

    log_cb("info", f"[Deploy] Template stack '{project_name}' successfully deployed and operational!")
    return {"success": True, "workspace": target_dir}

HANDLERS = {
    "server.ping": handle_server_ping,
    "container.start": handle_container_start,
    "container.stop": handle_container_stop,
    "container.restart": handle_container_restart,
    "container.remove": handle_container_remove,
    "system.prune": handle_system_prune,
    "deployment.git": handle_deployment_git,
    "deployment.zip": handle_deployment_zip,
    "deployment.compose": handle_deployment_compose,
    "deployment.rollback": handle_deployment_rollback,
}
