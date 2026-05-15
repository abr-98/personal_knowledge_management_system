"""
LLM Document-Level Semantic Extraction
--------------------------------------
Uses LLM ONLY for:
- domain
- subdomain
- topics
- summary

NOT:
- chunk extraction
- entity extraction
- embeddings

This is the scalable PKMS approach.

Install:
pip install openai
"""

import json
import fitz

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
# PROMPT
# =========================================================
DOCUMENT_ANALYSIS_PROMPT = """
Analyze the following document.

Extract:

1. Main domain
2. Subdomain
3. Important topics
4. Short summary

Return ONLY valid JSON.

Format:

{
    "domain": "...",
    "subdomain": "...",
    "topics": [...],
    "summary": "..."
}

DOCUMENT:
{TEXT}
"""


# =========================================================
# TEXT REDUCTION
# =========================================================
def reduce_document_text(

    text,

    max_chars=12000
):

    """
    Reduce document size
    before sending to LLM.

    Keeps:
    - beginning
    - middle
    - end
    """

    text = text.strip()

    if len(text) <= max_chars:

        return text

    third = max_chars // 3

    beginning = text[:third]

    middle_start = len(text) // 2

    middle = text[
        middle_start:
        middle_start + third
    ]

    end = text[-third:]

    reduced = (

        beginning

        +

        "\n\n"

        +

        middle

        +

        "\n\n"

        +

        end
    )

    return reduced


# =========================================================
# LLM CALL
# =========================================================
def call_llm(prompt):

    response = (
        client.chat.completions.create(

            model="gpt-4o-mini",

            messages=[

                {
                    "role": "user",

                    "content": prompt
                }
            ],

            temperature=0
        )
    )

    return response.choices[
        0
    ].message.content


# =========================================================
# DOCUMENT ANALYSIS
# =========================================================
def analyze_document(text):

    # ---------------------------------------------
    # Reduce size
    # ---------------------------------------------
    reduced_text = (
        reduce_document_text(
            text
        )
    )

    # ---------------------------------------------
    # Create prompt
    # ---------------------------------------------
    prompt = (
        DOCUMENT_ANALYSIS_PROMPT
        .replace(
            "{TEXT}",
            reduced_text
        )
    )

    # ---------------------------------------------
    # Call LLM
    # ---------------------------------------------
    response = call_llm(
        prompt
    )

    # ---------------------------------------------
    # Parse JSON
    # ---------------------------------------------
    try:

        data = json.loads(
            response
        )

    except Exception:

        data = {

            "domain": "Unknown",

            "subdomain": "Unknown",

            "topics": [],

            "summary": ""
        }

    return data


# =========================================================
# PROCESS DOCUMENT OBJECT
# =========================================================
def process_document(document):


    analysis = analyze_document(
        document
    )

    return {

        "domain": analysis.get(
            "domain",
            "Unknown"
        ),

        "subdomain": analysis.get(
            "subdomain",
            "Unknown"
        ),

        "topics": analysis.get(
            "topics",
            []
        ),

        "summary": analysis.get(
            "summary",
            ""
        )
    }
    
# =========================================================

# LOAD AND PROCESS DOCUMENT

def load_and_process_document(consolidated_chunks):
    # ---------------------------------------------
    # Combine text
    # ---------------------------------------------
    for chunk in consolidated_chunks:
        
        text = chunk.get(
            "text",
            ""
        )
        
        chunk["meta_details"] = process_document(text)
        
    return consolidated_chunks
        
            
    