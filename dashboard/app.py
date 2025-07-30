# dashboard/app.py
from flask import Flask, render_template
import asyncpg
import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente (como a DATABASE_URL)
load_dotenv()

app = Flask(__name__)
DATABASE_URL = os.getenv("DATABASE_URL")

async def get_db_pool():
    # Retorna uma pool de conexões com o banco de dados
    return await asyncpg.create_pool(dsn=DATABASE_URL, min_size=1, max_size=5)

@app.route('/')
async def show_dashboard():
    pool = await get_db_pool()
    dashboard_data = {}
    try:
        async with pool.acquire() as connection:
            # Busca a quantidade total de vendas
            total_sales = await connection.fetchval("SELECT COUNT(*) FROM purchases;")
            
            # Busca o faturamento total (dividindo por 100 para corrigir o valor em centavos)
            total_revenue_cents = await connection.fetchval("SELECT SUM(price_brl) FROM purchases;")
            total_revenue = float(total_revenue_cents / 100) if total_revenue_cents else 0.0

            # Busca o número de entregas por atendente
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
        # Em caso de erro, exibe dados zerados para não quebrar a página
        dashboard_data = { "total_sales": "Erro", "total_revenue": "Erro", "deliverer_counts": [] }
    finally:
        await pool.close()

    # Renderiza a página 'dashboard.html' e passa os dados para ela
    return render_template('dashboard.html', data=dashboard_data)

if __name__ == '__main__':
    # Esta parte é para rodar localmente, o Railway usa o gunicorn
    app.run(debug=True)
