import discord
from pycord.ext import commands
import logging
import asyncio
import re # Para expressões regulares
import config
from utils.database import Database
from utils.embeds import create_embed, create_error_embed, create_success_embed

logger = logging.getLogger('discord_bot')

class CommonListeners(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db: Database = bot.database

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Listener para verificar mensagens em threads de carrinho,
        especialmente para capturar o link da gamepass.
        """
        if message.author.bot:
            return

        # Verificar se a mensagem está em uma thread privada
        if isinstance(message.channel, discord.Thread) and message.channel.type == discord.ChannelType.private_thread:
            # Buscar o carrinho associado a esta thread e usuário
            cart = await self.db.fetchrow("SELECT * FROM carts WHERE thread_id = $1 AND user_id = $2", 
                                          message.channel.id, message.author.id)
            
            if cart:
                # Lógica para Robux: esperando o link da Gamepass APÓS o pagamento aprovado
                if cart['product_type'] == 'Robux' and cart['cart_status'] == 'payment_approved_awaiting_gamepass':
                    gamepass_link = message.content.strip()
                    
                    # Validação básica de URL do Roblox
                    if re.match(r"https?:\/\/(www\.)?roblox\.com\/games\/\d+\/.*(\/store\/|\/game-pass\/)", gamepass_link):
                        # Pergunta de confirmação de preços regionais
                        embed = create_embed(
                            "Link da Gamepass Recebido!",
                            f"Você enviou o link: `{gamepass_link}`\n\n"
                            "**Importante:** Você já criou a Gamepass com o valor exato de R${cart['price']:.2f} e "
                            "**desativou os preços regionais** conforme o tutorial? "
                            "A confirmação é essencial para prosseguir."
                        )
                        view = ConfirmGamepassView(self.bot, cart['cart_id'], gamepass_link)
                        await message.channel.send(embed=embed, view=view)
                        logger.info(f"Link de Gamepass recebido para carrinho {cart['cart_id']} de {message.author.name}: {gamepass_link}. Aguardando confirmação regional.")
                    else:
                        await message.channel.send(embed=create_error_embed("O link da Gamepass parece inválido. Por favor, envie um link válido do Roblox (que contenha '/games/' e '/store/' ou '/game-pass/')."))
                
                # Para outros jogos (sem automação completa de Gamepass)
                elif cart['product_type'] != 'Robux' and cart['cart_status'] == 'awaiting_admin_delivery':
                    # Se o carrinho já está no status de aguardando admin para entrega
                    admin_role = message.guild.get_role(config.ADMIN_ROLE_ID)
                    if admin_role:
                        await message.channel.send(f"{admin_role.mention}, o usuário {message.author.mention} enviou uma nova mensagem no carrinho para {cart['product_name']}. Por favor, verifique.")
                    logger.info(f"Mensagem em carrinho manual {cart['cart_id']} de {message.author.name}: {message.content[:50]}...")
            
            # TODO: Lógica para casos onde o usuário manda mensagem mas não tem carrinho em status de espera de gamepass
            # ou está em outro status que exija interação.
            # No momento, ignoramos para simplificar, mas pode ser expandido.


    @commands.Cog.listener()
    async def on_raw_thread_update(self, payload: discord.RawThreadUpdateEvent):
        """
        Listener para monitorar atualizações de threads, como arquivamento.
        Usado para marcar o carrinho como encerrado quando a thread é arquivada pelo bot ou admin.
        """
        if payload.thread_type == discord.ChannelType.private_thread:
            thread = self.bot.get_channel(payload.thread_id) # Objeto Thread
            if thread and payload.archived and not payload.old_thread.archived:
                # Thread foi arquivada
                cart = await self.db.fetchrow("SELECT * FROM carts WHERE thread_id = $1", payload.thread_id)
                if cart and cart['cart_status'] != 'completed' and cart['cart_status'] != 'cancelled':
                    # Se o carrinho não estava marcado como completo, marque como 'archived' ou 'closed'
                    await self.db.execute("UPDATE carts SET cart_status = $1, updated_at = NOW() WHERE cart_id = $2",
                                          'closed_by_archive', cart['cart_id'])
                    logger.info(f"Carrinho {cart['cart_id']} arquivado por admin ou bot. Status atualizado para 'closed_by_archive'.")


class CommonViews(discord.ui.View):
    def __init__(self, bot: commands.Bot, user_id: int):
        super().__init__(timeout=config.CART_EXPIRATION_MINUTES * 60) # Timeout em segundos
        self.bot = bot
        self.user_id = user_id
        self.db: Database = bot.database
        self.message = None # Para armazenar a mensagem que contém a view

    async def on_timeout(self):
        """Chamado quando a view expira (carrinho inativo)."""
        cart = await self.db.fetchrow("SELECT * FROM carts WHERE user_id = $1 AND thread_id IS NOT NULL AND cart_status NOT IN ('completed', 'cancelled', 'expired', 'closed_by_archive')", self.user_id)
        if cart:
            thread = self.bot.get_channel(cart['thread_id'])
            if thread and isinstance(thread, discord.Thread):
                if not thread.archived:
                    try:
                        await thread.send(embed=create_error_embed("Seu carrinho expirou devido à inatividade. Inicie um novo com /robux ou /jogos se desejar."))
                        await thread.edit(archived=True, locked=True) # Arquiva e bloqueia a thread
                    except discord.Forbidden:
                        logger.error(f"Não foi possível arquivar thread {thread.id} (permissão negada).")
                else:
                    logger.info(f"Carrinho {cart['cart_id']} de {self.user_id} expirou, mas já estava arquivado.")
            await self.db.execute("UPDATE carts SET cart_status = 'expired', updated_at = NOW() WHERE cart_id = $1", cart['cart_id'])
            logger.info(f"Carrinho {cart['cart_id']} de {self.user_id} expirou e foi marcado como 'expired'.")

        if self.message:
            # Remove os botões da mensagem para evitar interações após o timeout
            try:
                await self.message.edit(view=None)
            except discord.HTTPException:
                pass # A mensagem pode já ter sido deletada

    @discord.ui.button(label="Pegar Ticket", style=discord.ButtonStyle.red, custom_id="pegarticket_button")
    async def pegar_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Botão para chamar um atendente."""
        await interaction.response.defer() # Acknowledge the interaction, mas sem resposta imediata visível

        cart = await self.db.fetchrow("SELECT * FROM carts WHERE user_id = $1 AND thread_id = $2", 
                                      interaction.user.id, interaction.channel_id)
        
        if not cart:
            await interaction.followup.send(embed=create_error_embed("Este não é um carrinho válido ou não foi iniciado por você."), ephemeral=True)
            return
        
        admin_role = interaction.guild.get_role(config.ADMIN_ROLE_ID)
        admin_channel = self.bot.get_channel(config.CARRINHO_EM_ANDAMENTO_CHANNEL_ID)

        if admin_role and admin_channel:
            # Notificar na thread do carrinho
            await interaction.channel.send(f"{admin_role.mention}, o usuário {interaction.user.mention} clicou em 'Pegar Ticket' e precisa de ajuda com o carrinho para **{cart['product_name']}** (`{cart['quantity_or_value']}`).\n"
                                           f"**Status atual:** `{cart['cart_status']}`")
            
            # Notificar no canal de "Carrinhos em Andamento"
            embed_admin_notify = create_embed(
                f"🚨 Novo Ticket Aberto: {cart['product_name']}",
                f"**Usuário:** {interaction.user.mention} (ID: `{interaction.user.id}`)\n"
                f"**Produto:** {cart['product_name']} - `{cart['quantity_or_value']}`\n"
                f"**Link do Carrinho:** {interaction.channel.mention}\n"
                f"**Status do Carrinho:** `{cart['cart_status']}`\n\n"
                f"{admin_role.mention}, por favor, atenda este ticket!"
            )
            await admin_channel.send(embed=embed_admin_notify)

            await interaction.followup.send(embed=create_success_embed("Atendente Notificado!", "Um de nossos atendentes foi notificado e logo virá te ajudar."), ephemeral=True)
            logger.info(f"Ticket aberto para carrinho {cart['cart_id']} de {interaction.user.name} por clique no botão.")
        else:
            await interaction.followup.send(embed=create_error_embed("Não foi possível notificar um atendente. Tente novamente mais tarde ou contate um administrador diretamente."), ephemeral=True)
            logger.error(f"Erro: Cargo de ADMIN_ROLE_ID ({config.ADMIN_ROLE_ID}) ou canal CARRINHO_EM_ANDAMENTO_CHANNEL_ID ({config.CARRINHO_EM_ANDAMENTO_CHANNEL_ID}) não encontrado para notificar.")

class ConfirmGamepassView(discord.ui.View):
    def __init__(self, bot: commands.Bot, cart_id: int, gamepass_link: str):
        super().__init__(timeout=config.CART_EXPIRATION_MINUTES * 60)
        self.bot = bot
        self.db: Database = bot.database
        self.cart_id = cart_id
        self.gamepass_link = gamepass_link
        self.message = None

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(view=None)
            except discord.HTTPException:
                pass

    @discord.ui.button(label="✅ Já criei e desativei preços regionais", style=discord.ButtonStyle.green, custom_id="confirm_gamepass_yes")
    async def confirm_gamepass_yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        cart = await self.db.fetchrow("SELECT * FROM carts WHERE cart_id = $1", self.cart_id)

        if not cart or cart['user_id'] != interaction.user.id:
            await interaction.followup.send(embed=create_error_embed("Este carrinho não é válido ou não foi iniciado por você."), ephemeral=True)
            return
        
        # Atualizar o status do carrinho para aguardando entrega do admin
        await self.db.execute("UPDATE carts SET gamepass_link = $1, cart_status = $2, updated_at = NOW() WHERE cart_id = $3",
                              self.gamepass_link, 'awaiting_admin_delivery', self.cart_id)
        
        # Remover botões após a confirmação
        if self.message:
            try:
                await self.message.edit(view=None)
            except discord.HTTPException:
                pass

        # Notificar o usuário
        await interaction.followup.send(embed=create_success_embed("Confirmação Recebida!", "Obrigado por confirmar! Um atendente será notificado para verificar sua Gamepass e prosseguir com a entrega. Por favor, aguarde."), ephemeral=True)

        # Notificar o admin (na thread e no canal de carrinhos em andamento)
        admin_role = interaction.guild.get_role(config.ADMIN_ROLE_ID)
        admin_channel = self.bot.get_channel(config.CARRINHO_EM_ANDAMENTO_CHANNEL_ID)

        if admin_role and admin_channel:
            # Notificar na thread do carrinho
            await interaction.channel.send(f"{admin_role.mention}, o usuário {interaction.user.mention} confirmou a Gamepass e o carrinho está pronto para a verificação e entrega!\n"
                                           f"**Link da Gamepass:** {self.gamepass_link}")
            
            # Notificar no canal de "Carrinhos em Andamento"
            embed_admin_notify = create_embed(
                f"📦 Carrinho Pronto para Entrega: {cart['product_name']}",
                f"**Usuário:** {interaction.user.mention} (ID: `{interaction.user.id}`)\n"
                f"**Produto:** {cart['product_name']} - `{cart['quantity_or_value']}`\n"
                f"**Valor:** R${cart['price']:.2f}\n"
                f"**Nickname Roblox:** `{cart['roblox_nickname']}`\n"
                f"**Link da Gamepass:** [Clique aqui]({self.gamepass_link})\n"
                f"**Link do Carrinho:** {interaction.channel.mention}\n\n"
                f"{admin_role.mention}, por favor, verifique a Gamepass e realize a entrega!"
            )
            await admin_channel.send(embed=embed_admin_notify)
        else:
            logger.error(f"Erro: Cargo de ADMIN_ROLE_ID ({config.ADMIN_ROLE_ID}) ou canal CARRINHO_EM_ANDAMENTO_CHANNEL_ID ({config.CARRINHO_EM_ANDAMENTO_CHANNEL_ID}) não encontrado para notificar admin após confirmação de Gamepass.")
        
        logger.info(f"Carrinho {self.cart_id} de {interaction.user.name}: Usuário confirmou Gamepass. Status para 'awaiting_admin_delivery'.")


    @discord.ui.button(label="❌ Preciso de ajuda com a Gamepass", style=discord.ButtonStyle.red, custom_id="confirm_gamepass_no")
    async def confirm_gamepass_no(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        cart = await self.db.fetchrow("SELECT * FROM carts WHERE cart_id = $1", self.cart_id)

        if not cart or cart['user_id'] != interaction.user.id:
            await interaction.followup.send(embed=create_error_embed("Este carrinho não é válido ou não foi iniciado por você."), ephemeral=True)
            return

        # Notificar o admin que o usuário precisa de ajuda
        admin_role = interaction.guild.get_role(config.ADMIN_ROLE_ID)
        admin_channel = self.bot.get_channel(config.CARRINHO_EM_ANDAMENTO_CHANNEL_ID)

        if admin_role and admin_channel:
            await interaction.channel.send(f"{admin_role.mention}, o usuário {interaction.user.mention} precisa de ajuda para configurar a Gamepass para o carrinho **{cart['product_name']}** (`{cart['quantity_or_value']}`). Por favor, atenda-o.")
            
            embed_admin_notify = create_embed(
                f"⚠️ Ticket de Ajuda Gamepass: {cart['product_name']}",
                f"**Usuário:** {interaction.user.mention} (ID: `{interaction.user.id}`)\n"
                f"**Produto:** {cart['product_name']} - `{cart['quantity_or_value']}`\n"
                f"**Link do Carrinho:** {interaction.channel.mention}\n"
                f"**Status do Carrinho:** `{cart['cart_status']}`\n\n"
                f"{admin_role.mention}, o usuário está com dificuldades na Gamepass."
            )
            await admin_channel.send(embed=embed_admin_notify)

            await interaction.followup.send(embed=create_embed("Ajuda Solicitada!", "Um atendente foi notificado para te ajudar com a Gamepass. Por favor, aguarde."), ephemeral=True)
            logger.info(f"Carrinho {self.cart_id} de {interaction.user.name}: Usuário pediu ajuda com Gamepass.")
        else:
            await interaction.followup.send(embed=create_error_embed("Não foi possível notificar um atendente. Tente novamente mais tarde."), ephemeral=True)
            logger.error(f"Erro: Cargo de ADMIN_ROLE_ID ({config.ADMIN_ROLE_ID}) ou canal CARRINHO_EM_ANDAMENTO_CHANNEL_ID ({config.CARRINHO_EM_ANDAMENTO_CHANNEL_ID}) não encontrado para notificar admin sobre ajuda Gamepass.")
        
        # Opcional: Altere o status do carrinho para um estado de "ajuda" para que o admin saiba ao entrar
        await self.db.execute("UPDATE carts SET cart_status = $1, updated_at = NOW() WHERE cart_id = $2",
                              'awaiting_gamepass_help', self.cart_id)
        
        # Remova os botões após a seleção
        if self.message:
            try:
                await self.message.edit(view=None)
            except discord.HTTPException:
                pass


async def setup(bot):
    await bot.add_cog(CommonListeners(bot))
