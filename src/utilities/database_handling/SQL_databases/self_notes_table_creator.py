import psycopg2


def create_self_notes_table():
    conn = psycopg2.connect(host="localhost",
                            database= "Pkms_db",
                            user="postgres",
                            password="1234",
                            port="5432")
    
    
    
    cur = conn.cursor()
    
    try:
        embedding_type = "DOUBLE PRECISION[]"

        try:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            embedding_type = "vector(768)"
        except Exception:
            # pgvector may be unavailable on this server; fallback keeps startup working.
            conn.rollback()

        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS notes (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                title TEXT NOT NULL,
                file_path TEXT UNIQUE NOT NULL,
                content TEXT NOT NULL,
                backlinks TEXT[],
                tags TEXT[],
                topics TEXT[],
                embedding {embedding_type},
                search_vector tsvector,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS notes_search_idx
            ON notes
            USING GIN(search_vector);
        """)

        cur.execute("""
            ALTER TABLE notes
            ADD COLUMN IF NOT EXISTS user_id VARCHAR(255);
        """)

        cur.execute("""
            UPDATE notes
            SET user_id = COALESCE(user_id, 'default')
            WHERE user_id IS NULL;
        """)

        cur.execute("""
            ALTER TABLE notes
            ALTER COLUMN user_id SET NOT NULL;
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_notes_user_id
            ON notes(user_id);
        """)
        
        conn.commit()
    except Exception as e:
        print("Error creating table:", e)
        conn.rollback()
    finally:
        cur.close()
        conn.close()