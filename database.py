# database.py
import asyncpg
import datetime
import config

pool = None

async def init_db():
    """Inicializa a pool de conexões e cria as tabelas se não existirem."""
    global pool
    if not config.DATABASE_URL:
        raise Exception("DATABASE_URL não foi encontrada nas variáveis de ambiente.")
    
    pool = await asyncpg.create_pool(dsn=config.DATABASE_URL)
    async with pool.acquire() as connection:
        await connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                purchase_count INTEGER DEFAULT 0,
                is_vip BOOLEAN DEFAULT FALSE,
                vip_purchases_this_month INTEGER DEFAULT 0
            );
        """)
        await connection.execute("""
            CREATE TABLE IF NOT EXISTS purchases (
                purchase_id SERIAL PRIMARY KEY,
                user_id BIGINT,
                product_name TEXT,
                price_brl NUMERIC(10, 2),
                purchase_date TIMESTAMP WITH TIME ZONE,
                attendant_id BIGINT,
                deliverer_id BIGINT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );
        """)

async def add_purchase(user_id: int, product_name: str, price: float, attendant_id: int, deliverer_id: int):
    """Adiciona uma compra ao DB, incrementa o contador e retorna o ID da nova compra e a contagem total."""
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO users (user_id) VALUES ($1) ON CONFLICT (user_id) DO NOTHING;", user_id)
        
        new_purchase = await conn.fetchrow(
            "INSERT INTO purchases (user_id, product_name, price_brl, purchase_date, attendant_id, deliverer_id) VALUES ($1, $2, $3, $4, $5, $6) RETURNING purchase_id;",
            user_id, product_name, price, datetime.datetime.now(datetime.timezone.utc), attendant_id, deliverer_id
        )
        
        user_data = await conn.fetchrow("UPDATE users SET purchase_count = purchase_count + 1 WHERE user_id = $1 RETURNING purchase_count;", user_id)
        
        return new_purchase['purchase_id'], user_data['purchase_count']

async def get_purchase_history(user_id: int):
    """Retorna o histórico de compras de um usuário."""
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT product_name, price_brl, purchase_date FROM purchases WHERE user_id = $1 ORDER BY purchase_date DESC;", user_id)

async def set_purchase_count(user_id: int, count: int):
    """Define manualmente a contagem de compras de um usuário."""
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO users (user_id, purchase_count) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET purchase_count = $2;", user_id, count)

async def get_user_data(user_id: int):
    """Retorna os dados de um usuário (contagem de compras, etc)."""
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO users (user_id) VALUES ($1) ON CONFLICT (user_id) DO NOTHING;", user_id)
        return await conn.fetchrow("SELECT * FROM users WHERE user_id = $1;", user_id)

async def set_vip_status(user_id: int, status: bool):
    """Define o status VIP de um usuário."""
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO users (user_id, is_vip) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET is_vip = $2;", user_id, status)

async def get_user_spend(user_id: int):
    """Retorna o total gasto por um usuário."""
    async with pool.acquire() as conn:
        total = await conn.fetchval("SELECT SUM(price_brl) FROM purchases WHERE user_id = $1;", user_id)
        return total if total is not None else 0
