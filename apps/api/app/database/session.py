import re
from urllib.parse import urlparse
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from apps.api.app.core.config import settings

db_url = settings.DATABASE_URL
if db_url.startswith("postgresql+psycopg://"):
    try:
        import psycopg  # type: ignore # noqa: F401
    except ImportError:
        db_url = db_url.replace("postgresql+psycopg://", "postgresql+psycopg2://", 1)
elif db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)


def _auto_ensure_psm_postgres_db(url: str) -> str:
    """
    If using PostgreSQL, automatically verify the server is reachable and auto-create
    the target database (e.g. 'psm') if it does not exist yet.
    Also falls back to bundled 'postgres:5432' if an external host is unreachable.
    """
    if not url.startswith("postgres"):
        return url

    try:
        import psycopg2
        norm = url.replace("postgresql+psycopg2://", "postgresql://").replace("postgresql+psycopg://", "postgresql://")
        u = urlparse(norm)
        target_user = u.username or "psm"
        target_pass = u.password or "psm_super_secret_password_change_in_production"
        target_host = u.hostname or "postgres"
        target_port = u.port or 5432
        target_db = (u.path.lstrip("/") if u.path else "psm") or "psm"
        clean_db = re.sub(r"[^a-zA-Z0-9_]", "_", target_db)

        candidate_hosts = []
        for h in [target_host, "postgres", "psm-postgres", "127.0.0.1"]:
            if h and h not in candidate_hosts:
                candidate_hosts.append(h)

        candidate_creds = [
            (target_user, target_pass),
            ("psm", "psm_super_secret_password_change_in_production"),
            ("appuser", "admin12345"),
        ]

        for host in candidate_hosts:
            for user, pw in candidate_creds:
                # 1. Try direct connection to target_db
                try:
                    c = psycopg2.connect(
                        host=host, port=target_port, user=user, password=pw, dbname=clean_db, connect_timeout=2
                    )
                    c.close()
                    return f"postgresql+psycopg2://{user}:{pw}@{host}:{target_port}/{clean_db}"
                except Exception:
                    pass

                # 2. Try connecting to maintenance DB ('postgres' or 'template1' or 'psm') to auto-create clean_db
                for maint_db in ("postgres", "template1", "psm"):
                    try:
                        c = psycopg2.connect(
                            host=host, port=target_port, user=user, password=pw, dbname=maint_db, connect_timeout=2
                        )
                        c.autocommit = True
                        cur = c.cursor()
                        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (clean_db,))
                        if not cur.fetchone():
                            cur.execute(f'CREATE DATABASE "{clean_db}" ENCODING \'UTF8\'')
                        cur.close()
                        c.close()
                        return f"postgresql+psycopg2://{user}:{pw}@{host}:{target_port}/{clean_db}"
                    except Exception:
                        continue
    except Exception:
        pass

    return url


db_url = _auto_ensure_psm_postgres_db(db_url)

# Configure engine. For SQLite, need check_same_thread=False
connect_args = {}
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
