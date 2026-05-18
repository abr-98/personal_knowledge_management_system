
import psycopg2


def get_connection():
    return psycopg2.connect(
        host="localhost",
        database="Pkms_db",
        user="postgres",
        password="1234",
        port="5432"
    )



def build_notes_graph(user_id: str):
    """
    Build a graph representation of all notes.

    Returns:
    {
        "nodes": [...],
        "edges": [...]
    }

    Nodes:
    {
        "id": 1,
        "title": "Agent Memory",
        "tags": ["AI", "Agents"],
        "topics": ["Memory", "Retrieval"]
    }

    Edges:
    {
        "source": "Agent Memory",
        "target": "GraphRAG"
    }
    """

    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT
                id,
                title,
                tags,
                topics,
                links
            FROM notes
            WHERE user_id = %s
        """, (user_id,))

        rows = cur.fetchall()

        nodes = []
        edges = []

        # Store all note titles for validation
        existing_titles = set()

        for row in rows:
            existing_titles.add(row[1])

        # Build nodes
        for row in rows:
            note_id = row[0]
            title = row[1]
            tags = row[2] or []
            topics = row[3] or []
            links = row[4] or []

            nodes.append({
                "id": note_id,
                "title": title,
                "tags": tags,
                "topics": topics
            })

            # Build edges
            for linked_note in links:

                # Only create edges to notes that exist
                if linked_note in existing_titles:
                    edges.append({
                        "source": title,
                        "target": linked_note
                    })

        return {
            "nodes": nodes,
            "edges": edges
        }

    except Exception as e:
        print("Error:", e)
        return {
            "nodes": [],
            "edges": []
        }

    finally:
        cur.close()
        conn.close()

