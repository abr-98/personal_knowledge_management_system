import uuid
import tiktoken
from entity_handlers.entity_extractor import extract_metadata
from entity_handlers.relationship_extractor_auto import extract_relationships


# =========================================================
# TOKENIZER
# =========================================================
def get_tokenizer(model_name="gpt-4o-mini"):

    return tiktoken.encoding_for_model(model_name)


# =========================================================
# TOKEN COUNTER
# =========================================================
def count_tokens(text, tokenizer):

    return len(tokenizer.encode(text))


# =========================================================
# GENERIC FIXED CHUNKER
# =========================================================
def fixed_size_chunker(
    text,
    chunk_size=500,
    overlap=100,
    model_name="gpt-4o-mini"
):

    """
    Generic token-based chunker.

    Parameters
    ----------
    text : str
        Input text

    chunk_size : int
        Max tokens per chunk

    overlap : int
        Overlapping tokens between chunks

    model_name : str
        Tokenizer model

    Returns
    -------
    List[dict]
    """

    tokenizer = get_tokenizer(model_name)

    tokens = tokenizer.encode(text)

    chunks = []

    start = 0

    while start < len(tokens):

        end = start + chunk_size

        chunk_tokens = tokens[start:end]

        chunk_text = tokenizer.decode(chunk_tokens)

        chunks.append({

            "chunk_id": str(uuid.uuid4()),

            "text": chunk_text,
            
            "entities": extract_metadata(chunk_text)["entities"],

            "start_token": start,
            "end_token": end,

            "token_count": len(chunk_tokens),

            "chunk_type": "fixed_overlap"
        })

        # Move window with overlap
        start += chunk_size - overlap

    return chunks


# =========================================================
# FILE LOADER
# =========================================================
def load_text_file(file_path):

    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


# =========================================================
# CHUNK FILE DIRECTLY
# =========================================================
def chunk_file(
    file_path,
    chunk_size=500,
    overlap=100,
    model_name="gpt-4o-mini"
):

    text = load_text_file(file_path)

    chunks = fixed_size_chunker(
        text=text,
        chunk_size=chunk_size,
        overlap=overlap,
        model_name=model_name
    )
    
    for chunk in chunks:
        if len(chunk) > 0:
            relationships = extract_relationships(
                chunk["text"],
                [i["text"] for i in chunk["entities"]])
            chunk["relationships"] = relationships

    # Add source metadata
    for chunk in chunks:

        chunk["source"] = file_path
        
    

    return chunks
