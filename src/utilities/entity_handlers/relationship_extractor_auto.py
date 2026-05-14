"""
Relationship Extraction for PKMS / Graph RAG
--------------------------------------------
Features:
- Entity co-occurrence relationships
- spaCy dependency relationships
- Graph-ready triples
- Chunk-aware relationship extraction
- Confidence scoring

Install:
pip install spacy
python -m spacy download en_core_web_md
"""

import itertools
import spacy


# =========================================================
# LOAD MODEL
# =========================================================
nlp = spacy.load("en_core_web_md")


# =========================================================
# NORMALIZATION
# =========================================================
def normalize_entity(text):

    return (
        text.strip()
        .lower()
        .replace("\n", " ")
    )


# =========================================================
# CO-OCCURRENCE RELATIONSHIPS
# =========================================================
def create_cooccurrence_relationships(

    entities,

    chunk_id=None
):

    """
    Creates weak graph edges based on
    entity co-occurrence inside a chunk.
    """

    relationships = []

    unique_entities = list(set([
        normalize_entity(e)
        for e in entities
    ]))

    # Create all pair combinations
    for source, target in itertools.combinations(
        unique_entities,
        2
    ):

        relationships.append({

            "source": source,

            "relation": "RELATED_TO",

            "target": target,

            "confidence": 0.5,

            "method": "cooccurrence",

            "chunk_id": chunk_id
        })

    return relationships


# =========================================================
# DEPENDENCY RELATIONSHIPS
# =========================================================
def create_dependency_relationships(

    text,

    chunk_id=None
):

    """
    Extracts:
        subject -> verb -> object

    Example:
        Transformer uses attention
    """

    doc = nlp(text)

    relationships = []

    for token in doc:

        # Look for verbs
        if token.pos_ != "VERB":
            continue

        subject = None
        obj = None

        # -----------------------------------------
        # Find subject
        # -----------------------------------------
        for child in token.children:

            if child.dep_ in (
                "nsubj",
                "nsubjpass"
            ):

                subject = child.text

            # -------------------------------------
            # Find object
            # -------------------------------------
            if child.dep_ in (
                "dobj",
                "pobj",
                "attr"
            ):

                obj = child.text

        # -----------------------------------------
        # Create relationship
        # -----------------------------------------
        if subject and obj:

            relationships.append({

                "source": normalize_entity(
                    subject
                ),

                "relation": token.lemma_.upper(),

                "target": normalize_entity(
                    obj
                ),

                "confidence": 0.85,

                "method": "dependency_parse",

                "chunk_id": chunk_id
            })

    return relationships


# =========================================================
# DEDUPLICATE RELATIONSHIPS
# =========================================================
def deduplicate_relationships(
    relationships
):

    unique = {}

    for rel in relationships:

        key = (
            rel["source"],
            rel["relation"],
            rel["target"]
        )

        # Keep highest confidence
        if (
            key not in unique
            or
            rel["confidence"]
            > unique[key]["confidence"]
        ):

            unique[key] = rel

    return list(unique.values())


# =========================================================
# MAIN RELATIONSHIP EXTRACTOR
# =========================================================
def extract_relationships(

    text,

    entities,

    chunk_id=None
):

    """
    Hybrid relationship extraction:
    - co-occurrence
    - dependency parsing
    """

    # ---------------------------------------------
    # Weak graph edges
    # ---------------------------------------------
    cooccurrence_relationships = (
        create_cooccurrence_relationships(

            entities,

            chunk_id=chunk_id
        )
    )

    # ---------------------------------------------
    # Strong semantic edges
    # ---------------------------------------------
    dependency_relationships = (
        create_dependency_relationships(

            text,

            chunk_id=chunk_id
        )
    )

    # ---------------------------------------------
    # Merge
    # ---------------------------------------------
    all_relationships = (

        cooccurrence_relationships

        +

        dependency_relationships
    )

    # ---------------------------------------------
    # Deduplicate
    # ---------------------------------------------
    final_relationships = (
        deduplicate_relationships(
            all_relationships
        )
    )

    return final_relationships


# =========================================================
# EXAMPLE USAGE
# =========================================================
if __name__ == "__main__":

    chunk_text = """
    Transformers use self-attention
    mechanisms to improve sequence
    modeling.

    PyTorch is commonly used for
    training Transformer models.

    Neo4j can be used for Graph RAG.
    """

    entities = [

        "Transformers",

        "Self-Attention",

        "Sequence Modeling",

        "PyTorch",

        "Neo4j",

        "Graph RAG"
    ]

    relationships = extract_relationships(

        text=chunk_text,

        entities=entities,

        chunk_id="chunk_001"
    )

    print("\n" + "=" * 80)

    print("\nRELATIONSHIPS:\n")

    for rel in relationships:

        print(
            f"{rel['source']} "
            f"--{rel['relation']}--> "
            f"{rel['target']}"
        )

        print(
            f"Method: {rel['method']}"
        )

        print(
            f"Confidence: "
            f"{rel['confidence']}"
        )

        print()