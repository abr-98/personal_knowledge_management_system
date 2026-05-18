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
            CREATE TABLE IF NOT EXISTS workitems (
                    id SERIAL PRIMARY KEY,

                    user_id VARCHAR(255) NOT NULL,

                    title TEXT NOT NULL,

                    description TEXT,

                    status VARCHAR(50)
                        CHECK (
                            status IN (
                                'pending',
                                'in_progress',
                                'completed',
                                'blocked',
                                'cancelled'
                            )
                        ),

                    priority VARCHAR(50)
                        CHECK (
                            priority IN (
                                'low',
                                'medium',
                                'high',
                                'critical'
                            )
                        ),

                    related_notes TEXT[],

                    tags TEXT[],

                    topics TEXT[],

                    due_date TIMESTAMPTZ,

                    created_at TIMESTAMPTZ DEFAULT NOW(),

                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS timelines (
                id SERIAL PRIMARY KEY,

                user_id VARCHAR(255),

                event_type VARCHAR(100),

                title TEXT,

                description TEXT,

                related_notes TEXT[],

                related_workitems INT[],
                
                tags TEXT[],

                topics TEXT[],

                timestamp TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        
        conn.commit()
        
        
        conn.commit()
    except Exception as e:
        print("Error creating table:", e)
        conn.rollback()
    finally:
        cur.close()
        conn.close()