import psycopg2
from typing import Optional, List


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_connection():
    return psycopg2.connect(
        host="localhost",
        database="Pkms_db",
        user="postgres",
        password="1234",
        port="5432"
    )


# =========================================================
# CREATE TABLE
# =========================================================

def create_timelines_table():
    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS timelines (
                id SERIAL PRIMARY KEY,

                user_id VARCHAR(255) NOT NULL,

                event_type VARCHAR(100),

                title TEXT NOT NULL,

                description TEXT,

                related_notes TEXT[],

                related_workitems INT[],

                tags TEXT[],

                topics TEXT[],

                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        conn.commit()

        print("Timelines table ready.")

    except Exception as e:
        conn.rollback()
        print("Error:", e)

    finally:
        cur.close()
        conn.close()


# =========================================================
# CREATE TIMELINE EVENT
# =========================================================

def create_timeline_event(
    user_id: str,
    event_type: str,
    title: str,
    description: Optional[str] = None,
    related_notes: Optional[List[str]] = None,
    related_workitems: Optional[List[int]] = None,
    tags: Optional[List[str]] = None,
    topics: Optional[List[str]] = None
):
    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO timelines (
                user_id,
                event_type,
                title,
                description,
                related_notes,
                related_workitems,
                tags,
                topics
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            user_id,
            event_type,
            title,
            description,
            related_notes,
            related_workitems,
            tags,
            topics
        ))

        timeline_id = cur.fetchone()[0]

        conn.commit()

        print(f"Created timeline event ID: {timeline_id}")

    except Exception as e:
        conn.rollback()
        print("Error:", e)

    finally:
        cur.close()
        conn.close()


# =========================================================
# FETCH TIMELINE EVENTS
# =========================================================

def fetch_timeline_events(user_id: str):
    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT *
            FROM timelines
            WHERE user_id = %s
            ORDER BY created_at DESC
        """, (user_id,))

        rows = cur.fetchall()

        return rows

    except Exception as e:
        print("Error:", e)
        return []

    finally:
        cur.close()
        conn.close()


# =========================================================
# UPDATE TIMELINE EVENT
# =========================================================

def update_timeline_event(
    timeline_id: int,
    user_id: str,
    event_type: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    related_notes: Optional[List[str]] = None,
    related_workitems: Optional[List[int]] = None,
    tags: Optional[List[str]] = None,
    topics: Optional[List[str]] = None
):
    conn = get_connection()

    try:
        cur = conn.cursor()

        fields = []
        values = []

        if event_type is not None:
            fields.append("event_type = %s")
            values.append(event_type)

        if title is not None:
            fields.append("title = %s")
            values.append(title)

        if description is not None:
            fields.append("description = %s")
            values.append(description)

        if related_notes is not None:
            fields.append("related_notes = %s")
            values.append(related_notes)

        if related_workitems is not None:
            fields.append("related_workitems = %s")
            values.append(related_workitems)

        if tags is not None:
            fields.append("tags = %s")
            values.append(tags)

        if topics is not None:
            fields.append("topics = %s")
            values.append(topics)

        values.extend([timeline_id, user_id])

        query = f"""
            UPDATE timelines
            SET {", ".join(fields)}
            WHERE id = %s
            AND user_id = %s
        """

        cur.execute(query, tuple(values))

        conn.commit()

        print("Timeline event updated.")

    except Exception as e:
        conn.rollback()
        print("Error:", e)

    finally:
        cur.close()
        conn.close()


# =========================================================
# DELETE TIMELINE EVENT
# =========================================================

def delete_timeline_event(timeline_id: int, user_id: str):
    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute("""
            DELETE FROM timelines
            WHERE id = %s
            AND user_id = %s
        """, (
            timeline_id,
            user_id
        ))

        conn.commit()

        print("Timeline event deleted.")

    except Exception as e:
        conn.rollback()
        print("Error:", e)

    finally:
        cur.close()
        conn.close()
        
# =========================================================
# FETCH ALL TIMELINE EVENTS
# =========================================================

def fetch_all_timeline_events(user_id: str):
    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT *
            FROM timelines
            WHERE user_id = %s
            ORDER BY created_at DESC
        """, (user_id,))

        rows = cur.fetchall()

        return rows

    except Exception as e:
        print("Error:", e)
        return []

    finally:
        cur.close()
        conn.close()


# =========================================================
# FETCH TIMELINE EVENTS BY TAGS / TOPICS
# =========================================================

def fetch_timeline_events_by_filters(
    user_id: str,
    tags: list[str] | None = None,
    topics: list[str] | None = None
):
    conn = get_connection()

    try:
        cur = conn.cursor()

        query = """
            SELECT *
            FROM timelines
            WHERE user_id = %s
        """

        params = [user_id]

        if tags:
            query += " AND tags && %s"
            params.append(tags)

        if topics:
            query += " AND topics && %s"
            params.append(topics)

        query += " ORDER BY created_at DESC"

        cur.execute(query, tuple(params))

        rows = cur.fetchall()

        return rows

    except Exception as e:
        print("Error:", e)
        return []

    finally:
        cur.close()
        conn.close()