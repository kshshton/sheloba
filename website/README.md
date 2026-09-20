# Dummy Flats Website

The Dummy Flats website displays available flat listings and serves the HTML pages consumed by the Airflow DAG. It is a small Python server backed by `data/flats.json`.

## Run locally

From the repository root:

```sh
cd website
python3 server.py
```

Open <http://127.0.0.1:8765/> in a browser.

The server binds to `127.0.0.1` by default. Set `SHELOBA_HOST` when the site must be reachable by another container:

```sh
SHELOBA_HOST=0.0.0.0 python3 server.py
```

## Routes

- `/` or `/index.html`: rendered flat listing index
- `/flat.html?slug=riverside-loft`: rendered details for one flat
- `/flat?slug=riverside-loft`: short equivalent of the detail route

The raw `data/` directory and `server.py` are intentionally not exposed over HTTP.

## Data

Listing metadata is loaded from `data/flats.json` when the server starts. The index page renders listing cards, and detail pages expose the metadata required by the Airflow scraper through HTML attributes and visible address text.

When running with Docker Compose, the website is published on the host at:

```text
http://localhost:8765/
```

The Airflow scheduler reaches the same server through Docker's host gateway:

```text
http://host.docker.internal:8765/
```

After changing `data/flats.json`, restart the server to load the updated listings.
