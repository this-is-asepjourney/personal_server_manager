import asyncio
import json
import logging
import httpx
import websockets
from apps.agent.app.core.config import agent_settings
from apps.agent.app.collectors.metrics import get_metrics_snapshot
from apps.agent.app.collectors.system import get_system_info
from apps.agent.app.jobs.executor import JobExecutor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("psm-agent")

async def register_agent():
    """Initial handshake and registration with Control Plane."""
    url = f"{agent_settings.CONTROL_PLANE_URL}/api/v1/agents/register"
    sys_info = get_system_info()
    payload = {
        "server_id": agent_settings.SERVER_ID,
        "agent_token": agent_settings.AGENT_TOKEN,
        "agent_version": agent_settings.AGENT_VERSION,
        "os_name": sys_info["os_name"],
        "os_version": sys_info["os_version"],
        "architecture": sys_info["architecture"],
        "hostname": sys_info["hostname"]
    }
    logger.info(f"Registering with Control Plane at {url}...")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.post(url, json=payload)
            if res.status_code == 200:
                logger.info("Successfully registered with Control Plane.")
            else:
                logger.warning(f"Registration response: {res.status_code} - {res.text}")
    except Exception as e:
        logger.warning(f"Registration request error (will retry): {e}")

async def heartbeat_loop():
    """Sends heartbeat every 15s."""
    url = f"{agent_settings.CONTROL_PLANE_URL}/api/v1/agents/heartbeat"
    while True:
        try:
            payload = {
                "agent_id": f"agent-{agent_settings.SERVER_ID}",
                "server_id": agent_settings.SERVER_ID,
                "agent_version": agent_settings.AGENT_VERSION,
                "status": "online"
            }
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(url, json=payload)
        except Exception as e:
            logger.debug(f"Heartbeat failed: {e}")
        await asyncio.sleep(agent_settings.HEARTBEAT_INTERVAL)

async def metrics_loop():
    """Collects & reports CPU, RAM, Disk, Network every 5s."""
    url = f"{agent_settings.CONTROL_PLANE_URL}/api/v1/agents/metrics"
    while True:
        try:
            metrics = get_metrics_snapshot()
            metrics["server_id"] = agent_settings.SERVER_ID
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(url, json=metrics)
        except Exception as e:
            logger.debug(f"Metrics report failed: {e}")
        await asyncio.sleep(agent_settings.METRICS_INTERVAL)

async def websocket_loop():
    """Maintains persistent WebSocket connection to Control Plane for instant job delivery."""
    ws_base = agent_settings.CONTROL_PLANE_URL.replace("http://", "ws://").replace("https://", "wss://")
    ws_url = f"{ws_base}/api/v1/agents/connect?server_id={agent_settings.SERVER_ID}&token={agent_settings.AGENT_TOKEN}"

    retry_delay = 2
    while True:
        try:
            logger.info(f"Connecting to Control Plane WSS: {ws_url}")
            async with websockets.connect(ws_url) as ws:
                logger.info("Persistent WSS connection established.")
                retry_delay = 2
                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    if data.get("event") == "job.dispatch":
                        logger.info(f"Received job dispatch: {data.get('job_type')} (id: {data.get('job_id')})")
                        # Run job executor in thread pool
                        asyncio.get_event_loop().run_in_executor(
                            None,
                            JobExecutor.execute_job,
                            data.get("job_id"),
                            data.get("job_type"),
                            data.get("server_id"),
                            data.get("payload")
                        )
        except Exception as e:
            logger.warning(f"WebSocket disconnected or failed ({e}). Reconnecting in {retry_delay}s...")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 30)

async def main():
    logger.info(f"Starting PSM Agent v{agent_settings.AGENT_VERSION} for server '{agent_settings.SERVER_ID}'")
    await register_agent()
    await asyncio.gather(
        heartbeat_loop(),
        metrics_loop(),
        websocket_loop()
    )

if __name__ == "__main__":
    asyncio.run(main())

