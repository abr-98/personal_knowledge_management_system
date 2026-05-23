import re
import spacy

for _model_name in ("en_core_web_md", "en_core_web_sm"):
    try:
        nlp = spacy.load(_model_name)
        break
    except OSError:
        continue
else:
    nlp = spacy.blank("en")


# =========================================================
# CLEAN
# =========================================================
def clean_text(text):

    text = re.sub(r"\s+", " ", text)

    return text.strip()


# =========================================================
# HEADINGS
# =========================================================
def extract_headings(markdown):

    headings = re.findall(

        r"^#+\s+(.*)",

        markdown,

        re.MULTILINE
    )

    return headings


# =========================================================
# BOLD TEXT
# =========================================================
def extract_bold(markdown):

    return re.findall(

        r"\*\*(.*?)\*\*",

        markdown
    )


# =========================================================
# INLINE CODE
# =========================================================
def extract_inline_code(markdown):

    return re.findall(

        r"`([^`]+)`",

        markdown
    )


# =========================================================
# NOUN CHUNKS
# =========================================================
def extract_noun_chunks(text):

    doc = nlp(text)

    chunks = []

    for chunk in doc.noun_chunks:

        text = chunk.text.strip()

        if len(text) < 3:
            continue

        chunks.append(text)

    return chunks


# =========================================================
# FILTER
# =========================================================
def filter_entities(entities):

    cleaned = []

    for entity in entities:

        entity = entity.strip()

        # Remove numbers
        if re.fullmatch(
            r"\d+",
            entity
        ):

            continue

        # Remove tiny entities
        if len(entity) < 3:
            continue

        cleaned.append(entity)

    return sorted(list(set(cleaned)))


# =========================================================
# MAIN EXTRACTOR
# =========================================================
def extract_markdown_entities(markdown):

    markdown = clean_text(markdown)

    headings = extract_headings(
        markdown
    )

    bold_text = extract_bold(
        markdown
    )

    inline_code = extract_inline_code(
        markdown
    )

    noun_chunks = extract_noun_chunks(
        markdown
    )

    all_entities = (

        headings

        +

        bold_text

        +

        inline_code

        +

        noun_chunks
    )

    entities = filter_entities(
        all_entities
    )

    tags = [

        "#" + e.lower().replace(" ", "_")

        for e in entities
    ]

    return {

        "entities": entities,

        "tags": tags
    }
