from contextlib import asynccontextmanager
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from apps.api.app.core.config import settings
from apps.api.app.core.security import hash_password
from apps.api.app.database.session import engine, Base, SessionLocal
from apps.api.app.models.entities import User, Server, Container, ServerMetric, Project, ProjectSource
from apps.api.app.api.v1.router import api_router
from apps.api.app.websocket.handlers import ws_router

def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Seed default admin user
        admin = db.query(User).filter(User.email == "admin@psm.local").first()
        if not admin:
            admin = User(
                name="PSM Administrator",
                email="admin@psm.local",
                password_hash=hash_password("Admin12345!"),
                role="owner",
                theme="system",
                is_active=True
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)

        # Seed initial local server for homelab if no servers exist
        server_count = db.query(Server).count()
        if server_count == 0:
            local_server = Server(
                owner_id=admin.id,
                name="Homelab-Primary",
                hostname="ubuntu-homelab.local",
                description="Primary Ubuntu Server (HomeLab)",
                os_name="Ubuntu Server",
                os_version="24.04 LTS",
                architecture="x86_64",
                status="online"
            )
            db.add(local_server)
            db.commit()
            db.refresh(local_server)

            # Add demo containers for homelab
            containers = [
                Container(
                    server_id=local_server.id,
                    docker_id="d1a2b3c4d5e6",
                    name="nextcloud-app",
                    image="nextcloud:latest",
                    status="running",
                    state="running",
                    ports=[{"internal": 80, "external": 80, "protocol": "tcp"}]
                ),
                Container(
                    server_id=local_server.id,
                    docker_id="e2b3c4d5e6f7",
                    name="prometheus",
                    image="prom/prometheus:v2.50.0",
                    status="running",
                    state="running",
                    ports=[{"internal": 9090, "external": 9001, "protocol": "tcp"}]
                ),
                Container(
                    server_id=local_server.id,
                    docker_id="f3c4d5e6f7a8",
                    name="grafana",
                    image="grafana/grafana:10.4.0",
                    status="running",
                    state="running",
                    ports=[{"internal": 3000, "external": 3001, "protocol": "tcp"}]
                ),
                Container(
                    server_id=local_server.id,
                    docker_id="a4b5c6d7e8f9",
                    name="uptime-kuma",
                    image="louislam/uptime-kuma:1",
                    status="running",
                    state="running",
                    ports=[{"internal": 3001, "external": 3002, "protocol": "tcp"}]
                )
            ]
            db.add_all(containers)

            # Add sample metrics
            metric = ServerMetric(
                server_id=local_server.id,
                cpu_usage=24.5,
                memory_usage=58.2,
                memory_used_bytes=2415919104, # ~2.25 GB
                memory_total_bytes=4294967296, # 4 GB
                disk_usage=42.0,
                disk_used_bytes=107374182400, # 100 GB
                disk_total_bytes=256000000000, # 256 GB
                network_rx=142050.0,
                network_tx=98200.0,
                uptime=345600 # 4 days
            )
            db.add(metric)

            # Add a sample project
            demo_project = Project(
                server_id=local_server.id,
                owner_id=admin.id,
                name="portfolio-website",
                description="Personal developer website and blog",
                framework="Next.js",
                source_type="git",
                status="active"
            )
            db.add(demo_project)
            db.commit()
            db.refresh(demo_project)

            src = ProjectSource(
                project_id=demo_project.id,
                repository_url="https://github.com/example/portfolio.git",
                branch="main",
                dockerfile_path="Dockerfile",
                compose_path="docker-compose.yml"
            )
            db.add(src)
            db.commit()

    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    yield
    # Shutdown

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Personal Server Manager (PSM) - Self-hosted Multi-Server Management Platform",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(ws_router)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "PSM Control Plane API",
        "version": settings.VERSION
    }

@app.get("/install-agent.sh")
def get_agent_install_script():
    script_content = """#!/usr/bin/env bash
set -e
echo "========================================="
echo "Personal Server Manager (PSM) Agent Setup"
echo "========================================="

if [ -z "$PSM_SERVER_ID" ] || [ -z "$PSM_TOKEN" ]; then
  echo "Error: PSM_SERVER_ID and PSM_TOKEN environment variables are required."
  exit 1
fi

PSM_CONTROL_PLANE="${PSM_CONTROL_PLANE:-http://localhost:8000}"
INSTALL_DIR="/opt/psm/agent"

echo "Target Control Plane: $PSM_CONTROL_PLANE"
echo "Server ID: $PSM_SERVER_ID"

mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Write agent configuration
cat <<EOF > agent.env
SERVER_ID=$PSM_SERVER_ID
AGENT_TOKEN=$PSM_TOKEN
CONTROL_PLANE_URL=$PSM_CONTROL_PLANE
EOF

echo "PSM Agent configured successfully at $INSTALL_DIR/agent.env"
"""
    return Response(content=script_content, media_type="text/x-shellscript")

