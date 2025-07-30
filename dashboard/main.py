# dashboard/main.py
from flask import Flask, render_template
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
DATABASE_URL = os.getenv("DATABASE_URL")

@app.route('/')
async def show_dashboard():
    pool = None
    # Dados padrão em caso de erro, para a página não quebrar
    dashboard_data = { "total_sales": "Erro", "total_revenue": "Erro", "deliverer_counts": [] }
    
    try:
        if not DATABASE_URL:
            raise Exception("DATABASE_URL não foi encontrada nas variáveis de ambiente.")
        
        # Cria uma nova conexão com o banco de dados a cada visita
        pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=1, max_size=5)
        
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
        # Garante que a conexão com o banco de dados seja sempre fechada
        if pool:
            await pool.close()

    return render_template('dashboard.html', data=dashboard_data)

# Esta parte é usada pelo Railway para iniciar o servidor
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
