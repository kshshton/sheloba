"""Load Sheloba flat listings into PostgreSQL."""

from datetime import timedelta

import pendulum
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

from scripts.config import POSTGRES_CONNECTION_ID
from scripts.load_flats.scrape_listings import scrape_listings


def load_flats(
    source_url: str,
    request_timeout_seconds: int,
) -> None:
    flats = scrape_listings(source_url, request_timeout_seconds)
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONNECTION_ID)

    with hook.get_conn() as connection:
        with connection.cursor() as cursor:
            cursor.execute("CREATE SCHEMA IF NOT EXISTS data")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS data.listings (
                    id TEXT NOT NULL,
                    slug TEXT NOT NULL,
                    name TEXT NOT NULL,
                    price TEXT NOT NULL,
                    living_space TEXT NOT NULL,
                    rooms TEXT NOT NULL,
                    address TEXT NOT NULL,
                    latitude DOUBLE PRECISION NOT NULL,
                    longitude DOUBLE PRECISION NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (id, updated_at)
                )
                """
            )
            cursor.execute("ALTER TABLE data.listings DROP COLUMN IF EXISTS image")
            cursor.execute("ALTER TABLE data.listings DROP CONSTRAINT IF EXISTS listings_pkey")
            cursor.execute("ALTER TABLE data.listings DROP CONSTRAINT IF EXISTS listings_slug_key")
            cursor.execute(
                """
                ALTER TABLE data.listings
                ADD CONSTRAINT listings_pkey PRIMARY KEY (id, updated_at)
                """
            )
            # Set retention policy to keep only the most recent version of each listing
            cursor.execute(
                "DELETE FROM data.listings WHERE updated_at < NOW() - INTERVAL '1 hour'"
            )
            cursor.executemany(
                """
                INSERT INTO data.listings (
                    id, slug, name, price, living_space, rooms, address,
                    latitude, longitude, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """,
                [
                    (
                        flat["id"],
                        flat["slug"],
                        flat["name"],
                        flat["price"],
                        flat["livingSpace"],
                        flat["rooms"],
                        flat["address"],
                        flat["latitude"],
                        flat["longitude"],
                    )
                    for flat in flats
                ],
            )


with DAG(
    dag_id="extract_listings",
    description="Load listings from the website",
    start_date=pendulum.now("Europe/Berlin"),
    schedule=None,
    catchup=False,
    tags=["flats"],
) as dag:
    load_flats_task = PythonOperator(
        task_id="extract_listings",
        python_callable=load_flats,
        op_kwargs={
            "source_url": "http://website:8765/",
            "request_timeout_seconds": 30,
        },
        dag=dag,
    )
