"""
Improved Relationship Extraction
--------------------------------
Features:
- Co-occurrence relationships
- Dependency relationships
- Semantic scoring
- Weak entity filtering
- Relationship pruning
- Graph-ready triples

Install:
pip install spacy sentence-transformers scikit-learn
python -m spacy download en_core_web_md
"""

import itertools
import spacy

from collections import defaultdict

from sentence_transformers import (
    SentenceTransformer
)

from sklearn.metrics.pairwise import (
    cosine_similarity
)


# =========================================================
# LOAD MODELS
# =========================================================
for _model_name in ("en_core_web_md", "en_core_web_sm"):
    try:
        nlp = spacy.load(_model_name)
        break
    except OSError:
        continue
else:
    nlp = spacy.blank("en")

embedding_model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)


# =========================================================
# GENERIC LOW-INFORMATION ENTITIES
# =========================================================
GENERIC_ENTITIES = {

    "paper",
    "work",
    "time",
    "table",
    "figure",
    "quality",
    "permission",
    "result",
    "method",
    "model",
    "task",
    "approach",
    "problem",
    "system"
}


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
# ENTITY VALIDATION
# =========================================================
def is_valid_entity(entity):

    entity = normalize_entity(
        entity
    )

    # ---------------------------------------------
    # Empty
    # ---------------------------------------------
    if not entity:
        return False

    # ---------------------------------------------
    # Tiny entities
    # ---------------------------------------------
    if len(entity) < 3:
        return False

    # ---------------------------------------------
    # Generic entities
    # ---------------------------------------------
    if entity in GENERIC_ENTITIES:
        return False

    # ---------------------------------------------
    # Numeric
    # ---------------------------------------------
    if entity.isdigit():
        return False

    return True


# =========================================================
# SEMANTIC SIMILARITY
# =========================================================
def semantic_similarity(

    source,

    target
):

    embeddings = embedding_model.encode([

        source,
        target
    ])

    similarity = cosine_similarity(

        [embeddings[0]],

        [embeddings[1]]
    )[0][0]

    return float(similarity)


# =========================================================
# RELATIONSHIP SCORE
# =========================================================
def compute_relationship_score(

    relationship,

    entity_frequency
):

    source = relationship["source"]

    target = relationship["target"]

    base_confidence = (
        relationship["confidence"]
    )

    similarity = semantic_similarity(

        source,

        target
    )

    source_freq = entity_frequency.get(
        source,
        1
    )

    target_freq = entity_frequency.get(
        target,
        1
    )

    # ---------------------------------------------
    # Final weighted score
    # ---------------------------------------------
    score = (

        base_confidence

        +

        similarity

        +

        (0.1 * source_freq)

        +

        (0.1 * target_freq)
    )

    return round(score, 4)


# =========================================================
# CO-OCCURRENCE RELATIONSHIPS
# =========================================================
def create_cooccurrence_relationships(

    entities,

    chunk_id=None
):

    relationships = []

    unique_entities = list(set([

        normalize_entity(e)

        for e in entities

        if is_valid_entity(e)
    ]))

    for source, target in itertools.combinations(

        unique_entities,

        2
    ):

        relationships.append({

            "source": source,

            "relation": "RELATED_TO",

            "target": target,

            "confidence": 0.45,

            "method": "cooccurrence",

            "chunk_id": chunk_id
        })

    return relationships


# =========================================================
# DEPENDENCY RELATIONSHIPS
# =========================================================
def create_dependency_relationships(

    text,

    entities,

    chunk_id=None
):

    """
    Extracts:
        subject -> verb -> object

    ONLY between valid entities.
    """

    doc = nlp(text)

    relationships = []

    # ---------------------------------------------
    # Valid entity set
    # ---------------------------------------------
    valid_entities = set([

        normalize_entity(e)

        for e in entities
    ])

    for token in doc:

        # -----------------------------------------
        # Only verbs
        # ---------------------------------------------
        if token.pos_ != "VERB":
            continue

        subject = None
        obj = None

        # -----------------------------------------
        # Find subject/object
        # ---------------------------------------------
        for child in token.children:

            if child.dep_ in (
                "nsubj",
                "nsubjpass"
            ):

                subject = normalize_entity(
                    child.text
                )

            if child.dep_ in (
                "dobj",
                "pobj",
                "attr"
            ):

                obj = normalize_entity(
                    child.text
                )

        # -----------------------------------------
        # Must exist
        # ---------------------------------------------
        if not subject or not obj:
            continue

        # -----------------------------------------
        # MUST be canonical entities
        # ---------------------------------------------
        if (
            subject not in valid_entities
            or
            obj not in valid_entities
        ):

            continue

        # -----------------------------------------
        # Create relationship
        # ---------------------------------------------
        relationships.append({

            "source": subject,

            "relation": token.lemma_.upper(),

            "target": obj,

            "confidence": 0.9,

            "method": "dependency_parse",

            "chunk_id": chunk_id
        })

    return relationships

# =========================================================
# DEDUPLICATE
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

        # Keep strongest
        if (
            key not in unique
            or
            rel["score"]
            > unique[key]["score"]
        ):

            unique[key] = rel

    return list(unique.values())


# =========================================================
# FILTER RELATIONSHIPS
# =========================================================
def filter_relationships(

    relationships,

    min_score=1.2
):

    filtered = []

    for rel in relationships:

        # -----------------------------------------
        # Remove self loops
        # -----------------------------------------
        if (
            rel["source"]
            ==
            rel["target"]
        ):

            continue

        # -----------------------------------------
        # Remove weak relationships
        # -----------------------------------------
        if rel["score"] < min_score:
            continue

        filtered.append(rel)

    return filtered


# =========================================================
# MAIN EXTRACTOR
# =========================================================
def extract_relationships(

    text,

    entities,

    chunk_id=None
):

    # ---------------------------------------------
    # Entity frequency
    # ---------------------------------------------
    entity_frequency = defaultdict(int)

    for entity in entities:

        entity = normalize_entity(
            entity
        )

        entity_frequency[
            entity
        ] += 1

    # ---------------------------------------------
    # Co-occurrence
    # ---------------------------------------------
    cooccurrence_relationships = (

        create_cooccurrence_relationships(

            entities,

            chunk_id=chunk_id
        )
    )

    # ---------------------------------------------
    # Dependency relationships
    # ---------------------------------------------
    dependency_relationships = (

        create_dependency_relationships(

            text,
            
            entities,

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
    # Add semantic score
    # ---------------------------------------------
    for rel in all_relationships:

        rel["score"] = (
            compute_relationship_score(

                rel,

                entity_frequency
            )
        )

    # ---------------------------------------------
    # Filter
    # ---------------------------------------------
    filtered_relationships = (
        filter_relationships(
            all_relationships
        )
    )

    # ---------------------------------------------
    # Deduplicate
    # ---------------------------------------------
    final_relationships = (
        deduplicate_relationships(

            filtered_relationships
        )
    )

    # ---------------------------------------------
    # Sort strongest first
    # ---------------------------------------------
    final_relationships = sorted(

        final_relationships,

        key=lambda x: x["score"],

        reverse=True
    )

    return final_relationships