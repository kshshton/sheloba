# Dummy Flats Website

The Dummy Flats website displays the available flat listings and serves the HTML pages scraped by the Airflow DAG.

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

When running with Docker Compose, the website is available to Airflow at:

```text
http://website:8765/
```

After changing `data/flats.json`, restart the server to load the updated listings.
