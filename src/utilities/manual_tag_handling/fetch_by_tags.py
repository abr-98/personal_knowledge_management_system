import psycopg2


def get_connection():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="your_database",
        user="your_username",
        password="your_password"
    )


def get_records_by_tags(
    user_id: str,
    tags: list[str]
):
    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT
                id,
                link_or_path,
                source,
                tags,
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
                "tags": row[3],
                "created_at": row[4]
            })

        return results

    except Exception as e:
        print("Error:", e)
        return []

    finally:
        cur.close()
        conn.close()


# Example usage

results = get_records_by_tags(
    user_id="user_123",
    tags=["AI", "GraphRAG"]
)

for record in results:
    print(record["link_or_path"])