import argparse
import socket
from pathlib import Path

import paramiko
import psycopg2
from config import get_api_url, get_base_domain, get_frontend_url, load_environment, read_env, slugify_project_name
from db_service import db_connection, ensure_project_not_exists, find_next_ports, insert_project_record
from filesystem_service import create_angular_nginx_conf, write_file
from templates import (
    BACK_DOCKERFILE_TEMPLATE,
    FRONT_DOCKERFILE_TEMPLATE,
    render_compose,
    render_github_actions_workflow,
)
from vps import upload_compose_to_vps


def main() -> None:
    working_root = Path.cwd()
    load_environment(working_root)

    parser = argparse.ArgumentParser(description="Generateur de projet full-stack Angular + Spring + PostgreSQL")
    parser.add_argument("--project-name", required=True, help="Nom projet, ex: my-project")
    parser.add_argument(
        "--output-dir",
        default="",
        help="Dossier de generation. Par defaut: ~/Downloads/<project-name>",
    )

    args = parser.parse_args()

    project_name = slugify_project_name(args.project_name)
    output_root = Path(args.output_dir).expanduser() if args.output_dir else (Path.home() / "Downloads" / project_name)
    output_root.mkdir(parents=True, exist_ok=True)
    front_dir_name = f"{project_name}-app"
    back_dir_name = f"{project_name}-api"

    try:
        with db_connection() as conn:
            ensure_project_not_exists(conn, project_name)
            ports = find_next_ports(conn)

           
            (output_root / front_dir_name).mkdir(exist_ok=True)
            (output_root / back_dir_name).mkdir(exist_ok=True)
            create_angular_nginx_conf(output_root / front_dir_name)
            write_file(
                output_root / front_dir_name / "Dockerfile",
                FRONT_DOCKERFILE_TEMPLATE.format(frontend_dir=front_dir_name),
            )
            write_file(
                output_root / back_dir_name / "Dockerfile",
                BACK_DOCKERFILE_TEMPLATE.format(backend_dir=back_dir_name),
            )

            compose = render_compose(project_name, ports)
            compose_path = output_root / "docker-compose.yml"
            write_file(compose_path, compose)
            workflow_path = output_root / ".github" / "workflows" / "docker-build-deploy.yml"
            write_file(workflow_path, render_github_actions_workflow(project_name))

            upload_compose_to_vps(project_name, compose_path)
            insert_project_record(conn, project_name, ports)
    except RuntimeError as exc:
        print(f"Erreur de configuration: {exc}")
        raise SystemExit(1)
    except psycopg2.Error as exc:
        print(f"Erreur PostgreSQL: {exc}")
        raise SystemExit(1)
    except paramiko.SSHException as exc:
        print(f"Erreur SSH/VPS: {exc}")
        raise SystemExit(1)
    except (socket.gaierror, TimeoutError, OSError) as exc:
        print(f"Erreur reseau VPS (DNS/connexion): {exc}")
        raise SystemExit(1)

    print("Generation terminee.")
    print(f"Projet: {project_name}")
    print(f"Dossier genere: {output_root}")
    print(f"Front: {ports.front_http}/{ports.front_https}")
    print(f"API: {ports.api_http}/{ports.api_https}")
    print(f"DB: {ports.db_http}/{ports.db_https}")
    print("")
    print("Actions manuelles a faire:")
    print("1) Creer les noms de domaine (DNS OVH)")
    print(f"   - {get_frontend_url(project_name, trailing_slash=True)}")
    print(f"   - {get_api_url(project_name, trailing_slash=True)}")
    print(f"   - IP de redirection: {read_env('TARGET_HOST', required=True)}")
    print("   - OVH Manager: https://www.ovh.com/manager/")
    print("2) Creer les proxies dans Nginx Proxy Manager")
    print(f"   - NPM: https://nginx.{get_base_domain()}/")
    print("3) Generer les sources applicatives")
    print(f"   - Angular: ng new {front_dir_name} --routing --style=scss --skip-git")
    print("   - Spring Initializr:")
    print(f"     https://start.spring.io/#!type=maven-project&language=java&groupId=com.avernet&artifactId={back_dir_name}&name={back_dir_name}&packageName=com.example.{back_dir_name.replace('-', '')}&packaging=jar&javaVersion=17&dependencies=web,data-jpa,postgresql,flyway,lombok,validation,security, testcontainers")


if __name__ == "__main__":
    main()
