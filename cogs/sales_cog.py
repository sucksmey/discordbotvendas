# cogs/sales_cog.py
import discord
from discord.ext import commands
from discord.ui import View, Button, Select, button
import asyncio
import re
import os

import config
from utils.logger import log_command

def parse_robux_amount(text: str) -> int:
    text = text.lower().replace('robux', '').strip().replace('.', '').replace(',', '.')
    if 'k' in text:
        return int(float(text.replace('k', '')) * 1000)
    numeric_part = re.sub(r'[^0-9]', '', text)
    return int(numeric_part) if numeric_part else 0

class GamepassCreationView(View):
    def __init__(self, bot, thread, required_value):
        super().__init__(timeout=None)
        self.bot = bot
        self.thread = thread
        self.required_value = required_value
    @button(label="Sim, sei criar", style=discord.ButtonStyle.success, custom_id="knows_gamepass")
    async def knows_callback(self, b, i):
        await i.response.defer()
        e = discord.Embed(title="Ótimo!", description=f"Crie a Gamepass com o valor de **{self.required_value} Robux** e envie o link aqui.", color=config.EMBED_COLOR)
        await self.thread.send(embed=e)
        self.stop()
    @button(label="Não, preciso de ajuda", style=discord.ButtonStyle.danger, custom_id="needs_help_gamepass")
    async def needs_help_callback(self, b, i):
        await i.response.defer()
        e = discord.Embed(title="Siga o tutorial", description=f"Crie a Gamepass com o valor de **{self.required_value} Robux**.\n\n**IMPORTANTE:** Lembre-se de **DESATIVAR OS PREÇOS REGIONAIS**!", color=config.EMBED_COLOR)
        await self.thread.send(embed=e)
        await self.thread.send(config.TUTORIAL_VIDEO_URL)
        await self.thread.send("Após criar, envie o link da sua Gamepass aqui.")
        self.stop()

class SalesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    class InitialPurchaseView(View):
        def __init__(self, cog_instance):
            super().__init__(timeout=None)
            self.cog = cog_instance
        @button(label="Comprar Robux", style=discord.ButtonStyle.success, custom_id="buy_robux", emoji="💰")
        async def buy_robux_callback(self, b, i):
            await self.cog.start_robux_purchase(i)
        @button(label="Comprar Gamepass", style=discord.ButtonStyle.primary, custom_id="buy_gamepass", emoji="🎟️")
        async def buy_gamepass_callback(self, b, i):
            await self.cog.start_gamepass_purchase(i)
        @button(label="Ver Tabela de Preços", style=discord.ButtonStyle.secondary, custom_id="show_prices")
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

    async def start_robux_purchase(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        u, c = interaction.user, interaction.channel
        t = await c.create_thread(name=f"🛒 Robux - {u.display_name}", type=discord.ChannelType.private_thread)
        await t.add_user(u)
        await interaction.followup.send(f"Seu carrinho para Robux foi criado aqui: {t.mention}", ephemeral=True)
        
        log_channel = self.bot.get_channel(config.ATTENDANCE_LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(f"🛒 Novo carrinho de **Robux** criado para {u.mention}. Aguardando comprovante.")

        we = discord.Embed(title=f"👋 Olá, {u.display_name}!", description="Bem-vindo(a)! Para começar, me informe seu **nickname no Roblox**.", color=config.EMBED_COLOR)
        await t.send(u.mention, embed=we)
        
        def chk(m): return m.author == u and m.channel == t
        try:
            nick_msg = await self.bot.wait_for('message', check=chk, timeout=172800.0)
            nick = nick_msg.content
            await t.send(f"Ok, **{nick}**! Qual a **quantidade de Robux** você deseja?")
            amt_msg = await self.bot.wait_for('message', check=chk, timeout=172800.0)
            amt = parse_robux_amount(amt_msg.content)
            
            if not (100 <= amt <= 10000):
                return await t.send("Quantidade inválida. Por favor, inicie uma nova compra.")

            price = config.calculate_robux_price(amt)
            disc = 0.0
            ncr = interaction.guild.get_role(config.NEW_CUSTOMER_ROLE_ID)
            if ncr and ncr in u.roles:
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
                await t.send(file=qrf, embed=pe)
            else: await t.send(embed=pe)
            
            await self.bot.wait_for('message', check=lambda m: m.author==u and m.channel==t and m.attachments, timeout=172800.0)
            await t.send("✅ Comprovante recebido!")
            
            ac = self.bot.get_channel(config.ADMIN_NOTIF_CHANNEL_ID)
            av = View(timeout=None)
            av.add_item(Button(label="Atender Robux", style=discord.ButtonStyle.green, custom_id=f"attend_robux_{t.id}_{u.id}_{price}_{amt}"))
            ae = discord.Embed(title="🔔 Pedido de Robux!", description=f"O cliente {u.mention} enviou comprovante para **{amt} Robux** (Valor: R$ {price:.2f}).", color=0x2ECC71)
            await ac.send(embed=ae, view=av)

            re = discord.Embed(description=f"{u.mention}, a entrega é via Gamepass. Você sabe criar uma?", color=config.EMBED_COLOR)
            req_val = config.get_gamepass_value(amt)
            await t.send(embed=re, view=GamepassCreationView(self.bot, t, req_val))
            
            await self.bot.wait_for('message', check=chk, timeout=172800.0)
            await t.send("**⚠️ ATENÇÃO!**\nOs **preços regionais** da sua Gamepass devem estar **DESATIVADOS**. Você confirma?")
            await self.bot.wait_for('message', check=chk, timeout=172800.0)
            await t.send("Obrigado pela confirmação! Um atendente já está com seu pedido.")
        except asyncio.TimeoutError:
            await t.send("Seu pedido expirou por inatividade."); await asyncio.sleep(5); await t.edit(archived=True, locked=True)

    async def start_gamepass_purchase(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        u, c = interaction.user, interaction.channel
        t = await c.create_thread(name=f"🎟️ Gamepass - {u.display_name}", type=discord.ChannelType.private_thread)
        await t.add_user(u)
        await interaction.followup.send(f"Seu carrinho para Gamepass foi criado aqui: {t.mention}", ephemeral=True)
        
        log_channel = self.bot.get_channel(config.ATTENDANCE_LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(f"🎟️ Novo carrinho de **Gamepass** criado para {u.mention}. Aguardando comprovante.")
            
        we = discord.Embed(title="🎟️ Compra via Gamepass", description=f"Olá, {u.display_name}! Qual a **quantidade de Robux** que você deseja?", color=config.EMBED_COLOR)
        await t.send(u.mention, embed=we)
        
        def chk(m): return m.author == u and m.channel == t
        try:
            amt_msg = await self.bot.wait_for('message', check=chk, timeout=172800.0)
            amt = parse_robux_amount(amt_msg.content)
            if not (100 <= amt <= 10000):
                return await t.send("Quantidade inválida. Por favor, inicie uma nova compra.")
            price = config.calculate_gamepass_price(amt)
            await t.send("Ok! Qual o seu **nickname no Roblox**?")
            nick_msg = await self.bot.wait_for('message', check=chk, timeout=172800.0)
            nick = nick_msg.content
            
            pe = discord.Embed(title="✅ Pedido Resumido (Gamepass)", description=f"**Nickname:** `{nick}`\n**Quantidade:** `{amt}` Robux\n**Valor a pagar:** `R$ {price:.2f}`\n\nPor favor, realize o pagamento e envie o comprovante.", color=config.EMBED_COLOR)
            pe.add_field(name="Chave PIX", value=config.PIX_KEY)
            if os.path.exists("assets/qrcode.png"):
                qrf = discord.File("assets/qrcode.png", "qrcode.png")
                pe.set_image(url="attachment://qrcode.png")
                await t.send(file=qrf, embed=pe)
            else: await t.send(embed=pe)

            await self.bot.wait_for('message', check=lambda m: m.author==u and m.channel==t and m.attachments, timeout=172800.0)
            await t.send("✅ Comprovante recebido!")

            ac = self.bot.get_channel(config.ADMIN_NOTIF_CHANNEL_ID)
            av = View(timeout=None)
            av.add_item(Button(label="Atender Gamepass", style=discord.ButtonStyle.blurple, custom_id=f"attend_gamepass_{t.id}_{u.id}_{price}_{amt}"))
            ae = discord.Embed(title="🔔 Pedido de Gamepass!", description=f"O cliente {u.mention} enviou comprovante para **{amt} Robux via Gamepass** (Valor: R$ {price:.2f}).", color=0x5865F2)
            await ac.send(embed=ae, view=av)
            
            await t.send("Obrigado! Agora, por favor, envie o **link do seu jogo** no Roblox.")
            await self.bot.wait_for('message', check=chk, timeout=172800.0)
            await t.send("**⚠️ IMPORTANTE!**\nSeu jogo precisa ter um sistema de **Giftpass** para que a entrega seja feita. Você confirma?")
            await self.bot.wait_for('message', check=chk, timeout=172800.0)
            await t.send("Obrigado pela confirmação! Um atendente já está com seu pedido.")
        except asyncio.TimeoutError:
            await t.send("Seu pedido expirou por inatividade."); await asyncio.sleep(5); await t.edit(archived=True, locked=True)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        cid = interaction.data.get("custom_id", "")
        if cid.startswith("attend_robux_") or cid.startswith("attend_gamepass_"):
            if not any(r.id in config.ATTENDANT_ROLE_IDS for r in interaction.user.roles):
                return await interaction.response.send_message("Você não tem permissão para atender este pedido.", ephemeral=True)
            
            await interaction.response.defer()
            p = cid.split("_")
            tid, uid, price = int(p[2]), int(p[3]), float(p[4])
            att, u = interaction.user, self.bot.get_user(uid) or await self.bot.fetch_user(uid)
            
            lc = self.bot.get_channel(config.ATTENDANCE_LOG_CHANNEL_ID)
            if lc: await lc.send(embed=discord.Embed(description=f"{att.mention} está cuidando do pedido de {u.mention} (Valor: R$ {price:.2f})", color=0x32CD32))
            
            t = self.bot.get_channel(tid)
            if t:
                await t.add_user(att)
                await t.send(f"Olá! Eu sou {att.mention} e vou finalizar a sua entrega.")

            await (await interaction.original_response()).edit(content=f"Pedido assumido por {att.mention}!", view=None)

def setup(bot):
    bot.add_cog(SalesCog(bot))
