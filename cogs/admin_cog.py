# cogs/admin_cog.py
import discord
from discord.ext import commands
from discord import option
import datetime

import config
import database
from utils.logger import log_dm, log_command

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # COMANDO /entregue
    @commands.slash_command(name="entregue", description="Finaliza um pedido, registrando no DB e notificando o cliente.")
    @option("cliente", discord.Member, description="O cliente que recebeu o pedido.")
    @option("produto", str, description="O nome do produto vendido. Ex: 1000 Robux")
    @option("valor", float, description="O valor da compra.")
    @option("atendente", discord.Member, description="Quem atendeu o pedido.")
    @commands.has_any_role(*config.ATTENDANT_ROLE_IDS)
    async def entregue(self, ctx: discord.ApplicationContext, cliente: discord.Member, produto: str, valor: float, atendente: discord.Member):
        entregador = ctx.author

        purchase_count = await database.add_purchase(cliente.id, produto, valor, atendente.id, entregador.id)
        
        dm_embed = discord.Embed(title="🎉 Pedido Entregue!", color=config.EMBED_COLOR)
        dm_embed.description = (
            f"Olá, {cliente.display_name}! Seu produto **({produto})** foi entregue com sucesso.\n\n"
            f"Você pode verificar o saldo pendente de Robux em: [Roblox Transactions]({config.PENDING_ROBUX_URL})\n\n"
            "**Obrigado pela sua preferência!**"
        )
        vip_role = cliente.get_role(config.VIP_ROLE_ID)
        if vip_role:
             dm_embed.add_field(name="⭐ Benefício VIP", value=f"Como VIP, você pode comprar 1k de Robux por R${config.VIP_ROBUX_DEAL_PRICE:.2f} até {config.VIP_DEAL_USES_PER_MONTH}x por mês.", inline=False)

        await log_dm(self.bot, cliente, embed=dm_embed)

        loyalty_channel = self.bot.get_channel(config.LOYALTY_LOG_CHANNEL_ID)
        if loyalty_channel:
            loyalty_embed = self.create_loyalty_embed(cliente, purchase_count)
            await loyalty_channel.send(embed=loyalty_embed)
        
        await ctx.respond(f"O pedido de {cliente.mention} foi marcado como entregue e registrado!", ephemeral=True)

    # COMANDO /addcompra
    @commands.slash_command(name="addcompra", description="Adiciona manualmente uma compra antiga para um usuário.")
    @option("cliente", discord.Member, description="O cliente que fez a compra.")
    @option("produto", str, description="O nome do produto vendido.")
    @option("valor", float, description="O valor da compra.")
    @commands.has_any_role(*config.ATTENDANT_ROLE_IDS)
    async def addcompra(self, ctx: discord.ApplicationContext, cliente: discord.Member, produto: str, valor: float):
         await database.add_purchase(cliente.id, produto, valor, ctx.author.id, ctx.author.id)
         await ctx.respond(f"Compra manual de '{produto}' para {cliente.mention} adicionada com sucesso.", ephemeral=True)

    # COMANDO /setfidelidade
    @commands.slash_command(name="setfidelidade", description="Define o número de compras de um usuário para a fidelidade.")
    @option("cliente", discord.Member, description="O cliente a ser modificado.")
    @option("compras", int, description="O número total de compras.")
    @commands.has_any_role(*config.ATTENDANT_ROLE_IDS)
    async def setfidelidade(self, ctx: discord.ApplicationContext, cliente: discord.Member, compras: int):
        await database.set_purchase_count(cliente.id, compras)
        await ctx.respond(f"A contagem de compras de {cliente.mention} foi definida para **{compras}**.", ephemeral=True)
    
    # NOVO COMANDO /fechar
    @commands.slash_command(
        name="fechar",
        description="Fecha e arquiva o carrinho de compras atual.",
        guild_ids=[config.GUILD_ID]
    )
    @option("motivo", str, description="O motivo para fechar o carrinho (opcional).", required=False)
    @commands.has_any_role(*config.ATTENDANT_ROLE_IDS)
    async def fechar(self, ctx: discord.ApplicationContext, motivo: str = "Carrinho fechado pela equipe por inatividade."):
        if not isinstance(ctx.channel, discord.Thread):
            await ctx.respond("Este comando só pode ser usado em um carrinho (tópico).", ephemeral=True)
            return

        if not ctx.channel.name.startswith("🛒-"):
            await ctx.respond("Este não parece ser um carrinho de compras válido.", ephemeral=True)
            return
            
        await ctx.respond("Fechando e arquivando este carrinho...", ephemeral=True)

        close_embed = discord.Embed(
            title="🛒 Carrinho Fechado",
            description=f"Este carrinho foi fechado por {ctx.author.mention}.\n**Motivo:** {motivo}",
            color=discord.Color.red()
        )
        try:
            await ctx.channel.send(embed=close_embed)
            
            log_channel = self.bot.get_channel(config.GENERAL_LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(f"🔒 O carrinho `{ctx.channel.name}` foi fechado por {ctx.author.mention}. Motivo: {motivo}")

            await ctx.channel.edit(archived=True, locked=True)
        except Exception as e:
            print(f"Erro ao fechar o tópico: {e}")
            await ctx.followup.send("Ocorreu um erro ao fechar o tópico.", ephemeral=True)


    def create_loyalty_embed(self, user: discord.Member, count: int):
        embed = discord.Embed(
            title=f"🌟 Programa de Fidelidade de {user.display_name}",
            description=f"{user.mention} tem atualmente **{count} compras verificadas**.",
            color=config.EMBED_COLOR
        )
        embed.set_thumbnail(url=user.display_avatar.url)

        for required, title, reward in config.LOYALTY_TIERS:
            if count >= required:
                embed.add_field(name=f"✅ {title}", value=reward, inline=False)
            else:
                embed.add_field(name=f"❌ {title}", value=reward, inline=False)
        return embed

def setup(bot):
    bot.add_cog(AdminCog(bot))
