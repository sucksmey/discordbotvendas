# cogs/sales_cog.py
import discord
from discord.ext import commands
from discord.ui import View, Button, button
import asyncio
import re
import os

import config
from utils.logger import log_command

class InitialPurchaseView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    # --- EMOJI CORRIGIDO AQUI ---
    @button(label="Comprar Robux", style=discord.ButtonStyle.success, custom_id="buy_robux", emoji="💰")
    async def buy_robux_callback(self, button_obj: discord.ui.Button, interaction: discord.Interaction):
        await SalesCog.start_robux_purchase(self.bot, interaction)

    @button(label="Comprar Gamepass", style=discord.ButtonStyle.primary, custom_id="buy_gamepass", emoji="🎟️")
    async def buy_gamepass_callback(self, button_obj: discord.ui.Button, interaction: discord.Interaction):
        await SalesCog.start_gamepass_purchase(self.bot, interaction)

    @button(label="Ver Tabela de Preços", style=discord.ButtonStyle.secondary, custom_id="show_prices")
    async def show_prices_callback(self, button_obj: discord.ui.Button, interaction: discord.Interaction):
        await log_command(self.bot, interaction, is_button=True, button_id="Ver Tabela de Preços")
        embed = discord.Embed(title="Tabela de Preços - IsraBuy", description="Confira nossos valores competitivos!", color=config.EMBED_COLOR)
        
        # --- EMOJI CORRIGIDO AQUI TAMBÉM ---
        robux_prices_str = "\n".join([f"**{amount} Robux:** R$ {price:.2f}" for amount, price in config.ROBUX_PRICES.items()])
        gamepass_prices_str = "\n".join([f"**{amount} Robux:** R$ {price:.2f}" for amount, price in config.GAMEPASS_PRICES.items()])
        
        embed.add_field(name="💰 Compra Direta (Robux)", value=robux_prices_str, inline=True)
        embed.add_field(name="🎟️ Compra via Gamepass", value=gamepass_prices_str, inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class GamepassCreationView(View):
    def __init__(self, bot, thread, required_value):
        super().__init__(timeout=None)
        self.bot = bot
        self.thread = thread
        self.required_value = required_value

    @button(label="Sim, sei criar", style=discord.ButtonStyle.success, custom_id="knows_gamepass")
    async def knows_callback(self, button_obj: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.defer()
        embed = discord.Embed(title="Ótimo!", description=f"Por favor, crie a Gamepass com o valor exato de **{self.required_value} Robux**.\n\nApós criar, envie o link ou o ID da sua Gamepass aqui.", color=config.EMBED_COLOR)
        await self.thread.send(embed=embed)
        self.stop()

    @button(label="Não, preciso de ajuda", style=discord.ButtonStyle.danger, custom_id="needs_help_gamepass")
    async def needs_help_callback(self, button_obj: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.defer()
        embed = discord.Embed(title="Sem problemas! Siga o tutorial", description=f"Para criar sua Gamepass, assista ao vídeo abaixo. Você deve criar a Gamepass com o valor exato de **{self.required_value} Robux**.\n\n**IMPORTANTE:** Lembre-se de **DESATIVAR OS PREÇOS REGIONAIS**!", color=config.EMBED_COLOR)
        await self.thread.send(embed=embed)
        await self.thread.send(config.TUTORIAL_VIDEO_URL)
        await self.thread.send("Após criar, envie o link ou o ID da sua Gamepass aqui.")
        self.stop()

class SalesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(InitialPurchaseView(bot=self.bot))
        print("View de vendas persistente registrada.")
        
    @commands.slash_command(name="iniciarvendas", description="Cria o painel inicial de vendas no canal de compras.", guild_ids=[config.GUILD_ID])
    @commands.has_any_role(*config.ATTENDANT_ROLE_IDS)
    async def start_sales(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(title="🛒 Central de Pedidos da IsraBuy", description="Nossa loja oferece os melhores produtos com os melhores preços do Brasil!\n\n**Como Comprar:**\nClique em um dos botões abaixo para iniciar o processo de compra!", color=config.EMBED_COLOR)
        purchase_channel = self.bot.get_channel(config.PURCHASE_CHANNEL_ID)
        if purchase_channel:
            await purchase_channel.send(embed=embed, view=InitialPurchaseView(bot=self.bot))
            await ctx.respond("Painel de vendas criado com sucesso!", ephemeral=True)
        else:
            await ctx.respond("Erro: Canal de compras não encontrado.", ephemeral=True)

    @staticmethod
    async def start_robux_purchase(bot, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user = interaction.user
        thread = await interaction.channel.create_thread(name=f"🛒 Robux - {user.display_name}", type=discord.ChannelType.private_thread)
        await thread.add_user(user)
        await interaction.followup.send(f"Seu carrinho para comprar Robux foi criado aqui: {thread.mention}", ephemeral=True)

        welcome_embed = discord.Embed(title=f"👋 Olá, {user.display_name}!", description="Bem-vindo(a) ao seu carrinho para compra de Robux!\n\nPara começar, por favor, me informe seu **nickname no Roblox**.", color=config.EMBED_COLOR)
        await thread.send(user.mention, embed=welcome_embed)

        def check(m):
            return m.author == user and m.channel == thread

        try:
            msg_nickname = await bot.wait_for('message', check=check, timeout=300.0)
            nickname = msg_nickname.content
            await thread.send(f"Entendido, **{nickname}**! Agora, qual a **quantidade de Robux** que você deseja comprar?")
            msg_amount = await bot.wait_for('message', check=check, timeout=300.0)
            amount = parse_robux_amount(msg_amount.content)

            if not (100 <= amount <= 10000):
                await thread.send("Quantidade inválida. Por favor, inicie uma nova compra.")
                return

            price = config.calculate_robux_price(amount)
            discount = 0.0
            new_customer_role = interaction.guild.get_role(config.NEW_CUSTOMER_ROLE_ID)
            if new_customer_role and new_customer_role in user.roles:
                discount = price * (config.NEW_CUSTOMER_DISCOUNT_PERCENT / 100)
                price -= discount
            
            payment_embed = discord.Embed(title="✅ Pedido Resumido (Robux)", color=config.EMBED_COLOR)
            description = f"**Nickname:** `{nickname}`\n**Quantidade:** `{amount}` Robux\n"
            if discount > 0:
                description += f"**Subtotal:** `R$ {(price + discount):.2f}`\n**Desconto ({config.NEW_CUSTOMER_DISCOUNT_PERCENT}%):** `-R$ {discount:.2f}`\n**Valor a pagar:** `R$ {price:.2f}`\n\n"
            else:
                description += f"**Valor a pagar:** `R$ {price:.2f}`\n\n"
            description += "Por favor, realize o pagamento via PIX e envie o comprovante aqui."
            payment_embed.description = description
            payment_embed.add_field(name="Chave PIX (Aleatória)", value="b1a2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6")
            
            qr_code_file_path = "assets/qrcode.png"
            if os.path.exists(qr_code_file_path):
                qr_code_file = discord.File(qr_code_file_path, filename="qrcode.png")
                payment_embed.set_image(url="attachment://qrcode.png")
                await thread.send(file=qr_code_file, embed=payment_embed)
            else:
                await thread.send(embed=payment_embed)

            msg_receipt = await bot.wait_for('message', check=lambda m: m.author == user and m.channel == thread and m.attachments, timeout=600.0)
            await thread.send("✅ Comprovante recebido!")

            admin_channel = bot.get_channel(config.ADMIN_NOTIF_CHANNEL_ID)
            admin_view = View(timeout=None)
            admin_view.add_item(Button(label="Atender Robux", style=discord.ButtonStyle.green, custom_id=f"attend_robux_{thread.id}_{user.id}_{price}_{amount}"))
            admin_embed = discord.Embed(title="🔔 Novo Pedido de Robux!", description=f"O cliente {user.mention} enviou um comprovante para **{amount} Robux** no valor de **R$ {price:.2f}**.", color=0x2ECC71)
            await admin_channel.send(embed=admin_embed, view=admin_view)

            receipt_embed = discord.Embed(description=f"{user.mention}, recebemos seu comprovante! A entrega é via Gamepass, você sabe criar uma?", color=config.EMBED_COLOR)
            required_value = config.get_gamepass_value(amount)
            await thread.send(embed=receipt_embed, view=GamepassCreationView(bot, thread, required_value))

            msg_gamepass_link = await bot.wait_for('message', check=check, timeout=300.0)
            await thread.send("**⚠️ ATENÇÃO!**\nOs **preços regionais** precisam estar **DESATIVADOS**.\n\nVocê confirma que desativou?")
            await bot.wait_for('message', check=check, timeout=300.0)
            await thread.send("Obrigado pela confirmação! Um atendente já está com seu pedido.")

        except asyncio.TimeoutError:
            await thread.send("Seu pedido expirou por inatividade.")
            await asyncio.sleep(10)
            await thread.edit(archived=True, locked=True)

    @staticmethod
    async def start_gamepass_purchase(bot, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user = interaction.user
        thread = await interaction.channel.create_thread(name=f"🎟️ GP - {user.display_name}", type=discord.ChannelType.private_thread)
        await thread.add_user(user)
        await interaction.followup.send(f"Seu carrinho para comprar Gamepass foi criado aqui: {thread.mention}", ephemeral=True)

        welcome_embed = discord.Embed(title="🎟️ Compra de Robux via Gamepass", description=f"Olá, {user.display_name}! Para começar, qual a **quantidade de Robux** que você deseja?", color=config.EMBED_COLOR)
        await thread.send(user.mention, embed=welcome_embed)

        def check(m):
            return m.author == user and m.channel == thread

        try:
            msg_amount = await bot.wait_for('message', check=check, timeout=300.0)
            amount = parse_robux_amount(msg_amount.content)

            if not (100 <= amount <= 10000):
                await thread.send("Quantidade inválida. Por favor, inicie uma nova compra.")
                return

            price = config.calculate_gamepass_price(amount)
            await thread.send(f"Entendido! Agora, por favor, me informe seu **nickname no Roblox**.")
            msg_nickname = await bot.wait_for('message', check=check, timeout=300.0)
            nickname = msg_nickname.content

            payment_embed = discord.Embed(title="✅ Pedido Resumido (Gamepass)", description=f"**Nickname:** `{nickname}`\n**Quantidade:** `{amount}` Robux\n**Valor a pagar:** `R$ {price:.2f}`\n\nPor favor, realize o pagamento via PIX e envie o comprovante aqui.", color=config.EMBED_COLOR)
            payment_embed.add_field(name="Chave PIX (Aleatória)", value="b1a2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6")
            
            qr_code_file_path = "assets/qrcode.png"
            if os.path.exists(qr_code_file_path):
                qr_code_file = discord.File(qr_code_file_path, filename="qrcode.png")
                payment_embed.set_image(url="attachment://qrcode.png")
                await thread.send(file=qr_code_file, embed=payment_embed)
            else:
                await thread.send(embed=payment_embed)

            msg_receipt = await bot.wait_for('message', check=lambda m: m.author == user and m.channel == thread and m.attachments, timeout=600.0)
            await thread.send("✅ Comprovante recebido!")

            admin_channel = bot.get_channel(config.ADMIN_NOTIF_CHANNEL_ID)
            admin_view = View(timeout=None)
            admin_view.add_item(Button(label="Atender Gamepass", style=discord.ButtonStyle.blurple, custom_id=f"attend_gamepass_{thread.id}_{user.id}_{price}_{amount}"))
            admin_embed = discord.Embed(title="🔔 Novo Pedido de Gamepass!", description=f"O cliente {user.mention} enviou um comprovante para **{amount} Robux via Gamepass** no valor de **R$ {price:.2f}**.", color=0x5865F2)
            await admin_channel.send(embed=admin_embed, view=admin_view)
            
            await thread.send(f"Obrigado! Agora, por favor, envie o **link do seu jogo** no Roblox.")
            msg_game_link = await bot.wait_for('message', check=check, timeout=300.0)
            await thread.send("**⚠️ IMPORTANTE!**\nSeu jogo precisa ter um sistema de **Giftpass** para que a entrega seja feita.\n\nVocê confirma que o jogo possui esse sistema?")
            await bot.wait_for('message', check=check, timeout=300.0)
            await thread.send("Obrigado pela confirmação! Um atendente já está com seu pedido.")

        except asyncio.TimeoutError:
            await thread.send("Seu pedido expirou por inatividade.")
            await asyncio.sleep(10)
            await thread.edit(archived=True, locked=True)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        custom_id = interaction.data.get("custom_id", "")
        if custom_id.startswith("attend_robux_") or custom_id.startswith("attend_gamepass_"):
            if not any(role.id in config.ATTENDANT_ROLE_IDS for role in interaction.user.roles):
                return await interaction.response.send_message("Você não tem permissão para atender pedidos.", ephemeral=True)
            
            await interaction.response.defer()
            parts = custom_id.split("_")
            thread_id, user_id, price, amount = int(parts[2]), int(parts[3]), float(parts[4]), int(parts[5])
            
            attendant = interaction.user
            user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
            
            log_channel = self.bot.get_channel(config.ATTENDANCE_LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(embed=discord.Embed(description=f"Atendente {attendant.mention} está cuidando do pedido de {user.mention} (Valor: R$ {price:.2f})", color=0x32CD32))
            
            thread = self.bot.get_channel(thread_id)
            if thread:
                await thread.add_user(attendant)
                await thread.send(f"Olá! Eu sou {attendant.mention} e vou finalizar a sua entrega. Já estou verificando tudo!")

            original_message = await interaction.original_response()
            await original_message.edit(content=f"Pedido assumido por {attendant.mention}!", view=None)

def setup(bot):
    bot.add_cog(SalesCog(bot))
