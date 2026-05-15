import re
import uuid

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from entity_handlers.entity_extractor import extract_metadata
from entity_handlers.relationship_extractor_auto import extract_relationships
from entity_handlers.clean_entites import canonicalize_entities


# =========================================================
# PARSE SRT FILE
# =========================================================
def parse_srt(srt_path):

    """
    Parses standard .srt files.

    Supports formats like:

    1
    00:00:01,000 --> 00:00:05,000
    Speaker: Hello everyone.

    2
    00:00:05,500 --> 00:00:08,000
    Today we discuss RAG systems.
    """

    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(
        r"(\d+)\s+"
        r"(\d{2}:\d{2}:\d{2},\d{3})\s-->\s"
        r"(\d{2}:\d{2}:\d{2},\d{3})\s+"
        r"(.*?)(?=\n\d+\n|\Z)",
        re.DOTALL
    )

    matches = pattern.findall(content)

    entries = []

    for idx, start, end, text in matches:

        text = text.strip().replace("\n", " ")

        # -----------------------------------------
        # Detect optional speaker
        # -----------------------------------------
        speaker_match = re.match(r"^(.*?):\s(.*)", text)

        if speaker_match:

            speaker = speaker_match.group(1).strip()
            actual_text = speaker_match.group(2).strip()

        else:
            speaker = "UNKNOWN"
            actual_text = text

        entries.append({

            "index": int(idx),

            "start_time": start,
            "end_time": end,

            "speaker": speaker,

            "text": actual_text
        })

    return entries


# =========================================================
# SEMANTIC CHUNKING
# =========================================================
def semantic_srt_chunking(
    entries,
    model,
    similarity_threshold=0.65,
    max_entries_per_chunk=10
):

    if len(entries) <= 1:
        return [entries]

    texts = [
        f"{e['speaker']}: {e['text']}"
        for e in entries
    ]

    embeddings = model.encode(texts)

    chunks = []

    current_chunk = [entries[0]]

    for i in range(1, len(entries)):

        prev_emb = embeddings[i - 1].reshape(1, -1)
        curr_emb = embeddings[i].reshape(1, -1)

        similarity = cosine_similarity(
            prev_emb,
            curr_emb
        )[0][0]

        # -----------------------------------------
        # Topic shift detection
        # -----------------------------------------
        if (
            similarity < similarity_threshold
            or len(current_chunk) >= max_entries_per_chunk
        ):

            chunks.append(current_chunk)

            current_chunk = [entries[i]]

        else:
            current_chunk.append(entries[i])

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


# =========================================================
# MAIN CHUNKER
# =========================================================
def chunk_srt_transcript(
    srt_path,
    embedding_model="all-MiniLM-L6-v2",
    similarity_threshold=0.60,
    max_entries_per_chunk=8
):

    model = SentenceTransformer(embedding_model)

    # -----------------------------------------
    # Parse SRT
    # -----------------------------------------
    entries = parse_srt(srt_path)

    # -----------------------------------------
    # Semantic segmentation
    # -----------------------------------------
    semantic_chunks = semantic_srt_chunking(
        entries,
        model=model,
        similarity_threshold=similarity_threshold,
        max_entries_per_chunk=max_entries_per_chunk
    )

    final_chunks = []

    # =====================================================
    # Build structured chunks
    # =====================================================
    for chunk_idx, chunk_entries in enumerate(semantic_chunks):

        parent_chunk_id = f"srt_window_{chunk_idx}"

        parent_text = "\n".join([
            f"[{e['start_time']}] "
            f"{e['speaker']}: {e['text']}"
            for e in chunk_entries
        ])

        speakers = list(set([
            e["speaker"]
            for e in chunk_entries
        ]))

        window_start = chunk_entries[0]["start_time"]

        window_end = chunk_entries[-1]["end_time"]

        # -----------------------------------------
        # Child chunks
        # -----------------------------------------
        for child_idx, entry in enumerate(chunk_entries):
            
            entities = extract_metadata(entry)["entities"]
        
            entities_cleaned  = canonicalize_entities([e["text"] for e in entities])

            final_chunks.append({

                # IDs
                "chunk_id": str(uuid.uuid4()),
                "parent_chunk_id": parent_chunk_id,

                # Source
                "source": srt_path,

                # Timestamps
                "start_time": entry["start_time"],
                "end_time": entry["end_time"],

                # Window timestamps
                "window_start": window_start,
                "window_end": window_end,

                # Speaker info
                "speaker": entry["speaker"],
                "all_speakers": speakers,

                # Retrieval text
                "text": entry["text"],
                "entities": entities_cleaned,

                # Parent conversational context
                "parent_context": parent_text,

                # Metadata
                "sequence_index": entry["index"],
                "chunk_type": "srt_semantic",

                # Ordering
                "child_index": child_idx
            })
    
    for chunk in final_chunks:
        if len(chunk) > 0:
            relationships = extract_relationships(
                chunk["text"],
                chunk["entities"])
            chunk["relationships"] = relationships      
    

    return final_chunks
