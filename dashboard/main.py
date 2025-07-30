# dashboard/main.py
from flask import Flask, render_template
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
DATABASE_URL = os.getenv("DATABASE_URL")

# A pool de conexões será criada uma vez quando o app iniciar
app.pool = None

@app.before_serving
async def create_pool():
    """Cria a pool de conexões com o banco de dados antes do servidor iniciar."""
    if DATABASE_URL:
        app.pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=1, max_size=5)
        print("Pool de conexões com o banco de dados criada.")
    else:
        print("ERRO: DATABASE_URL não encontrada. O dashboard não conseguirá buscar dados.")

@app.route('/')
async def show_dashboard():
    dashboard_data = { "total_sales": 0, "total_revenue": "0.00", "deliverer_counts": [] }
    if not app.pool:
        print("Dashboard acessado, mas a pool de conexões com o DB não existe.")
        return render_template('dashboard.html', data=dashboard_data)

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
        print(f"Erro ao buscar dados do banco de dados: {e}")
        dashboard_data = { "total_sales": "Erro", "total_revenue": "Erro", "deliverer_counts": [] }

    return render_template('dashboard.html', data=dashboard_data)

if __name__ == '__main__':
    # Esta parte é para o Gunicorn (usado pelo Railway) encontrar a aplicação
    # Não é usada quando você roda o arquivo diretamente
    pass
