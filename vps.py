from pathlib import Path

import paramiko

from config import read_env


def _connect_client() -> paramiko.SSHClient:
    target_host = read_env("TARGET_HOST", required=True)
    ssh_port = int(read_env("SSH_PORT", "22"))
    ssh_user = read_env("SSH_USER", required=True)
    ssh_password = read_env("SSH_PASSWORD", "")
    ssh_key_path = read_env("SSH_KEY_PATH", "")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    if ssh_key_path:
        client.connect(target_host, port=ssh_port, username=ssh_user, key_filename=ssh_key_path)
    else:
        client.connect(target_host, port=ssh_port, username=ssh_user, password=ssh_password)
    return client


def upload_compose_to_vps(project_name: str, compose_local_path: Path) -> None:
    ssh_base_dir = read_env("SSH_BASE_DIR", "/home/debian/apps")
    remote_dir = f"{ssh_base_dir}/{project_name}"
    remote_compose = f"{remote_dir}/docker-compose.yml"
    client = _connect_client()

    try:
        stdin, stdout, stderr = client.exec_command(f"mkdir -p {remote_dir}")
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            raise RuntimeError(stderr.read().decode("utf-8"))

        with client.open_sftp() as sftp:
            sftp.put(str(compose_local_path), remote_compose)
    finally:
        client.close()


def check_vps_health() -> None:
    client = _connect_client()
    try:
        stdin, stdout, stderr = client.exec_command("echo ok")
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            raise RuntimeError(stderr.read().decode("utf-8"))
    finally:
        client.close()
