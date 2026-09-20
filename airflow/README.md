# Sheloba Airflow

Sheloba uses Apache Airflow and PostgreSQL to load flat listings scraped from the website into the `data.listings` table.

## What is included

- Sheloba website source used by the scraper
- PostgreSQL 16 for Airflow metadata and listing data
- Airflow webserver for the management UI
- Airflow scheduler for DAG execution
- `load_flats` DAG for loading timestamped listing snapshots
- Reusable scraper logic in `scripts/`
- Docker Compose configuration for local development

## Quick start

From this directory, start the environment with:

```sh
docker compose up -d --build
```

Then open <http://localhost:8080> and sign in with the Airflow credentials configured in `.env`.

Check service status with:

```sh
docker compose ps
```

## Load listings

Enable and trigger the `load_flats` DAG in the Airflow UI. It runs daily after activation and can also be triggered manually.

The DAG scrapes the host-published website at `http://host.docker.internal:8765/` and inserts one snapshot per listing for each load timestamp into `data.listings`. The DAG definition lives in `dags/`, while reusable scraper logic lives in `scripts/`. The composite key `(id, updated_at)` preserves snapshots for one hour before the DAG removes them.

The scraper uses its known DOM definition first. If it finds no listings or required detail metadata, it opens the pages with Playwright, asks the configured OpenAI-compatible model to define the current selectors, and retries with that definition. Set `OPENAI_API_KEY` for this recovery path and optionally set `SHELOBA_LLM_MODEL` (default: `gpt-4o-mini`) in the Airflow container environment. The LLM is not contacted when the known DOM definition succeeds.

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
