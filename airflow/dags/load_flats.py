"""Load Sheloba flat listings into PostgreSQL."""

import json
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
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS listings (
                    id TEXT PRIMARY KEY,
                    slug TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    price TEXT NOT NULL,
                    living_space TEXT NOT NULL,
                    rooms TEXT NOT NULL,
                    address TEXT NOT NULL,
                    latitude DOUBLE PRECISION NOT NULL,
                    longitude DOUBLE PRECISION NOT NULL,
                    image TEXT NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cursor.executemany(
                """
                INSERT INTO listings (
                    id, slug, name, price, living_space, rooms, address,
                    latitude, longitude, image, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (id) DO UPDATE SET
                    slug = EXCLUDED.slug,
                    name = EXCLUDED.name,
                    price = EXCLUDED.price,
                    living_space = EXCLUDED.living_space,
                    rooms = EXCLUDED.rooms,
                    address = EXCLUDED.address,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    image = EXCLUDED.image,
                    updated_at = NOW()
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
    schedule="@daily",
    start_date=pendulum.datetime(2026, 9, 10, tz="UTC"),
    catchup=True,
    tags=["sheloba", "postgresql"],
)

load_flats_task = PythonOperator(
    task_id="load_flats",
    python_callable=load_flats,
    dag=dag,
)

load_flats_task
