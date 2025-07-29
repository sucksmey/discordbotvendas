# cogs/admin_cog.py
import discord
from discord.ext import commands
from discord.ui import View, Button
from discord import option
import datetime

import config
import database
from utils.logger import log_dm

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def update_user_roles_by_spend(self, member: discord.Member, total_spent: float):
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

    @commands.slash_command(name="entregue", description="[BACKUP] Registra uma entrega que falhou na automação.")
    @option("cliente", discord.Member, description="O cliente que recebeu o pedido.")
    @option("produto", str, description="O nome do produto vendido. Ex: 1000 Robux")
    @option("valor", float, description="O valor da compra.")
    @option("atendente", discord.Member, description="Quem atendeu o pedido.")
    @commands.has_any_role(*config.ATTENDANT_ROLE_IDS)
    async def entregue(self, ctx: discord.ApplicationContext, cliente: discord.Member, produto: str, valor: float, atendente: discord.Member):
        entregador = ctx.author
        purchase_id = await database.add_purchase(cliente.id, produto, valor, atendente.id, entregador.id)
        total_spent, purchase_count = await database.get_user_spend_and_count(cliente.id)
        await self.update_user_roles_by_spend(cliente, total_spent)
        await database.set_active_thread(cliente.id, None)
        
        review_view = View(timeout=None); review_view.add_item(Button(label="⭐ Avaliar esta Compra", style=discord.ButtonStyle.success, custom_id=f"review_purchase_{purchase_id}"))
        await log_dm(self.bot, cliente, content="Sua compra foi registrada manualmente! Agradecemos a preferência.", view=review_view)
        await ctx.channel.send("Após receber seu produto, por favor, deixe sua avaliação clicando no botão abaixo!", view=review_view)

        delivery_log_channel = self.bot.get_channel(config.DELIVERY_LOG_CHANNEL_ID)
        if delivery_log_channel:
            log_embed = discord.Embed(description=f"Obrigado, {cliente.mention}, por comprar conosco!", color=0x28a745, timestamp=datetime.datetime.now())
            log_embed.set_author(name="🛒 Nova Compra (MANUAL) na IsraBuy!", icon_url=self.bot.user.display_avatar.url)
            log_embed.set_thumbnail(url=cliente.display_avatar.url)
            log_embed.add_field(name="Produto", value=produto).add_field(name="Valor", value=f"R$ {valor:.2f}")
            log_embed.add_field(name="Histórico", value=f"Esta é a **{purchase_count}ª compra**.").add_field(name="Total Gasto", value=f"R$ {total_spent:.2f}")
            log_embed.add_field(name="Atendido por", value=atendente.mention, inline=True).add_field(name="Entregue por", value=entregador.mention, inline=True)
            await delivery_log_channel.send(embed=log_embed)
        
        await ctx.respond(f"✅ Compra manual para {cliente.mention} registrada com sucesso!", ephemeral=True)

    @commands.slash_command(name="addcompra", description="[LEGADO] Adiciona uma compra antiga e atualiza os cargos.")
    @commands.has_any_role(*config.ATTENDANT_ROLE_IDS)
    @option("cliente", discord.Member, description="O cliente que fez a compra.")
    @option("produto", str, description="O nome do produto vendido.")
    @option("valor", float, description="O valor da compra.")
    async def addcompra(self, ctx: discord.ApplicationContext, cliente: discord.Member, produto: str, valor: float):
        await database.add_purchase(cliente.id, produto, valor, ctx.author.id, ctx.author.id)
        total_spent, _ = await database.get_user_spend_and_count(cliente.id)
        await self.update_user_roles_by_spend(cliente, total_spent)
        await ctx.respond(f"Compra antiga de '{produto}' para {cliente.mention} adicionada! Cargos por gasto atualizados.", ephemeral=True)

    @commands.slash_command(name="fechar", description="Fecha e arquiva um carrinho inativo.")
    @commands.has_any_role(*config.ATTENDANT_ROLE_IDS)
    @option("cliente", discord.Member, description="O cliente dono do carrinho a ser fechado.")
    @option("motivo", str, description="O motivo do fechamento (opcional).", required=False)
    async def fechar(self, ctx: discord.ApplicationContext, cliente: discord.Member, motivo: str = "Carrinho fechado pela equipe."):
        if not isinstance(ctx.channel, discord.Thread):
            return await ctx.respond("Este comando só pode ser usado em um tópico.", ephemeral=True)
        await ctx.respond("Fechando carrinho...", ephemeral=True)
        await database.set_active_thread(cliente.id, None)
        embed = discord.Embed(title="🛒 Carrinho Fechado", description=f"Este carrinho foi fechado por {ctx.author.mention}.\n**Motivo:** {motivo}", color=discord.Color.red())
        try:
            await ctx.channel.send(embed=embed)
            log_channel = self.bot.get_channel(config.GENERAL_LOG_CHANNEL_ID)
            if log_channel: await log_channel.send(f"🔒 O carrinho `{ctx.channel.name}` de {cliente.mention} foi fechado por {ctx.author.mention}.")
            await ctx.channel.edit(archived=True, locked=True)
        except Exception as e: print(f"Erro ao fechar o tópico: {e}")

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        custom_id = interaction.data.get("custom_id", "")
        if not custom_id.startswith("follow_up_"): return
        if not any(r.id in config.ATTENDANT_ROLE_IDS for r in interaction.user.roles):
            return await interaction.response.send_message("Você não tem permissão.", ephemeral=True)
        await interaction.response.defer()
        user_id = int(custom_id.split("_")[2])
        cliente = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
        entregador = interaction.user
        if cliente:
            await log_dm(self.bot, entregador, content=f"Olá! Você iniciou o acompanhamento da entrega para **{cliente.display_name}**. Entre em contato com o cliente para finalizar a entrega.")
        await (await interaction.original_response()).edit(content=f"Acompanhamento para {cliente.mention} iniciado por {entregador.mention}!", view=None)

def setup(bot):
    bot.add_cog(AdminCog(bot))
