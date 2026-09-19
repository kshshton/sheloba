"""Load Sheloba flat listings into PostgreSQL."""

import json
from datetime import timedelta
from pathlib import Path

import pendulum
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

SOURCE_FILE = Path("/opt/airflow/data/flats.json")
POSTGRES_CONNECTION_ID = "sheloba_postgres"


def load_flats() -> None:
    flats = json.loads(SOURCE_FILE.read_text(encoding="utf-8"))
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
                    image TEXT NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (id, updated_at)
                )
                """
            )
            cursor.execute("ALTER TABLE data.listings DROP CONSTRAINT IF EXISTS listings_pkey")
            cursor.execute("ALTER TABLE data.listings DROP CONSTRAINT IF EXISTS listings_slug_key")
            cursor.execute(
                """
                ALTER TABLE data.listings
                ADD CONSTRAINT listings_pkey PRIMARY KEY (id, updated_at)
                """
            )
            cursor.executemany(
                """
                INSERT INTO data.listings (
                    id, slug, name, price, living_space, rooms, address,
                    latitude, longitude, image, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
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
                        flat["image"],
                    )
                    for flat in flats
                ],
            )

dag = DAG(
    dag_id="load_sheloba_flats",
    description="Load website flat listings into PostgreSQL",
    start_date=pendulum.now("UTC"),
    schedule_interval=timedelta(minutes=10),
    catchup=True,
    tags=["sheloba", "postgresql"],
)

load_flats_task = PythonOperator(
    task_id="load_flats",
    python_callable=load_flats,
    dag=dag,
)

load_flats_task
