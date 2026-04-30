import os
import re
from pathlib import Path

from dotenv import load_dotenv


def load_environment(working_root: Path) -> None:
    env_path = working_root / ".env"
    load_dotenv(dotenv_path=env_path if env_path.exists() else None)


def read_env(name: str, default: str | None = None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(
            f"Variable d'environnement manquante: {name}. "
            "Cree un fichier .env a la racine (copie de .env.example) puis renseigne les variables."
        )
    return value or ""


def slugify_project_name(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9-]+", "-", name.strip().lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    if not slug:
        raise ValueError("Project name invalide.")
    return slug


def get_base_domain() -> str:
    return read_env("BASE_DOMAIN", "alexandre-vernet.fr", required=True)


def get_frontend_url(project_name: str, trailing_slash: bool = True) -> str:
    suffix = "/" if trailing_slash else ""
    return f"https://{project_name}.{get_base_domain()}{suffix}"


def get_api_url(project_name: str, trailing_slash: bool = True) -> str:
    suffix = "/" if trailing_slash else ""
    return f"https://{project_name}-api.{get_base_domain()}{suffix}"
