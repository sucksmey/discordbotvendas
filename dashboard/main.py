# dashboard/main.py
from quart import Quart, render_template
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

app = Quart(__name__)

# --- CORREÇÃO DEFINITIVA ---
# Força a configuração que está causando o erro a existir.
app.config["PROVIDE_AUTOMATIC_OPTIONS"] = False

DATABASE_URL = os.getenv("DATABASE_URL")

@app.before_serving
async def create_pool():
    """Cria a pool de conexões com o banco de dados antes do servidor iniciar."""
    if DATABASE_URL:
        app.pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=1, max_size=5)
        print("Pool de conexões com o banco de dados criada.")
    else:
        print("ERRO: DATABASE_URL não encontrada.")

@app.route('/')
async def show_dashboard():
    dashboard_data = { "total_sales": 0, "total_revenue": "0.00", "deliverer_counts": [] }
    if not hasattr(app, 'pool') or app.pool is None:
        print("Dashboard acessado, mas a pool de conexões com o DB não existe.")
        return await render_template('dashboard.html', data=dashboard_data)

    try:
        async with app.pool.acquire() as connection:
            total_sales = await connection.fetchval("SELECT COUNT(*) FROM purchases;")
            total_revenue_cents = await connection.fetchval("SELECT SUM(price_brl) FROM purchases;")
            total_revenue = float(total_revenue_cents / 100) if total_revenue_cents else 0.0
            
            deliverer_counts_records = await connection.fetch("""
                SELECT deliverer_id, COUNT(*) as count 
                FROM purchases 
                WHERE deliverer_id IS NOT NULL 
                GROUP BY deliverer_id ORDER BY count DESC;
            """)
            
            dashboard_data = {
                "total_sales": total_sales or 0,
                "total_revenue": f"{total_revenue:.2f}",
                "deliverer_counts": deliverer_counts_records
            }
    except Exception as e:
        print(f"ERRO NO DASHBOARD: {e}")
        dashboard_data = { "total_sales": "Erro", "total_revenue": "Erro", "deliverer_counts": [] }

    return await render_template('dashboard.html', data=dashboard_data)

if __name__ == '__main__':
    # O Gunicorn vai cuidar de rodar a aplicação no Railway
    pass
