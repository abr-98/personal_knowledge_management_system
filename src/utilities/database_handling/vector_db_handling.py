"""
Persistent ChromaDB Vector Store
--------------------------------
Features:
- Persistent client
- Automatically reuses DB if folder exists
- Stores:
    - embeddings from actual text
    - entities
    - tags
    - source
    - chunk_id

Install:
pip install chromadb sentence-transformers
"""

import chromadb

from sentence_transformers import (
    SentenceTransformer
)


# =========================================================
# VECTOR STORE
# =========================================================
class VectorStore:

    def __init__(

        self,

        persist_directory="./vector_db",

        collection_name="pkms",

        embedding_model=(
            "all-MiniLM-L6-v2"
        )
    ):

        # -----------------------------------------
        # Persistent client
        # -----------------------------------------
        self.client = (
            chromadb.PersistentClient(
                path=persist_directory
            )
        )

        # -----------------------------------------
        # Create/load collection
        # -----------------------------------------
        self.collection = (
            self.client.get_or_create_collection(
                name=collection_name
            )
        )

        # -----------------------------------------
        # Embedding model
        # -----------------------------------------
        self.model = SentenceTransformer(
            embedding_model
        )

    # =====================================================
    # CREATE EMBEDDING
    # =====================================================
    def create_embedding(self, text):

        embedding = self.model.encode(
            text
        )

        return embedding.tolist()

    # =====================================================
    # PREPARE METADATA
    # =====================================================
    def prepare_metadata(self, item):

    # ---------------------------------------------
    # Normalize entities
    # ---------------------------------------------
        entities = []

        for entity in item.get(
            "entities",
            []
        ):

            # Dict entity
            if isinstance(entity, dict):

                entity_text = entity.get(
                    "text",
                    ""
                )

                if entity_text:

                    entities.append(
                        str(entity_text)
                    )

            # String entity
            else:

                entities.append(
                    str(entity)
                )

        # ---------------------------------------------
        # Normalize tags
        # ---------------------------------------------
        tags = [

            str(tag)

            for tag in item.get(
                "tags",
                []
            )
        ]

        # ---------------------------------------------
        # Metadata
        # ---------------------------------------------
        metadata = {

            "chunk_id": str(
                item.get(
                    "chunk_id",
                    ""
                )
            ),

            "source": str(
                item.get(
                    "source",
                    ""
                )
            ),

            "text": str(
                item.get(
                    "text",
                    ""
                )
            ),

            "entities": ", ".join(
                entities
            ),

            "tags": ", ".join(
                tags
            )
        }

        return metadata

    # =====================================================
    # ADD SINGLE ITEM
    # =====================================================
    def add_item(self, item):

        text = item.get(
            "text",
            ""
        )

        if not text.strip():
            return

        chunk_id = str(
            item.get(
                "chunk_id"
            )
        )

        embedding = (
            self.create_embedding(
                text
            )
        )

        metadata = (
            self.prepare_metadata(
                item
            )
        )

        self.collection.add(

            ids=[chunk_id],

            embeddings=[embedding],

            documents=[text],

            metadatas=[metadata]
        )

    # =====================================================
    # ADD MULTIPLE ITEMS
    # =====================================================
    def add_items(self, items):

        ids = []

        embeddings = []

        documents = []

        metadatas = []

        for item in items:

            text = item.get(
                "text",
                ""
            )

            if not text.strip():
                continue

            chunk_id = str(
                item.get(
                    "chunk_id"
                )
            )

            ids.append(chunk_id)

            documents.append(text)

            embeddings.append(

                self.create_embedding(
                    text
                )
            )

            metadatas.append(

                self.prepare_metadata(
                    item
                )
            )

        if len(ids) == 0:
            return

        self.collection.add(

            ids=ids,

            embeddings=embeddings,

            documents=documents,

            metadatas=metadatas
        )

    # =====================================================
    # SEARCH
    # =====================================================
    def search(

        self,

        query,

        top_k=5
    ):

        query_embedding = (
            self.create_embedding(
                query
            )
        )

        results = self.collection.query(

            query_embeddings=[
                query_embedding
            ],

            n_results=top_k
        )

        return results

    # =====================================================
    # COUNT
    # =====================================================
    def count(self):

        return self.collection.count()
