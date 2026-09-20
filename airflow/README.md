# Dummy Flats data pipeline

This project has two cooperating parts:

1. The Dummy Flats website serves flat listing pages.
2. The Airflow pipeline visits those pages with Playwright and stores listing metadata in PostgreSQL.

The website is deliberately simple: its HTML is the source consumed by the scraper. Airflow owns the workflow, database connection, and DOM-recovery logic.

## What is included

- Dummy Flats website source used by the scraper
- PostgreSQL 16 for Airflow metadata and listing data
- Airflow webserver for the management UI
- Airflow scheduler for DAG execution
- `load_flats` DAG for loading timestamped listing snapshots
- Reusable scraper logic in `scripts/`
- Docker Compose configuration for local development

## Quick start

From this directory, start all servers and supporting services with:

```sh
docker compose up -d --build
```

This starts the website, PostgreSQL, Airflow initialization, Airflow webserver, and Airflow scheduler. Open <http://localhost:8080> and sign in with the Airflow credentials configured in `.env`. The website is available at <http://localhost:8765>.

Check service status with:

```sh
docker compose ps
```

## Load listings

Enable and trigger the `load_flats` DAG in the Airflow UI. It runs daily after activation and can also be triggered manually.

The DAG scrapes the host-published website at `http://host.docker.internal:8765/` and inserts one snapshot per listing for each load timestamp into `data.listings`. The DAG definition lives in `dags/`, while reusable scraper logic lives in `scripts/`. The composite key `(id, updated_at)` preserves snapshots for one hour before the DAG removes them. Images are not scraped or stored.

The scraper uses the selectors in `scripts/load_flats/dom_definition.json` first. If they no longer match the page, it uses Playwright to inspect the current index and detail DOM, asks the configured Gemini model for CSS selectors, saves the new definition to that JSON file, and retries the static scraper. Set `GEMINI_API_KEY` for this recovery path and optionally set `SHELOBA_LLM_MODEL` (default: `gemini-3.6-flash`) in `.env`. The LLM is not contacted when the saved DOM definition succeeds.

## How the servers work

`docker compose up -d --build` starts the services in dependency order:

1. `website` serves Dummy Flats on port `8765`.
2. `postgres` stores Airflow metadata and listing data on host port `5433`.
3. `airflow-init` runs database migrations and creates the Airflow administrator.
4. `airflow-webserver` provides the UI on port `8080`.
5. `airflow-scheduler` executes the `load_flats` DAG.

The scheduler reaches the website through `host.docker.internal:8765`. In the Airflow UI, trigger `load_flats` manually because its current schedule is `None`.

After changing dependencies, the Dockerfile, or environment variables, rebuild and recreate the services:

```sh
docker compose up -d --build
```

Inspect loaded records with:

```sh
docker compose exec postgres sh -c \
  'PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT id, name, latitude, longitude, updated_at FROM data.listings ORDER BY updated_at, id;"'
```

## Documentation

See [SETUP.md](SETUP.md) for the complete technical guide, including:

- Docker and Compose setup
- Service architecture and startup order
- Environment variables and credentials
- Airflow and PostgreSQL connection strings
- SQLTools configuration
- PostgreSQL persistence and password changes
- Restart, logging, and troubleshooting procedures

## Stop the environment

Stop the containers without deleting stored data:

```sh
docker compose down
```

The technical setup guide explains how to remove the PostgreSQL volume when a complete reset is required.
