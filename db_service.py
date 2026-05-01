import psycopg2

from config import get_api_url, get_frontend_url, read_env
from models import Ports

TABLE = "projects"
C_NAME = "name"
C_URL = "url"
C_HTTP = "http_port"
C_HTTPS = "https_port"


def db_connection():
    target_host = read_env("TARGET_HOST", required=True)
    return psycopg2.connect(
        host=target_host,
        port=int(read_env("PM_DB_PORT", "5432")),
        dbname=read_env("PM_DB_NAME", required=True),
        user=read_env("PM_DB_USER", required=True),
        password=read_env("PM_DB_PASSWORD", required=True),
    )


def find_next_ports(conn) -> Ports:
    sql = f"""
        SELECT
            COALESCE(MAX({C_HTTP}) FILTER (WHERE {C_HTTP} BETWEEN 3000 AND 3999), 3006) AS max_front_http,
            COALESCE(MAX({C_HTTPS}) FILTER (WHERE {C_HTTPS} BETWEEN 3000 AND 3999), 3007) AS max_front_https,
            COALESCE(MAX({C_HTTP}) FILTER (WHERE {C_HTTP} BETWEEN 4000 AND 4999), 4006) AS max_api_http,
            COALESCE(MAX({C_HTTPS}) FILTER (WHERE {C_HTTPS} BETWEEN 4000 AND 4999), 4007) AS max_api_https,
            COALESCE(MAX({C_HTTP}) FILTER (WHERE {C_HTTP} BETWEEN 5000 AND 5999), 5007) AS max_db_http,
            COALESCE(MAX({C_HTTPS}) FILTER (WHERE {C_HTTPS} BETWEEN 5000 AND 5999), 5008) AS max_db_https
        FROM public.{TABLE}
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone()

    return Ports(
        front_http=int(row[0]) + 2,
        front_https=int(row[1]) + 2,
        api_http=int(row[2]) + 2,
        api_https=int(row[3]) + 2,
        db_http=int(row[4]) + 1,
        db_https=int(row[5]) + 1,
    )


def ensure_project_not_exists(conn, project_name: str) -> None:
    front_url = get_frontend_url(project_name, trailing_slash=True)
    api_url = get_api_url(project_name, trailing_slash=True)

    sql = f"""
        SELECT 1
        FROM public.{TABLE}
        WHERE {C_NAME} IN (%s, %s, %s)
           OR {C_URL} IN (%s, %s)
        LIMIT 1
    """
    with conn.cursor() as cur:
        cur.execute(
            sql,
            (
                f"{project_name}-app",
                f"{project_name}-api",
                f"{project_name}-db",
                front_url,
                api_url,
            ),
        )
        exists = cur.fetchone() is not None

    if exists:
        raise RuntimeError(f"Le projet '{project_name}' existe deja dans la base.")


def insert_project_record(conn, project_name: str, ports: Ports) -> None:
    sql = f"""
        INSERT INTO public.{TABLE}
            ({C_NAME}, {C_URL}, {C_HTTP}, {C_HTTPS})
        VALUES (%s, %s, %s, %s)
    """
    front_url = get_frontend_url(project_name, trailing_slash=True)
    api_url = get_api_url(project_name, trailing_slash=True)
    with conn.cursor() as cur:
        rows = [
            (f"{project_name}-app", front_url, ports.front_http, ports.front_https),
            (f"{project_name}-api", api_url, ports.api_http, ports.api_https),
            (f"{project_name}-db", None, ports.db_http, ports.db_https),
        ]
        for row in rows:
            cur.execute(sql, row)
    conn.commit()


def check_db_health() -> None:
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
