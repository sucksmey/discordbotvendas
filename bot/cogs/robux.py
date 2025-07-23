import discord
from discord.ext import commands
from discord import slash_command # Manter para outros comandos se necessário, mas não para /robux
import logging
import asyncio
import datetime
import re
import base64

import config
from utils.database import Database
from utils.embeds import create_embed, create_error_embed, create_success_embed
from cogs.common_listeners import CommonViews, ConfirmGamepassView

logger = logging.getLogger('discord_bot')

# --- CONFIGURAÇÃO DO QR CODE E INFORMAÇÕES PIX ---
# SUBSTITUA esta URL pela URL do seu QR Code REAL, hospedado em algum lugar (ex: Imgur).
# Se você tiver a imagem em arquivo e quiser que o bot a envie, a lógica será diferente (File upload).
# Por enquanto, usaremos uma URL de placeholder genérica para simular.
PIX_QR_CODE_IMAGE_URL = "https://i.imgur.com/example_qrcode.png" # SUBSTITUA PELA URL DO SEU QR CODE REAL

class RobuxPurchaseInitialView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None) # View persistente
        self.bot = bot
        self.db: Database = bot.database

    @discord.ui.button(label="Comprar Robux", style=discord.ButtonStyle.green, custom_id="start_robux_purchase_button")
    async def start_robux_purchase_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Botão inicial para começar a compra de Robux."""
        await interaction.response.defer(ephemeral=True) # Resposta ephemera, visível só para o usuário

        # Loga a ação privada
        private_log_channel = self.bot.get_channel(config.PRIVATE_ACTIONS_LOG_CHANNEL_ID)
        if private_log_channel:
            log_embed = create_embed(
                "👁️ Ação Privada Registrada",
                f"**Usuário:** {interaction.user.mention} (ID: `{interaction.user.id}`)\n"
                f"**Ação:** Clicou no botão 'Comprar Robux'."
            )
            await private_log_channel.send(embed=log_embed)
            logger.info(f"Usuário {interaction.user.name} ({interaction.user.id}) clicou no botão 'Comprar Robux'.")

        # Verificar se o usuário já tem carrinhos ativos (múltiplos são permitidos, mas avisamos)
        active_carts = await self.db.fetch(
            "SELECT cart_id, thread_id, product_name, quantity_or_value FROM carts WHERE user_id = $1 AND cart_status NOT IN ('completed', 'cancelled', 'expired', 'closed_by_archive')",
            interaction.user.id
        )

        if active_carts:
            # Se já tem carrinhos ativos, lista e pergunta se quer iniciar novo
            embed_existing = create_embed(
                "🛒 Você já tem compras em andamento!",
                "**Carrinhos Ativos:**\n" + 
                "\n".join([f"- {cart['quantity_or_value']} de {cart['product_name']} [Link da Conversa](<#{cart['thread_id']}>)" for cart in active_carts]) +
                "\n\nDeseja iniciar uma nova compra de Robux?"
            )
            class NewPurchaseDecisionView(discord.ui.View):
                def __init__(self, bot_ref: commands.Bot, user: discord.Member, original_interaction: discord.Interaction):
                    super().__init__(timeout=60) # Timeout curto para esta view de decisão
                    self.bot_ref = bot_ref
                    self.user = user
                    self.original_interaction = original_interaction

                async def on_timeout(self):
                    # Tenta remover os botões se a interação expirar
                    try:
                        await self.original_interaction.edit_original_response(view=None)
                    except discord.NotFound:
                        pass # Mensagem já deletada ou não encontrada

                @discord.ui.button(label="Iniciar Nova Compra", style=discord.ButtonStyle.green)
                async def start_new_purchase(self, interaction_btn: discord.Interaction, button: discord.ui.Button):
                    if interaction_btn.user.id != self.user.id:
                        await interaction_btn.response.send_message(embed=create_error_embed("Este botão não é para você."), ephemeral=True)
                        return
                    await interaction_btn.response.defer(ephemeral=True)
                    await self.original_interaction.edit_original_response(view=None) # Remove os botões da mensagem de decisão

                    # Iniciar o fluxo principal para nova compra
                    await self.bot_ref.get_cog("Robux")._start_robux_purchase_flow(interaction_btn)

                @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.red)
                async def cancel_new_purchase(self, interaction_btn: discord.Interaction, button: discord.ui.Button):
                    if interaction_btn.user.id != self.user.id:
                        await interaction_btn.response.send_message(embed=create_error_embed("Este botão não é para você."), ephemeral=True)
                        return
                    await interaction_btn.response.send_message(embed=create_embed("Compra Cancelada", "Você pode iniciar uma nova compra a qualquer momento."), ephemeral=True)
                    await self.original_interaction.edit_original_response(view=None) # Remove os botões
                    self.stop()
            
            # Enviar a mensagem com a pergunta para iniciar nova compra
            await interaction.followup.send(embed=embed_existing, view=NewPurchaseDecisionView(self.bot, interaction.user, interaction), ephemeral=True)
            return

        # Se não houver carrinho ativo, inicia o fluxo de seleção de quantidade
        await self._start_robux_purchase_flow(interaction)

class SelectRobuxQuantityView(discord.ui.View):
    def __init__(self, bot: commands.Bot, user: discord.Member, original_interaction: discord.Interaction):
        super().__init__(timeout=config.CART_EXPIRATION_MINUTES * 60)
        self.bot = bot
        self.user = user
        self.db: Database = bot.database
        self.original_interaction = original_interaction # Guarda a interação original para editar ou responder efemeramente
        self.message = None # Para armazenar a mensagem com a view do select
        self.add_item(self.create_select_menu())

    def create_select_menu(self):
        options = []
        robux_data = config.PRODUCTS.get("Robux")
        if robux_data:
            for qty_str, price in robux_data['prices'].items():
                options.append(
                    discord.SelectOption(
                        label=f"{robux_data['emoji']} {qty_str} - R${price:.2f}",
                        value=f"Robux|{qty_str}|{price}" # Ex: "Robux|100 Robux|4.50"
                    )
                )
            if "vip_prices" in robux_data:
                for qty_str, price in robux_data['vip_prices'].items():
                     options.append(
                        discord.SelectOption(
                            label=f"{robux_data['emoji']} {qty_str} VIP - R${price:.2f}",
                            value=f"Robux|{qty_str}|{price}",
                            description="Preço especial para membros VIP!"
                        )
                    )
        
        return discord.ui.Select(
            placeholder="Selecione a quantidade de Robux",
            options=options[:25], # Limita a 25 opções, limite do Discord
            custom_id="select_robux_quantity"
        )

    async def on_timeout(self):
        # A mensagem original deve ser editada para remover a view
        try:
            if self.message:
                await self.message.edit(view=None)
            elif self.original_interaction.response.is_done(): # Fallback para a interação original
                await self.original_interaction.edit_original_response(view=None)
        except discord.NotFound:
            pass
        except Exception as e:
            logger.error(f"Erro ao remover view em timeout de SelectRobuxQuantityView: {e}")

class RobloxNicknameModal(discord.ui.Modal):
    def __init__(self, bot: commands.Bot, selected_product_name: str, selected_quantity_value: str, selected_price: float, original_interaction_message: discord.Message):
        super().__init__(title="Seu Nickname no Roblox")
        self.bot = bot
        self.db: Database = bot.db # Acessa o atributo db do bot
        self.selected_product_name = selected_product_name
        self.selected_quantity_value = selected_quantity_value
        self.selected_price = selected_price
        self.original_interaction_message = original_interaction_message # Mensagem que contém a Select View
        
        self.add_item(discord.ui.InputText(label="Nickname Roblox", placeholder="Seu nome de usuário no Roblox", style=discord.InputTextStyle.short, required=True))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True) # Deferir para não expirar

        roblox_nickname = self.children[0].value.strip()

        # Primeiro, garantir que o usuário existe no DB
        user_data = await self.db.fetchrow("SELECT * FROM users WHERE user_id = $1", interaction.user.id)
        if not user_data:
            await self.db.execute(
                "INSERT INTO users (user_id, username, discriminator) VALUES ($1, $2, $3)",
                interaction.user.id, interaction.user.name, interaction.user.discriminator
            )
            logger.info(f"Usuário {interaction.user.name} ({interaction.user.id}) adicionado ao DB.")

        # Criar o carrinho no DB
        try:
            cart_id_row = await self.db.fetchrow(
                """
                INSERT INTO carts (user_id, product_type, product_name, quantity_or_value, price, roblox_nickname, cart_status)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING cart_id
                """,
                interaction.user.id, "Robux", self.selected_product_name, self.selected_quantity_value, 
                self.selected_price, roblox_nickname, 'initiated' # Status inicial do carrinho
            )
            cart_id = cart_id_row['cart_id']

            # Criar a thread privada
            compra_channel = self.bot.get_channel(config.COMPRE_AQUI_CHANNEL_ID)
            if not compra_channel:
                await interaction.followup.send(embed=create_error_embed("Erro: Canal de compras não encontrado. Contate um admin."), ephemeral=True)
                logger.error(f"Canal COMPRE_AQUI_CHANNEL_ID ({config.COMPRE_AQUI_CHANNEL_ID}) não encontrado.")
                return

            thread_name = f"carrinho-{interaction.user.name}-{datetime.datetime.now().strftime('%H%M%S')}"
            new_thread = await compra_channel.create_thread(
                name=thread_name,
                type=discord.ChannelType.private_thread,
                auto_archive_duration=1440, # 24 horas de inatividade
                invitable=True
            )
            await new_thread.add_user(interaction.user) # Adiciona o usuário

            # Adiciona admins à thread
            guild = self.bot.get_guild(config.GUILD_ID)
            admin_role = guild.get_role(config.ADMIN_ROLE_ID)
            if admin_role:
                for member in admin_role.members:
                    try:
                        await new_thread.add_user(member)
                    except discord.Forbidden:
                        logger.warning(f"Não foi possível adicionar admin {member.name} à thread {new_thread.id}. Permissão negada.")
            
            # Atualizar o carrinho com o thread_id e o status para aguardando método de pagamento
            await self.db.execute("UPDATE carts SET thread_id = $1, cart_status = $2, updated_at = NOW() WHERE cart_id = $3",
                                  new_thread.id, 'awaiting_payment_method_selection', cart_id)
            
            # Editar a mensagem original da seleção de Robux para redirecionar
            try:
                if self.original_interaction_message:
                    await self.original_interaction_message.edit(
                        embed=create_embed(
                            "🛒 Seu Carrinho Foi Criado!",
                            f"Seu carrinho para **{self.selected_quantity_value}** de {self.selected_product_name} foi criado! "
                            f"Por favor, continue a conversa em {new_thread.mention}."
                        ),
                        view=None # Remove os botões da mensagem original de seleção
                    )
            except Exception as e:
                logger.error(f"Erro ao editar mensagem original após criar carrinho: {e}")

            # Mensagem inicial na thread do carrinho
            initial_thread_embed = create_embed(
                f"🎉 Bem-vindo(a) ao seu Carrinho para {self.selected_product_name}!",
                f"Olá {interaction.user.mention}!\n\n"
                f"Você selecionou **{self.selected_quantity_value}** de {self.selected_product_name} por **R${self.selected_price:.2f}**.\n"
                f"Seu nickname no Roblox é: `{roblox_nickname}`\n\n"
                f"Por favor, selecione seu método de pagamento abaixo. Se precisar de ajuda, clique em 'Pegar Ticket'."
            )
            # Adicionar botões de método de pagamento (herda de CommonViews para o botão Pegar Ticket)
            payment_options_view = PaymentMethodView(self.bot, cart_id)
            await new_thread.send(embed=initial_thread_embed, view=payment_options_view)
            
            # Logar no canal público de logs de carrinho em andamento
            carrinho_em_andamento_channel = self.bot.get_channel(config.CARRINHO_EM_ANDAMENTO_CHANNEL_ID)
            if carrinho_em_andamento_channel:
                log_embed = create_embed(
                    f"🛒 Carrinho de Robux Iniciado",
                    f"**Usuário:** {interaction.user.mention} (ID: `{interaction.user.id}`)\n"
                    f"**Produto:** {self.selected_quantity_value} {self.selected_product_name}\n"
                    f"**Valor:** R${self.selected_price:.2f}\n"
                    f"**Nickname Roblox:** `{roblox_nickname}`\n"
                    f"**Link do Carrinho:** {new_thread.mention}\n"
                    f"**Status:** Aguardando seleção de método de pagamento."
                )
                await carrinho_em_andamento_channel.send(embed=log_embed)
            
            await interaction.followup.send(embed=create_success_embed("Carrinho Criado!", f"Continue sua compra em {new_thread.mention}."), ephemeral=True)
            logger.info(f"Carrinho {cart_id} criado para {interaction.user.name} ({self.selected_quantity_value} de {self.selected_product_name}). Thread: {new_thread.id}")

        except Exception as e:
            logger.error(f"Erro ao criar carrinho ou thread para {interaction.user.name}: {e}", exc_info=True)
            await interaction.followup.send(embed=create_error_embed("Ocorreu um erro ao criar seu carrinho. Por favor, tente novamente ou contate um admin."), ephemeral=True)


class PaymentMethodView(CommonViews):
    def __init__(self, bot: commands.Bot, cart_id: int):
        self.bot = bot
        self.db: Database = bot.db # Acessa o atributo db do bot
        self.cart_id = cart_id
        self._user_id = None # Para ser preenchido async
        
        # O self._set_user_id_from_cart precisa ser chamado e awaited para inicializar CommonViews corretamente
        # Como não podemos usar await no __init__ diretamente, faremos isso em um setup_hook_for_view
        super().__init__(bot, 0) # Inicializa CommonViews temporariamente com user_id 0
        
        # Adiciona os botões de método de pagamento
        self.add_item(discord.ui.Button(label="💳 PIX", style=discord.ButtonStyle.green, custom_id="payment_method_pix"))
        self.add_item(discord.ui.Button(label="📄 Boleto (Em Breve)", style=discord.ButtonStyle.grey, custom_id="payment_method_boleto", disabled=True))
        self.add_item(discord.ui.Button(label="💳 Cartão de Crédito (Em Breve)", style=discord.ButtonStyle.grey, custom_id="payment_method_credit_card", disabled=True))


    async def on_timeout(self):
        # A lógica de timeout da CommonViews já lida com o user_id e atualização do carrinho
        await super().on_timeout()
        if self.message:
            try:
                await self.message.edit(view=None)
            except discord.HTTPException:
                pass


    @discord.ui.button(label="💳 PIX", style=discord.ButtonStyle.green, custom_id="payment_method_pix")
    async def pix_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer() # Acknowledge the interaction
        
        # Revalidar o carrinho e o usuário para segurança
        cart = await self.db.fetchrow("SELECT * FROM carts WHERE cart_id = $1 AND user_id = $2", 
                                      self.cart_id, interaction.user.id)
        
        if not cart:
            await interaction.followup.send(embed=create_error_embed("Este carrinho não é válido ou não foi iniciado por você."), ephemeral=True)
            return
        
        # Atualiza status do carrinho
        await self.db.execute("UPDATE carts SET cart_status = $1, updated_at = NOW() WHERE cart_id = $2",
                              'awaiting_manual_pix_payment', self.cart_id)

        # Exibir informações do PIX manual (QR Code e chave)
        pix_embed = create_embed(
            "💰 Pagamento via PIX",
            f"Por favor, faça um PIX no valor de **R${cart['price']:.2f}** para:\n"
            f"**Chave PIX:** `{config.PIX_KEY_MANUAL}`\n"
            f"**Nome:** `{config.PIX_RECEIVER_NAME}`\n\n"
            f"Escaneie o QR Code abaixo ou utilize a chave PIX Copia e Cola. "
            f"**Após o pagamento, envie o comprovante neste chat para verificação.**"
        )
        
        # Anexa o QR Code. Isso requer que o arquivo do QR Code esteja acessível pelo bot.
        # Você deve ter o arquivo do QR Code (ex: "qrcode_pix.png") na pasta "bot/assets/"
        # e configurar para o Railway também ter acesso a ele.
        # Para fins de deploy no Railway, o ideal é que esse arquivo esteja no seu repo.
        qr_file_path = "assets/qrcode_pix.png" # Crie uma pasta 'assets' e coloque o QR Code lá

        try:
            # Envia a imagem do QR Code como um arquivo anexo
            pix_embed.set_image(url="attachment://qrcode_pix.png") # Define a imagem do embed para o anexo
            await interaction.followup.send(embed=pix_embed, file=discord.File(qr_file_path, filename="qrcode_pix.png"))
        except FileNotFoundError:
            logger.error(f"Arquivo QR Code não encontrado em {qr_file_path}. Enviando apenas texto.")
            await interaction.followup.send(embed=pix_embed)
        except Exception as e:
            logger.error(f"Erro ao enviar QR Code: {e}", exc_info=True)
            await interaction.followup.send(embed=pix_embed)


        # Remove os botões de método de pagamento após a seleção, mantendo apenas o "Pegar Ticket"
        # Usamos uma instância de CommonViews para manter apenas o botão "Pegar Ticket"
        # Garante que a mensagem que contém a view seja editada.
        if interaction.message:
            await interaction.message.edit(view=CommonViews(self.bot, interaction.user.id))

        logger.info(f"Carrinho {self.cart_id} de {interaction.user.name}: Selecionado PIX manual. Aguardando comprovante.")

    # Os botões de Boleto e Cartão de Crédito foram movidos para dentro da classe PaymentMethodView,
    # para que possam ser usados em discord.ui.Button
    @discord.ui.button(label="📄 Boleto (Em Breve)", style=discord.ButtonStyle.grey, custom_id="payment_method_boleto", disabled=True)
    async def boleto_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(embed=create_embed("Boleto", "O método de pagamento por Boleto estará disponível em breve!"), ephemeral=True)

    @discord.ui.button(label="💳 Cartão de Crédito (Em Breve)", style=discord.ButtonStyle.grey, custom_id="payment_method_credit_card", disabled=True)
    async def credit_card_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(embed=create_embed("Cartão de Crédito", "O método de pagamento por Cartão de Crédito estará disponível em breve!"), ephemeral=True)

class Robux(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db: Database = bot.db # Acessa o atributo db do bot

    # Removemos o @slash_command("robux") daqui. O fluxo será iniciado por um botão.
    # Adicionamos um comando de admin para enviar a mensagem inicial de Robux.
    @slash_command(name="setup_robux_button", description="Envia a mensagem com o botão 'Comprar Robux'.", guild_ids=[config.GUILD_ID])
    @commands.has_role(config.ADMIN_ROLE_ID)
    async def setup_robux_button(self, ctx: discord.ApplicationContext):
        # Verifica se o usuário tem o cargo de administrador
        if not discord.utils.get(ctx.author.roles, id=config.ADMIN_ROLE_ID):
            await ctx.respond(embed=create_error_embed("Você não tem permissão para usar este comando."), ephemeral=True)
            return

        embed = create_embed(
            "💎 Central de Robux",
            "Clique no botão abaixo para iniciar sua compra de Robux."
        )
        view = RobuxPurchaseInitialView(self.bot)
        
        message = await ctx.channel.send(embed=embed, view=view)
        view.message = message # Associa a mensagem à view para persistência
        await ctx.respond(embed=create_success_embed("Mensagem de Robux configurada!", "O botão 'Comprar Robux' foi enviado."), ephemeral=True)
        logger.info(f"Comando /setup_robux_button usado por {ctx.author.name} ({ctx.author.id}) no canal {ctx.channel.name} ({ctx.channel.id}).")

    async def _start_robux_purchase_flow(self, interaction: discord.Interaction):
        """Inicia a seleção de quantidade de Robux."""
        embed = create_embed(
            "💎 Central de Robux",
            "Selecione a quantidade de Robux que deseja comprar:"
        )
        view = SelectRobuxQuantityView(self.bot, interaction.user, interaction)
        
        # Envia a mensagem ephemera com o select menu
        # Se a interação já foi respondida (deferida), use followup.send
        if interaction.response.is_done():
            response_message = await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        else: # Caso a interação ainda não tenha sido respondida
            response_message = await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
        # Atribui a mensagem para a view para que ela possa ser editada/removida no timeout
        view.message = response_message


    @commands.Cog.listener("on_interaction")
    async def handle_robux_selection(self, interaction: discord.Interaction):
        """Lida com a seleção de quantidade de Robux pelo SelectMenu."""
        if interaction.type == discord.InteractionType.component and interaction.data['custom_id'] == "select_robux_quantity":
            # Deferir a resposta para ter tempo de processar
            await interaction.response.defer(ephemeral=True) 
            
            selected_value = interaction.data['values'][0] # Pega o valor selecionado
            product_name, quantity_value_str, price_str = selected_value.split('|')
            price = float(price_str)

            # Remover a view da mensagem original (ephemera) para não permitir mais seleções
            try:
                await interaction.message.edit(view=None) # Edita a mensagem da qual a interação veio
            except Exception as e:
                logger.error(f"Erro ao remover view da seleção de Robux: {e}", exc_info=True)

            # Abrir o modal para pedir o nickname Roblox
            modal = RobloxNicknameModal(self.bot, product_name, quantity_value_str, price, interaction.message)
            # Envia o modal como uma followup da interação original.
            # interaction.response.send_modal não funciona após deferimento ephemera,
            # é preciso usar interaction.followup.send_modal
            await interaction.followup.send_modal(modal)

async def setup(bot):
    await bot.add_cog(Robux(bot))
    # Adicionar a view persistente para o botão de compra de Robux
    bot.add_view(RobuxPurchaseInitialView(bot))
