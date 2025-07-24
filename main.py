# main.py
import discord
import os
from dotenv import load_dotenv

import config

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Definir as intenções (Intents) do bot
intents = discord.Intents.default()
intents.message_content = True  # Necessário para ler o conteúdo das mensagens
intents.members = True          # Necessário para obter informações dos membros

bot = discord.Bot(intents=intents)

# Lista de cogs para carregar
cogs_list = [
    'sales_cog',
    'admin_cog',
    'evaluation_cog'
]

# Carregar os cogs
for cog in cogs_list:
    bot.load_extension(f'cogs.{cog}')

@bot.event
async def on_ready():
    """Evento que é acionado quando o bot está online e pronto."""
    print(f'Bot conectado como {bot.user}')
    print(f'ID do Bot: {bot.user.id}')
    print('------')
    # Sincronizar comandos de barra com o servidor especificado
    await bot.sync_commands(guild_ids=[config.GUILD_ID])
    print('Comandos de barra sincronizados.')

# Iniciar o bot
bot.run(TOKEN)
