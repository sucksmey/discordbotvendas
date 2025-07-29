# cogs/sales_cog.py
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, InputText
import asyncio
import re
import os
import datetime

import config
import database
from utils.logger import log_command, log_dm

def parse_robux_amount(text: str) -> int:
    text = text.lower().replace('robux', '').strip().replace('.', '').replace(',', '.')
    if 'k' in text:
        return int(float(text.replace('k', '')) * 1000)
    numeric_part = re.sub(r'[^\d]', '', text)
    return int(numeric_part) if numeric_part else 0

class RobuxOrderModal(Modal):
    def __init__(self, cog, purchase_type):
        super().__init__(title="Iniciar Compra")
        self.cog = cog
        self.purchase_type = purchase_type
        self.add_item(InputText(label="Seu nickname no Roblox", placeholder="Ex: construtordomundo123", required=True))
        self.add_item(InputText(label="Quantidade de Robux", placeholder="Ex: 1000, 1.5k, 2000", required=True))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        nickname = self.children[0].value
        amount_str = self.children[1].value
        if self.purchase_type == 'robux':
            await self.cog.process_robux_order(interaction, nickname, amount_str)
        elif self.purchase_type == 'gamepass':
            await self.cog.process_gamepass_order(interaction, nickname, amount_str)

class SalesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def update_spend_roles(self, member: discord.Member, total_spent: float):
        if not member: return
        spend_role_ids = list(config.SPEND_ROLES_TIERS.values())
        highest_role_to_add = None
        for spend_threshold, role_id in sorted(config.SPEND_ROLES_TIERS.items(), reverse=True):
            if total_spent >= spend_threshold:
                highest_role_to_add = role_id
                break
        if highest_role_to_add:
            roles_to_remove = [r for r in member.roles if r.id in spend_role_ids and r.id != highest_role_to_add]
            if roles_to_remove: await member.remove_roles(*roles_to_remove, reason="Atualização de cargo por gasto")
            if not any(r.id == highest_role_to_add for r in member.roles):
                role_to_add = member.guild.get_role(highest_role_to_add)
                if role_to_add: await member.add_roles(role_to_add, reason=f"Atingiu R$ {total_spent:.2f} em gastos")

    class PrePurchaseConfirmationView(View):
        def __init__(self, cog, interaction, purchase_type):
            super().__init__(timeout=300)
            self.cog = cog
            self.original_interaction = interaction
            self.purchase_type = purchase_type
        async def interaction_check(self, i: discord.Interaction) -> bool:
            if i.user.id != self.original_interaction.user.id:
                await i.response.send_message("Estes botões não são para você.", ephemeral=True)
                return False
            return True
        @discord.ui.button(label="Confirmar Abertura do Carrinho", style=discord.ButtonStyle.success, emoji="✅")
        async def confirm(self, b, i):
            for item in self.children: item.disabled = True
            await self.original_interaction.edit_original_response(view=self)
            await i.response.send_modal(RobuxOrderModal(self.cog, self.purchase_type))
        @discord.ui.button(label="Cancelar Compra", style=discord.ButtonStyle.danger, emoji="❌")
        async def cancel(self, b, i):
            for item in self.children: item.disabled = True
            await i.response.edit_message(content="Sua compra foi cancelada.", view=self, embed=None)

    class InitialPurchaseView(View):
        def __init__(self, cog_instance):
            super().__init__(timeout=None)
            self.cog = cog_instance
        @discord.ui.button(label="Comprar Robux", style=discord.ButtonStyle.success, custom_id="buy_robux", emoji="💰")
        async def buy_robux(self, b, i):
            await self.cog.start_purchase_flow(i, 'robux')
        @discord.ui.button(label="Comprar Gamepass de Jogo", style=discord.ButtonStyle.primary, custom_id="buy_gamepass", emoji="🎟️")
        async def buy_gamepass(self, b, i):
            await self.cog.start_purchase_flow(i, 'gamepass')
        @discord.ui.button(label="Ver Tabela de Preços", style=discord.ButtonStyle.secondary, custom_id="show_prices")
        async def show_prices(self, b, i):
            await log_command(self.cog.bot, i, is_button=True, button_id="Ver Tabela de Preços")
            e = discord.Embed(title="Tabela de Preços - IsraBuy", color=config.EMBED_COLOR)
            rp = "\n".join([f"**{a} Robux:** R$ {p:.2f}" for a, p in config.ROBUX_PRICES.items()])
            gp = "\n".join([f"**{a} Robux:** R$ {p:.2f}" for a, p in config.GAMEPASS_PRICES.items()])
            e.add_field(name="💰 Compra Direta (Robux)", value=rp, inline=True)
            e.add_field(name="🎟️ Compra via Gamepass", value=gp, inline=True)
            await i.response.send_message(embed=e, ephemeral=True)

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(self.InitialPurchaseView(self))
        print("View de vendas registrada.")
        
    @commands.slash_command(name="iniciarvendas", description="Cria o painel de vendas de Robux e Gamepass.", guild_ids=[config.GUILD_ID])
    @commands.has_any_role(*config.ATTENDANT_ROLE_IDS)
    async def start_sales(self, ctx: discord.ApplicationContext):
        e = discord.Embed(title="🛒 Central de Pedidos da IsraBuy", description="Clique em um dos botões abaixo para comprar!", color=config.EMBED_COLOR)
        c = self.bot.get_channel(config.PURCHASE_CHANNEL_ID)
        await c.send(embed=e, view=self.InitialPurchaseView(self))
        await ctx.respond("Painel de vendas criado!", ephemeral=True)

    async def start_purchase_flow(self, interaction: discord.Interaction, purchase_type: str):
        uid = interaction.user.id
        tid = await database.get_active_thread(uid)
        if tid:
            t = self.bot.get_channel(tid)
            if t and not getattr(t, 'archived', True):
                v = View(); v.add_item(Button(label="Ir para o Carrinho", style=discord.ButtonStyle.link, url=t.jump_url))
                return await interaction.response.send_message(f"❌ Você já possui um carrinho aberto em {t.mention}.", view=v, ephemeral=True)
            else:
                await database.set_active_thread(uid, None)
        e = discord.Embed(title="👋 Bem-vindo(a) à Loja IsraBuy!", color=config.EMBED_COLOR, description="**Prazos Importantes (Robux):**\n• **Entrega:** Em até 3 dias úteis.\n• **Crédito:** De 5 a 7 dias úteis para aparecer no seu saldo.")
        v = self.PrePurchaseConfirmationView(self, interaction, purchase_type)
        await interaction.response.send_message(embed=e, view=v, ephemeral=True)

    async def process_robux_order(self, interaction: discord.Interaction, nickname: str, amount_str: str):
        user = interaction.user
        try:
            amount = parse_robux_amount(amount_str)
            if not (100 <= amount <= 10000):
                return await interaction.followup.send("❌ Quantidade de Robux inválida (100-10.000).", ephemeral=True)
        except:
            return await interaction.followup.send("❌ Quantidade de Robux inválida. Use apenas números.", ephemeral=True)

        thread = await interaction.channel.create_thread(name=f"🛒 {amount} Robux - {nickname}", type=discord.ChannelType.private_thread)
        await database.set_active_thread(user.id, thread.id)
        
        users_to_add = {user, await interaction.guild.fetch_member(config.LEADER_ID)}
        for role_id in config.ATTENDANT_ROLE_IDS:
            role = interaction.guild.get_role(role_id)
            if role: users_to_add.update(role.members)
        for u in users_to_add:
            if u: 
                try: 
                    await thread.add_user(u)
                    await asyncio.sleep(0.5)
                except Exception as e: 
                    print(f"Não foi possível adicionar o usuário {u.id} ao tópico: {e}")
        
        try:
            view = View(); view.add_item(Button(label="Ver seu Carrinho", style=discord.ButtonStyle.link, url=thread.jump_url))
            await interaction.followup.send(f"✅ Carrinho criado! Continue aqui: {thread.mention}", view=view, ephemeral=True)
        except Exception as e:
            print(f"Falha ao enviar followup: {e}")

        try:
            await log_dm(self.bot, user, content=f"Seu carrinho na IsraBuy foi aberto.", view=view)
        except Exception as e:
            print(f"Falha ao enviar DM: {e}")

        price = config.calculate_robux_price(amount)
        embed = discord.Embed(title="✅ Pedido Iniciado", description="Para continuar, pague e envie o comprovante aqui.", color=config.EMBED_COLOR)
        embed.add_field(name="Nickname", value=f"`{nickname}`").add_field(name="Robux", value=f"`{amount}`").add_field(name="Valor a Pagar", value=f"**R$ {price:.2f}**")
        embed.add_field(name="Chave PIX", value=config.PIX_KEY, inline=False)
        
        qr_code_file = None
        if os.path.exists("assets/qrcode.png"):
            qr_code_file = discord.File("assets/qrcode.png", filename="qrcode.png")
            embed.set_image(url="attachment://qrcode.png")
        await thread.send(user.mention, embed=embed, file=qr_code_file)

        admin_channel = self.bot.get_channel(config.ADMIN_NOTIF_CHANNEL_ID)
        if admin_channel:
            try:
                admin_view = View(timeout=None)
                admin_view.add_item(Button(label="Atender Pedido", style=discord.ButtonStyle.success, custom_id=f"attend_order_{thread.id}_{user.id}"))
                await admin_channel.send(f"🛒 Novo carrinho de **Robux** para {user.mention} (`{nickname}`) foi aberto e aguarda um atendente.", view=admin_view)
            except Exception as e:
                print(f"Falha ao notificar admins: {e}")

        try:
            msg_receipt = await self.bot.wait_for('message', check=lambda m: m.author.id == user.id and m.channel.id == thread.id and m.attachments, timeout=172800.0)
            
            if isinstance(user, discord.Member):
                initial_role = interaction.guild.get_role(config.INITIAL_BUYER_ROLE_ID)
                if initial_role: await user.add_roles(initial_role)

            await thread.edit(name=f"🛒 {amount} Robux - {nickname} - Aguardando Entrega")
            approved_embed = discord.Embed(title="✅ Pagamento Recebido!", color=0x28a745, description="Seu comprovante foi recebido! Nossa equipe já está analisando.")
            await thread.send(embed=approved_embed)
            
            purchase_id = await database.add_purchase(user.id, f"{amount} Robux", price, self.bot.user.id, None)
            total_spent, purchase_count = await database.get_user_spend_and_count(user.id)
            if isinstance(user, discord.Member): await self.update_spend_roles(user, total_spent)
            
            delivery_log_channel = self.bot.get_channel(config.DELIVERY_LOG_CHANNEL_ID)
            if delivery_log_channel:
                log_embed = discord.Embed(description=f"Obrigado, {user.mention}, por comprar conosco!", color=0x28a745, timestamp=datetime.datetime.now())
                log_embed.set_author(name="🛒 Nova Compra na IsraBuy!", icon_url=self.bot.user.display_avatar.url)
                log_embed.set_thumbnail(url=user.display_avatar.url)
                log_embed.add_field(name="Produto Comprado", value=f"{amount} Robux").add_field(name="Valor Pago", value=f"R$ {price:.2f}")
                compra_str = "🎉 **Primeira compra!**" if purchase_count == 1 else f"Esta é a **{purchase_count}ª compra**."
                log_embed.add_field(name="Histórico", value=compra_str).add_field(name="Total Gasto", value=f"R$ {total_spent:.2f}")
                await delivery_log_channel.send(embed=log_embed)

            tutorial_view = View(); tutorial_view.add_item(Button(label="Ver Tutorial em Vídeo", style=discord.ButtonStyle.link, url=config.TUTORIAL_VIDEO_URL, emoji="🎥"))
            await thread.send("A entrega é via Gamepass e pode demorar de 5 a 7 dias. Por favor, crie sua Gamepass e aguarde um atendente.", view=tutorial_view)

        except asyncio.TimeoutError:
            await thread.send("Seu pedido expirou."); await asyncio.sleep(5)
            await database.set_active_thread(user.id, None)
            await thread.edit(archived=True, locked=True)

    async def process_gamepass_order(self, interaction: discord.Interaction, nickname: str, amount_str: str):
        user = interaction.user
        try:
            amount = parse_robux_amount(amount_str)
            if not (100 <= amount <= 10000):
                return await interaction.followup.send("❌ Quantidade inválida (100-10.000).", ephemeral=True)
        except:
            return await interaction.followup.send("❌ Quantidade inválida.", ephemeral=True)

        thread = await interaction.channel.create_thread(name=f"🎟️ Gamepass - {nickname}", type=discord.ChannelType.private_thread)
        await database.set_active_thread(user.id, thread.id)
        
        users_to_add = {user, await interaction.guild.fetch_member(config.LEADER_ID)}
        for role_id in config.ATTENDANT_ROLE_IDS:
            role = interaction.guild.get_role(role_id)
            if role: users_to_add.update(role.members)
        for u in users_to_add:
            if u: 
                try: 
                    await thread.add_user(u)
                    await asyncio.sleep(0.5)
                except Exception as e:
                    print(f"Não foi possível adicionar o usuário {u.id} ao tópico: {e}")

        view = View(); view.add_item(Button(label="Ver seu Carrinho", style=discord.ButtonStyle.link, url=thread.jump_url))
        await interaction.followup.send(f"✅ Carrinho criado! Continue aqui: {thread.mention}", view=view, ephemeral=True)
        await log_dm(self.bot, user, content=f"Seu carrinho de Gamepass foi aberto.", view=view)

        price = config.calculate_gamepass_price(amount)
        embed = discord.Embed(title="✅ Pedido Iniciado", description="Para continuar, pague e envie o comprovante.", color=config.EMBED_COLOR)
        embed.add_field(name="Nickname", value=f"`{nickname}`").add_field(name="Robux", value=f"`{amount}`").add_field(name="Valor a Pagar", value=f"**R$ {price:.2f}**")
        embed.add_field(name="Chave PIX", value=config.PIX_KEY, inline=False)
        
        qr_code_file = None
        if os.path.exists("assets/qrcode.png"):
            qr_code_file = discord.File("assets/qrcode.png", filename="qrcode.png")
            embed.set_image(url="attachment://qrcode.png")
        await thread.send(user.mention, embed=embed, file=qr_code_file)

        admin_channel = self.bot.get_channel(config.ADMIN_NOTIF_CHANNEL_ID)
        if admin_channel:
            admin_view = View(timeout=None)
            admin_view.add_item(Button(label="Atender Pedido", style=discord.ButtonStyle.primary, custom_id=f"attend_order_{thread.id}_{user.id}"))
            await admin_channel.send(f"🎟️ Novo carrinho de **Gamepass** para {user.mention} (`{nickname}`) foi aberto.", view=admin_view)

        try:
            msg_receipt = await self.bot.wait_for('message', check=lambda m: m.author.id == user.id and m.channel.id == thread.id and m.attachments, timeout=172800.0)
            
            if isinstance(user, discord.Member):
                initial_role = interaction.guild.get_role(config.INITIAL_BUYER_ROLE_ID)
                if initial_role: await user.add_roles(initial_role)

            await thread.edit(name=f"🎟️ {amount} Gamepass - {nickname} - Aguardando Entrega")
            approved_embed = discord.Embed(title="✅ Pagamento Recebido!", color=0x28a745, description="Seu comprovante foi recebido! Nossa equipe já está analisando.")
            await thread.send(embed=approved_embed)

            await database.add_purchase(user.id, f"{amount} Robux (Gamepass)", price, self.bot.user.id, None)
            total_spent, purchase_count = await database.get_user_spend_and_count(user.id)
            if isinstance(user, discord.Member): await self.update_spend_roles(user, total_spent)

            delivery_log_channel = self.bot.get_channel(config.DELIVERY_LOG_CHANNEL_ID)
            if delivery_log_channel:
                log_embed = discord.Embed(description=f"Obrigado, {user.mention}, por comprar conosco!", color=0x28a745, timestamp=datetime.datetime.now())
                log_embed.set_author(name="🎟️ Nova Compra de Gamepass na IsraBuy!", icon_url=self.bot.user.display_avatar.url)
                log_embed.set_thumbnail(url=user.display_avatar.url)
                log_embed.add_field(name="Produto Comprado", value=f"{amount} Robux (Gamepass)").add_field(name="Valor Pago", value=f"R$ {price:.2f}")
                compra_str = "🎉 **Primeira compra!**" if purchase_count == 1 else f"Esta é a **{purchase_count}ª compra**."
                log_embed.add_field(name="Histórico", value=compra_str).add_field(name="Total Gasto", value=f"R$ {total_spent:.2f}")
                await delivery_log_channel.send(embed=log_embed)

            await thread.send("Obrigado! Agora, por favor, envie o **link do seu jogo** e aguarde um atendente.")

        except asyncio.TimeoutError:
            await thread.send("Seu pedido expirou."); await asyncio.sleep(5)
            await database.set_active_thread(user.id, None)
            await thread.edit(archived=True, locked=True)

def setup(bot):
    bot.add_cog(SalesCog(bot))
