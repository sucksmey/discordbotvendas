# main.py

import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio

# Carrega as variáveis de ambiente do arquivo .env BEM NO INÍCIO
load_dotenv()

# Agora sim, importa as configurações do seu config.py
import config
# Importa a classe Database
from utils.database import Database

# Lê as variáveis de ambiente APÓS load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
MERCADOPAGO_ACCESS_TOKEN = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

# --- VALIDAÇÕES DE VARIÁVEIS DE AMBIENTE ---
# É crucial que essas variáveis estejam definidas.
if not BOT_TOKEN:
    print("ERRO: Variável de ambiente BOT_TOKEN não encontrada. Certifique-se de que está no .env ou nas variáveis do Railway.")
    exit(1) # Sai do programa se o token não for encontrado
if not DATABASE_URL:
    print("ERRO: Variável de ambiente DATABASE_URL não encontrada. Certifique-se de que está no .env ou nas variáveis do Railway.")
    exit(1)
if not MERCADOPAGO_ACCESS_TOKEN:
    print("AVISO: Variável de ambiente MERCADOPAGO_ACCESS_TOKEN não encontrada. Pagamentos Mercado Pago podem não funcionar.")


# Define as intents necessárias para o bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

# Inicializa o bot
bot = commands.Bot(command_prefix="!", intents=intents)

# Instância do banco de dados - AGORA PASSA A DATABASE_URL
db = Database(DATABASE_URL)
# Anexa a instância do DB ao objeto bot para fácil acesso em cogs
bot.db = db

# Evento que é disparado quando o bot está pronto e online
@bot.event
async def on_ready():
    print(f'Bot logado como {bot.user}')
    print(f'ID: {bot.user.id}')
    
    # Conecta ao banco de dados e cria as tabelas
    await db.connect()
    await db.create_tables()

    # Sincroniza os comandos de barra (slash commands) com o Discord
    try:
        # Sincroniza comandos APENAS para o seu servidor de teste (mais rápido)
        guild_obj = discord.Object(id=config.GUILD_ID) 
        await bot.tree.sync(guild=guild_obj)
        print(f"Comandos de barra (slash commands) sincronizados para a guild: {config.GUILD_ID}!")
    except Exception as e:
        print(f"Erro ao sincronizar comandos de barra: {e}")

    # Define o status do bot
    await bot.change_presence(activity=discord.Game(name="Gerenciando Vendas de Jogos!"))

# Comando de teste simples para verificar se o bot está funcionando
@bot.tree.command(name="ola", description="Diz olá!")
async def ola(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Olá!",
        description=f"Olá, {interaction.user.display_name}! Eu sou seu bot de vendas.",
        color=config.ROSE_COLOR
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Função para carregar os cogs
async def load_cogs():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py') and not filename.startswith('__'):
            try:
                # Não passa 'db' aqui, pois ele já está em bot.db
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f'Carregado cog: {filename[:-3]}')
            except Exception as e:
                print(f'Falha ao carregar cog {filename[:-3]}: {e}')

# Inicia o bot e carrega os cogs
async def main():
    async with bot:
        await load_cogs()
        # Usa a variável BOT_TOKEN lida do ambiente
        await bot.start(BOT_TOKEN)

# Garante que a função main() seja executada
if __name__ == "__main__":
    asyncio.run(main())
