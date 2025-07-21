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

# Define as intents necessárias para o bot
intents = discord.Intents.default()
intents.message_content = True  # Necessário para ler o conteúdo de mensagens
intents.members = True          # Necessário para gerenciar membros (cargos, etc.)
intents.presences = True        # Opcional, para status de presença

# Inicializa o bot
bot = commands.Bot(command_prefix="!", intents=intents)

# Evento que é disparado quando o bot está pronto e online
@bot.event
async def on_ready():
    print(f'Bot logado como {bot.user}')
    print(f'ID: {bot.user.id}')
    
    # Sincroniza os comandos de barra (slash commands) com o Discord
    try:
        # Sincroniza comandos globais e para guilds específicas
        # Para testar comandos rapidamente em uma guild específica:
        # await bot.tree.sync(guild=discord.Object(id=config.GUILD_ID))
        await bot.tree.sync() # Sincroniza globalmente, pode levar até 1 hora para aparecer
        print("Comandos de barra (slash commands) sincronizados!")
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
    await interaction.response.send_message(embed=embed, ephemeral=True) # ephemeral=True torna a mensagem visível só para quem usou o comando

# Função para carregar os cogs
async def load_cogs():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py') and not filename.startswith('__'):
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f'Carregado cog: {filename[:-3]}')
            except Exception as e:
                print(f'Falha ao carregar cog {filename[:-3]}: {e}')

# Inicia o bot e carrega os cogs
async def main():
    async with bot:
        await load_cogs() # Chamada para carregar os cogs
        await bot.start(config.BOT_TOKEN)

# Garante que a função main() seja executada
if __name__ == "__main__":
    asyncio.run(main())
