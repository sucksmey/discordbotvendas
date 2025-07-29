# database.py
import asyncpg
import datetime
import config

pool = None

async def init_db():
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
                active_thread_id BIGINT DEFAULT NULL
            );
        """)
        await connection.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS active_thread_id BIGINT DEFAULT NULL;")
        
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
        await connection.execute("""
            CREATE TABLE IF NOT EXISTS products (
                product_id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                price NUMERIC(10, 2) NOT NULL,
                stock INTEGER NOT NULL DEFAULT 0,
                category TEXT NOT NULL
            );
        """)

async def get_active_thread(user_id: int):
    """Busca o ID do tópico de compra ativo de um usuário."""
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO users (user_id) VALUES ($1) ON CONFLICT (user_id) DO NOTHING;", user_id)
        thread_id = await conn.fetchval("SELECT active_thread_id FROM users WHERE user_id = $1;", user_id)
        return thread_id

async def set_active_thread(user_id: int, thread_id: int | None):
    """Define ou limpa o tópico de compra ativo de um usuário."""
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO users (user_id) VALUES ($1) ON CONFLICT (user_id) DO NOTHING;", user_id)
        await conn.execute("UPDATE users SET active_thread_id = $1 WHERE user_id = $2;", thread_id, user_id)

async def add_purchase(user_id: int, product_name: str, price: float, attendant_id: int, deliverer_id: int | None):
    """Adiciona uma compra ao DB e incrementa o contador de compras."""
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO users (user_id) VALUES ($1) ON CONFLICT (user_id) DO NOTHING;", user_id)
        new_purchase = await conn.fetchrow(
            "INSERT INTO purchases (user_id, product_name, price_brl, purchase_date, attendant_id, deliverer_id) VALUES ($1, $2, $3, $4, $5, $6) RETURNING purchase_id;",
            user_id, product_name, price, datetime.datetime.now(datetime.timezone.utc), attendant_id, deliverer_id
        )
        await conn.execute("UPDATE users SET purchase_count = purchase_count + 1 WHERE user_id = $1;", user_id)
        return new_purchase['purchase_id']

async def get_user_spend_and_count(user_id: int):
    """Retorna o total gasto e a contagem de compras de um usuário."""
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO users (user_id) VALUES ($1) ON CONFLICT (user_id) DO NOTHING;", user_id)
        data = await conn.fetchrow("""
            SELECT SUM(p.price_brl) as total_spent, u.purchase_count
            FROM users u
            LEFT JOIN purchases p ON u.user_id = p.user_id
            WHERE u.user_id = $1
            GROUP BY u.user_id, u.purchase_count;
        """, user_id)
        if not data:
             # Se o usuário existe mas não tem compras, busca a contagem de compras dele
            count_data = await conn.fetchrow("SELECT purchase_count FROM users WHERE user_id = $1", user_id)
            return 0.0, count_data['purchase_count'] if count_data else 0

        total_spent = data['total_spent'] if data['total_spent'] is not None else 0
        purchase_count = data['purchase_count'] if data['purchase_count'] is not None else 0
        return float(total_spent), purchase_count

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

async def add_product(name: str, price: float, stock: int, category: str):
    """Adiciona um novo produto ao banco de dados."""
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO products (name, price, stock, category) VALUES ($1, $2, $3, $4);", name, price, stock, category)

async def get_products_by_category(category: str):
    """Busca todos os produtos de uma categoria específica (case-insensitive)."""
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT * FROM products WHERE LOWER(category) = LOWER($1) ORDER BY name ASC;", category)

async def get_product_by_id(product_id: int):
    """Busca um produto específico pelo seu ID."""
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM products WHERE product_id = $1;", product_id)

async def update_stock(product_id: int, quantity: int):
    """Adiciona ou remove uma quantidade do estoque de um produto."""
    async with pool.acquire() as conn:
        await conn.execute("UPDATE products SET stock = stock + $1 WHERE product_id = $2;", quantity, product_id)
        
async def set_stock(product_id: int, quantity: int):
    """Define o estoque de um produto para um valor exato."""
    async with pool.acquire() as conn:
        await conn.execute("UPDATE products SET stock = $1 WHERE product_id = $2;", quantity, product_id)
