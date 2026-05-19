import fitz
import re
import uuid

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from src.utilities.entity_handlers.entity_extractor import extract_metadata
from src.utilities.entity_handlers.relationship_extractor_auto import extract_relationships
from src.utilities.entity_handlers.clean_entites import canonicalize_entities


# =========================================================
# PDF TEXT EXTRACTION
# =========================================================
def extract_pdf_text(pdf_path):

    doc = fitz.open(pdf_path)

    full_text = []

    for page in doc:

        text = page.get_text("text")

        full_text.append(text)

    return "\n".join(full_text)


# =========================================================
# CLEAN TEXT
# =========================================================
def clean_text(text):

    text = text.replace("\n", " ")

    text = re.sub(r"\s+", " ", text)

    return text.strip()


# =========================================================
# SENTENCE SPLITTING
# =========================================================
def split_into_sentences(text):

    """
    More stable sentence splitter.
    """

    sentences = re.split(
        r'(?<=[.!?])\s+',
        text
    )

    return [
        s.strip()
        for s in sentences
        if len(s.strip()) > 30
    ]


# =========================================================
# TOKEN COUNTER APPROX
# =========================================================
def approximate_token_count(text):

    """
    Rough approximation:
    1 token ~= 0.75 words
    """

    words = len(text.split())

    return int(words * 1.3)


# =========================================================
# WINDOW CREATION
# =========================================================
def create_windows(
    sentences,
    window_size=20,
    stride=10
):

    """
    Overlapping windows.

    Example:
    Window 1 -> sentences 0-20
    Window 2 -> sentences 10-30
    """

    windows = []

    for i in range(
        0,
        len(sentences),
        stride
    ):

        window_sentences = (
            sentences[i:i + window_size]
        )

        if not window_sentences:
            continue

        windows.append({

            "start_idx": i,

            "end_idx": i + len(window_sentences),

            "sentences": window_sentences,

            "text": " ".join(
                window_sentences
            )
        })

    return windows


# =========================================================
# IMPROVED SEMANTIC CHUNKER
# =========================================================
class SemanticChunker:

    def __init__(

        self,

        model_name="all-MiniLM-L6-v2",

        similarity_threshold=0.35,

        window_size=20,

        stride=10,

        min_tokens=400,

        max_tokens=1200
    ):

        self.model = SentenceTransformer(
            model_name
        )

        self.similarity_threshold = (
            similarity_threshold
        )

        self.window_size = window_size

        self.stride = stride

        self.min_tokens = min_tokens

        self.max_tokens = max_tokens

    # =====================================================
    # MAIN CHUNKING
    # =====================================================
    def chunk(self, sentences):

        windows = create_windows(

            sentences,

            window_size=self.window_size,

            stride=self.stride
        )

        if len(windows) <= 1:

            return [
                " ".join(sentences)
            ]

        window_texts = [
            w["text"]
            for w in windows
        ]

        embeddings = self.model.encode(
            window_texts
        )

        chunks = []

        current_chunk = []

        current_chunk.extend(
            windows[0]["sentences"]
        )

        # =================================================
        # WINDOW-LEVEL COMPARISON
        # =================================================
        for i in range(1, len(windows)):

            prev_emb = (
                embeddings[i - 1]
                .reshape(1, -1)
            )

            curr_emb = (
                embeddings[i]
                .reshape(1, -1)
            )

            similarity = cosine_similarity(
                prev_emb,
                curr_emb
            )[0][0]

            current_text = " ".join(
                current_chunk
            )

            current_tokens = (
                approximate_token_count(
                    current_text
                )
            )

            # ---------------------------------------------
            # Only split if:
            # 1. Large enough chunk
            # 2. Major semantic shift
            # ---------------------------------------------
            should_split = (

                similarity
                < self.similarity_threshold

                and

                current_tokens
                >= self.min_tokens
            )

            # ---------------------------------------------
            # Force split on huge chunks
            # ---------------------------------------------
            reached_max = (
                current_tokens
                >= self.max_tokens
            )

            if should_split or reached_max:

                chunks.append(
                    current_text
                )

                current_chunk = []

            # ---------------------------------------------
            # Add only NEW sentences
            # Prevent duplication from overlap
            # ---------------------------------------------
            new_sentences = (
                windows[i]["sentences"][
                    self.stride:
                ]
            )

            current_chunk.extend(
                new_sentences
            )

        # =================================================
        # FINAL CHUNK
        # =================================================
        final_text = " ".join(
            current_chunk
        )

        if final_text.strip():

            # Merge tiny final chunk
            if (
                approximate_token_count(
                    final_text
                )
                < self.min_tokens

                and

                len(chunks) > 0
            ):

                chunks[-1] += (
                    " " + final_text
                )

            else:

                chunks.append(
                    final_text
                )

        return chunks


# =========================================================
# MAIN PIPELINE
# =========================================================
def semantic_pdf_chunking(pdf_path):

    # -----------------------------------------------------
    # Extract COMPLETE document
    # -----------------------------------------------------
    full_text = extract_pdf_text(
        pdf_path
    )

    cleaned_text = clean_text(
        full_text
    )

    sentences = split_into_sentences(
        cleaned_text
    )

    if not sentences:
        return []

    # -----------------------------------------------------
    # Improved configuration
    # -----------------------------------------------------
    chunker = SemanticChunker(

        similarity_threshold=0.35,

        window_size=20,

        stride=10,

        min_tokens=400,

        max_tokens=1200
    )

    chunks = chunker.chunk(sentences)

    all_chunks = []

    for idx, chunk in enumerate(chunks):
        
        entities = extract_metadata(chunk)["entities"]
        
        entities_cleaned  = canonicalize_entities([e["text"] for e in entities])

        all_chunks.append({

            "chunk_id": str(uuid.uuid4()),

            "text": chunk,
            
            "entities": entities_cleaned,

            "source": pdf_path,

            "chunk_type": (
                "semantic_windowed_large"
            ),

            "token_count": (
                approximate_token_count(
                    chunk
                )
            ),

            "sentence_count": len(
                split_into_sentences(
                    chunk
                )
            )
        })
    
    for chunk in all_chunks:
        if len(chunk) > 0:
            relationships = extract_relationships(
                chunk["text"],
                chunk["entities"])
            chunk["relationships"] = relationships

    return all_chunks

