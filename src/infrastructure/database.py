from __future__ import annotations

import os
from dataclasses import dataclass

import psycopg2
from psycopg2.extras import RealDictCursor


@dataclass(frozen=True)
class DatabaseSettings:
    host: str
    port: int
    database: str
    user: str
    password: str


def load_database_settings() -> DatabaseSettings:
    return DatabaseSettings(
        host=os.getenv("PKMS_DB_HOST", "localhost"),
        port=int(os.getenv("PKMS_DB_PORT", "5432")),
        database=os.getenv("PKMS_DB_NAME", "Pkms_db"),
        user=os.getenv("PKMS_DB_USER", "postgres"),
        password=os.getenv("PKMS_DB_PASSWORD", "1234"),
    )


def get_connection(settings: DatabaseSettings | None = None):
    current = settings or load_database_settings()
    return psycopg2.connect(
        host=current.host,
        port=current.port,
        dbname=current.database,
        user=current.user,
        password=current.password,
        cursor_factory=RealDictCursor,
    )


def initialize_database(settings: DatabaseSettings | None = None) -> None:
    from src.utilities.database_handling.SQL_databases.records_table_creator import create_records_table
    from src.utilities.database_handling.SQL_databases.self_notes_table_creator import create_self_notes_table as create_notes_table
    from src.utilities.database_handling.SQL_databases.user_handler_table_creator import create_user_tables
    from src.utilities.database_handling.SQL_databases.workitems_table_creator import create_self_notes_table as create_workitem_tables

    current = settings or load_database_settings()

    for create_table in (
        create_user_tables,
        create_records_table,
        create_notes_table,
        create_workitem_tables,
    ):
        create_table()

    required_tables = {
        "users",
        "chat_threads",
        "messages",
        "token_usage",
        "records",
        "workitems",
        "timelines",
    }

    with get_connection(current) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = ANY(%s)
                """,
                (list(required_tables),),
            )
            found_tables = {row["table_name"] for row in cur.fetchall()}

    missing_tables = required_tables - found_tables
    if missing_tables:
        missing_csv = ", ".join(sorted(missing_tables))
        raise RuntimeError(f"Database initialization is incomplete. Missing tables: {missing_csv}")