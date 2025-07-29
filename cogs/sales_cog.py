# cogs/sales_cog.py
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, InputText
import asyncio
import re

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
        super().__init__(title="Iniciar Compra de Robux")
        self.cog = cog
        self.purchase_type = purchase_type
        self.add_item(InputText(label="Seu nickname no Roblox", placeholder="Ex: construtordomundo123", required=True))
        self.add_item(InputText(label="Quantidade de Robux", placeholder="Ex: 1000, 1.5k, 2000", required=True))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        nickname = self.children[0].value
        amount_str = self.children[1].value
        await self.cog.process_robux_order(interaction, nickname, amount_str, self.purchase_type)

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
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove, reason="Atualização de cargo por gasto")
            if not any(r.id == highest_role_to_add for r in member.roles):
                role_to_add = member.guild.get_role(highest_role_to_add)
                if role_to_add:
                    await member.add_roles(role_to_add, reason=f"Atingiu R$ {total_spent:.2f} em gastos")

    class PrePurchaseConfirmationView(View):
        def __init__(self, cog, interaction, purchase_type):
            super().__init__(timeout=180)
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
            for item in self.children: item.disabled = True
            await self.interaction.edit_original_response(view=self)
            await interaction.response.send_modal(RobuxOrderModal(self.cog, self.purchase_type))
        
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

    async def process_robux_order(self, interaction: discord.Interaction, nickname: str, amount_str: str, purchase_type: str):
        user = interaction.user
        try:
            amount = parse_robux_amount(amount_str)
            if not (100 <= amount <= 10000):
                await interaction.followup.send("❌ Quantidade de Robux inválida (mín: 100, máx: 10.000).", ephemeral=True)
                return
        except (ValueError, TypeError):
            await interaction.followup.send("❌ Quantidade de Robux inválida. Por favor, use apenas números.", ephemeral=True)
            return

        thread = await interaction.channel.create_thread(name=f"🛒 {amount} Robux - {nickname}", type=discord.ChannelType.private_thread)
        await database.set_active_thread(user.id, thread.id)
        
        for u in [user] + [await interaction.guild.fetch_member(config.LEADER_ID)]:
            if u: await thread.add_user(u)
        for role_id in config.ATTENDANT_ROLE_IDS:
            role = interaction.guild.get_role(role_id)
            if role:
                for member in role.members:
                    try: await thread.add_user(member)
                    except Exception: pass
        
        view = View(); view.add_item(Button(label="Ver seu Carrinho", style=discord.ButtonStyle.link, url=thread.jump_url))
        await interaction.followup.send(f"✅ Carrinho criado! Continue sua compra aqui: {thread.mention}", view=view, ephemeral=True)
        await log_dm(self.bot, user, content=f"Seu carrinho na IsraBuy foi aberto.", view=view)

        price = config.calculate_robux_price(amount) if purchase_type == 'robux' else config.calculate_gamepass_price(amount)

        embed = discord.Embed(title="✅ Pedido Iniciado", description="Para continuar, realize o pagamento e envie o comprovante de pagamento aqui no chat.", color=config.EMBED_COLOR)
        embed.add_field(name="Nickname Roblox", value=f"`{nickname}`").add_field(name="Quantidade", value=f"`{amount}`").add_field(name="Valor a Pagar", value=f"**R$ {price:.2f}**")
        embed.add_field(name="Chave PIX", value=config.PIX_KEY, inline=False)
        await thread.send(user.mention, embed=embed)

        try:
            msg_receipt = await self.bot.wait_for('message', check=lambda m: m.author.id == user.id and m.channel.id == thread.id and m.attachments, timeout=172800.0)
            
            initial_role = interaction.guild.get_role(config.INITIAL_BUYER_ROLE_ID)
            if initial_role: await user.add_roles(initial_role)

            await thread.edit(name=f"🛒 {amount} R$ - {nickname} - Aguardando Entrega")

            approved_embed = discord.Embed(title="✅ Pagamento Aprovado!", color=0x28a745, description="Seu pagamento foi aprovado com sucesso! Confira abaixo as informações da sua compra.")
            approved_embed.add_field(name="Nome no Roblox", value=nickname).add_field(name="Valor em Robux", value=str(amount)).add_field(name="Valor em Reais", value=f"R$ {price:.2f}")
            approved_embed.add_field(name="Entrega", value="Sua compra será entregue em até 72 Horas Úteis por um de nossos entregadores.")
            await thread.send(embed=approved_embed)
            
            delivery_channel = self.bot.get_channel(config.AWAITING_DELIVERY_CHANNEL_ID)
            if delivery_channel: await delivery_channel.send(f"⏳ O usuário {user.mention} (`{nickname}`) está aguardando a entrega de **{amount} Robux**.")
            
            attendant_bot_id = self.bot.user.id
            purchase_id = await database.add_purchase(user.id, f"{amount} Robux", price, attendant_bot_id, None)

            total_spent, _ = await database.get_user_spend_and_count(user.id)
            await self.update_spend_roles(user, total_spent)
            
            review_view = View(timeout=None); review_view.add_item(Button(label="⭐ Avaliar Compra", style=discord.ButtonStyle.success, custom_id=f"review_purchase_{purchase_id}"))
            await log_dm(self.bot, user, content="Sua compra foi aprovada! Quando receber, por favor, nos avalie.", view=review_view)
            await thread.send("Após a entrega ser concluída, por favor, deixe sua avaliação clicando no botão abaixo!", view=review_view)

            follow_up_channel = self.bot.get_channel(config.FOLLOW_UP_CHANNEL_ID)
            if follow_up_channel:
                follow_up_view = View(timeout=None)
                follow_up_view.add_item(Button(label="Iniciar Acompanhamento", style=discord.ButtonStyle.primary, custom_id=f"follow_up_{user.id}"))
                await follow_up_channel.send(f"Compra de {user.mention} aprovada. Um entregador precisa iniciar o acompanhamento.", view=follow_up_view)

            await thread.send(f"Obrigado! A entrega é via Gamepass. Para continuar, por favor, envie o link do seu jogo/passe. Um atendente irá te guiar com os próximos passos.")

        except asyncio.TimeoutError:
            await thread.send("Seu pedido expirou por inatividade."); await asyncio.sleep(5)
            await database.set_active_thread(user.id, None)
            await thread.edit(archived=True, locked=True)

def setup(bot):
    bot.add_cog(SalesCog(bot))
