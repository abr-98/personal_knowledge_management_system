from __future__ import annotations

from src.infrastructure.database import DatabaseSettings, get_connection, load_database_settings


def _get_connection(settings: DatabaseSettings | None = None):
    return get_connection(settings or load_database_settings())


def fetch_user_records(user_id: str, settings: DatabaseSettings | None = None):
    conn = _get_connection(settings)

    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT
                id,
                link_or_path,
                source,
                domain,
                tags,
                topics,
                created_at
            FROM records
            WHERE user_id = %s
            ORDER BY created_at DESC
        """, (user_id,))

        rows = cur.fetchall()

        records = []

        for row in rows:
            records.append({
                "id": row[0],
                "link_or_path": row[1],
                "source": row[2],
                "domain": row[3],
                "tags": row[4],
                "topics": row[5],
                "created_at": row[6]
            })

        return records

    except Exception as e:
        print("Error:", e)
        return []

    finally:
        cur.close()
        conn.close()


def update_tags(
    record_id: int,
    user_id: str,
    new_tags: list[str],
    settings: DatabaseSettings | None = None,
):
    conn = _get_connection(settings)

    try:
        cur = conn.cursor()

        cur.execute("""
            UPDATE records
            SET tags = %s
            WHERE id = %s
            AND user_id = %s
            RETURNING id
        """, (
            new_tags,
            record_id,
            user_id
        ))

        updated = cur.fetchone()

        conn.commit()

        return updated is not None

    except Exception as e:
        conn.rollback()
        raise e

    finally:
        cur.close()
        conn.close()


def update_topics(
    record_id: int,
    user_id: str,
    new_topics: list[str],
    settings: DatabaseSettings | None = None,
):
    conn = _get_connection(settings)

    try:
        cur = conn.cursor()

        cur.execute("""
            UPDATE records
            SET topics = %s
            WHERE id = %s
            AND user_id = %s
            RETURNING id
        """, (
            new_topics,
            record_id,
            user_id
        ))

        updated = cur.fetchone()

        conn.commit()

        return updated is not None

    except Exception as e:
        conn.rollback()
        raise e

    finally:
        cur.close()
        conn.close()


def get_records_by_tags(
    user_id: str,
    tags: list[str],
    settings: DatabaseSettings | None = None,
):
    conn = _get_connection(settings)

    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT
                id,
                link_or_path,
                source,
                domain,
                tags,
                topics,
                created_at
            FROM records
            WHERE user_id = %s
            AND tags && %s
            ORDER BY created_at DESC
        """, (
            user_id,
            tags
        ))

        rows = cur.fetchall()

        results = []

        for row in rows:
            results.append({
                "id": row[0],
                "link_or_path": row[1],
                "source": row[2],
                "domain": row[3],
                "tags": row[4],
                "topics": row[5],
                "created_at": row[6]
            })

        return results

    except Exception as e:
        raise e

    finally:
        cur.close()
        conn.close()

