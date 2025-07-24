# cogs/extras_cog.py
import discord
from discord.ext import commands
from discord.ui import View, Button, Select
import asyncio

import config
import database

class ExtrasPurchaseView(View):
    def __init__(self, cog_instance):
        super().__init__(timeout=None)
        self.cog = cog_instance

    @discord.ui.button(label="Comprar Extras", style=discord.ButtonStyle.success, custom_id="buy_extras", emoji="✨")
    async def buy_extras_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.cog.select_extra_item(interaction)

class ExtrasCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(ExtrasPurchaseView(self))
        print("View de vendas de Extras registrada.")

    @commands.slash_command(name="iniciarextras", description="Cria o painel de vendas para itens da categoria Extras.", guild_ids=[config.GUILD_ID])
    @commands.has_any_role(*config.ATTENDANT_ROLE_IDS)
    async def start_extras_sales(self, ctx: discord.ApplicationContext):
        channel = ctx.channel 
        embed = discord.Embed(title="✨ Loja de Itens Extras", description="Confira nossos produtos exclusivos! Clique no botão abaixo para ver o que temos em estoque.", color=config.EMBED_COLOR)
        await channel.send(embed=embed, view=ExtrasPurchaseView(self))
        await ctx.respond("Painel de Extras criado com sucesso!", ephemeral=True)

    async def select_extra_item(self, interaction: discord.Interaction):
        products = await database.get_products_by_category("Extras")
        if not products:
            return await interaction.response.send_message("Desculpe, não temos nenhum item extra em estoque no momento.", ephemeral=True)
        
        options = []
        for p in products:
            options.append(discord.SelectOption(
                label=f"{p['name']} - R$ {p['price']:.2f}",
                value=str(p['product_id']),
                description=f"Estoque: {p['stock']}",
                emoji="🎁" if p['stock'] > 0 else "❌",
                disabled=p['stock'] == 0
            ))

        select = Select(placeholder="Selecione um produto...", options=options, custom_id="extra_select")
        
        async def select_callback(interaction: discord.Interaction):
            product_id = int(interaction.data["values"][0])
            await self.start_extra_purchase(interaction, product_id)

        select.callback = select_callback
        view = View(timeout=180)
        view.add_item(select)
        await interaction.response.send_message("Escolha um dos nossos itens extras:", view=view, ephemeral=True)

    async def start_extra_purchase(self, interaction: discord.Interaction, product_id: int):
        await interaction.response.defer()
        product = await database.get_product_by_id(product_id)
        if not product or product['stock'] <= 0:
            return await interaction.followup.send(content="Desculpe, este item esgotou ou não existe mais.", view=None)

        user = interaction.user
        thread = await interaction.channel.create_thread(name=f"✨ {product['name']} - {user.display_name}", type=discord.ChannelType.private_thread)
        await thread.add_user(user)
        await interaction.edit_original_response(content=f"Seu carrinho foi criado aqui: {thread.mention}", view=None)

        try:
            embed = discord.Embed(title=f"✨ Compra de {product['name']}", color=config.EMBED_COLOR)
            embed.add_field(name="Produto", value=product['name'], inline=True)
            embed.add_field(name="Preço", value=f"R$ {product['price']:.2f}", inline=True)
            embed.add_field(name="Instruções", value="Realize o pagamento via PIX e envie o comprovante.", inline=False)
            embed.add_field(name="Chave PIX (Aleatória)", value="b1a2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6")
            
            await thread.send(user.mention, embed=embed)
            
            msg_receipt = await self.bot.wait_for('message', check=lambda m: m.author == user and m.channel == thread and m.attachments, timeout=600.0)
            await thread.send("✅ Comprovante recebido! A equipe foi notificada.")

            admin_channel = self.bot.get_channel(config.ADMIN_NOTIF_CHANNEL_ID)
            admin_view = View(timeout=None)
            admin_view.add_item(Button(label=f"Atender Item", style=discord.ButtonStyle.success, custom_id=f"attend_item_{thread.id}_{user.id}_{product_id}"))
            admin_embed = discord.Embed(title=f"🔔 Novo Pedido de Item!", description=f"O cliente {user.mention} quer comprar **{product['name']}**.", color=0x2ECC71)
            await admin_channel.send(embed=admin_embed, view=admin_view)
            
        except asyncio.TimeoutError:
            await thread.send("Pedido expirado.")
            await asyncio.sleep(10)
            await thread.edit(archived=True, locked=True)

def setup(bot):
    bot.add_cog(ExtrasCog(bot))
