import psycopg2


def _get_connection():
	return psycopg2.connect(
		host="localhost",
		dbname="Pkms_db",
		user="postgres",
		password="1234",
		port=5432,
	)


def create_user_tables():
	conn = _get_connection()
	cur = conn.cursor()
	try:
		cur.execute(
			"""
			CREATE TABLE IF NOT EXISTS users (
				id SERIAL PRIMARY KEY,
				email VARCHAR(255) UNIQUE NOT NULL,
				password_hash TEXT NOT NULL,
				created_at TIMESTAMP DEFAULT NOW(),
				plan_type VARCHAR(50) DEFAULT 'free',
				token_usage BIGINT DEFAULT 0
			)
			"""
		)

		cur.execute(
			"""
			CREATE TABLE IF NOT EXISTS chat_threads (
				id SERIAL PRIMARY KEY,
				user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
				title VARCHAR(255) NOT NULL,
				created_at TIMESTAMP DEFAULT NOW()
			)
			"""
		)

		cur.execute(
			"""
			CREATE TABLE IF NOT EXISTS messages (
				id SERIAL PRIMARY KEY,
				thread_id INTEGER NOT NULL REFERENCES chat_threads(id) ON DELETE CASCADE,
				role VARCHAR(20) NOT NULL,
				content TEXT NOT NULL,
				token_count INTEGER DEFAULT 0,
				model VARCHAR(100) DEFAULT 'gpt-4o',
				created_at TIMESTAMP DEFAULT NOW()
			)
			"""
		)

		cur.execute(
			"""
			CREATE TABLE IF NOT EXISTS token_usage (
				id SERIAL PRIMARY KEY,
				user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
				thread_id INTEGER REFERENCES chat_threads(id) ON DELETE SET NULL,
				input_tokens INTEGER DEFAULT 0,
				output_tokens INTEGER DEFAULT 0,
				total_tokens INTEGER DEFAULT 0,
				model VARCHAR(100) NOT NULL,
				cost NUMERIC(12, 6) DEFAULT 0,
				timestamp TIMESTAMP DEFAULT NOW()
			)
			"""
		)

		cur.execute("CREATE INDEX IF NOT EXISTS idx_chat_threads_user_id ON chat_threads(user_id)")
		cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_thread_id ON messages(thread_id)")
		cur.execute("CREATE INDEX IF NOT EXISTS idx_token_usage_user_id ON token_usage(user_id)")

		conn.commit()
	finally:
		cur.close()
		conn.close()