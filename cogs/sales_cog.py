# cogs/sales_cog.py
import discord
from discord.ext import commands
from discord.ui import View, Button, button
import asyncio
import re

import config

# --- Funções de Cálculo ---
def parse_robux_amount(text: str) -> int:
    """Extrai um número de uma string, lidando com 'k'."""
    text = text.lower().replace('robux', '').strip()
    if 'k' in text:
        return int(float(text.replace('k', '')) * 1000)
    return int(re.sub(r'[^0-9]', '', text))

# --- Views (Botões) ---
class GamepassCreationView(View):
    def __init__(self, bot, thread, required_value):
        super().__init__(timeout=None)
        self.bot = bot
        self.thread = thread
        self.required_value = required_value

    @button(label="Sim, sei criar", style=discord.ButtonStyle.success, custom_id="knows_gamepass")
    async def knows_callback(self, button, interaction):
        await interaction.response.defer()
        embed = discord.Embed(
            title="Ótimo!",
            description=f"Por favor, crie a Gamepass com o valor exato de **{self.required_value} Robux** para receber a quantia correta.\n\n"
                        f"Após criar, envie o link ou o ID da sua Gamepass aqui no chat.",
            color=config.EMBED_COLOR
        )
        await self.thread.send(embed=embed)
        self.stop()

    @button(label="Não, preciso de ajuda", style=discord.ButtonStyle.danger, custom_id="needs_help_gamepass")
    async def needs_help_callback(self, button, interaction):
        await interaction.response.defer()
        embed = discord.Embed(
            title="Sem problemas! Siga o tutorial",
            description=f"Para criar sua Gamepass, assista ao vídeo abaixo. É bem simples!\n\n"
                        f"Você deve criar a Gamepass com o valor exato de **{self.required_value} Robux**.\n\n"
                        f"**IMPORTANTE:** Lembre-se de **DESATIVAR OS PREÇOS REGIONAIS** nas configurações da sua Gamepass para que a entrega funcione!",
            color=config.EMBED_COLOR
        )
        await self.thread.send(embed=embed)
        await self.thread.send(config.TUTORIAL_VIDEO_URL)
        await self.thread.send("Após criar, envie o link ou o ID da sua Gamepass aqui no chat.")
        self.stop()

class SalesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="iniciarvendas")
    @commands.has_any_role(*config.ATTENDANT_ROLE_IDS)
    async def start_sales(self, ctx):
        """Cria o painel inicial de vendas."""
        view = View(timeout=None)
        view.add_item(Button(label="Comprar Robux", style=discord.ButtonStyle.success, custom_id="buy_robux"))
        view.add_item(Button(label="Ver Tabela de Preços", style=discord.ButtonStyle.secondary, custom_id="show_prices"))

        embed = discord.Embed(
            title="🛒 Central de Pedidos da Legacy",
            description="Nossa loja oferece os melhores produtos com os melhores preços do Brasil!\n\n"
                        "**Produtos:**\n"
                        "Robux - Robux direto na sua conta, sempre cobrindo todas as taxas do Roblox!\n\n"
                        "**Como Comprar:**\n"
                        "Clique no botão **Comprar Robux** para iniciar o processo de compra!",
            color=config.EMBED_COLOR
        )
        embed.set_image(url="attachment://welcome.png") # Exemplo
        
        purchase_channel = self.bot.get_channel(config.PURCHASE_CHANNEL_ID)
        if purchase_channel:
            await purchase_channel.send(
                file=discord.File("assets/welcome.png"),
                embed=embed,
                view=view
            )
        await ctx.send("Painel de vendas criado!", ephemeral=True)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.data and interaction.data.get("custom_id") == "buy_robux":
            await self.start_robux_purchase(interaction)

    async def start_robux_purchase(self, interaction: discord.Interaction):
        await interaction.response.defer()
        channel = interaction.channel
        user = interaction.user
        
        thread = await channel.create_thread(
            name=f"🛒-{user.display_name}",
            type=discord.ChannelType.private_thread
        )
        await thread.add_user(user)

        # Mensagem de boas-vindas na thread
        welcome_embed = discord.Embed(
            title=f"👋 Olá, {user.display_name}!",
            description="Bem-vindo(a) ao seu carrinho de compras. Estou aqui para te ajudar a adquirir seus Robux de forma rápida e segura!\n\nPara começar, por favor, me informe seu **nickname no Roblox**.",
            color=config.EMBED_COLOR
        )
        await thread.send(embed=welcome_embed)

        def check(m):
            return m.author == user and m.channel == thread

        try:
            # 1. Pegar Nickname
            msg_nickname = await self.bot.wait_for('message', check=check, timeout=300.0)
            nickname = msg_nickname.content

            # 2. Pegar Quantidade
            await thread.send(f"Entendido, **{nickname}**! Agora, qual a **quantidade de Robux** que você deseja comprar? (Ex: 1000 ou 1k)")
            msg_amount = await self.bot.wait_for('message', check=check, timeout=300.0)
            amount = parse_robux_amount(msg_amount.content)

            if not (100 <= amount <= 10000):
                await thread.send("Desculpe, a quantidade deve ser entre 100 e 10.000 Robux. Por favor, inicie a compra novamente.")
                return

            price = config.calculate_robux_price(amount)

            # 3. Confirmação e Pagamento
            qr_code_file = discord.File("assets/qrcode.png", filename="qrcode.png")
            payment_embed = discord.Embed(
                title="✅ Pedido Resumido",
                description=f"**Nickname:** `{nickname}`\n"
                            f"**Quantidade:** `{amount}` Robux\n"
                            f"**Valor a pagar:** `R$ {price:.2f}`\n\n"
                            "Por favor, realize o pagamento via PIX para a chave abaixo ou usando o QR Code. "
                            "Após o pagamento, **envie o comprovante** aqui no chat (.png, .jpg ou .pdf).",
                color=config.EMBED_COLOR
            )
            payment_embed.set_image(url="attachment://qrcode.png")
            payment_embed.add_field(name="Chave PIX (Exemplo)", value="b1a2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6") # TROCAR PELA SUA CHAVE REAL

            await thread.send(embed=payment_embed, file=qr_code_file)

            # 4. Esperar Comprovante
            msg_receipt = await self.bot.wait_for('message', check=lambda m: m.author == user and m.channel == thread and m.attachments, timeout=600.0)
            
            if not msg_receipt.attachments:
                await thread.send("Nenhum comprovante encontrado. Por favor, envie o arquivo.")
                return

            await thread.send("✅ Comprovante recebido! Nossa equipe já foi notificada e irá verificar seu pagamento.")

            # 5. Notificar Admins
            admin_channel = self.bot.get_channel(config.ADMIN_NOTIF_CHANNEL_ID)
            admin_view = View(timeout=None)
            admin_view.add_item(Button(label="Atender Pedido", style=discord.ButtonStyle.primary, custom_id=f"attend_order_{thread.id}_{user.id}_{price}"))
            
            admin_embed = discord.Embed(
                title="🔔 Novo Pedido Recebido!",
                description=f"O cliente **{user.mention}** enviou um comprovante no valor de **R$ {price:.2f}**.\n\n"
                            f"Clique no botão abaixo para assumir o atendimento.",
                color=0x00BFFF # Azul
            )
            await admin_channel.send(embed=admin_embed, view=admin_view)

            # 6. Instruções da Gamepass
            receipt_embed = discord.Embed(
                description=f"@{user.display_name}, recebemos seu comprovante! A forma de entrega é através de Gamepass, você sabe criar uma?",
                color=config.EMBED_COLOR
            )
            required_value = config.get_gamepass_value(amount)
            await thread.send(embed=receipt_embed, view=GamepassCreationView(self.bot, thread, required_value))

            # 7. Esperar link da Gamepass e confirmar preços regionais
            msg_gamepass_link = await self.bot.wait_for('message', check=check, timeout=300.0)
            
            await thread.send(
                "**⚠️ ATENÇÃO!**\n"
                "Para garantir a entrega, os **preços regionais** da sua Gamepass precisam estar **DESATIVADOS**.\n\n"
                "Você confirma que eles estão desativados?"
            )
            msg_confirmation = await self.bot.wait_for('message', check=check, timeout=300.0)

            await thread.send("Obrigado pela confirmação! Um atendente já está com seu pedido e fará a entrega dos Robux em breve. Qualquer dúvida, pode perguntar aqui.")

        except asyncio.TimeoutError:
            await thread.send("Seu pedido expirou por inatividade. Por favor, inicie uma nova compra se desejar.")
            # Opcional: arquivar a thread
            await thread.edit(archived=True)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        custom_id = interaction.data.get("custom_id", "")
        if custom_id.startswith("attend_order_"):
            parts = custom_id.split("_")
            thread_id, user_id, price = int(parts[2]), int(parts[3]), float(parts[4])
            
            attendant = interaction.user
            user = self.bot.get_user(user_id)
            
            # Logar atendimento
            log_channel = self.bot.get_channel(config.ATTENDANCE_LOG_CHANNEL_ID)
            log_embed = discord.Embed(
                description=f"Atendente {attendant.mention} está cuidando do pedido de {user.mention} (Valor: R$ {price:.2f})",
                color=0x32CD32 # Verde
            )
            await log_channel.send(embed=log_embed)
            
            # Adicionar atendente à thread e notificar
            thread = self.bot.get_channel(thread_id)
            if thread:
                await thread.add_user(attendant)
                await thread.send(f"Olá! Eu sou {attendant.mention} e vou finalizar a sua entrega. Já estou verificando tudo!")

            # Desativar o botão
            await interaction.response.edit_message(content="Pedido assumido!", view=None)

def setup(bot):
    bot.add_cog(SalesCog(bot))
