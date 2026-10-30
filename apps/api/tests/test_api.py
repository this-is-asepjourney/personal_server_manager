import pytest
from fastapi.testclient import TestClient
from apps.api.app.main import app, init_db

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    init_db()

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def get_auth_token(client):
    login_res = client.post("/api/v1/auth/login", json={
        "email": "admin@psm.local",
        "password": "Admin12345!"
    })
    return login_res.json()["access_token"]

def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

def test_admin_login(client):
    res = client.post("/api/v1/auth/login", json={
        "email": "admin@psm.local",
        "password": "Admin12345!"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["email"] == "admin@psm.local"

def test_servers_list(client):
    token = get_auth_token(client)
    res = client.get("/api/v1/servers", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    servers = res.json()
    assert len(servers) >= 1
    server_names = [s["name"] for s in servers]
    assert "Homelab-Primary" in server_names

def test_create_server_and_agent_register(client):
    token = get_auth_token(client)
    # 1. Create server
    create_res = client.post(
        "/api/v1/servers",
        json={"name": "Worker-Node-01", "hostname": "worker01.local"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert create_res.status_code == 200
    server_info = create_res.json()
    server_id = server_info["server_id"]
    agent_token = server_info["agent_token"]

    # 2. Register agent
    reg_res = client.post(
        "/api/v1/agents/register",
        json={
            "server_id": server_id,
            "agent_token": agent_token,
            "agent_version": "0.1.0",
            "os_name": "Ubuntu Server",
            "architecture": "x86_64"
        }
    )
    assert reg_res.status_code == 200
    assert reg_res.json()["status"] == "registered"

    # 3. Heartbeat
    hb_res = client.post(
        "/api/v1/agents/heartbeat",
        json={"agent_id": "test-agent", "server_id": server_id, "status": "online"}
    )
    assert hb_res.status_code == 200

    # 4. Metrics
    met_res = client.post(
        "/api/v1/agents/metrics",
        json={
            "server_id": server_id,
            "cpu_usage": 15.2,
            "memory_usage": 44.0,
            "disk_usage": 35.0
        }
    )
    assert met_res.status_code == 200

def test_project_and_git_deployment(client):
    token = get_auth_token(client)
    # Get server
    servers = client.get("/api/v1/servers", headers={"Authorization": f"Bearer {token}"}).json()
    server_id = servers[0]["id"]

    # Create project
    proj_res = client.post(
        "/api/v1/projects",
        json={
            "server_id": server_id,
            "name": "sample-backend-api",
            "framework": "FastAPI",
            "source_type": "git",
            "repository_url": "https://github.com/example/api.git",
            "branch": "main"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert proj_res.status_code == 200
    project = proj_res.json()
    project_id = project["id"]

    # Trigger Git deployment
    dep_res = client.post(
        "/api/v1/deployments/git",
        json={"project_id": project_id, "branch": "main"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert dep_res.status_code == 200
    deployment = dep_res.json()
    assert deployment["status"] in ["preparing", "building", "queued"]
    assert deployment["version"] >= 1
