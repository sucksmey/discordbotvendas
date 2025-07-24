# main.py
import discord
import os
import traceback
from dotenv import load_dotenv

import config
import database

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
    'evaluation_cog',
    'user_cog',
    'vip_cog'
]

# Carregar os cogs
for cog in cogs_list:
    try:
        bot.load_extension(f'cogs.{cog}')
    except Exception as e:
        print(f"Erro ao carregar o cog {cog}: {e}")

@bot.event
async def on_ready():
    """Evento que é acionado quando o bot está online e pronto."""
    print(f'Bot conectado como {bot.user}')
    # Inicializar a conexão com o banco de dados
    try:
        await database.init_db()
        print("Conexão com o banco de dados estabelecida e tabelas verificadas.")
    except Exception as e:
        print(f"ERRO: Falha ao conectar ao banco de dados: {e}")
    
    # Sincronizar comandos de barra com o servidor especificado
    await bot.sync_commands(guild_ids=[config.GUILD_ID])
    print('Comandos de barra sincronizados.')


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
    if not ctx.interaction.response.is_done():
        await ctx.respond(embed=embed, ephemeral=True)
    else:
        await ctx.followup.send(embed=embed, ephemeral=True)

# Iniciar o bot
if TOKEN:
    bot.run(TOKEN)
else:
    print("ERRO CRÍTICO: O DISCORD_TOKEN não foi encontrado nas variáveis de ambiente.")
