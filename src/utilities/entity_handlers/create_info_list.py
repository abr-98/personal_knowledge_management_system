"""
Simple Unified Knowledge Extractor
----------------------------------
- Accepts:
    - dict
    - list[dict]

- Reuses:
    - entities
    - tags
    - relationships

- Normalizes everything into:
    {
        text,
        entities,
        tags,
        relationships
    }
"""

import re


# =========================================================
# MARKDOWN EXTRACTION
# =========================================================
def extract_markdown_entities(text):

    tags = re.findall(
        r"#(\w+)",
        text
    )

    headings = re.findall(
        r"^#+\s+(.*)",
        text,
        re.MULTILINE
    )

    wikilinks = re.findall(
        r"\[\[(.*?)\]\]",
        text
    )

    entities = list(set(

        headings

        +

        wikilinks

        +

        tags
    ))

    return {

        "entities": entities,

        "tags": tags
    }


# =========================================================
# NORMALIZE RELATIONSHIPS
# =========================================================
def normalize_relationships(relationships):

    normalized = []

    for rel in relationships:

        # -----------------------------------------
        # Dict format
        # -----------------------------------------
        if isinstance(rel, dict):

            normalized.append({

                "source": rel.get(
                    "source",
                    ""
                ),

                "relation": rel.get(
                    "relation",
                    ""
                ),

                "target": rel.get(
                    "target",
                    ""
                )
            })

        # -----------------------------------------
        # Tuple/list format
        # -----------------------------------------
        elif (
            isinstance(rel, (list, tuple))
            and
            len(rel) == 3
        ):

            normalized.append({

                "source": rel[0],

                "relation": rel[1],

                "target": rel[2]
            })

    return normalized


# =========================================================
# PROCESS SINGLE ITEM
# =========================================================
def process_item(item):

    # ---------------------------------------------
    # Safe text extraction
    # ---------------------------------------------
    try:

        text = item["text"]

    except:

        return None

    source = item.get(
        "source",
        ""
    )

    # =====================================================
    # ENTITIES
    # =====================================================
    entities = []

    if (
        "entities" in item
        and
        len(item["entities"]) > 0
    ):

        for entity in item["entities"]:

            # -------------------------------------
            # Dict entity
            # -------------------------------------
            if isinstance(entity, dict):

                entity_text = entity.get(
                    "text",
                    ""
                )

                if entity_text:

                    entities.append(
                        entity_text
                    )

            # -------------------------------------
            # String entity
            # -------------------------------------
            else:

                entities.append(entity)

    # =====================================================
    # MARKDOWN FALLBACK
    # =====================================================
    elif source.endswith(".md"):

        metadata = (
            extract_markdown_entities(
                text
            )
        )

        entities = metadata[
            "entities"
        ]

    # =====================================================
    # TAGS
    # =====================================================
    tags = item.get(
        "tags",
        []
    )

    # =====================================================
    # RELATIONSHIPS
    # =====================================================
    relationships = []

    if (
        "relationships" in item
        and
        item["relationships"]
    ):

        relationships = (
            normalize_relationships(

                item["relationships"]
            )
        )

    # =====================================================
    # FINAL OUTPUT
    # =====================================================
    return {

        "chunk_id": item.get(
            "chunk_id"
        ),

        "source": source,

        "text": text,

        "entities": list(set(
            entities
        )),

        "tags": list(set(
            tags
        )),

        "relationships": (
            relationships
        )
    }


# =========================================================
# MAIN FUNCTION
# =========================================================
def extract_knowledge(data):

    # =====================================================
    # SINGLE ITEM
    # =====================================================
    if isinstance(data, dict):

        return process_item(data)

    # =====================================================
    # LIST
    # =====================================================
    results = []

    for item in data:

        result = process_item(
            item
        )

        if result:

            results.append(result)

    return results


