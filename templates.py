from config import get_frontend_url, read_env
from models import Ports


FRONT_DOCKERFILE_TEMPLATE = """FROM node:20-alpine AS build

WORKDIR /app

COPY {frontend_dir}/package*.json ./

RUN npm install --production

COPY {frontend_dir}/ .

RUN npm run build


FROM nginx:alpine

COPY {frontend_dir}/nginx.conf /etc/nginx/conf.d/default.conf

COPY --from=build app/www/browser /usr/share/nginx/html

EXPOSE 80
"""


BACK_DOCKERFILE_TEMPLATE = """FROM maven:3.8.3-openjdk-17 AS build

WORKDIR /app

COPY {backend_dir}/pom.xml .
COPY {backend_dir}/. .

RUN mvn dependency:go-offline

RUN mvn clean package -DskipTests

FROM eclipse-temurin:17-jre-jammy

WORKDIR /app
COPY --from=build /app/target/*.jar app.jar

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "app.jar"]
"""


def render_compose(project_name: str, ports: Ports) -> str:
    network_name = f"{project_name}-network"
    image_ns = read_env("DOCKER_IMAGE_NAMESPACE", "alexv31")
    frontend_url = get_frontend_url(project_name, trailing_slash=False)

    return f"""version: '3'
services:
  {project_name}-app:
    image: {image_ns}/{project_name}:app
    networks:
      - {network_name}
    ports:
      - "{ports.front_http}:80"
      - "{ports.front_https}:443"

  {project_name}-api:
    image: {image_ns}/{project_name}:api
    depends_on:
      - {project_name}-db
    environment:
      - spring.datasource.url={read_env("SPRING_DATASOURCE_URL", f"jdbc:postgresql://{project_name}-db:5432/database")}
      - spring.datasource.username=user
      - spring.datasource.password=password
      - spring.jpa.hibernate.ddl-auto=update
      - spring.jpa.properties.hibernate.dialect=org.hibernate.dialect.PostgreSQLDialect
      - spring.flyway.locations=classpath:db/migration
      - spring.flyway.baseline-on-migrate=true
      - server.servlet.context-path=/api
      - allowed.origin={frontend_url}
      - security.jwt.secret-key=
      - security.jwt.expiration-time=3600000
      - security.jwt.refresh.expiration-time=604800000
      - logging.level.org.springframework.security=INFO
      - server.port=80
      - server.address=0.0.0.0
    networks:
      - {network_name}
    ports:
      - "{ports.api_http}:80"
      - "{ports.api_https}:443"

  {project_name}-db:
    image: postgres:17
    restart: always
    networks:
      - {network_name}
    environment:
      - POSTGRES_DB=database
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    ports:
      - "{ports.db_http}:5432"
      - "{ports.db_https}:443"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:

networks:
  {network_name}:
    driver: bridge
"""


def render_github_actions_workflow_build_deploy(project_name: str) -> str:
    app_name = f"{project_name}-app"
    api_name = f"{project_name}-api"
    repo_name = project_name
    return f"""name: Docker build images, push to DockerHub and redeploy containers

on:
    push:
        branches: [ "main" ]

env:
    APP_NAME: {app_name}
    API_NAME: {api_name}
    DOCKERHUB_REPOSITORY_NAME: {repo_name}
    DOCKERHUB_USERNAME: ${{{{ secrets.DOCKERHUB_USERNAME }}}}
    DOCKERHUB_TOKEN: ${{{{ secrets.DOCKERHUB_TOKEN }}}}
    SERVER_HOST: ${{{{ secrets.SERVER_HOST }}}}
    SERVER_USERNAME: ${{{{ secrets.SERVER_USERNAME }}}}
    SERVER_PASSWORD: ${{{{ secrets.SERVER_PASSWORD }}}}
    SERVER_PORT: ${{{{ secrets.SERVER_PORT }}}}

jobs:
    build-push-images:
        runs-on: ubuntu-latest
        environment: production
        steps:
            - uses: actions/checkout@v3

            - name: Build images app and api
              run: |
                  docker build -t ${{{{ env.DOCKERHUB_REPOSITORY_NAME }}}}:app -f ${{{{ env.APP_NAME }}}}/Dockerfile .
                  docker build -t ${{{{ env.DOCKERHUB_REPOSITORY_NAME }}}}:api -f ${{{{ env.API_NAME }}}}/Dockerfile .

            - name: Login to Docker Hub
              uses: docker/login-action@v3
              with:
                  username: ${{{{ env.DOCKERHUB_USERNAME }}}}
                  password: ${{{{ env.DOCKERHUB_TOKEN }}}}

            - name: Extract metadata (tags, labels) for Docker
              id: meta
              uses: docker/metadata-action@9ec57ed1fcdbf14dcef7dfbe97b2010124a938b7
              with:
                  images: ${{{{ env.DOCKERHUB_USERNAME }}}}/${{{{ env.DOCKERHUB_REPOSITORY_NAME }}}}

            - name: Push image app
              uses: docker/build-push-action@3b5e8027fcad23fda98b2e3ac259d8d67585f671
              with:
                  context: .
                  file: ${{{{ env.APP_NAME }}}}/Dockerfile
                  push: true
                  tags: ${{{{ env.DOCKERHUB_USERNAME }}}}/${{{{ env.DOCKERHUB_REPOSITORY_NAME }}}}:app

            - name: Push image api
              uses: docker/build-push-action@3b5e8027fcad23fda98b2e3ac259d8d67585f671
              with:
                  context: .
                  file: ${{{{ env.API_NAME }}}}/Dockerfile
                  push: true
                  tags: ${{{{ env.DOCKERHUB_USERNAME }}}}/${{{{ env.DOCKERHUB_REPOSITORY_NAME }}}}:api

    redeploy-containers:
        needs: build-push-images
        runs-on: ubuntu-latest
        environment: production
        steps:
            - name: executing remote ssh commands using password
              uses: appleboy/ssh-action@v1.1.0
              with:
                  host: ${{{{ env.SERVER_HOST }}}}
                  username: ${{{{ env.SERVER_USERNAME }}}}
                  password: ${{{{ env.SERVER_PASSWORD }}}}
                  port: ${{{{ env.SERVER_PORT }}}}
                  script: |
                      docker pull ${{{{ env.DOCKERHUB_USERNAME }}}}/${{{{ env.DOCKERHUB_REPOSITORY_NAME }}}}:app
                      docker pull ${{{{ env.DOCKERHUB_USERNAME }}}}/${{{{ env.DOCKERHUB_REPOSITORY_NAME }}}}:api
                      docker system prune -f
                      cd /home/debian/apps/${{{{ env.DOCKERHUB_REPOSITORY_NAME }}}}/
                      docker-compose up -d
"""


def render_github_actions_workflow_tests(project_name: str) -> str:
    api_name = f"{project_name}-api"
    return f"""name: Run test

on:
    push:
        branches: 
            - "**"
    pull_request: 

jobs:
    tests:
        runs-on: ubuntu-latest
        steps:
            - name: Checkout code
              uses: actions/checkout@v4

            - name: Set up Java
              uses: actions/setup-java@v4
              with:
                  distribution: temurin
                  java-version: 17

            - name: Run tests
              run: mvn clean test
              working-directory: {api_name}
"""
