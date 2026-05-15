"""
Neo4j Aura Graph Store
----------------------
Features:
- Adds entities as nodes
- Adds relationships as edges
- Stores originating chunk text
- Stores source + chunk_id on nodes
- Uses MERGE to avoid duplicates

Install:
pip install neo4j
"""

from neo4j import GraphDatabase
import json


# =========================================================
# GRAPH STORE
# =========================================================
class GraphStore:

    def __init__(

        self,

        uri,

        username,

        password
    ):
        
        with open("neo4j_settings.json", "r") as f:
            settings = json.load(f)

        self.driver = (
            GraphDatabase.driver(

                settings["NEO4J_URI"],

                auth=(
                    settings["NEO4J_USERNAME"],
                    settings["NEO4J_PASSWORD"]
                )
            )
        )

    # =====================================================
    # CLOSE
    # =====================================================
    def close(self):

        self.driver.close()

    # =====================================================
    # ADD ENTITY NODE
    # =====================================================
    def add_entity(

        self,

        tx,

        entity_name,

        text,

        source_file,

        chunk_id
    ):

        query = """
        MERGE (e:Entity {
            name: $name
        })

        SET e.text = $text,
            e.source = $source_file,
            e.chunk_id = $chunk_id
        """

        tx.run(

            query,

            name=entity_name,

            text=text,

            source_file=source_file,

            chunk_id=chunk_id
        )

    # =====================================================
    # ADD RELATIONSHIP
    # =====================================================
    def add_relationship(

        self,

        tx,

        source,

        relation,

        target,

        chunk_id,

        source_file,

        text
    ):

        query = f"""
        MERGE (a:Entity {{
            name: $source
        }})

        MERGE (b:Entity {{
            name: $target
        }})

        MERGE (a)-[r:{relation}]->(b)

        SET r.chunk_id = $chunk_id,
            r.source = $source_file,
            r.text = $text
        """

        tx.run(

            query,

            source=source,

            target=target,

            chunk_id=chunk_id,

            source_file=source_file,

            text=text
        )

    # =====================================================
    # ADD DOCUMENT
    # =====================================================
    def add_document(self, item):

        entities = item.get(
            "entities",
            []
        )

        relationships = item.get(
            "relationships",
            []
        )

        chunk_id = item.get(
            "chunk_id"
        )

        source_file = item.get(
            "source"
        )

        text = item.get(
            "text"
        )

        with self.driver.session() as session:

            # -----------------------------------------
            # Add entity nodes
            # -----------------------------------------
            for entity in entities:

                # Dict entity
                if isinstance(entity, dict):

                    entity_name = entity.get(
                        "text",
                        ""
                    )

                # String entity
                else:

                    entity_name = entity

                if not entity_name:
                    continue

                session.write_transaction(

                    self.add_entity,

                    entity_name,

                    text,

                    source_file,

                    chunk_id
                )

            # -----------------------------------------
            # Add relationships
            # -----------------------------------------
            for rel in relationships:

                # Dict relationship
                if isinstance(rel, dict):

                    source = rel.get(
                        "source",
                        ""
                    )

                    relation = rel.get(
                        "relation",
                        "RELATED_TO"
                    )

                    target = rel.get(
                        "target",
                        ""
                    )

                # Tuple relationship
                elif (
                    isinstance(
                        rel,
                        (list, tuple)
                    )
                    and
                    len(rel) == 3
                ):

                    source = rel[0]

                    relation = rel[1]

                    target = rel[2]

                else:

                    continue

                if (
                    not source
                    or
                    not target
                ):

                    continue

                # Neo4j relationship format
                relation = (
                    relation.upper()
                    .replace(" ", "_")
                )

                session.write_transaction(

                    self.add_relationship,

                    source,

                    relation,

                    target,

                    chunk_id,

                    source_file,

                    text
                )

    # =====================================================
    # ADD MULTIPLE DOCUMENTS
    # =====================================================
    def add_documents(self, items):

        for item in items:

            self.add_document(item)

    # =====================================================
    # CYPHER QUERY
    # =====================================================
    def query(self, cypher_query):

        with self.driver.session() as session:

            result = session.run(
                cypher_query
            )

            return [

                record.data()

                for record in result
            ]


# =========================================================
# EXAMPLE
# =========================================================
if __name__ == "__main__":

    URI = (
        "neo4j+s://f1d9637d.databases.neo4j.io"
    )

    USERNAME = "neo4j"

    PASSWORD = "YOUR_PASSWORD"

    graph_store = GraphStore(

        uri=URI,

        username=USERNAME,

        password=PASSWORD
    )

    item = {

        "chunk_id": "chunk_001",

        "source": "notes.md",

        "text": """
        Transformers use self-attention
        mechanisms.
        """,

        "entities": [

            "Transformers",

            "Self-Attention",

            "PyTorch"
        ],

        "relationships": [

            {
                "source": "Transformers",

                "relation": "USES",

                "target": "Self-Attention"
            },

            (
                "PyTorch",
                "TRAINS",
                "Transformers"
            )
        ]
    }

    # ---------------------------------------------
    # Add to graph
    # ---------------------------------------------
    graph_store.add_document(item)

    # ---------------------------------------------
    # Query
    # ---------------------------------------------
    results = graph_store.query("""

    MATCH (e:Entity)

    RETURN e

    LIMIT 5

    """)

    print(results)

    graph_store.close()