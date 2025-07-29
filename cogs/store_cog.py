# cogs/store_cog.py
import discord
from discord.ext import commands
from discord.ui import View, Button, Select
import asyncio
import os

import config
import database

class StoreCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    class StoreView(View):
        def __init__(self, cog_instance):
            super().__init__(timeout=None)
            self.cog = cog_instance
        @discord.ui.button(label="🛒 Acessar Loja de Itens", style=discord.ButtonStyle.success, custom_id="enter_store")
        async def enter_store_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
            await self.cog.select_category(interaction)

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(self.StoreView(self))
        print("View da Loja Dinâmica registrada.")

    @commands.slash_command(name="iniciarloja", description="Cria o painel de acesso à loja de itens com estoque.", guild_ids=[config.GUILD_ID])
    @commands.has_any_role(*config.ATTENDANT_ROLE_IDS)
    async def start_store(self, ctx: discord.ApplicationContext):
        channel = ctx.channel 
        embed = discord.Embed(title="🛍️ Loja de Itens da IsraBuy", description="Clique no botão abaixo para ver todas as nossas categorias de itens!", color=config.EMBED_COLOR)
        await channel.send(embed=embed, view=self.StoreView(self))
        await ctx.respond("Painel da Loja criado com sucesso!", ephemeral=True)

    async def select_category(self, interaction: discord.Interaction):
        async with database.pool.acquire() as conn:
            records = await conn.fetch("SELECT DISTINCT category FROM products WHERE stock > 0 ORDER BY category ASC;")
        if not records:
            return await interaction.response.send_message("Nenhuma categoria com itens em estoque no momento.", ephemeral=True)
        options = [discord.SelectOption(label=record['category']) for record in records]
        select = Select(placeholder="Selecione uma categoria...", options=options, custom_id="category_select")
        async def select_callback(interaction: discord.Interaction):
            category_name = interaction.data["values"][0]
            await self.select_item(interaction, category_name)
        select.callback = select_callback
        view = View(timeout=180)
        view.add_item(select)
        await interaction.response.send_message("Escolha uma categoria para ver os produtos:", view=view, ephemeral=True)

    async def select_item(self, interaction: discord.Interaction, category_name: str):
        products = await database.get_products_by_category(category_name)
        options = []
        for p in products:
            if p['stock'] > 0:
                options.append(discord.SelectOption(label=f"{p['name']} - R$ {p['price']:.2f}", value=str(p['product_id']), description=f"Estoque: {p['stock']}", emoji="🎁"))
        if not options:
            return await interaction.response.edit_message(content="Todos os itens desta categoria esgotaram.", view=None)
        select = Select(placeholder="Selecione um produto...", options=options, custom_id="item_select")
        async def select_callback(interaction: discord.Interaction):
            product_id = int(interaction.data["values"][0])
            await self.start_item_purchase(interaction, product_id)
        select.callback = select_callback
        view = View(timeout=180)
        view.add_item(select)
        await interaction.response.edit_message(content=f"Você está vendo os itens da categoria **{category_name}**:", view=view)

    async def start_item_purchase(self, interaction: discord.Interaction, product_id: int):
        await interaction.response.defer()
        user = interaction.user
        active_thread_id = await database.get_active_thread(user.id)
        if active_thread_id:
            thread = self.bot.get_channel(active_thread_id)
            if thread and not getattr(thread, 'archived', True):
                view = View(); view.add_item(Button(label="Ir para o Carrinho", style=discord.ButtonStyle.link, url=thread.jump_url))
                await interaction.followup.send(f"❌ Você já possui um carrinho aberto em {thread.mention}.", view=view, ephemeral=True)
                return
            else:
                await database.set_active_thread(user.id, None)

        product = await database.get_product_by_id(product_id)
        if not product or product['stock'] <= 0:
            return await interaction.followup.send(content="Este item esgotou.", ephemeral=True)
        
        thread = await interaction.channel.create_thread(name=f"🛍️ {product['name']} - {user.display_name}", type=discord.ChannelType.private_thread)
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
                    print(f"Não foi possível adicionar o usuário {u.id} ao tópico da loja: {e}")

        try:
            await interaction.edit_original_response(content=f"Seu carrinho foi criado aqui: {thread.mention}", view=None)
        except Exception as e:
            print(f"Falha ao editar resposta original da loja: {e}")

        log_channel = self.bot.get_channel(config.ATTENDANCE_LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(f"🛍️ Novo carrinho de **Item ({product['name']})** criado para {user.mention}.")
        try:
            embed = discord.Embed(title=f"🛍️ Compra de {product['name']}", color=config.EMBED_COLOR)
            embed.add_field(name="Produto", value=product['name'], inline=True).add_field(name="Preço", value=f"R$ {product['price']:.2f}", inline=True)
            embed.add_field(name="Instruções", value="Realize o pagamento e envie o comprovante.", inline=False)
            embed.add_field(name="Chave PIX", value=config.PIX_KEY, inline=False)
            await thread.send(user.mention, embed=embed)
            
            msg_receipt = await self.bot.wait_for('message', check=lambda m: m.author == user and m.channel == thread and m.attachments, timeout=172800.0)
            customer_role = interaction.guild.get_role(config.INITIAL_BUYER_ROLE_ID)
            if customer_role: await user.add_roles(customer_role, reason="Enviou comprovante de item")
            
            await thread.send("✅ Comprovante recebido!")
            admin_channel = self.bot.get_channel(config.ADMIN_NOTIF_CHANNEL_ID)
            admin_view = View(timeout=None)
            admin_view.add_item(Button(label="Atender Item", style=discord.ButtonStyle.success, custom_id=f"attend_item_{thread.id}_{user.id}_{product['product_id']}"))
            admin_embed = discord.Embed(title="🔔 Novo Pedido de Item!", description=f"O cliente {user.mention} quer comprar **{product['name']}**.", color=0x2ECC71)
            await admin_channel.send(embed=admin_embed, view=admin_view)
        except asyncio.TimeoutError:
            await thread.send("Pedido expirou."); await asyncio.sleep(5)
            await database.set_active_thread(user.id, None)
            await thread.edit(archived=True, locked=True)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        custom_id = interaction.data.get("custom_id", "")
        if custom_id.startswith("attend_item_"):
            if not any(r.id in config.ATTENDANT_ROLE_IDS for r in interaction.user.roles):
                return await interaction.response.send_message("Sem permissão.", ephemeral=True)
            
            await interaction.response.defer()
            parts = custom_id.split("_")
            thread_id, user_id, product_id = int(parts[2]), int(parts[3]), int(parts[4])
            attendant, user = interaction.user, self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
            
            log_channel = self.bot.get_channel(config.ATTENDANCE_LOG_CHANNEL_ID)
            if log_channel: await log_channel.send(embed=discord.Embed(description=f"{attendant.mention} está cuidando do carrinho de item de {user.mention}.", color=0x32CD32))
            
            thread = self.bot.get_channel(thread_id)
            if thread: await thread.send(f"Olá! Eu sou {attendant.mention} e vou te atender.")

            await (await interaction.original_response()).edit(content=f"Carrinho de item assumido por {attendant.mention}!", view=None)

def setup(bot):
    bot.add_cog(StoreCog(bot))
