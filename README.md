# Project Generator

<a href="README-fr.md">fr</a>

Automates the creation of a new project with:

- Angular Dockerfile  
- Spring Boot Dockerfile  
- `docker-compose.yml`  
- Copy of the compose file to the VPS  
- Automatic port allocation from the `project-manager` database  
- Insertion of the 3 services (`app`, `api`, `db`) into `public.projects`  

## Prerequisites

- Python 3.10+  
- PostgreSQL access to the `project-manager` database  
- SSH access to the OVH VPS  

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Configuration

Copy the example file:

```bash
copy .env.example .env
```

Main variables:

- `TARGET_HOST`: common host for PostgreSQL + VPS SSH (required)  
- `BASE_DOMAIN`: root domain (e.g., `alexandre-vernet.fr`)  
- `PM_DB_PORT`, `PM_DB_NAME`, `PM_DB_USER`, `PM_DB_PASSWORD`  
- `SSH_PORT`, `SSH_USER`, `SSH_PASSWORD` or `SSH_KEY_PATH`  
- `SSH_BASE_DIR` (default: `/home/debian/apps`)  

## Run the generator

By default, files are generated in `~/Downloads/<project-name>`:

```bash
python generator.py --project-name my-project
```

With a custom directory:

```bash
python generator.py --project-name my-project --output-dir "C:\Users\JohnDoe\Downloads\my-projects\my-project"
```

With the Windows script (`.bat`):

```bat
create_project.bat
```

## What the script does

1. Checks that the project does not already exist in `public.projects`  
2. Calculates the next available ports by range:
   - Frontend: `3000-3999`
   - API: `4000-4999`
   - DB: `5000-5999`
3. Generates:
   - `<project>-app/Dockerfile`
   - `<project>-app/nginx.conf`
   - `<project>-api/Dockerfile`
   - `docker-compose.yml`
   - `.github/workflows/docker-build-deploy.yml`
4. Creates `/home/debian/apps/<project>` on the VPS and copies the compose file there  
5. Inserts into `public.projects`:
   - `<project>-app` with URL `https://<project>.<BASE_DOMAIN>/`
   - `<project>-api` with URL `https://<project>-api.<BASE_DOMAIN>/`
   - `<project>-db` with URL `NULL`
6. Displays a summary with:
   - allocated ports  
   - URLs to create  
   - redirection IP (`TARGET_HOST`)  
   - OVH + Nginx Proxy Manager links  

## Application source generation

Angular:

```bash
ng new my-project-app --routing --style=scss --skip-git
```

Spring Initializr:

```text
https://start.spring.io/#!type=maven-project&language=java&groupId=com.example&artifactId=my-project-api&name=my-project-api&packageName=com.example.myworkoutapi&packaging=jar&javaVersion=17&dependencies=web,data-jpa,postgresql,flyway,lombok,validation,security
```