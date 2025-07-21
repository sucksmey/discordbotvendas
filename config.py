# main.py

import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Importa as configurações do seu config.py
import config
# Importa a classe Database
from utils.database import Database

# Define as intents necessárias para o bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

# Inicializa o bot
bot = commands.Bot(command_prefix="!", intents=intents)

# Instância do banco de dados
db = Database()

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
        # O ID da guild está no config.py
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
                # Passa a instância do banco de dados para o cog
                await bot.load_extension(f'cogs.{filename[:-3]}', db=db)
                print(f'Carregado cog: {filename[:-3]}')
            except Exception as e:
                print(f'Falha ao carregar cog {filename[:-3]}: {e}')

# Inicia o bot e carrega os cogs
async def main():
    async with bot:
        await load_cogs()
        await bot.start(config.BOT_TOKEN)

# Garante que a função main() seja executada
if __name__ == "__main__":
    asyncio.run(main())
