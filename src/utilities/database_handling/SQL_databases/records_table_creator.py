import psycopg2

def create_records_table():
    conn = psycopg2.connect(host="localhost",
                            database= "Pkms_db",
                            user="postgres",
                            password="1234",
                            port="5432")
    
    
    
    cur = conn.cursor()
    
    try:
        cur.execute("""
                    CREATE TABLE IF NOT EXISTS records (
                            id SERIAL PRIMARY KEY,
                            user_id VARCHAR(255) NOT NULL,
                            link_or_path TEXT NOT NULL,
                            created_at TIMESTAMPTZ DEFAULT NOW(),
                            source VARCHAR(255),
                            tags TEXT[],
                            domain VARCHAR(255),
                            topics TEXT[]
                        )
                    """)
        conn.commit()
        
        
        conn.commit()
    except Exception as e:
        print("Error creating table:", e)
        conn.rollback()
    finally:
        cur.close()
        conn.close()