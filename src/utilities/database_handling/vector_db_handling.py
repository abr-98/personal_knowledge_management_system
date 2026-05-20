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
import re

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
        # Base collection (fallback when no domain is available)
        # -----------------------------------------
        self.default_collection_name = collection_name
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

    def _normalize_collection_name(self, domain):

        if not domain:
            return self.default_collection_name

        normalized = re.sub(
            r"[^a-zA-Z0-9_-]+",
            "_",
            str(domain).strip().lower()
        ).strip("_")

        if not normalized:
            return self.default_collection_name

        return f"{self.default_collection_name}_{normalized}"

    def _get_collection_for_item(self, item):

        domain = item.get("domain")

        if not domain:
            meta_details = item.get("meta_details", {})
            if isinstance(meta_details, dict):
                domain = meta_details.get("domain")

        collection_name = self._normalize_collection_name(domain)

        return self.client.get_or_create_collection(
            name=collection_name
        )

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
        metadata["domain"] = str(item.get("domain", ""))

        collection = self._get_collection_for_item(item)

        collection.add(

            ids=[chunk_id],

            embeddings=[embedding],

            documents=[text],

            metadatas=[metadata]
        )

    # =====================================================
    # ADD MULTIPLE ITEMS
    # =====================================================
    def add_items(self, items):

        grouped_payload = {}

        for item in items:

            text = item.get(
                "text",
                ""
            )

            if not text.strip():
                continue

            collection = self._get_collection_for_item(item)
            collection_name = collection.name

            if collection_name not in grouped_payload:
                grouped_payload[collection_name] = {
                    "collection": collection,
                    "ids": [],
                    "embeddings": [],
                    "documents": [],
                    "metadatas": []
                }

            chunk_id = str(
                item.get(
                    "chunk_id"
                )
            )

            metadata = self.prepare_metadata(
                item
            )
            metadata["domain"] = str(item.get("domain", ""))

            grouped_payload[collection_name]["ids"].append(chunk_id)
            grouped_payload[collection_name]["documents"].append(text)
            grouped_payload[collection_name]["embeddings"].append(
                self.create_embedding(
                    text
                )
            )
            grouped_payload[collection_name]["metadatas"].append(metadata)

        for payload in grouped_payload.values():
            if len(payload["ids"]) == 0:
                continue

            payload["collection"].add(
                ids=payload["ids"],
                embeddings=payload["embeddings"],
                documents=payload["documents"],
                metadatas=payload["metadatas"]
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
