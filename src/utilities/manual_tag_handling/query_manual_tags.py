import psycopg2


def get_connection():
    return psycopg2.connect(host="localhost",
                            database= "Pkms_db",
                            user="postgres",
                            password="1234",
                            port="5432")


def fetch_user_records(user_id: str):
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
            ORDER BY created_at DESC
        """, (user_id,))

        rows = cur.fetchall()

        records = []

        for row in rows:
            records.append({
                "id": row[0],
                "link_or_path": row[1],
                "source": row[2],
                "tags": row[3],
                "created_at": row[4]
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
    new_tags: list[str]
):
    conn = get_connection()

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

        if updated:
            print(f"Updated tags for record ID: {updated[0]}")
        else:
            print("No matching record found")

    except Exception as e:
        conn.rollback()
        print("Error:", e)

    finally:
        cur.close()
        conn.close()
