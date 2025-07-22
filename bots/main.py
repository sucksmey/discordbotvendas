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
if not BOT_TOKEN:
    print("ERRO: Variável de ambiente BOT_TOKEN não encontrada. Certifique-se de que está no .env ou nas variáveis do Railway.")
    exit(1)
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

# Instância do banco de dados
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
        # Sincroniza comandos GLOBALMENTE (pode levar até 1 hora para aparecer)
        await bot.tree.sync()
        print("Comandos de barra (slash commands) sincronizados GLOBALMENTE!")
        print(f"Comandos carregados na árvore do bot: {[command.name for command in bot.tree.walk_commands()]}")
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
    # Lista dos cogs a serem carregados
    cogs_to_load = ["robux", "jogos", "giftcard", "common_listeners"] 
    # Adicione "test_commands" se você tiver o arquivo cogs/test_commands.py e quiser carregá-lo
    if os.path.exists('./cogs/test_commands.py'):
        cogs_to_load.append("test_commands")


    for cog_name in cogs_to_load:
        try:
            # Imprime o conteúdo do arquivo do cog antes de carregar para depuração
            cog_path = os.path.join('./cogs', f"{cog_name}.py")
            print(f"\n--- Conteúdo do arquivo {cog_path} antes de carregar ---")
            try:
                with open(cog_path, 'r', encoding='utf-8') as f:
                    print(f.read())
            except Exception as file_e:
                print(f"Erro ao ler arquivo {cog_path}: {file_e}")
            print(f"--- Fim do conteúdo de {cog_path} ---\n")

            await bot.load_extension(f'cogs.{cog_name}')
            print(f'Carregado cog: {cog_name}')
        except Exception as e:
            print(f'Falha ao carregar cog {cog_name}: {e}')
    print(f"Cogs carregados: {[cog.qualified_name for cog in bot.cogs.values()]}")


# Inicia o bot e carrega os cogs
async def main():
    async with bot:
        await load_cogs()
        await bot.start(BOT_TOKEN)

# Garante que a função main() seja executada
if __name__ == "__main__":
    asyncio.run(main())

