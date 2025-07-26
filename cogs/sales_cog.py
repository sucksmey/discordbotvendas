# cogs/sales_cog.py
import discord
from discord.ext import commands
from discord.ui import View, Button
import asyncio
import re
import os

import config
import database
from utils.logger import log_command, log_dm

def parse_robux_amount(text: str) -> int:
    text = text.lower().replace('robux', '').strip().replace('.', '').replace(',', '.')
    if 'k' in text:
        return int(float(text.replace('k', '')) * 1000)
    numeric_part = re.sub(r'[^\d]', '', text)
    return int(numeric_part) if numeric_part else 0

class SalesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    class PrePurchaseConfirmationView(View):
        def __init__(self, cog, interaction, purchase_type):
            super().__init__(timeout=300)
            self.cog = cog
            self.interaction = interaction
            self.purchase_type = purchase_type

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if interaction.user.id != self.interaction.user.id:
                await interaction.response.send_message("Você não pode usar os botões de outra pessoa.", ephemeral=True)
                return False
            return True

        @discord.ui.button(label="Confirmar Abertura do Carrinho", style=discord.ButtonStyle.success, emoji="✅")
        async def confirm_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
            await interaction.response.defer()
            for item in self.children: item.disabled = True
            await self.interaction.edit_original_response(view=self)

            if self.purchase_type == 'robux':
                await self.cog.create_robux_thread(interaction)
            elif self.purchase_type == 'gamepass':
                await self.cog.create_gamepass_thread(interaction)
        
        @discord.ui.button(label="Cancelar Compra", style=discord.ButtonStyle.danger, emoji="❌")
        async def cancel_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
            for item in self.children: item.disabled = True
            await interaction.response.edit_message(content="Sua compra foi cancelada.", view=self, embed=None)
            self.stop()

    class InitialPurchaseView(View):
        def __init__(self, cog_instance):
            super().__init__(timeout=None)
            self.cog = cog_instance
        
        @discord.ui.button(label="Comprar Robux", style=discord.ButtonStyle.success, custom_id="buy_robux", emoji="💰")
        async def buy_robux_callback(self, b, i):
            await self.cog.start_purchase_flow(i, 'robux')

        @discord.ui.button(label="Comprar Gamepass de Jogo", style=discord.ButtonStyle.primary, custom_id="buy_gamepass", emoji="🎟️")
        async def buy_gamepass_callback(self, b, i):
            await self.cog.start_purchase_flow(i, 'gamepass')
        
        @discord.ui.button(label="Ver Tabela de Preços", style=discord.ButtonStyle.secondary, custom_id="show_prices")
        async def show_prices_callback(self, b, i):
            await log_command(self.cog.bot, i, is_button=True, button_id="Ver Tabela de Preços")
            e = discord.Embed(title="Tabela de Preços - IsraBuy", color=config.EMBED_COLOR)
            rp_str = "\n".join([f"**{a} Robux:** R$ {p:.2f}" for a, p in config.ROBUX_PRICES.items()])
            gp_str = "\n".join([f"**{a} Robux:** R$ {p:.2f}" for a, p in config.GAMEPASS_PRICES.items()])
            e.add_field(name="💰 Compra Direta (Robux)", value=rp_str, inline=True)
            e.add_field(name="🎟️ Compra via Gamepass", value=gp_str, inline=True)
            await i.response.send_message(embed=e, ephemeral=True)

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(self.InitialPurchaseView(self))
        print("View de vendas de Robux/Gamepass registrada.")
        
    @commands.slash_command(name="iniciarvendas", description="Cria o painel de vendas de Robux e Gamepass.", guild_ids=[config.GUILD_ID])
    @commands.has_any_role(*config.ATTENDANT_ROLE_IDS)
    async def start_sales(self, ctx: discord.ApplicationContext):
        e = discord.Embed(title="🛒 Central de Pedidos da IsraBuy", description="Clique em um dos botões abaixo para comprar Robux!", color=config.EMBED_COLOR)
        c = self.bot.get_channel(config.PURCHASE_CHANNEL_ID)
        await c.send(embed=e, view=self.InitialPurchaseView(self))
        await ctx.respond("Painel de vendas de Robux criado!", ephemeral=True)

    async def start_purchase_flow(self, interaction: discord.Interaction, purchase_type: str):
        user_id = interaction.user.id
        active_thread_id = await database.get_active_thread(user_id)
        if active_thread_id:
            thread = self.bot.get_channel(active_thread_id)
            if thread and not getattr(thread, 'archived', True):
                view = View(); view.add_item(Button(label="Ir para o Carrinho", style=discord.ButtonStyle.link, url=thread.jump_url))
                await interaction.response.send_message(f"❌ Você já possui um carrinho aberto em {thread.mention}.", view=view, ephemeral=True)
                return
            else:
                await database.set_active_thread(user_id, None)

        embed = discord.Embed(title="👋 Bem-vindo(a) à Loja IsraBuy!", color=config.EMBED_COLOR,
            description="Aqui você encontra os melhores produtos com os melhores preços!\n\n"
                        "**Prazos Importantes (Robux):**\n"
                        "• **Entrega:** Em até 3 dias úteis.\n"
                        "• **Crédito:** Após a entrega, os Robux podem levar de 5 a 7 dias úteis para aparecer no seu saldo (prazo do Roblox).")
        view = self.PrePurchaseConfirmationView(self, interaction, purchase_type)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def create_robux_thread(self, interaction: discord.Interaction):
        user = interaction.user
        thread = await interaction.channel.create_thread(name=f"🛒 Robux - {user.display_name}", type=discord.ChannelType.private_thread)
        await database.set_active_thread(user.id, thread.id)
        
        await thread.add_user(user)
        for role_id in config.ATTENDANT_ROLE_IDS:
            role = interaction.guild.get_role(role_id)
            if role:
                for member in role.members:
                    try: await thread.add_user(member)
                    except Exception: pass
        
        view = View(); view.add_item(Button(label="Ver seu Carrinho", style=discord.ButtonStyle.link, url=thread.jump_url))
        await interaction.followup.send(f"✅ Carrinho criado! Continue sua compra aqui: {thread.mention}", view=view, ephemeral=True)
        await log_dm(self.bot, user, content=f"Seu carrinho na IsraBuy foi aberto. Clique no botão para acessá-lo.", view=view)

        admin_channel = self.bot.get_channel(config.ADMIN_NOTIF_CHANNEL_ID)
        admin_view = View(timeout=None)
        admin_view.add_item(Button(label="Atender Pedido", style=discord.ButtonStyle.green, custom_id=f"attend_robux_{thread.id}_{user.id}"))
        if admin_channel: await admin_channel.send(f"🛒 Novo carrinho de **Robux** para {user.mention} aguarda um atendente.", view=admin_view)
        
        robux_prices_str = "\n".join([f"**{a} Robux:** R$ {p:.2f}" for a, p in config.ROBUX_PRICES.items()])
        welcome_embed = discord.Embed(title="Tabela de Preços (Robux)", description=robux_prices_str, color=config.EMBED_COLOR)
        await thread.send(embed=welcome_embed)
        await thread.send(f"Olá {user.mention}, bem-vindo(a)! Para começar, por favor, me informe seu **nickname no Roblox**.")

        def chk(m): return m.author == user and m.channel == thread
        try:
            nick_msg = await self.bot.wait_for('message', check=chk, timeout=172800.0)
            nick = nick_msg.content
            await thread.send(f"Ok, **{nick}**! Qual a **quantidade de Robux** você deseja?")
            amt_msg = await self.bot.wait_for('message', check=chk, timeout=172800.0)
            amt = parse_robux_amount(amt_msg.content)
            
            if not (100 <= amt <= 10000):
                await database.set_active_thread(user.id, None)
                return await thread.send("Quantidade inválida. Este carrinho foi cancelado.")

            price = config.calculate_robux_price(amt)
            disc = 0.0
            ncr = interaction.guild.get_role(config.NEW_CUSTOMER_ROLE_ID)
            if ncr and ncr in user.roles:
                disc = price * (config.NEW_CUSTOMER_DISCOUNT_PERCENT / 100)
                price -= disc
            
            pe = discord.Embed(title="✅ Pedido Resumido (Robux)", color=config.EMBED_COLOR)
            desc = f"**Nickname:** `{nick}`\n**Quantidade:** `{amt}` Robux\n"
            if disc > 0: desc += f"**Subtotal:** `R$ {(price + disc):.2f}`\n**Desconto:** `-R$ {disc:.2f}`\n**Valor a pagar:** `R$ {price:.2f}`\n\n"
            else: desc += f"**Valor a pagar:** `R$ {price:.2f}`\n\n"
            pe.description = desc + "Por favor, realize o pagamento via PIX e envie o comprovante."
            pe.add_field(name="Chave PIX", value=config.PIX_KEY)
            
            if os.path.exists("assets/qrcode.png"):
                qrf = discord.File("assets/qrcode.png", filename="qrcode.png")
                pe.set_image(url="attachment://qrcode.png")
                await thread.send(file=qrf, embed=pe)
            else: await thread.send(embed=pe)
            
            msg_receipt = await self.bot.wait_for('message', check=lambda m: m.author.id == user.id and m.channel.id == thread.id and m.attachments, timeout=172800.0)
            customer_role = interaction.guild.get_role(config.EXISTING_CUSTOMER_ROLE_ID)
            if customer_role: await user.add_roles(customer_role, reason="Enviou comprovante de pagamento")

            await thread.send("✅ Comprovante recebido! Um atendente já está com seu pedido e irá te guiar.")
            await thread.send("A entrega é via Gamepass. **Um atendente irá te auxiliar e informar o valor exato a ser colocado na Gamepass.** Por favor, aguarde.")

        except asyncio.TimeoutError:
            await thread.send("Seu pedido expirou por inatividade."); await asyncio.sleep(5)
            await database.set_active_thread(user.id, None)
            await thread.edit(archived=True, locked=True)

    async def create_gamepass_thread(self, interaction: discord.Interaction):
        user = interaction.user
        thread = await interaction.channel.create_thread(name=f"🎟️ Gamepass - {user.display_name}", type=discord.ChannelType.private_thread)
        await database.set_active_thread(user.id, thread.id)
        
        await thread.add_user(user)
        for role_id in config.ATTENDANT_ROLE_IDS:
            role = interaction.guild.get_role(role_id)
            if role:
                for member in role.members:
                    try: await thread.add_user(member)
                    except Exception: pass

        view = View(); view.add_item(Button(label="Ver seu Carrinho", style=discord.ButtonStyle.link, url=thread.jump_url))
        await interaction.followup.send(f"✅ Carrinho criado! Continue sua compra aqui: {thread.mention}", view=view, ephemeral=True)
        await log_dm(self.bot, user, content=f"Seu carrinho na IsraBuy foi aberto. Clique no botão para acessá-lo.", view=view)

        admin_channel = self.bot.get_channel(config.ADMIN_NOTIF_CHANNEL_ID)
        admin_view = View(timeout=None)
        admin_view.add_item(Button(label="Atender Pedido", style=discord.ButtonStyle.primary, custom_id=f"attend_gamepass_{thread.id}_{user.id}"))
        if admin_channel: await admin_channel.send(f"🎟️ Novo carrinho de **Gamepass** para {user.mention} aguarda um atendente.", view=admin_view)
            
        gamepass_prices_str = "\n".join([f"**{a} Robux:** R$ {p:.2f}" for a, p in config.GAMEPASS_PRICES.items()])
        welcome_embed = discord.Embed(title="Tabela de Preços (Gamepass)", description=gamepass_prices_str, color=config.EMBED_COLOR)
        await thread.send(embed=welcome_embed)
        await thread.send(f"Olá {user.mention}, bem-vindo(a)! Qual a **quantidade de Robux** que você deseja?")
        
        def chk(m): return m.author == user and m.channel == thread
        try:
            amt_msg = await self.bot.wait_for('message', check=chk, timeout=172800.0)
            amt = parse_robux_amount(amt_msg.content)
            if not (100 <= amt <= 10000):
                await database.set_active_thread(user.id, None)
                return await thread.send("Quantidade inválida. Carrinho cancelado.")
            price = config.calculate_gamepass_price(amt)
            await thread.send("Ok! Qual o seu **nickname no Roblox**?")
            nick_msg = await self.bot.wait_for('message', check=chk, timeout=172800.0)
            nick = nick_msg.content
            
            pe = discord.Embed(title="✅ Pedido Resumido (Gamepass)", description=f"**Nickname:** `{nick}`\n**Quantidade:** `{amt}` Robux\n**Valor a pagar:** `R$ {price:.2f}`\n\nPor favor, realize o pagamento e envie o comprovante.", color=config.EMBED_COLOR)
            pe.add_field(name="Chave PIX", value=config.PIX_KEY)
            if os.path.exists("assets/qrcode.png"):
                qrf = discord.File("assets/qrcode.png", "qrcode.png")
                pe.set_image(url="attachment://qrcode.png")
                await thread.send(file=qrf, embed=pe)
            else: await thread.send(embed=pe)

            msg_receipt = await self.bot.wait_for('message', check=lambda m: m.author.id == user.id and m.channel.id == thread.id and m.attachments, timeout=172800.0)
            customer_role = interaction.guild.get_role(config.EXISTING_CUSTOMER_ROLE_ID)
            if customer_role: await user.add_roles(customer_role, reason="Enviou comprovante de pagamento")
            
            await thread.send("✅ Comprovante recebido! Um atendente já está com seu pedido.")
            await thread.send("Por favor, envie o **link do seu jogo** no Roblox e aguarde as instruções do atendente.")
        except asyncio.TimeoutError:
            await thread.send("Seu pedido expirou por inatividade."); await asyncio.sleep(5)
            await database.set_active_thread(user.id, None)
            await thread.edit(archived=True, locked=True)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        custom_id = interaction.data.get("custom_id", "")
        if custom_id.startswith("attend_robux_") or custom_id.startswith("attend_gamepass_"):
            if not any(r.id in config.ATTENDANT_ROLE_IDS for r in interaction.user.roles):
                return await interaction.response.send_message("Você não tem permissão para atender este pedido.", ephemeral=True)
            
            await interaction.response.defer()
            parts = custom_id.split("_")
            thread_id, user_id = int(parts[2]), int(parts[3])
            attendant, user = interaction.user, self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
            
            await log_dm(self.bot, attendant, content="Você assumiu um novo ticket! Use o site abaixo para calcular a taxa da Gamepass (marcando 'Robux After Tax'):\nhttps://rbxtax.com/tax.html")
            
            log_channel = self.bot.get_channel(config.ATTENDANCE_LOG_CHANNEL_ID)
            if log_channel: await log_channel.send(embed=discord.Embed(description=f"{attendant.mention} está cuidando do carrinho de {user.mention}.", color=0x32CD32))
            
            thread = self.bot.get_channel(thread_id)
            if thread: await thread.send(f"Olá! Eu sou {attendant.mention} e vou te atender a partir de agora.")

            await (await interaction.original_response()).edit(content=f"Carrinho assumido por {attendant.mention}!", view=None)

def setup(bot):
    bot.add_cog(SalesCog(bot))
