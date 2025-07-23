import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import logging

from utils.database import Database
from utils.embeds import create_error_embed, create_embed
import config

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s:%(levelname)s:%(name)s: %(message)s')
logger = logging.getLogger('discord_bot')

# Carregar variáveis de ambiente
load_dotenv()

# Definir intents do Discord
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=config.BOT_PREFIX, intents=intents)
        self.database = Database(os.getenv("DATABASE_URL"))
        self.db = self.database # Facilita o acesso ao DB nos cogs
        
        self.initial_extensions = [
            "cogs.robux",             
            # "cogs.jogos",           
            # "cogs.giftcard",        
            "cogs.common_listeners",  
            "cogs.client_area",       
            # "cogs.admin_commands",  
        ]

    async def setup_hook(self):
        """Chamado quando o bot está pronto para carregar extensões e conectar ao DB."""
        await self.database.connect()
        logger.info("Conectado ao banco de dados PostgreSQL.")

        # Carregar cogs
        for extension in self.initial_extensions:
            try:
                await self.load_extension(extension)
                logger.info(f"Cog '{extension}' carregado com sucesso.")
            except Exception as e:
                logger.error(f"Falha ao carregar cog '{extension}'. Erro: {e}", exc_info=True) # Adiciona exc_info=True para mais detalhes no log
                
        # Sincronizar comandos de barra
        if config.COMMAND_SYNC_GLOBAL:
            await self.tree.sync()
            logger.info("Comandos de barra sincronizados globalmente.")
        else:
            test_guild_id = config.GUILD_ID 
            if test_guild_id:
                guild = discord.Object(id=test_guild_id)
                self.tree.copy_global_commands(guild=guild) # Copia comandos globais para o guild de teste
                await self.tree.sync(guild=guild)
                logger.info(f"Comandos de barra sincronizados para o servidor de teste: {test_guild_id}")
            else:
                logger.warning("GUILD_ID não configurado em config.py. Comandos de barra não serão sincronizados localmente.")

    async def on_ready(self):
        """Evento disparado quando o bot está online e pronto."""
        logger.info(f'Bot logado como {self.user} (ID: {self.user.id})')
        logger.info('Bot está pronto!')

    async def on_disconnect(self):
        """Evento disparado quando o bot é desconectado."""
        logger.warning("Bot desconectado.")

    async def on_command_error(self, ctx, error):
        """Tratamento de erros para comandos de barra."""
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(embed=create_error_embed(f"Parâmetros faltando: `{error.param.name}`"), ephemeral=True)
        elif isinstance(error, commands.CommandNotFound):
            return 
        elif isinstance(error, commands.NotOwner):
            await ctx.send(embed=create_error_embed("Você não tem permissão para usar este comando."), ephemeral=True)
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send(embed=create_error_embed("Você não tem as permissões necessárias para usar este comando."), ephemeral=True)
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send(embed=create_error_embed("O bot não tem as permissões necessárias para executar este comando."), ephemeral=True)
        else:
            logger.error(f"Erro no comando '{ctx.command}':", exc_info=error)
            await ctx.send(embed=create_error_embed("Ocorreu um erro inesperado ao executar o comando."), ephemeral=True)

    async def on_error(self, event_method, *args, **kwargs):
        """Captura e loga erros não tratados de eventos."""
        logger.exception(f"Erro inesperado no evento '{event_method}':")


# Instanciar e rodar o bot
bot = MyBot()
token = os.getenv("DISCORD_BOT_TOKEN")

if token:
    bot.run(token)
else:
    logger.error("Token do bot não encontrado em .env. Por favor, adicione DISCORD_BOT_TOKEN.")
