
import re
import uuid
import numpy as np

from markdown_it import MarkdownIt
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from entity_handlers.entity_extractor_markdown import extract_markdown_entities
from entity_handlers.relationship_extractor_auto import extract_relationships
from entity_handlers.clean_entites import canonicalize_entities


# =========================================================
# LOAD MARKDOWN
# =========================================================
def load_markdown(md_path):

    with open(md_path, "r", encoding="utf-8") as f:
        return f.read()


# =========================================================
# EXTRACT WIKILINKS
# =========================================================
def extract_wikilinks(text):

    pattern = r"\[\[(.*?)\]\]"

    return re.findall(pattern, text)


# =========================================================
# EXTRACT TAGS
# =========================================================
def extract_tags(text):

    pattern = r"#(\w+)"

    return re.findall(pattern, text)


# =========================================================
# SPLIT INTO SENTENCES
# =========================================================
def split_sentences(text):

    sentences = re.split(r'(?<=[.!?])\s+', text)

    return [s.strip() for s in sentences if s.strip()]


# =========================================================
# SEMANTIC CHUNKING
# =========================================================
def semantic_chunk(
    sentences,
    model,
    similarity_threshold=0.65,
    max_sentences=6
):

    if len(sentences) <= 1:
        return [" ".join(sentences)]

    embeddings = model.encode(sentences)

    chunks = []

    current_chunk = [sentences[0]]

    for i in range(1, len(sentences)):

        prev_emb = embeddings[i - 1].reshape(1, -1)
        curr_emb = embeddings[i].reshape(1, -1)

        similarity = cosine_similarity(
            prev_emb,
            curr_emb
        )[0][0]

        if (
            similarity < similarity_threshold
            or len(current_chunk) >= max_sentences
        ):

            chunks.append(" ".join(current_chunk))

            current_chunk = [sentences[i]]

        else:
            current_chunk.append(sentences[i])

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


# =========================================================
# MARKDOWN SECTION PARSER
# =========================================================
def parse_markdown_sections(md_text):

    """
    Extracts sections using markdown headings.
    """

    lines = md_text.split("\n")

    sections = []

    current_heading = "ROOT"

    current_content = []

    for line in lines:

        heading_match = re.match(r"^(#{1,6})\s+(.*)", line)

        if heading_match:

            if current_content:

                sections.append({
                    "heading": current_heading,
                    "content": "\n".join(current_content)
                })

            current_heading = heading_match.group(2).strip()

            current_content = []

        else:
            current_content.append(line)

    if current_content:

        sections.append({
            "heading": current_heading,
            "content": "\n".join(current_content)
        })

    return sections


# =========================================================
# MAIN CHUNKER
# =========================================================
def chunk_markdown_note(
    md_path,
    embedding_model="all-MiniLM-L6-v2",
    similarity_threshold=0.65,
    max_sentences=6
):

    model = SentenceTransformer(embedding_model)

    md_text = load_markdown(md_path)

    sections = parse_markdown_sections(md_text)

    note_title = md_path.split("/")[-1].replace(".md", "")

    final_chunks = []

    for section_idx, section in enumerate(sections):

        heading = section["heading"]

        content = section["content"].strip()

        if not content:
            continue

        # -----------------------------------
        # Extract metadata
        # -----------------------------------
        wikilinks = extract_wikilinks(content)

        tags = extract_tags(content)

        # -----------------------------------
        # Semantic chunking
        # -----------------------------------
        sentences = split_sentences(content)

        semantic_chunks = semantic_chunk(
            sentences,
            model=model,
            similarity_threshold=similarity_threshold,
            max_sentences=max_sentences
        )

        # -----------------------------------
        # Parent section text
        # -----------------------------------
        parent_text = content

        parent_id = f"{note_title}_section_{section_idx}"

        # -----------------------------------
        # Create child chunks
        # -----------------------------------
        for child_idx, chunk_text in enumerate(semantic_chunks):

            chunk_id = str(uuid.uuid4())
            
            entities = extract_markdown_entities(chunk)["entities"]
        
            entities_cleaned  = canonicalize_entities(entities)

            final_chunks.append({

                # IDs
                "chunk_id": chunk_id,
                "parent_chunk_id": parent_id,

                # Source info
                "source": md_path,
                "note_title": note_title,

                # Hierarchy
                "heading": heading,

                # Text
                "text": chunk_text,
                "entities": entities_cleaned,
                "parent_text": parent_text,

                # Graph metadata
                "wikilinks": wikilinks,
                "tags": tags,

                # Chunk info
                "chunk_type": "atomic_semantic",

                # Useful later
                "child_index": child_idx
            })
            
    for chunk in final_chunks:
        if len(chunk) > 0:
            relationships = extract_relationships(
                chunk["text"],
                [i for i in chunk["entities"]])
            chunk["relationships"] = relationships
        

    return final_chunks
