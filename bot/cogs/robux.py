import discord
from discord.ext import commands
from discord import slash_command
import logging
import asyncio
import datetime # Para timestamp e expiração
import re # Para validar links
import base64 # Para decodificar o QR Code

import config
from utils.database import Database
from utils.embeds import create_embed, create_error_embed, create_success_embed
from cogs.common_listeners import CommonViews, ConfirmGamepassView # Importa views comuns

logger = logging.getLogger('discord_bot')

# QR Code Base64 (substitua pelo seu QR Code real em Base64)
# Use uma ferramenta online para converter sua imagem .png do QR Code em Base64 string
# Exemplo de como seria: 'iVBORw0KGgoAAAANSUhEUgAAAQAAAAE... (muitos caracteres)'
# Por enquanto, vou usar um placeholder. VOCÊ DEVE SUBSTITUIR ISSO.
PIX_QR_CODE_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=" # Placeholder: Imagem 1x1 pixel transparente
# A imagem do QR Code deve ser anexada ou convertida para Base64 e colocada aqui.
# Para evitar URLs muito longas, o ideal é que essa imagem seja servida de um CDN
# ou o bot faça upload para o Discord e use o link gerado.
# Por simplicidade inicial, usaremos um link direto ou base64 curto se possível.
# Para o seu caso, como você forneceu a imagem, o ideal seria o bot fazer o upload programaticamente
# para o Discord ou você hospedar essa imagem em algum lugar e usar a URL aqui.
# Para esta primeira versão, usaremos um placeholder. A exibição real do QR code via base64
# em embeds é limitada ou exige que o bot envie a imagem como arquivo.

# Como alternativa, podemos ter a URL do QR Code em algum lugar acessível se você preferir hospedar.
# Por agora, para simular a entrega, vamos enviar uma URL de uma imagem de QR Code genérica.
# Você deve SUBISTITUIR esta URL pela URL do seu QR Code ou pela lógica de upload da imagem.
PIX_QR_CODE_IMAGE_URL = "https://i.imgur.com/example_qrcode.png" # SUBSTITUA PELA URL DO SEU QR CODE REAL

class SelectRobuxQuantityView(discord.ui.View):
    def __init__(self, bot: commands.Bot, user: discord.Member, original_interaction: discord.Interaction):
        super().__init__(timeout=config.CART_EXPIRATION_MINUTES * 60)
        self.bot = bot
        self.user = user
        self.db: Database = bot.database
        self.original_interaction = original_interaction # Guarda a interação original para editar ou responder efemeramente
        self.add_item(self.create_select_menu())

    def create_select_menu(self):
        options = []
        for name, data in config.PRODUCTS.items():
            if data['type'] == 'robux':
                for qty_str, price in data['prices'].items():
                    options.append(
                        discord.SelectOption(
                            label=f"{data['emoji']} {qty_str} - R${price:.2f}",
                            value=f"{name}|{qty_str}|{price}" # Ex: "Robux|100 Robux|4.50"
                        )
                    )
                # Adicionar opções VIP se existirem
                if "vip_prices" in data:
                    for qty_str, price in data['vip_prices'].items():
                         options.append(
                            discord.SelectOption(
                                label=f"{data['emoji']} {qty_str} VIP - R${price:.2f}",
                                value=f"{name}|{qty_str}|{price}",
                                description="Preço especial para membros VIP!"
                            )
                        )
        
        # O limite do Discord para SelectOption é 25. Se tivermos mais, precisamos paginar ou agrupar.
        # Por simplicidade, assumimos que não excederemos 25 para Robux inicialmente.
        return discord.ui.Select(
            placeholder="Selecione a quantidade de Robux",
            options=options,
            custom_id="select_robux_quantity"
        )

    async def on_timeout(self):
        # A mensagem original deve ser editada para remover a view
        try:
            if self.original_interaction.response.is_done():
                await self.original_interaction.edit_original_response(view=None)
            else: # Se a resposta ainda não foi feita (ex: interação ephemera inicial)
                await self.original_interaction.edit_original_response(view=None)
        except discord.NotFound: # Mensagem já deletada
            pass
        except Exception as e:
            logger.error(f"Erro ao remover view em timeout de SelectRobuxQuantityView: {e}")

class RobloxNicknameModal(discord.ui.Modal):
    def __init__(self, bot: commands.Bot, selected_product_name: str, selected_quantity_value: str, selected_price: float, original_interaction: discord.Interaction):
        super().__init__(title="Seu Nickname no Roblox")
        self.bot = bot
        self.db: Database = bot.database
        self.selected_product_name = selected_product_name
        self.selected_quantity_value = selected_quantity_value
        self.selected_price = selected_price
        self.original_interaction = original_interaction

        self.add_item(discord.ui.InputText(label="Nickname Roblox", placeholder="Seu nome de usuário no Roblox", style=discord.InputTextStyle.short))

    async def callback(self, interaction: discord.Interaction):
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
            cart_id = await self.db.fetchrow(
                """
                INSERT INTO carts (user_id, product_type, product_name, quantity_or_value, price, roblox_nickname, cart_status)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING cart_id
                """,
                interaction.user.id, "Robux", self.selected_product_name, self.selected_quantity_value, 
                self.selected_price, roblox_nickname, 'awaiting_payment_method_selection'
            )
            cart_id = cart_id['cart_id']

            # Criar a thread privada
            compra_channel = self.bot.get_channel(config.COMPRE_AQUI_CHANNEL_ID)
            if not compra_channel:
                await interaction.response.send_message(embed=create_error_embed("Erro: Canal de compras não encontrado. Contate um admin."), ephemeral=True)
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
            
            # Atualizar o carrinho com o thread_id
            await self.db.execute("UPDATE carts SET thread_id = $1, cart_status = $2, updated_at = NOW() WHERE cart_id = $3",
                                  new_thread.id, 'awaiting_payment_method_selection', cart_id)
            
            # Editar a mensagem original do comando para redirecionar
            try:
                if self.original_interaction.response.is_done():
                    await self.original_interaction.edit_original_response(
                        embed=create_embed(
                            "🛒 Seu Carrinho Foi Criado!",
                            f"Seu carrinho para **{self.selected_quantity_value}** de {self.selected_product_name} foi criado! "
                            f"Por favor, continue a conversa em {new_thread.mention}."
                        ),
                        view=None # Remove os botões da mensagem original
                    )
                else:
                     await self.original_interaction.response.edit_message(
                        embed=create_embed(
                            "🛒 Seu Carrinho Foi Criado!",
                            f"Seu carrinho para **{self.selected_quantity_value}** de {self.selected_product_name} foi criado! "
                            f"Por favor, continue a conversa em {new_thread.mention}."
                        ),
                        view=None
                    )
            except discord.NotFound:
                logger.warning("Mensagem original da interação não encontrada ao tentar editar.")
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
            # Adicionar botões de método de pagamento
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
            
            logger.info(f"Carrinho {cart_id} criado para {interaction.user.name} ({self.selected_quantity_value} de {self.selected_product_name}). Thread: {new_thread.id}")

        except Exception as e:
            logger.error(f"Erro ao criar carrinho ou thread para {interaction.user.name}: {e}", exc_info=True)
            await interaction.response.send_message(embed=create_error_embed("Ocorreu um erro ao criar seu carrinho. Por favor, tente novamente ou contate um admin."), ephemeral=True)


class PaymentMethodView(CommonViews): # Herda de CommonViews para incluir o botão "Pegar Ticket" e timeout
    def __init__(self, bot: commands.Bot, cart_id: int):
        # Passa o user_id para CommonViews
        # cart_id é necessário para buscar o user_id e outros detalhes do carrinho
        self.bot = bot
        self.db: Database = bot.database
        self.cart_id = cart_id
        # Recuperar user_id para a CommonViews
        asyncio.create_task(self._set_user_id_from_cart()) # Executa de forma assíncrona

    async def _set_user_id_from_cart(self):
        cart = await self.db.fetchrow("SELECT user_id FROM carts WHERE cart_id = $1", self.cart_id)
        if cart:
            super().__init__(self.bot, cart['user_id']) # Inicializa CommonViews com o user_id
        else:
            logger.error(f"Carrinho {self.cart_id} não encontrado ao inicializar PaymentMethodView.")
            super().__init__(self.bot, 0) # Inicializa com user_id 0 para evitar erro, mas é um estado de erro

    @discord.ui.button(label="💳 PIX", style=discord.ButtonStyle.green, custom_id="payment_method_pix")
    async def pix_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer() # Acknowledge the interaction

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
            f"**Nome:** `{config.PIX_RECEIVER_NAME}`\n\n" # Será adicionado no config.py
            f"Escaneie o QR Code abaixo ou utilize a chave PIX Copia e Cola. "
            f"**Após o pagamento, envie o comprovante neste chat para verificação.**"
        )
        # pix_embed.set_image(url=PIX_QR_CODE_IMAGE_URL) # Usar URL da imagem do QR Code
        # Como o Discord não suporta base64 diretamente em embeds para imagem,
        # e para evitar ter que lidar com uploads de arquivo por enquanto,
        # vou apenas exibir a chave e o nome. Se o QR code for essencial e não houver URL,
        # teremos que enviar a imagem do QR Code como anexo separado.
        # Por enquanto, focaremos na chave PIX e nome.

        # Para incluir o QR Code, você pode adicionar um campo com uma URL
        # ou, se o QR Code for uma imagem que você mesmo hospeda:
        # pix_embed.set_image(url="URL_DO_SEU_QR_CODE_HOSPEDADO")
        # Ou, se for enviar como anexo:
        # await interaction.channel.send(file=discord.File("caminho/para/seu/qrcode.png"))

        await interaction.followup.send(embed=pix_embed)
        # Remove os botões de método de pagamento após a seleção
        await interaction.message.edit(view=CommonViews(self.bot, interaction.user.id)) # Mantém apenas o botão "Pegar Ticket"

        logger.info(f"Carrinho {self.cart_id} de {interaction.user.name}: Selecionado PIX manual. Aguardando comprovante.")

    @discord.ui.button(label="📄 Boleto (Em Breve)", style=discord.ButtonStyle.grey, disabled=True)
    async def boleto_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(embed=create_embed("Boleto", "O método de pagamento por Boleto estará disponível em breve!"), ephemeral=True)

    @discord.ui.button(label="💳 Cartão de Crédito (Em Breve)", style=discord.ButtonStyle.grey, disabled=True)
    async def credit_card_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(embed=create_embed("Cartão de Crédito", "O método de pagamento por Cartão de Crédito estará disponível em breve!"), ephemeral=True)


class Robux(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db: Database = bot.database

    @slash_command(name="robux", description="Inicia o processo de compra de Robux.", guild_ids=[config.GUILD_ID])
    async def robux_command(self, ctx: discord.ApplicationContext):
        # Verifica se o comando foi usado no canal correto
        if ctx.channel.id != config.COMPRE_AQUI_CHANNEL_ID:
            await ctx.respond(embed=create_error_embed(f"Este comando só pode ser usado no canal {self.bot.get_channel(config.COMPRE_AQUI_CHANNEL_ID).mention}."), ephemeral=True)
            return

        # Loga a ação privada
        private_log_channel = self.bot.get_channel(config.PRIVATE_ACTIONS_LOG_CHANNEL_ID)
        if private_log_channel:
            log_embed = create_embed(
                "👁️ Ação Privada Registrada",
                f"**Usuário:** {ctx.author.mention} (ID: `{ctx.author.id}`)\n"
                f"**Ação:** Iniciou o comando `/robux`."
            )
            await private_log_channel.send(embed=log_embed)
            logger.info(f"Usuário {ctx.author.name} ({ctx.author.id}) iniciou o comando /robux.")

        # Verificar se o usuário já tem um carrinho em andamento ATIVO (não expirado, completo ou cancelado)
        # Consideramos que múltiplos carrinhos são permitidos, então esta verificação é mais sobre um "carrinho principal"
        # Ou para redirecionar para uma thread existente se o usuário tentar criar outra no mesmo canal
        active_carts = await self.db.fetch(
            "SELECT cart_id, thread_id FROM carts WHERE user_id = $1 AND cart_status NOT IN ('completed', 'cancelled', 'expired', 'closed_by_archive')",
            ctx.author.id
        )

        if active_carts:
            # Se já tem carrinhos ativos, lista e pergunta se quer iniciar novo
            # Por simplicidade da "resposta curta", vamos direto para "Deseja comprar mais?"
            # ou lista os carrinhos ativos e pergunta qual quer acessar/se quer um novo.
            # Baseado na sua resposta de "Múltiplos carrinhos podem ser gerados simultaneamente sem um afetar o outro",
            # não precisamos de um botão "acessar carrinho", apenas "iniciar nova compra".

            embed_existing = create_embed(
                "🛒 Você já tem um ou mais carrinhos em andamento!",
                "Deseja iniciar uma nova compra de Robux?"
            )
            class NewPurchaseView(discord.ui.View):
                def __init__(self, bot_ref: commands.Bot, user: discord.Member, original_ctx: discord.ApplicationContext):
                    super().__init__(timeout=60) # Timeout curto para esta view de decisão
                    self.bot_ref = bot_ref
                    self.user = user
                    self.original_ctx = original_ctx

                @discord.ui.button(label="Iniciar Nova Compra", style=discord.ButtonStyle.green)
                async def start_new_purchase(self, interaction: discord.Interaction, button: discord.ui.Button):
                    if interaction.user.id != self.user.id:
                        await interaction.response.send_message(embed=create_error_embed("Este botão não é para você."), ephemeral=True)
                        return
                    await interaction.response.defer(ephemeral=True)
                    await self.original_ctx.edit_original_response(view=None) # Remove os botões

                    # Iniciar o fluxo principal para nova compra
                    await self.bot_ref.get_cog("Robux")._start_robux_purchase_flow(interaction)

                @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.red)
                async def cancel_new_purchase(self, interaction: discord.Interaction, button: discord.ui.Button):
                    if interaction.user.id != self.user.id:
                        await interaction.response.send_message(embed=create_error_embed("Este botão não é para você."), ephemeral=True)
                        return
                    await interaction.response.send_message(embed=create_embed("Compra Cancelada", "Você pode iniciar uma nova compra a qualquer momento."), ephemeral=True)
                    await self.original_ctx.edit_original_response(view=None) # Remove os botões
                    self.stop()
            
            # Enviar a mensagem para iniciar nova compra ou não
            await ctx.respond(embed=embed_existing, view=NewPurchaseView(self.bot, ctx.author, ctx), ephemeral=True)
            return

        # Se não houver carrinho ativo, inicia o fluxo de seleção de quantidade
        await self._start_robux_purchase_flow(ctx)

    async def _start_robux_purchase_flow(self, interaction: discord.Interaction):
        """Inicia a seleção de quantidade de Robux."""
        embed = create_embed(
            "💎 Central de Robux",
            "Selecione a quantidade de Robux que deseja comprar:"
        )
        # Crie a view com o select menu
        view = SelectRobuxQuantityView(self.bot, interaction.user, interaction)
        
        # Envie a mensagem original (ou edite a resposta se já deferida)
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @commands.Cog.listener("on_interaction")
    async def handle_robux_selection(self, interaction: discord.Interaction):
        """Lida com a seleção de quantidade de Robux pelo SelectMenu."""
        if interaction.type == discord.InteractionType.component and interaction.data['custom_id'] == "select_robux_quantity":
            await interaction.response.defer(ephemeral=True) # Acknowledge the interaction
            
            selected_value = interaction.data['values'][0] # Pega o valor selecionado
            product_name, quantity_value_str, price_str = selected_value.split('|')
            price = float(price_str)

            # Remover a view da mensagem original para não permitir mais seleções
            try:
                # Tenta editar a mensagem que contém o select menu (a mensagem ephemera)
                await interaction.message.edit(view=None)
            except Exception as e:
                logger.error(f"Erro ao remover view da seleção de Robux: {e}")

            # Abrir o modal para pedir o nickname Roblox
            modal = RobloxNicknameModal(self.bot, product_name, quantity_value_str, price, interaction)
            await interaction.followup.send_modal(modal)

async def setup(bot):
    await bot.add_cog(Robux(bot))
