
from __future__ import annotations

from src.infrastructure.database import DatabaseSettings, get_connection, load_database_settings


def _get_connection(settings: DatabaseSettings | None = None):
    return get_connection(settings or load_database_settings())



def build_notes_graph(user_id: str, settings: DatabaseSettings | None = None):
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

    conn = _get_connection(settings)

    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT
                id,
                title,
                tags,
                topics,
                backlinks
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
        raise e

    finally:
        cur.close()
        conn.close()

