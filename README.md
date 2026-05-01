# Project Generator

Automatise la creation d'un nouveau projet avec:

- Dockerfile Angular
- Dockerfile Spring Boot
- `docker-compose.yml`
- Copie du compose sur le VPS
- Allocation automatique des ports depuis la base `project-manager`
- Insertion des 3 services (`app`, `api`, `db`) dans `public.projects`

## Prerequis

- Python 3.10+
- Acces PostgreSQL a la base `project-manager`
- Acces SSH au VPS OVH
- (Optionnel) Angular CLI et Java/Maven pour generer les sources applicatives

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Configuration

Copier le fichier d'exemple:

```bash
copy .env.example .env
```

Variables principales:

- `TARGET_HOST`: host commun pour PostgreSQL + SSH VPS (obligatoire)
- `BASE_DOMAIN`: domaine racine (ex: `alexandre-vernet.fr`)
- `PM_DB_PORT`, `PM_DB_NAME`, `PM_DB_USER`, `PM_DB_PASSWORD`
- `SSH_PORT`, `SSH_USER`, `SSH_PASSWORD` ou `SSH_KEY_PATH`
- `SSH_BASE_DIR` (par defaut `/home/debian/apps`)

## Lancer la generation

Par defaut, les fichiers sont generes dans `~/Downloads/<project-name>`:

```bash
python generator.py --project-name my-project
```

Avec un dossier personnalise:

```bash
python generator.py --project-name my-project --output-dir "C:\Users\JohnDoe\Downloads\mes-projets\my-project"
```

Options utiles:

- `--dry-run`: simulation complete (pas d'ecriture locale/DB/VPS)
- `--skip-vps`: ne fait pas l'upload VPS
- `--skip-db`: ne fait pas l'insertion DB
- `--only-files`: genere uniquement les fichiers (`--skip-vps --skip-db`)
- `--check`: verifie la connectivite DB/VPS puis quitte

## Ce que fait le script

1. Verifie que le projet n'existe pas deja dans `public.projects`
2. Calcule les prochains ports disponibles par tranche:
   - Front: `3000-3999`
   - API: `4000-4999`
   - DB: `5000-5999`
3. Genere:
   - `<project>-app/Dockerfile`
   - `<project>-app/nginx.conf`
   - `<project>-api/Dockerfile`
   - `docker-compose.yml`
   - `.github/workflows/docker-build-deploy.yml`
4. Cree `/home/debian/apps/<project>` sur le VPS et y copie le compose
5. Insere dans `public.projects`:
   - `<project>-app` avec URL `https://<project>.<BASE_DOMAIN>/`
   - `<project>-api` avec URL `https://<project>-api.<BASE_DOMAIN>/`
   - `<project>-db` avec URL `NULL`
6. Affiche un recap avec:
   - ports alloues
   - URLs a creer
   - IP de redirection (`TARGET_HOST`)
   - liens OVH + Nginx Proxy Manager

## Exemples rapides

Verification de config:

```bash
python generator.py --project-name my-project --check
```

Generation fichiers uniquement:

```bash
python generator.py --project-name my-project --only-files
```

## Generation des sources applicatives (manuel)

Angular:

```bash
ng new my-project-app --routing --style=scss --skip-git
```

Spring Initializr:

```text
https://start.spring.io/#!type=maven-project&language=java&groupId=com.example&artifactId=my-project-api&name=my-project-api&packageName=com.example.myworkoutapi&packaging=jar&javaVersion=17&dependencies=web,data-jpa,postgresql,flyway,lombok,validation,security
```
