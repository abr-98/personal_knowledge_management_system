"""
Entity Canonicalization + Intelligent Filtering
------------------------------------------------
Purpose:
- Normalize entities
- Remove noisy variants
- Remove verbs/adjectives
- Deduplicate entities
- Remove fragment entities
- Keep important generic concepts
- Domain agnostic filtering
- Prevent graph explosion

Install:
pip install spacy
python -m spacy download en_core_web_md
"""

import re
import spacy

from collections import Counter


# =========================================================
# LOAD MODEL
# =========================================================
for _model_name in ("en_core_web_md", "en_core_web_sm"):
    try:
        nlp = spacy.load(_model_name)
        break
    except OSError:
        continue
else:
    nlp = spacy.blank("en")


# =========================================================
# SINGLE ENTITY CLEANER
# =========================================================
def canonicalize_entity(entity):

    if not entity:
        return ""

    # ---------------------------------------------
    # Normalize
    # ---------------------------------------------
    entity = entity.strip().lower()

    # ---------------------------------------------
    # Remove punctuation
    # ---------------------------------------------
    entity = re.sub(
        r"[^\w\s-]",
        "",
        entity
    )

    # ---------------------------------------------
    # Remove extra spaces
    # ---------------------------------------------
    entity = re.sub(
        r"\s+",
        " ",
        entity
    )

    # ---------------------------------------------
    # Process with spaCy
    # ---------------------------------------------
    doc = nlp(entity)

    cleaned_tokens = []

    for token in doc:

        # -----------------------------------------
        # Remove stopwords
        # -----------------------------------------
        if token.is_stop:
            continue

        # -----------------------------------------
        # Remove verbs
        # -----------------------------------------
        if token.pos_ == "VERB":
            continue

        # -----------------------------------------
        # Remove adjectives
        # -----------------------------------------
        if token.pos_ == "ADJ":
            continue

        # -----------------------------------------
        # Remove numbers
        # -----------------------------------------
        if token.like_num:
            continue

        # -----------------------------------------
        # Keep nouns/proper nouns only
        # -----------------------------------------
        if token.pos_ in (
            "NOUN",
            "PROPN"
        ):

            cleaned_tokens.append(
                token.lemma_
            )

    # ---------------------------------------------
    # Join cleaned tokens
    # ---------------------------------------------
    canonical = " ".join(
        cleaned_tokens
    ).strip()

    return canonical


# =========================================================
# REMOVE FRAGMENT ENTITIES
# =========================================================
def filter_fragment_entities(
    entities
):

    """
    Removes:
    - substring entities
    - weaker phrase variants

    Example:
        translation
        machine translation

    Keeps:
        machine translation
    """

    # ---------------------------------------------
    # Sort longest first
    # ---------------------------------------------
    entities = sorted(

        list(set(entities)),

        key=len,

        reverse=True
    )

    filtered = []

    for entity in entities:

        is_fragment = False

        for kept_entity in filtered:

            # -------------------------------------
            # Substring check
            # -------------------------------------
            if (

                entity in kept_entity

                and

                entity != kept_entity
            ):

                # ---------------------------------
                # Token overlap check
                # ---------------------------------
                entity_tokens = set(
                    entity.split()
                )

                kept_tokens = set(
                    kept_entity.split()
                )

                overlap_ratio = (

                    len(
                        entity_tokens
                        &
                        kept_tokens
                    )

                    /

                    len(entity_tokens)
                )

                # ---------------------------------
                # Strong overlap
                # ---------------------------------
                if overlap_ratio >= 0.8:

                    is_fragment = True

                    break

        if not is_fragment:

            filtered.append(entity)

    return filtered


# =========================================================
# ENTITY IMPORTANCE
# =========================================================
def compute_entity_importance(
    entities
):

    frequency = Counter(entities)

    scores = {}

    for entity in entities:

        words = entity.split()

        # -----------------------------------------
        # Phrase specificity
        # -----------------------------------------
        specificity = len(words)

        # -----------------------------------------
        # Frequency
        # -----------------------------------------
        freq = frequency[
            entity
        ]

        # -----------------------------------------
        # Character richness
        # -----------------------------------------
        richness = min(
            len(entity) / 10,
            2
        )

        # -----------------------------------------
        # Final score
        # -----------------------------------------
        score = (

            specificity * 0.5

            +

            freq * 0.3

            +

            richness * 0.2
        )

        scores[entity] = round(
            score,
            4
        )

    return scores


# =========================================================
# LOW INFORMATION FILTER
# =========================================================
def filter_low_information_entities(
    entities
):

    scores = compute_entity_importance(
        entities
    )

    filtered = []

    for entity, score in scores.items():

        word_count = len(
            entity.split()
        )

        # -----------------------------------------
        # Remove ultra weak single words
        # -----------------------------------------
        if (
            word_count == 1
            and
            score < 1.1
        ):
            continue

        # -----------------------------------------
        # Remove repeated character garbage
        # -----------------------------------------
        if len(set(entity)) <= 2:
            continue

        # -----------------------------------------
        # Remove very short entities
        # -----------------------------------------
        if len(entity) < 3:
            continue

        filtered.append(entity)

    return filtered


# =========================================================
# MAIN CLEANER
# =========================================================
def canonicalize_entities(entities):

    """
    Accepts:
    - list[str]
    - list[dict]

    Returns:
    cleaned entities
    """

    cleaned = []

    # =====================================================
    # CANONICALIZATION
    # =====================================================
    for entity in entities:

        # -----------------------------------------
        # Dict entity
        # -----------------------------------------
        if isinstance(entity, dict):

            entity_text = entity.get(
                "text",
                ""
            )

        # -----------------------------------------
        # String entity
        # -----------------------------------------
        else:

            entity_text = str(entity)

        canonical = (
            canonicalize_entity(
                entity_text
            )
        )

        # -----------------------------------------
        # Remove empty
        # -----------------------------------------
        if not canonical:
            continue

        cleaned.append(canonical)

    # =====================================================
    # DEDUPLICATE
    # =====================================================
    cleaned = list(set(cleaned))

    # =====================================================
    # REMOVE FRAGMENT ENTITIES
    # =====================================================
    cleaned = filter_fragment_entities(
        cleaned
    )

    # =====================================================
    # REMOVE LOW INFORMATION ENTITIES
    # =====================================================
    cleaned = (
        filter_low_information_entities(
            cleaned
        )
    )

    # =====================================================
    # SORT
    # =====================================================
    cleaned = sorted(cleaned)

    return cleaned

