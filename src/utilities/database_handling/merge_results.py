from collections import defaultdict


# =========================================================
# MERGE SAME TEXT RESULTS
# =========================================================
def merge_same_text_results(results):

    # -----------------------------------------------------
    # Handle retrieval dict
    # -----------------------------------------------------
    if isinstance(results, dict):

        results = results.get(
            "results",
            []
        )

    grouped = defaultdict(list)

    for result in results:

        # ---------------------------------------------
        # Skip invalid
        # ---------------------------------------------
        if not isinstance(
            result,
            dict
        ):
            continue

        text = (
            result.get("text", "")
            .strip()
        )

        grouped[text].append(
            result
        )

    merged_results = []

    # -----------------------------------------------------
    # MERGE GROUPS
    # -----------------------------------------------------
    for text, group in grouped.items():

        entities = set()

        topics = set()

        scores = []

        descriptions = []

        sources = set()

        for item in group:

            # ---------------------------------------------
            # Entity
            # ---------------------------------------------
            entity = item.get(
                "entity",
                ""
            )

            if entity:
                entities.add(entity)

            # ---------------------------------------------
            # Topics
            # ---------------------------------------------
            for topic in item.get(
                "topics",
                []
            ):

                topics.add(topic)

            # ---------------------------------------------
            # Scores
            # ---------------------------------------------
            score = item.get(
                "semantic_score",
                0
            )

            scores.append(score)

            # ---------------------------------------------
            # Description
            # ---------------------------------------------
            desc = item.get(
                "description",
                ""
            )

            if desc:
                descriptions.append(
                    desc
                )

            # ---------------------------------------------
            # Source
            # ---------------------------------------------
            source = item.get(
                "source",
                ""
            )

            if source:
                sources.add(source)

        # -------------------------------------------------
        # FINAL MERGED OBJECT
        # -------------------------------------------------
        merged_results.append({

            "entities":
                sorted(
                    list(entities)
                ),

            "topics":
                sorted(
                    list(topics)
                ),

            "text":
                text,

            "descriptions":
                descriptions,

            "sources":
                sorted(
                    list(sources)
                ),

            "semantic_score":
                max(scores),

            "entity_count":
                len(entities)
        })

    # -----------------------------------------------------
    # SORT
    # -----------------------------------------------------
    merged_results = sorted(

        merged_results,

        key=lambda x:
            x["semantic_score"],

        reverse=True
    )

    return merged_results