# utils/database.py

import asyncpg
import config

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        """Estabelece a conexão com o banco de dados."""
        if not self.pool:
            try:
                self.pool = await asyncpg.create_pool(dsn=config.DATABASE_URL)
                print("Conexão com o banco de dados PostgreSQL estabelecida.")
            except Exception as e:
                print(f"Erro ao conectar ao banco de dados: {e}")
                self.pool = None # Garante que o pool é None em caso de falha

    async def close(self):
        """Fecha a conexão com o banco de dados."""
        if self.pool:
            await self.pool.close()
            print("Conexão com o banco de dados PostgreSQL fechada.")
            self.pool = None

    async def fetch_one(self, query, *args):
        """Executa uma query e retorna uma única linha."""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetch_all(self, query, *args):
        """Executa uma query e retorna múltiplas linhas."""
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def execute(self, query, *args):
        """Executa uma query que não retorna dados (INSERT, UPDATE, DELETE)."""
        async with self.pool.acquire() as conn:
            await conn.execute(query, *args)

    async def create_tables(self):
        """Cria as tabelas necessárias se não existirem."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    robux_purchases INTEGER DEFAULT 0,
                    loyalty_points INTEGER DEFAULT 0,
                    cart_thread_id BIGINT DEFAULT NULL,
                    cart_product_name TEXT DEFAULT NULL,
                    cart_quantity TEXT DEFAULT NULL,
                    cart_status TEXT DEFAULT NULL,
                    last_cart_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS orders (
                    order_id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    product_name TEXT NOT NULL,
                    quantity TEXT NOT NULL,
                    total_price NUMERIC(10, 2) NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending', -- pending, paid, delivered, cancelled
                    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    delivery_date TIMESTAMP DEFAULT NULL,
                    thread_id BIGINT DEFAULT NULL,
                    pix_qr_code TEXT DEFAULT NULL,
                    pix_copy_paste TEXT DEFAULT NULL,
                    roblox_nickname TEXT DEFAULT NULL,
                    gamepass_link TEXT DEFAULT NULL,
                    admin_id BIGINT DEFAULT NULL,
                    delivery_admin_id BIGINT DEFAULT NULL,
                    review_rating INTEGER DEFAULT NULL,
                    review_comment TEXT DEFAULT NULL
                );

                -- Adicione mais tabelas conforme necessário (ex: para FAQ, estoque se não for fixo)
            """)
            print("Tabelas do banco de dados verificadas/criadas.")
