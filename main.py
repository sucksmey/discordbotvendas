# main.py
import discord
import os
import traceback
from dotenv import load_dotenv

import config
import database

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = discord.Bot(intents=intents)

# Lista de cogs para carregar
cogs_list = [
    'sales_cog',
    'admin_cog',
    'evaluation_cog',
    'user_cog',
    'vip_cog',
    'stock_cog',
    'calculator_cog'
]

for cog in cogs_list:
    try:
        bot.load_extension(f'cogs.{cog}')
        print(f"Cog '{cog}' carregado com sucesso.")
    except Exception as e:
        print(f"Erro ao carregar o cog {cog}: {e}")

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    try:
        await database.init_db()
        print("Conexão com o banco de dados estabelecida.")
    except Exception as e:
        print(f"ERRO: Falha ao conectar ao banco de dados: {e}")
    
    await bot.sync_commands(guild_ids=[config.GUILD_ID])
    print('Comandos de barra sincronizados.')

@bot.event
async def on_application_command_error(ctx: discord.ApplicationContext, error: discord.DiscordException):
    print(f"Ocorreu um erro no comando '{ctx.command.name}':")
    traceback.print_exception(type(error), error, error.__traceback__)
    embed = discord.Embed(title="❌ Ocorreu um Erro", description="Um erro inesperado ocorreu. A equipe de desenvolvimento foi notificada.", color=discord.Color.red())
    if not ctx.interaction.response.is_done():
        await ctx.respond(embed=embed, ephemeral=True)
    else:
        await ctx.followup.send(embed=embed, ephemeral=True)

if TOKEN:
    bot.run(TOKEN)
else:
    print("ERRO CRÍTICO: DISCORD_TOKEN não encontrado.")
