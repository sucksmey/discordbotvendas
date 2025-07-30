# dashboard/main.py
from quart import Quart, render_template
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

app = Quart(__name__)
DATABASE_URL = os.getenv("DATABASE_URL")

@app.route('/')
async def show_dashboard():
    pool = None
    dashboard_data = { "total_sales": "Erro", "total_revenue": "Erro", "deliverer_counts": [] }
    
    try:
        if not DATABASE_URL:
            raise Exception("DATABASE_URL não foi encontrada.")
        
        # Cria e fecha a conexão a cada visita - mais simples e estável
        pool = await asyncpg.create_pool(dsn=DATABASE_URL)
        
        async with pool.acquire() as connection:
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
    finally:
        if pool:
            await pool.close()

    return await render_template('dashboard.html', data=dashboard_data)

# Roda o servidor diretamente, sem Gunicorn
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
