import psycopg2

def create_self_notes_table():
    conn = psycopg2.connect(host="localhost",
                            database= "Pkms_db",
                            user="postgres",
                            password="1234",
                            port="5432")
    
    
    
    cur = conn.cursor()
    
    try:
        cur.execute("""
            CREATE EXTENSION IF NOT EXISTS vector;

            CREATE TABLE IF NOT EXISTS notes (
                id SERIAL PRIMARY KEY,


                title TEXT NOT NULL,

                file_path TEXT UNIQUE NOT NULL,

                content TEXT NOT NULL,

                backlinks TEXT[],

                tags TEXT[],

                topics TEXT[],

                embedding vector(768),

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
        
        conn.commit()
        
        
        conn.commit()
    except Exception as e:
        print("Error creating table:", e)
        conn.rollback()
    finally:
        cur.close()
        conn.close()