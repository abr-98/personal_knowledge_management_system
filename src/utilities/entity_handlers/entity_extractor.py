"""
Improved PKMS Entity Extractor
------------------------------
Goal:
- Remove useless entities
- Remove integers/numeric junk
- Remove stopword-heavy phrases
- Use TopicRank importance
- Use TF-IDF filtering
- Keep highly important concepts only

Uses:
- spaCy
- KeyBERT
- YAKE
- TF-IDF
- TopicRank-inspired ranking

Install:
pip install spacy keybert yake scikit-learn sentence-transformers
python -m spacy download en_core_web_md
"""

import re
from collections import defaultdict, Counter

import spacy
import yake

from keybert import KeyBERT

from sklearn.feature_extraction.text import (
    TfidfVectorizer
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

kw_model = KeyBERT(
    model="all-MiniLM-L6-v2"
)

yake_extractor = yake.KeywordExtractor(

    lan="en",

    n=3,

    top=30
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
def normalize_entity(text):

    text = text.strip().lower()

    text = re.sub(r"\s+", " ", text)

    return text


# =========================================================
# ENTITY FILTERING
# =========================================================
def is_valid_entity(text):

    text = text.strip()

    normalized = normalize_entity(text)

    words = normalized.split()

    # ---------------------------------------------
    # Too short
    # ---------------------------------------------
    if len(words) == 0:
        return False

    # ---------------------------------------------
    # Remove pure numbers
    # ---------------------------------------------
    if re.fullmatch(r"\d+", normalized):
        return False

    # ---------------------------------------------
    # Remove decimals
    # ---------------------------------------------
    if re.fullmatch(
        r"\d+\.\d+",
        normalized
    ):
        return False

    # ---------------------------------------------
    # Remove numeric-heavy phrases
    # ---------------------------------------------
    digit_ratio = sum(
        c.isdigit()
        for c in normalized
    ) / max(len(normalized), 1)

    if digit_ratio > 0.25:
        return False

    # ---------------------------------------------
    # Remove stopword-heavy phrases
    # ---------------------------------------------
    stopword_ratio = sum(

        1

        for word in words

        if word in nlp.Defaults.stop_words

    ) / len(words)

    if stopword_ratio > 0.5:
        return False

    # ---------------------------------------------
    # Remove very generic single words
    # ---------------------------------------------
    generic_words = {

        "paper",
        "method",
        "methods",
        "result",
        "results",
        "task",
        "tasks",
        "problem",
        "problems",
        "approach",
        "system",
        "model",
        "models",
        "data"
    }

    if (
        len(words) == 1
        and
        words[0] in generic_words
    ):

        return False

    return True


# =========================================================
# SPACY ENTITIES
# =========================================================
def extract_spacy_entities(text):

    doc = nlp(text)

    entities = []

    for ent in doc.ents:

        entity_text = ent.text.strip()

        if not is_valid_entity(
            entity_text
        ):
            continue

        entities.append({

            "text": entity_text,

            "normalized": normalize_entity(
                entity_text
            ),

            "score": 0.9,

            "source": "spacy",

            "label": ent.label_
        })

    return entities


# =========================================================
# KEYBERT
# =========================================================
def extract_keybert_keywords(

    text,

    top_n=30
):

    keywords = kw_model.extract_keywords(

        text,

        keyphrase_ngram_range=(1, 3),

        stop_words="english",

        top_n=top_n
    )

    entities = []

    for keyword, score in keywords:

        if not is_valid_entity(
            keyword
        ):
            continue

        entities.append({

            "text": keyword,

            "normalized": normalize_entity(
                keyword
            ),

            "score": float(score),

            "source": "keybert",

            "label": "KEYPHRASE"
        })

    return entities


# =========================================================
# YAKE
# =========================================================
def extract_yake_keywords(text):

    keywords = yake_extractor.extract_keywords(
        text
    )

    entities = []

    for keyword, score in keywords:

        if not is_valid_entity(
            keyword
        ):
            continue

        # YAKE:
        # lower score = better
        adjusted_score = (
            1 - min(score, 1)
        )

        entities.append({

            "text": keyword,

            "normalized": normalize_entity(
                keyword
            ),

            "score": adjusted_score,

            "source": "yake",

            "label": "YAKE"
        })

    return entities


# =========================================================
# TF-IDF SCORING
# =========================================================
def compute_tfidf_scores(

    text,

    entities
):

    vectorizer = TfidfVectorizer(

        stop_words="english"
    )

    vectorizer.fit([text])

    vocab = vectorizer.vocabulary_

    for entity in entities:

        words = entity[
            "normalized"
        ].split()

        tfidf_score = 0

        for word in words:

            if word in vocab:

                tfidf_score += (
                    vocab[word]
                )

        entity["tfidf_score"] = (
            tfidf_score
        )

    return entities


# =========================================================
# TOPICRANK-STYLE SCORING
# =========================================================
def apply_topic_rank(entities):

    """
    Simple TopicRank-inspired scoring:
    frequent entities across methods
    become more important.
    """

    counter = Counter([

        entity["normalized"]

        for entity in entities
    ])

    for entity in entities:

        topic_rank_score = counter[
            entity["normalized"]
        ]

        entity["topic_rank_score"] = (
            topic_rank_score
        )

    return entities


# =========================================================
# MERGE ENTITIES
# =========================================================
def merge_entities(entity_lists):

    merged = {}

    for entity_group in entity_lists:

        for entity in entity_group:

            key = entity["normalized"]

            if key not in merged:

                merged[key] = entity

            else:

                merged[key]["score"] = max(

                    merged[key]["score"],

                    entity["score"]
                )

    return list(merged.values())


# =========================================================
# FINAL RANKING
# =========================================================
def rank_entities(entities):

    for entity in entities:

        entity["final_score"] = (

            entity.get("score", 0)

            +

            entity.get(
                "tfidf_score",
                0
            ) * 0.05

            +

            entity.get(
                "topic_rank_score",
                0
            ) * 0.5
        )

    ranked = sorted(

        entities,

        key=lambda x: x["final_score"],

        reverse=True
    )

    return ranked


# =========================================================
# GENERATE TAGS
# =========================================================
def generate_tags(entities):

    tags = []

    for entity in entities:

        tag = (
            entity["normalized"]
            .replace(" ", "_")
        )

        tags.append(f"#{tag}")

    return sorted(list(set(tags)))


# =========================================================
# GROUP ENTITIES
# =========================================================
def group_entities(entities):

    grouped = defaultdict(list)

    for entity in entities:

        grouped[
            entity["label"]
        ].append(entity["text"])

    return dict(grouped)


# =========================================================
# MAIN FUNCTION
# =========================================================
def extract_metadata(

    text,

    top_n=20
):

    text = clean_text(text)

    # ---------------------------------------------
    # Extract entities
    # ---------------------------------------------
    spacy_entities = (
        extract_spacy_entities(text)
    )

    keybert_entities = (
        extract_keybert_keywords(
            text,
            top_n=30
        )
    )

    yake_entities = (
        extract_yake_keywords(text)
    )

    # ---------------------------------------------
    # Merge
    # ---------------------------------------------
    merged_entities = merge_entities([

        spacy_entities,

        keybert_entities,

        yake_entities
    ])

    # ---------------------------------------------
    # TF-IDF scoring
    # ---------------------------------------------
    merged_entities = (
        compute_tfidf_scores(

            text,

            merged_entities
        )
    )

    # ---------------------------------------------
    # TopicRank scoring
    # ---------------------------------------------
    merged_entities = (
        apply_topic_rank(
            merged_entities
        )
    )

    # ---------------------------------------------
    # Final ranking
    # ---------------------------------------------
    ranked_entities = rank_entities(
        merged_entities
    )

    # ---------------------------------------------
    # Top entities only
    # ---------------------------------------------
    ranked_entities = ranked_entities[
        :top_n
    ]

    # ---------------------------------------------
    # Tags
    # ---------------------------------------------
    tags = generate_tags(
        ranked_entities
    )

    # ---------------------------------------------
    # Grouping
    # ---------------------------------------------
    grouped = group_entities(
        ranked_entities
    )

    # =====================================================
    # FINAL OUTPUT
    # =====================================================
    return {

        "entities": ranked_entities,

        "grouped_entities": grouped,

        "tags": tags
    }