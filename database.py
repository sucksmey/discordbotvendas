# database.py
import asyncpg
import datetime
import config

pool = None

async def init_db():
    global pool
    if not config.DATABASE_URL:
        raise Exception("DATABASE_URL não foi encontrada.")
    pool = await asyncpg.create_pool(dsn=config.DATABASE_URL)
    async with pool.acquire() as c:
        await c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                active_thread_id BIGINT DEFAULT NULL
            );
        """)
        await c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS active_thread_id BIGINT DEFAULT NULL;")
        await c.execute("""
            CREATE TABLE IF NOT EXISTS purchases (
                purchase_id SERIAL PRIMARY KEY, user_id BIGINT, product_name TEXT,
                price_brl NUMERIC(10, 2), purchase_date TIMESTAMP WITH TIME ZONE,
                attendant_id BIGINT, deliverer_id BIGINT
            );""")

async def get_active_thread(user_id: int):
    async with pool.acquire() as c:
        await c.execute("INSERT INTO users (user_id) VALUES ($1) ON CONFLICT (user_id) DO NOTHING;", user_id)
        return await c.fetchval("SELECT active_thread_id FROM users WHERE user_id = $1;", user_id)

async def set_active_thread(user_id: int, thread_id: int | None):
    async with pool.acquire() as c:
        await c.execute("INSERT INTO users (user_id) VALUES ($1) ON CONFLICT (user_id) DO NOTHING;", user_id)
        await c.execute("UPDATE users SET active_thread_id = $1 WHERE user_id = $2;", thread_id, user_id)

async def add_purchase(user_id: int, product_name: str, price: float, attendant_id: int, deliverer_id: int | None):
    async with pool.acquire() as c:
        return await c.fetchval(
            "INSERT INTO purchases (user_id, product_name, price_brl, purchase_date, attendant_id, deliverer_id) VALUES ($1, $2, $3, $4, $5, $6) RETURNING purchase_id;",
            user_id, product_name, price, datetime.datetime.now(datetime.timezone.utc), attendant_id, deliverer_id
        )

async def get_user_spend_and_count(user_id: int):
    async with pool.acquire() as c:
        data = await c.fetchrow("SELECT SUM(price_brl) as total, COUNT(purchase_id) as count FROM purchases WHERE user_id = $1;", user_id)
        total = data['total'] if data and data['total'] is not None else 0
        count = data['count'] if data and data['count'] is not None else 0
        return float(total), count

async def get_purchase_history(user_id: int):
    async with pool.acquire() as c:
        return await c.fetch("SELECT product_name, price_brl, purchase_date FROM purchases WHERE user_id = $1 ORDER BY purchase_date DESC;", user_id)

# --- NOVAS FUNÇÕES ---
async def get_pending_purchase(user_id: int):
    """Busca a última compra pendente de um usuário (sem entregador)."""
    async with pool.acquire() as c:
        return await c.fetchrow("SELECT * FROM purchases WHERE user_id = $1 AND deliverer_id IS NULL ORDER BY purchase_date DESC LIMIT 1;", user_id)

async def update_purchase_delivery(purchase_id: int, deliverer_id: int):
    """Atualiza a compra com o ID do entregador."""
    async with pool.acquire() as c:
        await c.execute("UPDATE purchases SET deliverer_id = $1 WHERE purchase_id = $2;", deliverer_id, purchase_id)
