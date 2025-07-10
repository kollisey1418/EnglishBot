import aiosqlite

DB_NAME = "englishbot.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            level TEXT
        )
        """)
        await db.commit()
        print("✅ Database initialized (englishbot.db)")


async def set_user_level(user_id, level):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        INSERT INTO users (user_id, level) VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET level=excluded.level
        """, (user_id, level))
        await db.commit()
        print(f"✅ Saved user {user_id} with level {level}")

async def get_user_level(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT level FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                print(f"🔎 Fetched level for user {user_id}: {result[0] if result else 'None'}")
                return row[0]
            return None
