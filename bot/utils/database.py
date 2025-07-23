import asyncpg
import logging

logger = logging.getLogger('discord_bot')

class Database:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.pool = None

    async def connect(self):
        """Conecta-se ao banco de dados PostgreSQL e cria as tabelas se não existirem."""
        try:
            self.pool = await asyncpg.create_pool(self.db_url)
            logger.info("Pool de conexão com o banco de dados criado com sucesso.")
            await self.create_tables()
        except Exception as e:
            logger.error(f"Erro ao conectar ao banco de dados ou criar pool: {e}")
            raise # Re-levanta o erro para que o bot não inicie se o DB falhar

    async def close(self):
        """Fecha a conexão com o banco de dados."""
        if self.pool:
            await self.pool.close()
            logger.info("Conexão com o banco de dados fechada.")

    async def create_tables(self):
        """Cria as tabelas necessárias no banco de dados se elas não existirem."""
        async with self.pool.acquire() as conn:
            # Tabela de Usuários (para informações gerais e fidelidade)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username VARCHAR(255),
                    discriminator VARCHAR(4),
                    robux_purchases INTEGER DEFAULT 0,
                    loyalty_points INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Tabela de Carrinhos (para rastrear compras em andamento)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS carts (
                    cart_id SERIAL PRIMARY KEY,
                    user_id BIGINT, -- Pode ter múltiplos carrinhos, então não é UNIQUE
                    thread_id BIGINT UNIQUE, -- Uma thread é para um carrinho
                    product_type VARCHAR(50), -- 'Robux', 'Jogos', 'Giftcard'
                    product_name VARCHAR(255),
                    quantity_or_value VARCHAR(255), -- Ex: "100 Robux", "400 VP", "R$35"
                    price DECIMAL(10, 2),
                    roblox_nickname VARCHAR(255),
                    gamepass_link TEXT,
                    cart_status VARCHAR(50) DEFAULT 'initiated', -- 'initiated', 'selecting_quantity', 'waiting_gamepass', 'awaiting_payment', 'payment_pending', 'payment_approved_awaiting_gamepass', 'awaiting_admin_delivery', 'completed', 'cancelled', 'expired'
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_user
                        FOREIGN KEY(user_id)
                        REFERENCES users(user_id)
                        ON DELETE CASCADE
                );
            """)

            # Tabela de Pedidos/Compras (histórico de compras finalizadas)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    product_type VARCHAR(50),
                    product_name VARCHAR(255),
                    quantity_or_value VARCHAR(255),
                    total_price DECIMAL(10, 2),
                    roblox_nickname VARCHAR(255),
                    gamepass_link TEXT,
                    payment_status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'approved', 'declined'
                    delivery_status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'delivered', 'cancelled'
                    attended_by_admin_id BIGINT, -- ID do admin que marcou como entregue
                    delivered_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_user
                        FOREIGN KEY(user_id)
                        REFERENCES users(user_id)
                        ON DELETE CASCADE
                );
            """)

            # Tabela de Avaliações
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS reviews (
                    review_id SERIAL PRIMARY KEY,
                    order_id INTEGER UNIQUE,
                    user_id BIGINT,
                    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                    comment TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_order
                        FOREIGN KEY(order_id)
                        REFERENCES orders(order_id)
                        ON DELETE CASCADE,
                    CONSTRAINT fk_user
                        FOREIGN KEY(user_id)
                        REFERENCES users(user_id)
                        ON DELETE CASCADE
                );
            """)
            
            # Tabela para gerenciar produtos (dinamicamente, para os comandos de admin)
            # Isso substitui o PRODUCTS do config.py para persistência e edição
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    product_id SERIAL PRIMARY KEY,
                    name VARCHAR(255) UNIQUE NOT NULL,
                    emoji VARCHAR(100),
                    type VARCHAR(50) NOT NULL, -- 'robux', 'game', 'giftcard'
                    is_vip BOOLEAN DEFAULT FALSE,
                    stock INTEGER DEFAULT -1 -- -1 para estoque ilimitado
                );
            """)

            # Tabela para gerenciar os preços de cada produto
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS product_prices (
                    price_id SERIAL PRIMARY KEY,
                    product_id INTEGER NOT NULL,
                    quantity_or_value VARCHAR(255) NOT NULL, -- Ex: "100 Robux", "400 VP", "R$35"
                    price DECIMAL(10, 2) NOT NULL,
                    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE,
                    UNIQUE (product_id, quantity_or_value)
                );
            """)


            logger.info("Tabelas do banco de dados verificadas/criadas com sucesso.")

    async def fetch(self, query: str, *args):
        """Executa uma query SELECT e retorna múltiplos resultados."""
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args):
        """Executa uma query SELECT e retorna um único resultado."""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def execute(self, query: str, *args):
        """Executa uma query que não retorna resultados (INSERT, UPDATE, DELETE, CREATE TABLE)."""
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)
