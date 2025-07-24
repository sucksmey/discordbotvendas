# cogs/stock_cog.py
import discord
from discord.ext import commands
from discord import option

import config
import database

class StockCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="additem", description="Adiciona um novo item ao estoque.", guild_ids=[config.GUILD_ID])
    @commands.has_any_role(*config.ATTENDANT_ROLE_IDS)
    @option("nome", str, description="Nome do produto.")
    @option("preco", float, description="Preço do produto (ex: 7.50).")
    @option("estoque", int, description="Quantidade inicial em estoque.")
    @option("categoria", str, description="Categoria do item (ex: Extras, GiftCards).")
    async def add_item(self, ctx: discord.ApplicationContext, nome: str, preco: float, estoque: int, categoria: str):
        await database.add_product(nome, preco, estoque, categoria.capitalize())
        await ctx.respond(f"✅ Produto **{nome}** adicionado à categoria **{categoria.capitalize()}** com estoque de **{estoque}**.", ephemeral=True)

    @commands.slash_command(name="addstock", description="Adiciona mais unidades ao estoque de um item.", guild_ids=[config.GUILD_ID])
    @commands.has_any_role(*config.ATTENDANT_ROLE_IDS)
    @option("item_id", int, description="ID do produto a ser atualizado.")
    @option("quantidade", int, description="Quantidade a ser ADICIONADA ao estoque.")
    async def add_stock(self, ctx: discord.ApplicationContext, item_id: int, quantidade: int):
        product = await database.get_product_by_id(item_id)
        if not product:
            return await ctx.respond("❌ Produto não encontrado com este ID.", ephemeral=True)
        
        await database.update_stock(item_id, quantidade)
        new_stock = product['stock'] + quantidade
        await ctx.respond(f"✅ Estoque de **{product['name']}** atualizado para **{new_stock}** unidades.", ephemeral=True)

    @commands.slash_command(name="setstock", description="Define um valor exato para o estoque de um item.", guild_ids=[config.GUILD_ID])
    @commands.has_any_role(*config.ATTENDANT_ROLE_IDS)
    @option("item_id", int, description="ID do produto a ser atualizado.")
    @option("quantidade", int, description="Novo valor total do estoque.")
    async def set_stock(self, ctx: discord.ApplicationContext, item_id: int, quantidade: int):
        product = await database.get_product_by_id(item_id)
        if not product:
            return await ctx.respond("❌ Produto não encontrado com este ID.", ephemeral=True)
            
        await database.set_stock(item_id, quantidade)
        await ctx.respond(f"✅ Estoque de **{product['name']}** definido para **{quantidade}** unidades.", ephemeral=True)

    @commands.slash_command(name="listitems", description="Lista todos os itens de uma categoria.", guild_ids=[config.GUILD_ID])
    @commands.has_any_role(*config.ATTENDANT_ROLE_IDS)
    @option("categoria", str, description="Categoria para listar (ex: Extras).")
    async def list_items(self, ctx: discord.ApplicationContext, categoria: str):
        products = await database.get_products_by_category(categoria.capitalize())
        if not products:
            return await ctx.respond(f"Nenhum item encontrado na categoria **{categoria.capitalize()}**.", ephemeral=True)
            
        embed = discord.Embed(title=f"📦 Itens em Estoque - {categoria.capitalize()}", color=config.EMBED_COLOR)
        description = ""
        for p in products:
            description += f"**ID:** `{p['product_id']}` - **{p['name']}**\n"
            description += f"> Preço: `R$ {p['price']:.2f}` | Estoque: `{p['stock']}`\n"
        embed.description = description
        await ctx.respond(embed=embed, ephemeral=True)

def setup(bot):
    bot.add_cog(StockCog(bot))
