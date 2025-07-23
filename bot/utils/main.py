import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import logging
from aiohttp import web # Para o servidor web do webhook

from utils.database import Database
from utils.embeds import create_error_embed, create_embed # Importar as funções de embed
import config

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s:%(levelname)s:%(name)s: %(message)s')
logger = logging.getLogger('discord_bot')

# Carregar variáveis de ambiente
load_dotenv()

# Definir intents do Discord (Obrigatórias para certas funcionalidades)
intents = discord.Intents.default()
intents.message_content = True  # Para ler o conteúdo das mensagens (ex: link da Gamepass)
intents.members = True          # Para gerenciar membros, cargos, etc.
intents.guilds = True           # Para informações do servidor

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=config.BOT_PREFIX, intents=intents)
        self.database = Database(os.getenv("DATABASE_URL"))
        self.web_app = None # Para a aplicação Flask/Aiohttp que rodará o webhook
        
        # Lista de cogs para carregar. Descomente conforme eles forem criados.
        self.initial_extensions = [
            "cogs.robux",             # Automação de Robux (próximo passo)
            # "cogs.jogos",           # Fluxo de Jogos (futuro)
            # "cogs.giftcard",        # Fluxo de Giftcards (futuro)
            "cogs.common_listeners",  # Listeners comuns e o botão "Pegar Ticket"
            # "cogs.admin_commands",  # Comandos de administração (futuro)
            # "cogs.client_area",     # Área do Cliente e histórico (futuro)
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
                logger.error(f"Falha ao carregar cog '{extension}'. Erro: {e}")
                
        # Sincronizar comandos de barra
        if config.COMMAND_SYNC_GLOBAL:
            # Sincroniza comandos globalmente. Pode levar até 1 hora para aparecer.
            await self.tree.sync()
            logger.info("Comandos de barra sincronizados globalmente.")
        else:
            # Sincronizar em um servidor específico para testes mais rápidos
            test_guild_id = config.GUILD_ID 
            if test_guild_id:
                guild = discord.Object(id=test_guild_id)
                self.tree.copy_global_commands(guild=guild) # Copia comandos globais para o guild de teste
                await self.tree.sync(guild=guild)
                logger.info(f"Comandos de barra sincronizados para o servidor de teste: {test_guild_id}")
            else:
                logger.warning("GUILD_ID não configurado em config.py. Comandos de barra não serão sincronizados localmente.")

        # Inicializar e rodar o servidor web para webhooks (Mercado Pago)
        self.web_app = web.Application()
        # Adicione rotas de webhook aqui, por exemplo:
        # self.web_app.router.add_post('/mercadopago_webhook', self.handle_mercadopago_webhook)
        
        # Para fins de teste inicial e depuração do webhook
        self.web_app.router.add_get('/test_webhook', self.test_webhook_endpoint)
        self.web_app.router.add_post('/test_webhook_post', self.test_webhook_post_endpoint)


        # Criação da tarefa para rodar o servidor web
        # O Railway usa a porta 8080 por padrão para aplicações web
        runner = web.AppRunner(self.web_app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', int(os.getenv("PORT", 8080)))
        await site.start()
        logger.info(f"Servidor web iniciado na porta {os.getenv('PORT', 8080)}")


    async def on_ready(self):
        """Evento disparado quando o bot está online e pronto."""
        logger.info(f'Bot logado como {self.user} (ID: {self.user.id})')
        logger.info('Bot está pronto!')

    async def on_disconnect(self):
        """Evento disparado quando o bot é desconectado."""
        logger.warning("Bot desconectado.")
        if self.web_app:
            await self.web_app.shutdown()
            await self.web_app.cleanup()
            logger.info("Servidor web desligado.")

    async def on_command_error(self, ctx, error):
        """Tratamento de erros para comandos de barra."""
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(embed=create_error_embed(f"Parâmetros faltando: `{error.param.name}`"), ephemeral=True)
        elif isinstance(error, commands.CommandNotFound):
            return # Ignorar comandos não encontrados
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

    # --- Endpoints de Webhook (AIOHTTP) ---
    async def test_webhook_endpoint(self, request):
        """Endpoint de teste para verificar se o servidor web está funcionando."""
        logger.info("Requisição GET recebida em /test_webhook")
        return web.Response(text="Webhook GET endpoint is working!")

    async def test_webhook_post_endpoint(self, request):
        """Endpoint de teste para receber requisições POST (simula webhook)."""
        logger.info("Requisição POST recebida em /test_webhook_post")
        try:
            data = await request.json()
            logger.info(f"Dados do webhook recebidos: {data}")
            # Em um webhook real do Mercado Pago, você processaria os dados aqui
            # e chamaria a lógica do bot para atualizar o status do pagamento
            return web.Response(text="Dados do webhook recebidos com sucesso!", status=200)
        except Exception as e:
            logger.error(f"Erro ao processar webhook POST: {e}", exc_info=True)
            return web.Response(text=f"Erro: {e}", status=400)

    # TODO: Implementar handle_mercadopago_webhook
    # async def handle_mercadopago_webhook(self, request):
    #     """Endpoint para receber notificações de IPN do Mercado Pago."""
    #     # Lógica para validar e processar o webhook do Mercado Pago
    #     pass


# Instanciar e rodar o bot
bot = MyBot()
token = os.getenv("DISCORD_BOT_TOKEN")

if token:
    # Rodar o bot (que também inicializa o servidor web)
    bot.run(token)
else:
    logger.error("Token do bot não encontrado em .env. Por favor, adicione DISCORD_BOT_TOKEN.")
