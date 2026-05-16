"""
Neo4j Aura Semantic Graph Store
--------------------------------
Architecture:

(Domain)
    ↓
(Topic)
    ↓
(Entity)

Features:
- Domain nodes
- Topic nodes
- Entity nodes
- Entity embeddings
- Entity descriptions
- Subdomain metadata
- Relationship edges
- Merge-ready entity structure

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

        uri=None,

        username=None,

        password=None
    ):

        with open(
            "neo4j_settings.json",
            "r"
        ) as f:

            settings = json.load(f)

        self.driver = (
            GraphDatabase.driver(

                settings["NEO4J_URI"],

                auth=(

                    settings[
                        "NEO4J_USERNAME"
                    ],

                    settings[
                        "NEO4J_PASSWORD"
                    ]
                )
            )
        )

    # =====================================================
    # CLOSE
    # =====================================================
    def close(self):

        self.driver.close()

    # =====================================================
    # ADD DOMAIN
    # =====================================================
    def add_domain(

        self,

        tx,

        domain
    ):

        query = """
        MERGE (d:Domain {
            name: $domain
        })
        """

        tx.run(

            query,

            domain=domain
        )

    # =====================================================
    # ADD TOPIC
    # =====================================================
    def add_topic(

        self,

        tx,

        topic,

        domain
    ):

        query = """
        MERGE (t:Topic {
            name: $topic
        })

        MERGE (d:Domain {
            name: $domain
        })

        MERGE (t)-[:IN_DOMAIN]->(d)
        """

        tx.run(

            query,

            topic=topic,

            domain=domain
        )

    # =====================================================
    # ADD ENTITY
    # =====================================================
    def add_entity(

        self,

        tx,

        entity_name,

        topic,

        domain,

        subdomain,

        description,

        text,

        embedding,

        source_file
    ):

        query = """
        MERGE (e:Entity {
            name: $entity_name,
            subdomain: $subdomain
        })

        SET e.description = $description,
            e.text = $text,
            e.embedding = $embedding,
            e.source = $source_file

        MERGE (t:Topic {
            name: $topic
        })

        MERGE (e)-[:HAS_TOPIC]->(t)
        """

        tx.run(

            query,

            entity_name=entity_name,

            topic=topic,

            domain=domain,

            subdomain=subdomain,

            description=description,

            text=text,

            embedding=embedding,

            source_file=source_file
        )

    # =====================================================
    # ADD RELATIONSHIP
    # =====================================================
    def add_relationship(

        self,

        tx,

        source,

        target,

        relation,

        score=None
    ):

        query = f"""
        MERGE (a:Entity {{
            name: $source
        }})

        MERGE (b:Entity {{
            name: $target
        }})

        MERGE (a)-[r:{relation}]->(b)

        SET r.score = $score
        """

        tx.run(

            query,

            source=source,

            target=target,

            score=score
        )

        # =====================================================
    # ADD DOCUMENT
    # =====================================================
    def add_document(
        self,
        item
    ):

        # =================================================
        # META DETAILS
        # =================================================
        meta_details = item.get(
            "meta_details",
            {}
        )

        domain = meta_details.get(
            "domain",
            "Unknown"
        )

        subdomain = meta_details.get(
            "subdomain",
            "Unknown"
        )

        topics = meta_details.get(
            "topics",
            []
        )

        summary = meta_details.get(
            "summary",
            ""
        )

        # =================================================
        # DOCUMENT DETAILS
        # =================================================
        text = item.get(
            "text",
            ""
        )

        source_file = item.get(
            "source",
            ""
        )

        cluster_id = str(
            item.get(
                "cluster_id",
                ""
            )
        )

        entities = item.get(
            "entities",
            []
        )

        relationships = item.get(
            "relationships",
            []
        )

        # =================================================
        # SESSION
        # =================================================
        with self.driver.session() as session:

            # =============================================
            # DOMAIN
            # =============================================
            session.execute_write(

                self.add_domain,

                domain
            )

            # =============================================
            # TOPICS
            # =============================================
            for topic in topics:

                session.execute_write(

                    self.add_topic,

                    topic,

                    domain
                )

            # =============================================
            # ENTITIES
            # =============================================
            for entity in entities:

                # -----------------------------------------
                # Entity name
                # -----------------------------------------
                entity_name = str(
                    entity
                ).strip()

                if not entity_name:
                    continue

                # -----------------------------------------
                # Entity description
                # -----------------------------------------
                description = f"""
                Entity:
                {entity_name}

                Summary:
                {summary}

                Topics:
                {", ".join(topics)}

                Context:
                {text[:3000]}
                """

                # -----------------------------------------
                # Embedding placeholder
                # -----------------------------------------
                embedding = []

                # -----------------------------------------
                # Topic routing
                # -----------------------------------------
                topic = (

                    topics[0]

                    if topics

                    else "General"
                )

                # -----------------------------------------
                # Add entity
                # -----------------------------------------
                session.execute_write(

                    self.add_entity,

                    entity_name,

                    topic,

                    domain,

                    subdomain,

                    description,

                    text,

                    embedding,

                    source_file
                )

            # =============================================
            # RELATIONSHIPS
            # =============================================
            for rel in relationships:

                source = rel.get(
                    "source",
                    ""
                )

                target = rel.get(
                    "target",
                    ""
                )

                relation = rel.get(
                    "relation",
                    "RELATED_TO"
                )

                score = rel.get(
                    "score",
                    rel.get(
                        "weight",
                        1
                    )
                )

                if (
                    not source
                    or
                    not target
                ):
                    continue

                # -----------------------------------------
                # Neo4j-safe relation
                # -----------------------------------------
                relation = (

                    relation.upper()

                    .replace(" ", "_")

                    .replace("-", "_")
                )

                # -----------------------------------------
                # Add relationship
                # -----------------------------------------
                session.execute_write(

                    self.add_relationship,

                    source,

                    target,

                    relation,

                    score
                )

    # =====================================================
    # ADD MULTIPLE DOCUMENTS
    # =====================================================
    def add_documents(
        self,
        items
    ):

        for item in items:

            self.add_document(item)

    # =====================================================
    # QUERY
    # =====================================================
    def query(
        self,
        cypher_query
    ):

        with self.driver.session() as session:

            result = session.run(
                cypher_query
            )

            return [

                record.data()

                for record in result
                
            ]