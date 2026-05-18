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
# CREATE WORKITEM
# =========================================================

def create_workitem(
    user_id: str,
    title: str,
    description: Optional[str] = None,
    status: str = "pending",
    priority: str = "medium",
    related_notes: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    topics: Optional[List[str]] = None,
    due_date=None
):
    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO workitems (
                user_id,
                title,
                description,
                status,
                priority,
                related_notes,
                tags,
                topics,
                due_date
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            user_id,
            title,
            description,
            status,
            priority,
            related_notes,
            tags,
            topics,
            due_date
        ))

        workitem_id = cur.fetchone()[0]

        conn.commit()

        print(f"Created workitem ID: {workitem_id}")

    except Exception as e:
        conn.rollback()
        print("Error:", e)

    finally:
        cur.close()
        conn.close()


# =========================================================
# FETCH WORKITEMS
# =========================================================

def fetch_workitems(user_id: str):
    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT *
            FROM workitems
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
# UPDATE WORKITEM
# =========================================================

def update_workitem(
    workitem_id: int,
    user_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    related_notes: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    topics: Optional[List[str]] = None,
    due_date=None
):
    conn = get_connection()

    try:
        cur = conn.cursor()

        fields = []
        values = []

        if title is not None:
            fields.append("title = %s")
            values.append(title)

        if description is not None:
            fields.append("description = %s")
            values.append(description)

        if status is not None:
            fields.append("status = %s")
            values.append(status)

        if priority is not None:
            fields.append("priority = %s")
            values.append(priority)

        if related_notes is not None:
            fields.append("related_notes = %s")
            values.append(related_notes)

        if tags is not None:
            fields.append("tags = %s")
            values.append(tags)

        if topics is not None:
            fields.append("topics = %s")
            values.append(topics)

        if due_date is not None:
            fields.append("due_date = %s")
            values.append(due_date)

        fields.append("updated_at = NOW()")

        values.extend([workitem_id, user_id])

        query = f"""
            UPDATE workitems
            SET {", ".join(fields)}
            WHERE id = %s
            AND user_id = %s
        """

        cur.execute(query, tuple(values))

        conn.commit()

        print("Workitem updated.")

    except Exception as e:
        conn.rollback()
        print("Error:", e)

    finally:
        cur.close()
        conn.close()


# =========================================================
# DELETE WORKITEM
# =========================================================

def delete_workitem(workitem_id: int, user_id: str):
    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute("""
            DELETE FROM workitems
            WHERE id = %s
            AND user_id = %s
        """, (
            workitem_id,
            user_id
        ))

        conn.commit()

        print("Workitem deleted.")

    except Exception as e:
        conn.rollback()
        print("Error:", e)

    finally:
        cur.close()
        conn.close()
        
# =========================================================
# FETCH ALL WORKITEMS
# =========================================================

def fetch_all_workitems(user_id: str):
    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT *
            FROM workitems
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
# FETCH WORKITEMS BY TAGS / TOPICS
# =========================================================

def fetch_workitems_by_filters(
    user_id: str,
    tags: list[str] | None = None,
    topics: list[str] | None = None
):
    conn = get_connection()

    try:
        cur = conn.cursor()

        query = """
            SELECT *
            FROM workitems
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