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

    @commands.slash_command(name="entregue", description="Finaliza um pedido de ROBUX/GAMEPASS.")
    @option("cliente", discord.Member, description="O cliente que recebeu o pedido.")
    @option("produto", str, description="O nome do produto vendido. Ex: 1000 Robux")
    @option("valor", float, description="O valor da compra.")
    @option("atendente", discord.Member, description="Quem atendeu o pedido.")
    @commands.has_any_role(*config.ATTENDANT_ROLE_IDS)
    async def entregue(self, ctx: discord.ApplicationContext, cliente: discord.Member, produto: str, valor: float, atendente: discord.Member):
        entregador = ctx.author

        purchase_id, purchase_count = await database.add_purchase(cliente.id, produto, valor, atendente.id, entregador.id)
        total_spent = await database.get_user_spend(cliente.id)
        
        await database.set_active_thread(cliente.id, None)

        review_view = View(timeout=None)
        review_view.add_item(Button(
            label="⭐ Avaliar esta Compra",
            style=discord.ButtonStyle.success,
            custom_id=f"review_purchase_{purchase_id}"
        ))
        dm_embed = discord.Embed(title="🎉 Pedido Entregue!", description=f"Olá, {cliente.display_name}! Seu produto **({produto})** foi entregue com sucesso.", color=config.EMBED_COLOR)
        await log_dm(self.bot, cliente, embed=dm_embed, view=review_view)

        delivery_log_channel = self.bot.get_channel(config.DELIVERY_LOG_CHANNEL_ID)
        if delivery_log_channel:
            log_embed = discord.Embed(description=f"Obrigado, {cliente.mention}, por comprar conosco!", color=0x28a745, timestamp=datetime.datetime.now())
            log_embed.set_author(name="🛒 Nova Compra na IsraBuy!", icon_url=self.bot.user.display_avatar.url)
            log_embed.set_thumbnail(url=cliente.display_avatar.url)
            log_embed.add_field(name="Produto Comprado", value=produto, inline=False)
            log_embed.add_field(name="Valor Pago", value=f"R$ {valor:.2f}", inline=False)
            compra_str = "🎉 **Esta é a primeira compra!**" if purchase_count == 1 else f"Esta é a **{purchase_count}ª compra** do cliente."
            log_embed.add_field(name="Histórico do Cliente", value=compra_str, inline=False)
            log_embed.add_field(name="Total Gasto na Loja", value=f"R$ {float(total_spent):.2f}", inline=False)
            log_embed.add_field(name="Atendido por", value=atendente.mention, inline=True)
            log_embed.add_field(name="Entregue por", value=entregador.mention, inline=True)
            vip_role = ctx.guild.get_role(config.VIP_ROLE_ID)
            if vip_role and vip_role in cliente.roles:
                log_embed.add_field(name="Status", value="⭐ **Cliente VIP**", inline=False)
            await delivery_log_channel.send(embed=log_embed)

        loyalty_channel = self.bot.get_channel(config.LOYALTY_LOG_CHANNEL_ID)
        if loyalty_channel:
            loyalty_embed = self.create_loyalty_embed(cliente, purchase_count)
            await loyalty_channel.send(embed=loyalty_embed)
        
        await ctx.respond(f"O pedido de {cliente.mention} foi marcado como entregue e seu acesso a novos carrinhos foi liberado!", ephemeral=True)

    @commands.slash_command(name="entregueitem", description="Finaliza a entrega de um item com estoque (Extras, etc).")
    @commands.has_any_role(*config.ATTENDANT_ROLE_IDS)
    @option("cliente", discord.Member, description="O cliente que recebeu o pedido.")
    @option("item_id", int, description="O ID do produto que foi vendido.")
    @option("atendente", discord.Member, description="Quem atendeu o pedido.")
    async def entregue_item(self, ctx: discord.ApplicationContext, cliente: discord.Member, item_id: int, atendente: discord.Member):
        entregador = ctx.author
        
        product = await database.get_product_by_id(item_id)
        if not product:
            return await ctx.respond("❌ Produto com este ID não encontrado.", ephemeral=True)
        
        if product['stock'] <= 0:
            await ctx.respond(f"⚠️ Atenção: O estoque de **{product['name']}** já está zerado. A venda será registrada, mas verifique o estoque.", ephemeral=True)

        await database.update_stock(item_id, -1)
        
        product_name = product['name']
        price = float(product['price'])
        purchase_id, purchase_count = await database.add_purchase(cliente.id, product_name, price, atendente.id, entregador.id)
        total_spent = await database.get_user_spend(cliente.id)
        await database.set_active_thread(cliente.id, None)

        review_view = View(timeout=None)
        review_view.add_item(Button(label="⭐ Avaliar esta Compra", style=discord.ButtonStyle.success, custom_id=f"review_purchase_{purchase_id}"))
        dm_embed = discord.Embed(title="🎉 Pedido Entregue!", description=f"Olá, {cliente.display_name}! Seu produto **({product_name})** foi entregue com sucesso. Agradecemos a preferência!", color=config.EMBED_COLOR)
        await log_dm(self.bot, cliente, embed=dm_embed, view=review_view)

        delivery_log_channel = self.bot.get_channel(config.DELIVERY_LOG_CHANNEL_ID)
        if delivery_log_channel:
            log_embed = discord.Embed(description=f"Obrigado, {cliente.mention}, por comprar conosco!", color=0x28a745, timestamp=datetime.datetime.now())
            log_embed.set_author(name=f"✨ Nova Compra de Item na IsraBuy!", icon_url=self.bot.user.display_avatar.url)
            log_embed.set_thumbnail(url=cliente.display_avatar.url)
            log_embed.add_field(name="Produto Comprado", value=product_name, inline=False)
            log_embed.add_field(name="Valor Pago", value=f"R$ {price:.2f}", inline=False)
            compra_str = "🎉 **Esta é a primeira compra!**" if purchase_count == 1 else f"Esta é a **{purchase_count}ª compra** do cliente."
            log_embed.add_field(name="Histórico do Cliente", value=compra_str, inline=False)
            log_embed.add_field(name="Total Gasto na Loja", value=f"R$ {float(total_spent):.2f}", inline=False)
            log_embed.add_field(name="Atendido por", value=atendente.mention, inline=True)
            log_embed.add_field(name="Entregue por", value=entregador.mention, inline=True)
            await delivery_log_channel.send(embed=log_embed)
        
        loyalty_channel = self.bot.get_channel(config.LOYALTY_LOG_CHANNEL_ID)
        if loyalty_channel:
            loyalty_embed = self.create_loyalty_embed(cliente, purchase_count)
            await loyalty_channel.send(embed=loyalty_embed)

        await ctx.respond(f"✅ Entrega do item **{product_name}** para {cliente.mention} confirmada! Estoque atualizado.", ephemeral=True)

    @commands.slash_command(name="addcompra", description="Adiciona manualmente uma compra antiga para um usuário.")
    @option("cliente", discord.Member, description="O cliente que fez a compra.")
    @option("produto", str, description="O nome do produto vendido.")
    @option("valor", float, description="O valor da compra.")
    @commands.has_any_role(*config.ATTENDANT_ROLE_IDS)
    async def addcompra(self, ctx: discord.ApplicationContext, cliente: discord.Member, produto: str, valor: float):
         await database.add_purchase(cliente.id, produto, valor, ctx.author.id, ctx.author.id)
         await ctx.respond(f"Compra manual de '{produto}' para {cliente.mention} adicionada com sucesso.", ephemeral=True)

    @commands.slash_command(name="setfidelidade", description="Define o número de compras de um usuário para a fidelidade.")
    @option("cliente", discord.Member, description="O cliente a ser modificado.")
    @option("compras", int, description="O número total de compras.")
    @commands.has_any_role(*config.ATTENDANT_ROLE_IDS)
    async def setfidelidade(self, ctx: discord.ApplicationContext, cliente: discord.Member, compras: int):
        await database.set_purchase_count(cliente.id, compras)
        await ctx.respond(f"A contagem de compras de {cliente.mention} foi definida para **{compras}**.", ephemeral=True)
    
    @commands.slash_command(name="fechar", description="Fecha e arquiva um carrinho de compras inativo.")
    @commands.has_any_role(*config.ATTENDANT_ROLE_IDS)
    @option("cliente", discord.Member, description="O cliente dono do carrinho a ser fechado.")
    @option("motivo", str, description="O motivo para fechar o carrinho (opcional).", required=False)
    async def fechar(self, ctx: discord.ApplicationContext, cliente: discord.Member, motivo: str = "Carrinho fechado pela equipe."):
        if not isinstance(ctx.channel, discord.Thread):
            return await ctx.respond("Este comando só pode ser usado em um tópico (carrinho).", ephemeral=True)
            
        await ctx.respond("Fechando e arquivando este carrinho...", ephemeral=True)
        await database.set_active_thread(cliente.id, None)
        close_embed = discord.Embed(title="🛒 Carrinho Fechado", description=f"Este carrinho foi fechado por {ctx.author.mention}.\n**Motivo:** {motivo}", color=discord.Color.red())
        try:
            await ctx.channel.send(embed=close_embed)
            log_channel = self.bot.get_channel(config.GENERAL_LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(f"🔒 O carrinho `{ctx.channel.name}` de {cliente.mention} foi fechado por {ctx.author.mention}.")
            await ctx.channel.edit(archived=True, locked=True)
        except Exception as e:
            print(f"Erro ao fechar o tópico: {e}")
            await ctx.followup.send("Ocorreu um erro ao fechar o tópico.", ephemeral=True)

    def create_loyalty_embed(self, user: discord.Member, count: int):
        embed = discord.Embed(title=f"🌟 Programa de Fidelidade de {user.display_name}", description=f"{user.mention} tem atualmente **{count} compras verificadas**.", color=config.EMBED_COLOR)
        embed.set_thumbnail(url=user.display_avatar.url)
        for required, title, reward in config.LOYALTY_TIERS:
            if count >= required:
                embed.add_field(name=f"✅ {title}", value=reward, inline=False)
            else:
                embed.add_field(name=f"❌ {title}", value=reward, inline=False)
        return embed

def setup(bot):
    bot.add_cog(AdminCog(bot))
