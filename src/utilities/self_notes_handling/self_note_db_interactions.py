import os
import re
from typing import List, Optional

from src.infrastructure.database import DatabaseSettings, get_connection, load_database_settings


# =========================================================
# DATABASE CONNECTION
# =========================================================

def _get_connection(settings: DatabaseSettings | None = None):
    return get_connection(settings or load_database_settings())

# =========================================================
# MARKDOWN PARSING
# =========================================================

def extract_backlinks(markdown_content: str) -> List[str]:
    """
    Extract Obsidian style backlinks:
    [[GraphRAG]]
    [[Agent Memory]]
    """
    return re.findall(r"\[\[(.*?)\]\]", markdown_content)


def extract_title(markdown_content: str, file_path: str) -> str:
    """
    Use first markdown heading as title.
    Fallback to filename.
    """
    heading_match = re.search(r"^#\s+(.*)", markdown_content, re.MULTILINE)

    if heading_match:
        return heading_match.group(1).strip()

    return os.path.splitext(os.path.basename(file_path))[0]


# =========================================================
# INSERT NOTE
# =========================================================

def insert_note(
    user_id: str,
    md_file_path: str,
    tags: Optional[List[str]] = None,
    topics: Optional[List[str]] = None,
    embedding: Optional[List[float]] = None,
    settings: DatabaseSettings | None = None,
):
    conn = _get_connection(settings)

    try:
        # Read markdown file
        with open(md_file_path, "r", encoding="utf-8") as f:
            content = f.read()

        title = extract_title(content, md_file_path)

        backlinks = extract_backlinks(content)

        cur = conn.cursor()

        cur.execute("""
            INSERT INTO notes (
                user_id,
                title,
                file_path,
                content,
                backlinks,
                tags,
                topics,
                embedding,
                search_vector
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s,
                to_tsvector('english', %s)
            )
            RETURNING id
        """, (
            user_id,
            title,
            md_file_path,
            content,
            backlinks,
            tags,
            topics,
            embedding,
            f"{title} {content}"
        ))

        note_id = cur.fetchone()[0]

        conn.commit()

        return note_id

    except Exception as e:
        conn.rollback()
        raise e

    finally:
        cur.close()
        conn.close()


# =========================================================
# FULL TEXT SEARCH
# =========================================================

def search_notes(
    user_id: str,
    query: str,
    limit: int = 5,
    settings: DatabaseSettings | None = None,
):
    conn = _get_connection(settings)

    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT
                id,
                title,
                file_path,
                tags,
                topics,
                backlinks,
                ts_rank(search_vector, plainto_tsquery(%s)) AS rank
            FROM notes
            WHERE user_id = %s
            AND search_vector @@ plainto_tsquery(%s)
            ORDER BY rank DESC
            LIMIT %s
        """, (
            query,
            user_id,
            query,
            limit
        ))

        rows = cur.fetchall()

        results = []

        for row in rows:
            results.append({
                "id": row[0],
                "title": row[1],
                "file_path": row[2],
                "tags": row[3],
                "topics": row[4],
                "backlinks": row[5],
                "rank": row[6]
            })

        return results

    except Exception as e:
        raise e

    finally:
        cur.close()
        conn.close()


# =========================================================
# BACKLINK EXPANSION
# =========================================================

def expand_backlinks(
    user_id: str,
    note_titles: List[str],
    settings: DatabaseSettings | None = None,
):
    conn = _get_connection(settings)

    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT
                id,
                title,
                file_path,
                backlinks
            FROM notes
            WHERE user_id = %s
            AND (
                title = ANY(%s)
                OR backlinks && %s
            )
        """, (
            user_id,
            note_titles,
            note_titles
        ))

        rows = cur.fetchall()

        expanded = []

        for row in rows:
            expanded.append({
                "id": row[0],
                "title": row[1],
                "file_path": row[2],
                "backlinks": row[3]
            })

        return expanded

    except Exception as e:
        raise e

    finally:
        cur.close()
        conn.close()


# =========================================================
# HYBRID RETRIEVAL
# =========================================================

def retrieve_notes(
    user_id: str,
    query: str,
    settings: DatabaseSettings | None = None,
):
    """
    1. Full text search
    2. Expand backlinks
    """

    # Step 1 — Search
    search_results = search_notes(user_id, query, settings=settings)

    if not search_results:
        return []

    # Step 2 — Collect titles
    titles = [note["title"] for note in search_results]

    # Step 3 — Expand graph neighborhood
    graph_results = expand_backlinks(user_id, titles, settings=settings)

    # Merge uniquely
    unique_notes = {}

    for note in search_results + graph_results:
        unique_notes[note["id"]] = note

    return list(unique_notes.values())


# =========================================================
# EXAMPLE USAGE
# =========================================================

if __name__ == "__main__": 

    # Insert markdown note
    insert_note(
        user_id="user_123",
        md_file_path="AgentMemory.md",
        tags=["AI", "Agents"],
        topics=["Retrieval", "Memory"]
    )

    # Retrieve notes
    results = retrieve_notes(
        user_id="user_123",
        query="agent memory compression"
    )

    for note in results:
        print(note["title"])