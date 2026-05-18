import psycopg2


def get_connection():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="your_database",
        user="your_username",
        password="your_password"
    )


def search_records(
    user_id: str,
    tags: list[str] | None = None,
    topics: list[str] | None = None,
    domain: str | None = None
):
    conn = get_connection()

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
        print("Error:", e)
        return []

    finally:
        cur.close()
        conn.close()
