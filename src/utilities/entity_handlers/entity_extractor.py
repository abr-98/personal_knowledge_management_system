import re
from collections import defaultdict

import spacy

from keybert import KeyBERT


# =========================================================
# LOAD MODELS
# =========================================================
nlp = spacy.load("en_core_web_lg")

kw_model = KeyBERT(
    model="all-MiniLM-L6-v2"
)


# =========================================================
# CLEAN TEXT
# =========================================================
def clean_text(text):

    text = text.replace("\n", " ")

    text = re.sub(r"\s+", " ", text)

    return text.strip()


# =========================================================
# NORMALIZATION
# =========================================================
def normalize_entity(entity):

    entity = entity.strip()

    # Remove extra whitespace
    entity = re.sub(r"\s+", " ", entity)

    # Lowercase normalization
    entity = entity.lower()

    return entity


# =========================================================
# SPACY ENTITY EXTRACTION
# =========================================================
def extract_spacy_entities(text):

    """
    Extract classical entities:
    - ORG
    - PERSON
    - GPE
    - PRODUCT
    etc.
    """

    doc = nlp(text)

    entities = []

    for ent in doc.ents:

        # Skip tiny/noisy entities
        if len(ent.text.strip()) < 3:
            continue

        entities.append({

            "text": ent.text.strip(),

            "normalized": normalize_entity(
                ent.text
            ),

            "label": ent.label_,

            "source": "spacy"
        })

    return entities


# =========================================================
# KEYBERT EXTRACTION
# =========================================================
def extract_keybert_keywords(

    text,

    top_n=20,

    min_score=0.30
):

    """
    Extract semantic/technical concepts.
    """

    keywords = kw_model.extract_keywords(

        text,

        keyphrase_ngram_range=(1, 3),

        stop_words="english",

        top_n=top_n
    )

    extracted = []

    for keyword, score in keywords:

        if score < min_score:
            continue

        extracted.append({

            "text": keyword,

            "normalized": normalize_entity(
                keyword
            ),

            "score": float(score),

            "label": "KEYPHRASE",

            "source": "keybert"
        })

    return extracted


# =========================================================
# MERGE + DEDUPLICATE
# =========================================================
def merge_entities(

    spacy_entities,

    keybert_entities
):

    merged = {}

    # ---------------------------------------------
    # Add spaCy entities
    # ---------------------------------------------
    for entity in spacy_entities:

        key = entity["normalized"]

        merged[key] = entity

    # ---------------------------------------------
    # Add KeyBERT entities
    # ---------------------------------------------
    for entity in keybert_entities:

        key = entity["normalized"]

        # Prefer spaCy labels if exists
        if key not in merged:

            merged[key] = entity

    return list(merged.values())


# =========================================================
# GENERATE TAGS
# =========================================================
def generate_tags(entities):

    tags = []

    for entity in entities:

        normalized = entity["normalized"]

        # Replace spaces with underscores
        tag = normalized.replace(" ", "_")

        tags.append(f"#{tag}")

    return sorted(list(set(tags)))


# =========================================================
# GROUP ENTITIES BY TYPE
# =========================================================
def group_entities_by_label(entities):

    grouped = defaultdict(list)

    for entity in entities:

        grouped[
            entity["label"]
        ].append(entity["text"])

    return dict(grouped)


# =========================================================
# MAIN EXTRACTOR
# =========================================================
def extract_metadata(

    text,

    top_n_keywords=20
):

    """
    Universal extractor for:
    - PDFs
    - markdown
    - transcripts
    - notes
    - papers
    - books
    """

    cleaned_text = clean_text(text)

    # ---------------------------------------------
    # spaCy entities
    # ---------------------------------------------
    spacy_entities = extract_spacy_entities(
        cleaned_text
    )

    # ---------------------------------------------
    # KeyBERT keywords
    # ---------------------------------------------
    keybert_entities = (
        extract_keybert_keywords(

            cleaned_text,

            top_n=top_n_keywords
        )
    )

    # ---------------------------------------------
    # Merge entities
    # ---------------------------------------------
    merged_entities = merge_entities(

        spacy_entities,

        keybert_entities
    )

    # ---------------------------------------------
    # Generate tags
    # ---------------------------------------------
    tags = generate_tags(
        merged_entities
    )

    # ---------------------------------------------
    # Group by label
    # ---------------------------------------------
    grouped_entities = (
        group_entities_by_label(
            merged_entities
        )
    )

    # =====================================================
    # FINAL OUTPUT
    # =====================================================
    return {

        "entities": merged_entities,

        "grouped_entities": grouped_entities,

        "tags": tags,

        "entity_count": len(
            merged_entities
        )
    }