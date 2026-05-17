from openai import OpenAI


# =========================================================
# OPENAI CLIENT
# =========================================================

with open("OpenAI-Key.txt", "r") as f:
    api_key = f.read().strip()
client = OpenAI(
    api_key=api_key
)


# =========================================================
# BUILD GRAPH CONTEXT
# =========================================================
def build_graph_context(

    graph_results
):

    context_parts = []

    for item in graph_results:

        entities = item.get(
            "entities",
            []
        )

        topics = item.get(
            "topics",
            []
        )

        text = item.get(
            "text",
            ""
        )

        descriptions = item.get(
            "descriptions",
            []
        )

        semantic_score = item.get(
            "semantic_score",
            0
        )

        context_parts.append(

            f"""
            GRAPH MEMORY

            Semantic Score:
            {semantic_score}

            Entities:
            {", ".join(entities)}

            Topics:
            {", ".join(topics)}

            Descriptions:
            {" ".join(descriptions[:3])}

            Context:
            {text}
            """
        )

    return "\n\n".join(
        context_parts
    )


# =========================================================
# BUILD VECTOR CONTEXT
# =========================================================
def build_vector_context(

    vector_results
):

    context_parts = []

    for item in vector_results:

        document = item.get(
            "document",
            ""
        )

        metadata = item.get(
            "metadata",
            {}
        )

        entities = metadata.get(
            "entities",
            ""
        )

        tags = metadata.get(
            "tags",
            ""
        )

        retrieval = item.get(
            "retrieval",
            ""
        )

        score = item.get(

            "cross_score",

            item.get(
                "score",
                0
            )
        )

        context_parts.append(

            f"""
            VECTOR MEMORY

            Retrieval:
            {retrieval}

            Score:
            {score}

            Entities:
            {entities}

            Tags:
            {tags}

            Context:
            {document}
            """
        )

    return "\n\n".join(
        context_parts
    )


# =========================================================
# BUILD FINAL CONTEXT
# =========================================================
def build_context(

    graph_results,

    vector_results,

    max_chars=15000
):

    graph_context = (
        build_graph_context(
            graph_results
        )
    )

    vector_context = (
        build_vector_context(
            vector_results
        )
    )

    final_context = f"""
    ============================================
    GRAPH MEMORY
    ============================================

    {graph_context}

    ============================================
    VECTOR MEMORY
    ============================================

    {vector_context}
    """

    return final_context[
        :max_chars
    ]


# =========================================================
# GENERATE ANSWER
# =========================================================
def generate_answer(

    query,

    graph_results,

    vector_results,

    model="gpt-4.1-mini"
):

    # =====================================================
    # BUILD CONTEXT
    # =====================================================
    context = build_context(

        graph_results,

        vector_results
    )

    # =====================================================
    # SYSTEM PROMPT
    # =====================================================
    system_prompt = """
    You are an advanced semantic
    PKMS assistant.

    You are provided:
    - graph semantic memories
    - vector semantic memories

    Your goal:
    - synthesize concepts
    - explain semantic relationships
    - merge overlapping memories
    - answer clearly and coherently

    Prioritize:
    - semantic understanding
    - conceptual explanation
    - relationship reasoning

    Avoid:
    - repeating raw chunks
    - noisy entities
    - hallucinations
    """

    # =====================================================
    # USER PROMPT
    # =====================================================
    user_prompt = f"""
    USER QUERY:
    {query}

    ============================================
    RETRIEVED MEMORY
    ============================================

    {context}

    ============================================
    TASK
    ============================================

    Generate:
    1. concise answer
    2. semantic explanation
    3. important connected concepts
    4. relationship reasoning

    Use ONLY retrieved memory.
    """

    # =====================================================
    # LLM CALL
    # =====================================================
    response = client.chat.completions.create(

        model=model,

        messages=[

            {
                "role": "system",
                "content": system_prompt
            },

            {
                "role": "user",
                "content": user_prompt
            }
        ],

        temperature=0.2
    )

    return response.choices[
        0
    ].message.content


# =========================================================
# COMPLETE QA PIPELINE
# =========================================================
def answer_question(

    query,

    graph_results,

    vector_results
):

    answer = generate_answer(

        query=query,

        graph_results=
            graph_results,

        vector_results=
            vector_results
    )

    return {

        "query": query,

        "answer": answer
    }
