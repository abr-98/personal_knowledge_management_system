from __future__ import annotations

from src.infrastructure.database import DatabaseSettings, get_connection, load_database_settings


def _get_connection(settings: DatabaseSettings | None = None):
    return get_connection(settings or load_database_settings())


def search_records(
    user_id: str,
    tags: list[str] | None = None,
    topics: list[str] | None = None,
    domain: str | None = None,
    settings: DatabaseSettings | None = None,
):
    conn = _get_connection(settings)

    try:
        cur = conn.cursor()

        query = """
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
        """

        params = [user_id]

        # Optional tag filtering
        if tags:
            query += " AND tags && %s"
            params.append(tags)

        # Optional topic filtering
        if topics:
            query += " AND topics && %s"
            params.append(topics)

        # Optional domain filtering
        if domain:
            query += " AND domain = %s"
            params.append(domain)

        query += " ORDER BY created_at DESC"

        cur.execute(query, tuple(params))

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
