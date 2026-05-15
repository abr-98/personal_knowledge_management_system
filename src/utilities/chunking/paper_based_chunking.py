import re
import fitz
import uuid

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from entity_handlers.entity_extractor import extract_metadata
from entity_handlers.relationship_extractor_auto import extract_relationships
from entity_handlers.clean_entites import canonicalize_entities


# =========================================================
# IMPROVED PDF EXTRACTION
# =========================================================
def extract_pdf_text(pdf_path):

    """
    Better PDF extraction for:
    - research papers
    - arXiv PDFs
    - IEEE papers
    - two-column layouts

    Uses:
    - block extraction
    - reading-order sorting
    - footer/header cleanup
    """

    doc = fitz.open(pdf_path)

    full_text = []

    for page_num, page in enumerate(doc):

        # -------------------------------------------------
        # Extract text blocks
        # -------------------------------------------------
        blocks = page.get_text("blocks")

        # -------------------------------------------------
        # Sort blocks:
        # top-to-bottom
        # left-to-right
        # -------------------------------------------------
        blocks = sorted(
            blocks,
            key=lambda b: (b[1], b[0])
        )

        page_text = []

        for block in blocks:

            text = block[4].strip()

            # ---------------------------------------------
            # Skip tiny noisy blocks
            # ---------------------------------------------
            if len(text) < 20:
                continue

            # ---------------------------------------------
            # Skip page numbers
            # ---------------------------------------------
            if re.fullmatch(r"\d+", text):
                continue

            # ---------------------------------------------
            # Skip conference footer/header junk
            # ---------------------------------------------
            junk_patterns = [

                r"arXiv",

                r"Conference",

                r"Proceedings",

                r"NeurIPS",

                r"NIPS",

                r"ICML",

                r"ICLR",

                r"ACL",

                r"CVPR",

                r"ECCV",

                r"copyright",

                r"preprint",

                r"submitted"
            ]

            is_junk = any(

                re.search(
                    pattern,
                    text,
                    re.IGNORECASE
                )

                for pattern in junk_patterns
            )

            if is_junk:
                continue

            # ---------------------------------------------
            # Remove excessive whitespace
            # ---------------------------------------------
            text = re.sub(
                r"\s+",
                " ",
                text
            )

            page_text.append(text)

        cleaned_page = "\n".join(page_text)

        full_text.append(cleaned_page)

    return "\n".join(full_text)


# =========================================================
# CLEAN TEXT
# =========================================================
def clean_text(text):

    text = text.replace("\n", " ")

    text = re.sub(r"\s+", " ", text)

    return text.strip()


# =========================================================
# DETECT PAPER SECTIONS
# =========================================================
def detect_sections(text):

    section_patterns = [

        r"\bAbstract\b",

        r"\bIntroduction\b",

        r"\bBackground\b",

        r"\bRelated Work\b",

        r"\bMethodology\b",

        r"\bMethods\b",

        r"\bExperiments\b",

        r"\bResults\b",

        r"\bDiscussion\b",

        r"\bConclusion\b",

        r"\bReferences\b"
    ]

    pattern = (
        "(" +
        "|".join(section_patterns)
        + ")"
    )

    splits = re.split(
        pattern,
        text,
        flags=re.IGNORECASE
    )

    sections = []

    current_section = "Unknown"

    for part in splits:

        part = part.strip()

        if not part:
            continue

        if re.fullmatch(
            pattern,
            part,
            flags=re.IGNORECASE
        ):

            current_section = part

        else:

            sections.append({

                "section": current_section,

                "content": part
            })

    return sections


# =========================================================
# SENTENCE SPLITTING
# =========================================================
def split_sentences(text):

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
# TOKEN ESTIMATION
# =========================================================
def approximate_token_count(text):

    words = len(text.split())

    return int(words * 1.3)


# =========================================================
# CREATE OVERLAPPING WINDOWS
# =========================================================
def create_windows(

    sentences,

    window_size=20,

    stride=10
):

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

            "end_idx": (
                i + len(window_sentences)
            ),

            "sentences": (
                window_sentences
            ),

            "text": " ".join(
                window_sentences
            )
        })

    return windows


# =========================================================
# SEMANTIC CHUNKER
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

        # Keep track of already added sentences
        added_sentence_ids = set(
            range(
                0,
                len(windows[0]["sentences"])
            )
        )

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

            # -------------------------------------
            # Split ONLY on major semantic shifts
            # -------------------------------------
            should_split = (

                similarity
                < self.similarity_threshold

                and

                current_tokens
                >= self.min_tokens
            )

            if should_split:

                chunks.append(
                    current_text
                )

                current_chunk = []

                added_sentence_ids = set()

            # -------------------------------------
            # Add only unseen sentences
            # -------------------------------------
            window_start = windows[i]["start_idx"]

            for idx, sentence in enumerate(
                windows[i]["sentences"]
            ):

                global_idx = (
                    window_start + idx
                )

                if (
                    global_idx
                    not in added_sentence_ids
                ):

                    current_chunk.append(
                        sentence
                    )

                    added_sentence_ids.add(
                        global_idx
                    )

        # -----------------------------------------
        # Final chunk
        # -----------------------------------------
        final_text = " ".join(
            current_chunk
        )

        if final_text.strip():

            if (
                approximate_token_count(
                    final_text
                )< self.min_tokens

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
# MAIN FUNCTION
# =========================================================
def chunk_research_paper(

    pdf_path,

    embedding_model="all-MiniLM-L6-v2"
):

    # -----------------------------------------------------
    # Better PDF extraction
    # -----------------------------------------------------
    full_text = extract_pdf_text(
        pdf_path
    )

    cleaned_text = clean_text(
        full_text
    )

    sections = detect_sections(
        cleaned_text
    )

    chunker = SemanticChunker(

        model_name=embedding_model,

        similarity_threshold=0.35,

        window_size=20,

        stride=10,

        min_tokens=400,

        max_tokens=1200
    )

    final_chunks = []

    parent_id = 0

    # =====================================================
    # CHUNK SECTION BY SECTION
    # =====================================================
    for section_data in sections:

        section_name = (
            section_data["section"]
        )

        # Skip references
        if (
            section_name.lower()
            == "references"
        ):

            continue

        section_text = (
            section_data["content"]
        )

        sentences = split_sentences(
            section_text
        )

        if not sentences:
            continue

        semantic_chunks = chunker.chunk(
            sentences
        )

        parent_chunk_id = (
            f"section_{parent_id}"
        )

        for idx, chunk_text in enumerate(
            semantic_chunks
        ):
            
            entities = extract_metadata(chunk_text)["entities"]
        
            entities_cleaned  = canonicalize_entities([e["text"] for e in entities])

            final_chunks.append({

                "chunk_id": str(
                    uuid.uuid4()
                ),

                "parent_chunk_id": (
                    parent_chunk_id
                ),

                "section": section_name,

                "text": chunk_text,
                
                "entities": entities_cleaned,

                "source": pdf_path,

                "token_count": (
                    approximate_token_count(
                        chunk_text
                    )
                ),

                "sentence_count": len(
                    split_sentences(
                        chunk_text
                    )
                ),

                "chunk_type": (
                    "semantic_windowed_large"
                )
            })

        parent_id += 1

    for chunk in final_chunks:
        if len(chunk) > 0:
            relationships = extract_relationships(
                chunk["text"],
                chunk["entities"])
            chunk["relationships"] = relationships
        
    return final_chunks
