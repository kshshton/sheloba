# Project Setup

This guide describes how to run the full local stack for the project: the website scraper source, the Airflow pipeline, and the PostgreSQL database. It covers local startup, Docker networking, environment variables, credential handling, and troubleshooting.

## Prerequisites

Install and start:

- Docker Engine
- Docker Compose v2 (`docker compose`)
- Python 3.11+ if you want to run the website locally without Docker
- VS Code with SQLTools and its PostgreSQL driver, if database browsing is needed

Run commands from the repository root unless a step explicitly says otherwise.

## Website setup

The website is a lightweight Python HTTP app in `website/`. It serves static listing pages and detail pages from `website/data/flats.json` and is used as the scraper source in the Airflow stack.

### Run the website directly

```sh
cd website
python3 server.py
```

Then open:

- <http://127.0.0.1:8765/>

Use `SHELOBA_HOST=0.0.0.0` when the website must be reachable from another container or host machine.

### Website in Docker Compose

The `website` service is already defined in `airflow/docker-compose.yml` and is published on:

```text
http://localhost:8765
```

It runs with a local volume mount of the `website/` directory, so changes to HTML or Python files are reflected when the container is restarted.

## Services and network

The Compose project runs five services:

- `website`: listing site used as the scraper source.
- `postgres`: PostgreSQL 16 for Airflow metadata and listing data.
- `airflow-init`: waits for PostgreSQL, runs migrations, and creates the Airflow administrator.
- `airflow-webserver`: serves the Airflow UI.
- `airflow-scheduler`: schedules and executes DAG tasks.

Airflow containers use the internal Compose hostname and port:

```text
postgres:5432
```

The scheduler reaches the website through its internal Compose hostname:

```text
http://website:8765
```

The website is health-checked before the scheduler starts, so the first DAG run does not race website startup.

PostgreSQL is published to the host on port `5433` because host port `5432` is already used by another container:

```text
localhost:5433 -> postgres:5432
```

The Airflow UI is published on:

```text
http://localhost:8080
```

The website source is published on:

```text
http://localhost:8765
```

## Create the environment file

Create `airflow/.env` with the values required by the Compose file. The Docker stack is defined in `airflow/docker-compose.yml`, so the environment file lives alongside it:

```dotenv
POSTGRES_USER=airflow
POSTGRES_PASSWORD=admin
POSTGRES_DB=airflow
AIRFLOW_ADMIN_USERNAME=admin
AIRFLOW_ADMIN_PASSWORD=admin
AIRFLOW_PORT=8080
GEMINI_API_KEY=your-gemini-api-key
SHELOBA_LLM_MODEL=gemini-3.6-flash
```

The `.env` file is ignored by Git. Keep real passwords out of tracked files and use stronger values outside local development.

The passwords serve different systems:

- `POSTGRES_PASSWORD` authenticates the PostgreSQL role `airflow`.
- `AIRFLOW_ADMIN_PASSWORD` authenticates the Airflow web administrator.

## Build and start

From the Airflow directory, build the custom Airflow image and start the complete environment in the background:

```sh
cd airflow
docker compose up -d --build
```

Compose starts services in this order:

1. PostgreSQL starts and passes its health check.
2. `airflow-init` runs `airflow db migrate`.
3. `airflow-init` creates the administrator if it does not already exist.
4. The webserver and scheduler start after initialization succeeds.

Check the result:

```sh
docker compose ps
```

A successful status includes:

- `postgres`: `Up ... (healthy)`
- `airflow-webserver`: `Up`
- `airflow-scheduler`: `Up`
- `airflow-init`: `Exited` after successful completion

Open <http://localhost:8080> and sign in using `AIRFLOW_ADMIN_USERNAME` and `AIRFLOW_ADMIN_PASSWORD` from `.env`.

## Apply changes and restart

For a normal restart:

```sh
docker compose restart
```

After changing website data, restart the website container so the server reloads `website/data/flats.json`:

```sh
docker compose restart website
```

After changing dependencies, the Dockerfile, or environment variables, rebuild the stack:

```sh
docker compose up -d --build
```

After changing `.env`, `docker-compose.yml`, ports, or the Dockerfile, recreate the services:

```sh
docker compose up -d --build
```

Follow service logs with:

```sh
docker compose logs -f airflow-webserver airflow-scheduler postgres
```

Stop the containers without deleting data:

```sh
docker compose down
```

## PostgreSQL connection strings

### Airflow containers

Use the internal service hostname and port:

```text
postgresql://airflow:admin@postgres:5432/airflow
```

The Airflow metadata connection uses the SQLAlchemy driver form:

```text
postgresql+psycopg2://airflow:admin@postgres:5432/airflow
```

### Host applications and SQLTools

Use the published host port:

```text
postgresql://airflow:admin@localhost:5433/airflow
```

The workspace SQLTools connection is stored in `../.vscode/settings.json`:

| Field | Value |
| --- | --- |
| Driver | PostgreSQL |
| Server | `localhost` |
| Port | `5433` |
| Database | `airflow` |
| Username | `airflow` |
| Password | value of `POSTGRES_PASSWORD` |

Do not use `postgres` as the server name from SQLTools because SQLTools runs on the host, outside the Compose network.

## Verify PostgreSQL

Run a query inside the database container:

```sh
docker compose exec postgres sh -c \
  'PGPASSWORD="$POSTGRES_PASSWORD" psql -h 127.0.0.1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT current_user, current_database();"'
```

Verify the published host port from a machine with `psql` installed:

```sh
PGPASSWORD=admin psql -h localhost -p 5433 -U airflow -d airflow \
  -c 'SELECT current_user, current_database();'
```

A successful result shows `airflow` as both the current user and database.

## Persistent data and credentials

The named Docker volume `postgres-data` stores PostgreSQL data. Stopping or recreating containers does not delete it.

The PostgreSQL image uses `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` when the data directory is initialized for the first time. Changing `POSTGRES_PASSWORD` later does not automatically change the password of an existing PostgreSQL role.

To change the password of the existing role:

```sh
docker compose exec postgres psql -U airflow -d airflow \
  -c "ALTER USER airflow WITH PASSWORD 'new-password';"
```

Then update `POSTGRES_PASSWORD` in `.env`, update the SQLTools connection, and recreate the services:

```sh
docker compose up -d
```

To delete the database and all stored Airflow/listing data, explicitly remove volumes:

```sh
docker compose down -v
```

The next startup initializes an empty PostgreSQL database. This cannot be undone, so use it only when the stored data is disposable.

The Airflow administrator is created during `airflow-init`. If the administrator already exists, changing `AIRFLOW_ADMIN_PASSWORD` does not update it automatically. Reset it explicitly:

```sh
docker compose exec airflow-webserver \
  airflow users reset-password --username admin --password 'new-password'
```

## Troubleshooting

### Host port 5432 is allocated

The project uses `5433:5432` because another container owns host port `5432`. Inspect port usage with:

```sh
docker ps --format 'table {{.Names}}\t{{.Ports}}'
ss -ltnp ' sport = :5432 '
```

If host port `5433` is unavailable, change only the host side of the mapping in `docker-compose.yml`, for example:

```yaml
ports:
  - "5434:5432"
```

Use the same new host port in SQLTools.

### SQLTools cannot connect

Confirm that:

1. `docker compose ps postgres` reports `healthy`.
2. SQLTools uses `localhost`, not `postgres`.
3. SQLTools uses host port `5433`, not container port `5432`.
4. The password matches `POSTGRES_PASSWORD` in `.env` and the existing PostgreSQL role.
5. PostgreSQL is published in `docker-compose.yml`.

### Airflow services do not start

Inspect initialization and service logs:

```sh
docker compose logs airflow-init
docker compose logs airflow-webserver airflow-scheduler
```

After correcting configuration, run:

```sh
docker compose up -d --build
```

If the database is disposable and credentials or migrations are irreparably inconsistent, remove the volume and initialize again:

```sh
docker compose down -v
docker compose up -d --build
```
