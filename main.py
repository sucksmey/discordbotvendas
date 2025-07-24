# main.py
import discord
import os
import traceback
from dotenv import load_dotenv

import config
import database

# --- NOVO: Módulo de Utilitários para Logging ---
# Crie uma pasta 'utils' e dentro dela um arquivo 'logger.py'
# utils/logger.py
async def log_dm(bot, user, **kwargs):
    """Envia uma DM e loga a ação."""
    log_channel = bot.get_channel(config.GENERAL_LOG_CHANNEL_ID)
    try:
        await user.send(**kwargs)
        if log_channel:
            await log_channel.send(f"ℹ️ DM enviada com sucesso para {user.mention}.")
    except discord.Forbidden:
        if log_channel:
            await log_channel.send(f"⚠️ Falha ao enviar DM para {user.mention} (DM fechada).")

async def log_command(bot, ctx):
    """Loga o uso de um comando."""
    log_channel = bot.get_channel(config.GENERAL_LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(f"ℹ️ O usuário {ctx.author.mention} usou o comando `/{ctx.command.name}`.")
# -----------------------------------------------------

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = discord.Bot(intents=intents)

cogs_list = [
    'sales_cog',
    'admin_cog',
    'evaluation_cog',
    'user_cog' # <-- NOVO COG
]

for cog in cogs_list:
    bot.load_extension(f'cogs.{cog}')

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    # Inicializar a conexão com o banco de dados
    try:
        await database.init_db()
        print("Conexão com o banco de dados estabelecida e tabelas verificadas.")
    except Exception as e:
        print(f"ERRO: Falha ao conectar ao banco de dados: {e}")
    await bot.sync_commands(guild_ids=[config.GUILD_ID])
    print('Comandos de barra sincronizados.')


# --- IMPORTANTE: Sistema de Traceback de Erros ---
@bot.event
async def on_application_command_error(ctx: discord.ApplicationContext, error: discord.DiscordException):
    """Manipulador de erros global para comandos de barra."""
    
    # Imprime o traceback completo no console para debug
    print(f"Ocorreu um erro no comando '{ctx.command.name}':")
    traceback.print_exception(type(error), error, error.__traceback__)
    
    # Envia uma mensagem de erro genérica e amigável para o usuário
    embed = discord.Embed(
        title="❌ Ocorreu um Erro",
        description="Ocorreu um erro inesperado ao executar este comando. A equipe de desenvolvimento já foi notificada.",
        color=discord.Color.red()
    )
    await ctx.respond(embed=embed, ephemeral=True)


bot.run(TOKEN)
