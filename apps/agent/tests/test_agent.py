import pytest
import os
import zipfile
from apps.agent.app.collectors.metrics import get_metrics_snapshot, get_system_info
from apps.agent.app.jobs.handlers import ALLOWED_JOB_TYPES, handle_server_ping
from apps.agent.app.deployment.builder import DeploymentEngine

def test_system_and_metrics_collector():
    sys_info = get_system_info()
    assert "os_name" in sys_info
    assert "hostname" in sys_info

    metrics = get_metrics_snapshot()
    assert "cpu_usage" in metrics
    assert "memory_usage" in metrics
    assert "disk_usage" in metrics
    assert 0 <= metrics["cpu_usage"] <= 100
    assert 0 <= metrics["memory_usage"] <= 100

def test_allowed_job_types():
    assert "server.ping" in ALLOWED_JOB_TYPES
    assert "container.start" in ALLOWED_JOB_TYPES
    assert "system.prune" in ALLOWED_JOB_TYPES
    assert "deployment.git" in ALLOWED_JOB_TYPES
    assert "arbitrary.shell" not in ALLOWED_JOB_TYPES

def test_write_env_file(tmp_path):
    DeploymentEngine.write_env_file(str(tmp_path), {"PORT": "8080", "NODE_ENV": "production"})
    env_file = tmp_path / ".env"
    assert env_file.exists()
    content = env_file.read_text()
    assert "PORT=8080" in content
    assert "NODE_ENV=production" in content

def test_server_ping_handler():
    logs = []
    res = handle_server_ping({}, lambda level, msg: logs.append((level, msg)))
    assert res["status"] == "pong"
    assert len(logs) == 1

def test_safe_zip_extraction(tmp_path):
    zip_path = tmp_path / "test.zip"
    extract_dir = tmp_path / "extracted"

    # Create benign zip
    with zipfile.ZipFile(zip_path, "w") as z:
        z.writestr("index.js", "console.log('hello world');")

    success = DeploymentEngine.safe_extract_zip(str(zip_path), str(extract_dir))
    assert success is True
    assert (extract_dir / "index.js").exists()

def test_deployment_port_extraction_and_env(tmp_path):
    df_path = tmp_path / "Dockerfile"
    df_path.write_text("FROM alpine\nEXPOSE 3000\nCMD ['echo', 'hi']\n")

    logs = []
    args = DeploymentEngine._extract_port_args(str(df_path), str(tmp_path), lambda lvl, msg: logs.append(msg))
    assert "-p" in args
    assert "3000:3000" in args

    # Check env override
    env_file = tmp_path / ".env"
    env_file.write_text("PORT=8085\n")
    args_env = DeploymentEngine._extract_port_args(str(df_path), str(tmp_path), lambda lvl, msg: logs.append(msg))
    assert "8085:8085" in args_env

    # Missing Dockerfile handling
    res = DeploymentEngine.build_and_run_dockerfile(str(tmp_path), "MissingDockerfile", "tag:v1", "app", lambda l, m: None)
    assert res is False


