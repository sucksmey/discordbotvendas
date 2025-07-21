# cogs/jogos.py

import discord
from discord.ext import commands
import config
import asyncio # Para simular um delay
from datetime import datetime

# Adaptação da ProductSelectView do seu bot antigo (para itens de preço)
class ProductSelectView(discord.ui.View):
    def __init__(self, bot_instance, products_dict_flat: dict, category_name: str, parent_category_filter: str = None):
        super().__init__(timeout=180)
        self.bot = bot_instance
        self.category_name = category_name
        self.parent_category_filter = parent_category_filter

        options = []
        for name, price_info in products_dict_flat.items():
            label_text = name 
            if isinstance(price_info, (int, float)):
                label_text = f"{name} (R$ {price_info:.2f})"
            
            print(f"[DEBUG] ProductSelectView (adaptada) - Opção '{self.category_name}':")
            print(f"    Label (repr): {repr(label_text)} (len: {len(label_text)})")
            print(f"    Value (repr): {repr(name)} (len: {len(name)})")

            if len(label_text) > 100:
                print(f"[WARNING] Label '{label_text}' excede 100 caracteres. Será truncado.")
                label_text = label_text[:97] + "..."

            options.append(
                discord.SelectOption(
                    label=label_text,
                    value=name
                )
            )
        
        print(f"[DEBUG] ProductSelectView (adaptada): Número total de opções geradas para '{self.category_name}': {len(options)}.")
        
        if options:
            self.add_item(
                discord.ui.Select(
                    placeholder=f"Selecione um {self.category_name}...",
                    min_values=1,
                    max_values=1,
                    options=options[:25], # LIMITA A 25 OPÇÕES!
                    custom_id=f"product_select_{self.category_name}"
                )
            )
        else:
            print(f"[ERROR] ProductSelectView (adaptada): Nenhuma opção gerada para '{self.category_name}'. O SelectMenu não será adicionado.")
            self.add_item(discord.ui.Button(label="Nenhum item encontrado nesta categoria.", style=discord.ButtonStyle.red, disabled=True))

        if self.parent_category_filter:
            self.add_item(discord.ui.Button(label="Voltar para Categorias", style=discord.ButtonStyle.grey, custom_id=f"back_to_parent_category_{self.parent_category_filter}"))

    @discord.ui.select()
    async def select_product_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        print(f"[DEBUG] ProductSelectView (adaptada): select_product_callback por {interaction.user.name}.")
        selected_product_name = select.values[0]
        
        product_details = None
        for name, details in config.PRODUCTS.items():
            if name == selected_product_name:
                product_details = details
                break
            if 'prices' in details and selected_product_name in details['prices']:
                product_details = details
                break
        
        if not product_details:
            print(f"[ERROR] Produto '{selected_product_name}' (value selecionado) não encontrado nos detalhes completos do config.PRODUCTS!")
            embed = discord.Embed(
                title="Erro",
                description="Produto selecionado inválido. Por favor, tente novamente. Se o erro persistir, contate o suporte.",
                color=config.ROSE_COLOR
            )
            print(f"[DEBUG] Antes de interaction.response.send_message (ProductSelectView Erro - Produto não encontrado).")
            return await interaction.response.send_message(embed=embed, ephemeral=True)
            print(f"[DEBUG] Após interaction.response.send_message (ProductSelectView Erro - Produto não encontrado).")
            
        user_id = interaction.user.id

        try:
            current_cart = await self.bot.db.fetch_one(
                "SELECT cart_thread_id, cart_product_name FROM users WHERE user_id = $1 AND cart_thread_id IS NOT NULL",
                user_id
            )
            print(f"[DEBUG] Verificação de carrinho existente para {user_id}: {current_cart is not None}.")

            if current_cart:
                existing_thread_id = current_cart['cart_thread_id']
                existing_thread = interaction.guild.get_thread(existing_thread_id)
                
                if existing_thread:
                    embed = discord.Embed(
                        title="🛒 Você já tem um carrinho!",
                        description=f"Você já possui um carrinho em andamento! [Clique aqui para acessá-lo]({existing_thread.jump_url}).\n\nDeseja iniciar uma **nova compra**?",
                        color=config.ROSE_COLOR
                    )
                    print(f"[DEBUG] Carrinho existente detectado, redirecionando para {existing_thread.jump_url}.")
                    
                    class NewPurchaseOptionView(discord.ui.View):
                        def __init__(self, bot_instance, original_interaction, current_category_filter_param, current_category_name_param):
                            super().__init__(timeout=60)
                            self.bot = bot_instance
                            self.user_id = original_interaction.user.id
                            self.original_interaction = original_interaction
                            self.current_category_filter = current_category_filter_param
                            self.current_category_name = current_category_name_param

                        @discord.ui.button(label="Iniciar Nova Compra", style=discord.ButtonStyle.green, custom_id="start_new_purchase")
                        async def start_new_purchase_button(self, interaction_button: discord.Interaction, button: discord.ui.Button):
                            print(f"[DEBUG] Botão 'Iniciar Nova Compra' clicado por {interaction_button.user.name}.")
                            await self.bot.db.execute("UPDATE users SET cart_thread_id = NULL, cart_product_name = NULL, cart_quantity = NULL, cart_status = NULL, roblox_nickname = NULL WHERE user_id = $1", self.user_id)
                            
                            if self.current_category_filter == "robux":
                                await self.bot.get_cog("RobuxCog").robux_command.callback(self.bot.get_cog("RobuxCog"), interaction_button)
                            elif self.current_category_filter == "jogos":
                                await self.bot.get_cog("JogosCog").games_command.callback(self.bot.get_cog("JogosCog"), interaction_button)
                            elif self.current_category_filter == "giftcard":
                                await self.bot.get_cog("GiftcardCog").giftcard_command.callback(self.bot.get_cog("GiftcardCog"), interaction_button)
                            else:
                                await interaction_button.response.send_message("Não foi possível recarregar a categoria anterior. Por favor, use um comando de compra novamente.", ephemeral=True)

                            print(f"[DEBUG] Mensagem editada com nova seleção de produto.")
                    
                    print(f"[DEBUG] Enviando mensagem de carrinho existente com opção de nova compra para {interaction.user.name}.")
                    print(f"[DEBUG] Antes de interaction.response.send_message (ProductSelectView Existente).")
                    await interaction.response.send_message(embed=embed, view=NewPurchaseOptionView(self.bot, interaction, self.category_name, self.category_name.capitalize()), ephemeral=True)
                    print(f"[DEBUG] Após interaction.response.send_message (ProductSelectView Existente).")
                    return 
                else:
                    print(f"[DEBUG] Carrinho existente mas thread não encontrada, limpando DB para {user_id}.")
                    await self.db.execute("UPDATE users SET cart_thread_id = NULL, cart_product_name = NULL, cart_quantity = NULL, cart_status = NULL, roblox_nickname = NULL WHERE user_id = $1", user_id)
                    print(f"[DEBUG] DB limpo, prosseguindo para criar novo carrinho.")

            print(f"[DEBUG] Invocando _create_new_cart para {user_id} com produto: {selected_product_name}.")
            actual_product_name_for_cart = selected_product_name
            actual_product_details_for_cart = product_details 

            if 'prices' in product_details and selected_product_name in product_details['prices']:
                actual_product_name_for_cart = f"{product_details['emoji']} {product_details['category'].capitalize()} - {selected_product_name}"
                actual_product_details_for_cart = { 
                    'name': selected_product_name,
                    'price': product_details['prices'][selected_product_name],
                    'type': product_details['type'],
                    'category': product_details['category']
                }

            await self._create_new_cart(interaction, actual_product_name_for_cart, actual_product_details_for_cart)
            
        except Exception as e:
            print(f"[CRITICAL ERROR] Erro CRÍTICO em select_product_callback (ProductSelectView adaptada) para {interaction.user.name}: {e}")
            error_embed = discord.Embed(
                title="Erro na Seleção do Produto",
                description=f"Ocorreu um erro ao iniciar o processo de compra. Por favor, tente novamente. Erro: `{e}`",
                color=config.ROSE_COLOR
            )
            if interaction.response.is_done():
                await interaction.followup.send(embed=error_embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
            print(f"[DEBUG] Mensagem de erro de seleção de produto enviada.")


    async def _create_new_cart(self, interaction: discord.Interaction, selected_product_name: str, product_details: dict):
        print(f"[DEBUG] _create_new_cart iniciado para {interaction.user.name}. Produto: {selected_product_name}")
        user = interaction.user
        guild = interaction.guild
        
        parent_channel = guild.get_channel(config.CARRINHO_EM_ANDAMENTO_CHANNEL_ID)
        if not parent_channel:
            print(f"[ERROR] Canal pai de carrinhos não encontrado: {config.CARRINHO_EM_ANDAMENTO_CHANNEL_ID}.")
            embed = discord.Embed(
                title="Erro",
                description="Não foi possível encontrar o canal de carrinhos. Por favor, contate um administrador.",
                color=config.ROSE_COLOR
            )
            print(f"[DEBUG] Antes de interaction.response.send_message (_create_new_cart Erro - Canal não encontrado).")
            return await interaction.response.send_message(embed=embed, ephemeral=True)
            print(f"[DEBUG] Após interaction.response.send_message (_create_new_cart Erro - Canal não encontrado).")

        timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S")
        thread_name = f"carrinho-{user.name}-{timestamp_str}"
        
        try:
            print(f"[DEBUG] Tentando criar thread '{thread_name}' no canal {parent_channel.name}.")
            new_thread = await parent_channel.create_thread(
                name=thread_name,
                type=discord.ChannelType.private_thread,
                auto_archive_duration=1440,
                invitable=True
            )
            print(f"[DEBUG] Thread '{new_thread.name}' criada (ID: {new_thread.id}).")
            
            await new_thread.add_user(user)
            print(f"[DEBUG] Usuário {user.name} adicionado à thread.")
            
            admin_role = guild.get_role(config.ADMIN_ROLE_ID)
            if admin_role:
                print(f"[DEBUG] Adicionando admins à thread (Role ID: {config.ADMIN_ROLE_ID}).")
                for member in admin_role.members:
                    await new_thread.add_user(member)
                print(f"[DEBUG] Admins adicionados à thread.")
            else:
                print(f"[WARNING] Cargo de Admin ({config.ADMIN_ROLE_ID}) não encontrado para adicionar à thread.")

            print(f"[DEBUG] Salvando carrinho no DB para {user.name}.")
            await self.bot.db.execute(
                """
                INSERT INTO users (user_id, cart_thread_id, cart_product_name, cart_status)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id) DO UPDATE
                SET cart_thread_id = $2, cart_product_name = $3, cart_status = $4, roblox_nickname = NULL, last_cart_update = CURRENT_TIMESTAMP
                """,
                user.id, new_thread.id, selected_product_name, 'in_progress'
            )
            print(f"[DEBUG] Carrinho salvo no DB para {user.name}.")

            embed = discord.Embed(
                title=f"🛒 Carrinho Iniciado para {selected_product_name}!",
                description=f"Seu carrinho foi criado em {new_thread.mention}.\nPor favor, continue a conversa lá.",
                color=config.ROSE_COLOR
            )
            print(f"[DEBUG] Antes de interaction.response.edit_message (_create_new_cart).")
            await interaction.response.edit_message(embed=embed, view=None)
            print(f"[DEBUG] Após interaction.response.edit_message (_create_new_cart).")

            thread_embed = discord.Embed(
                title=f"Bem-vindo(a) ao seu Carrinho para {selected_product_name}!",
                description=f"Olá {user.mention}! Por favor, aguarde as instruções ou clique em 'Pegar Ticket' para chamar um atendente.",
                color=config.ROSE_COLOR
            )
            ticket_button_view = discord.ui.View()
            ticket_button_view.add_item(discord.ui.Button(label="Pegar Ticket", style=discord.ButtonStyle.primary, custom_id="get_cart_ticket"))
            
            print(f"[DEBUG] Antes de new_thread.send (_create_new_cart).")
            await new_thread.send(embed=thread_embed, view=ticket_button_view)
            print(f"[DEBUG] Após new_thread.send (_create_new_cart).")
            
            logs_channel = guild.get_channel(config.CARRINHO_EM_ANDAMENTO_CHANNEL_ID)
            if logs_channel and logs_channel.id != new_thread.id:
                 log_embed = discord.Embed(
                    title="Carrinho em Andamento!",
                    description=f"**Usuário:** {user.mention}\n**Produto:** {selected_product_name}\n**Carrinho:** {new_thread.mention}\n**Status:** Iniciado",
                    color=config.ROSE_COLOR
                 )
                 print(f"[DEBUG] Antes de logs_channel.send (_create_new_cart).")
                 await logs_channel.send(embed=log_embed)
                 print(f"[DEBUG] Após logs_channel.send (_create_new_cart).")

            if product_details.get('type') == 'automatized' and product_details.get('category') == 'robux':
                print(f"[DEBUG] Produto automatizado (Robux), enviando seleção de quantidade para {user.name}.")
                print(f"[DEBUG] Antes de new_thread.send (Robux Quantity Select).")
                await new_thread.send(
                    embed=discord.Embed(
                        title="Selecione a Quantidade de Robux",
                        description="Escolha a quantidade de Robux que deseja comprar.",
                        color=config.ROSE_COLOR
                    ),
                    view=RobuxQuantitySelectView(self.bot, "Robux")
                )
                print(f"[DEBUG] Após new_thread.send (Robux Quantity Select).")

            elif product_details.get('type') == 'manual':
                print(f"[DEBUG] Produto manual, notificando admin para {user.name}.")
                admin_role = guild.get_role(config.ADMIN_ROLE_ID)
                print(f"[DEBUG] Antes de new_thread.send (Manual Notify).")
                await new_thread.send(f"{admin_role.mention}, um atendimento manual é necessário para esta compra. Aguarde um momento por favor.")
                print(f"[DEBUG] Após new_thread.send (Manual Notify).")
            else:
                print(f"[WARNING] Tipo de produto não definido para automação ou manual. Notificando admin.")
                admin_role = guild.get_role(config.ADMIN_ROLE_ID)
                print(f"[DEBUG] Antes de new_thread.send (Fallback Notify).")
                await new_thread.send(f"{admin_role.mention}, a compra de {selected_product_name} requer atendimento. Aguarde um momento por favor.")
                print(f"[DEBUG] Após new_thread.send (Fallback Notify).")


        except Exception as e:
            print(f"[CRITICAL ERROR] Erro CRÍTICO em _create_new_cart para {interaction.user.name}: {e}")
            error_embed = discord.Embed(
                title="Erro ao Iniciar Carrinho",
                description=f"Ocorreu um erro ao criar seu carrinho. Por favor, tente novamente ou contate o administrador. Erro: `{e}`",
                color=config.ROSE_COLOR
            )
            if interaction.response.is_done():
                await interaction.followup.send(embed=error_embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
            print(f"[DEBUG] Mensagem de erro de carrinho enviada.")


# Nova View para seleção de subcategoria de jogos
class GameSubcategorySelectView(discord.ui.View):
    def __init__(self, bot_instance):
        super().__init__(timeout=180)
        self.bot = bot_instance
        
        game_subcategories = set()
        for product_name, details in config.PRODUCTS.items():
            if details.get('category') == 'jogos' and 'sub_category' in details:
                game_subcategories.add(details['sub_category'])
        
        options = []
        for sub_cat in sorted(list(game_subcategories)):
            options.append(discord.SelectOption(label=sub_cat, value=sub_cat))
        
        print(f"[DEBUG] GameSubcategorySelectView: Número total de subcategorias geradas: {len(options)}.")

        if options:
            self.add_item(
                discord.ui.Select(
                    placeholder="Selecione um tipo de jogo...",
                    min_values=1,
                    max_values=1,
                    options=options[:25],
                    custom_id="game_subcategory_select"
                )
            )
        else:
            print(f"[ERROR] GameSubcategorySelectView: Nenhuma subcategoria de jogos encontrada.")
            self.add_item(discord.ui.Button(label="Nenhum tipo de jogo encontrado.", style=discord.ButtonStyle.red, disabled=True))

    @discord.ui.select(custom_id="game_subcategory_select")
    async def select_subcategory_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        print(f"[DEBUG] GameSubcategorySelectView: select_subcategory_callback por {interaction.user.name}.")
        selected_subcategory = select.values[0]
        
        products_in_subcategory_flat = {}
        for product_name, details in config.PRODUCTS.items():
            if details.get('category') == 'jogos' and details.get('sub_category') == selected_subcategory:
                for item_name, item_price in details['prices'].items():
                    products_in_subcategory_flat[item_name] = item_price
        
        embed = discord.Embed(
            title=f"🛒 Selecione um Jogo ({selected_subcategory})",
            description="Use o menu abaixo para escolher o jogo que deseja comprar.",
            color=config.ROSE_COLOR
        )
        print(f"[DEBUG] Antes de interaction.response.edit_message (Game Subcategory Select).")
        await interaction.response.edit_message(
            embed=embed, 
            view=ProductSelectView(self.bot, products_in_subcategory_flat, "Jogo", parent_category_filter="jogos")
        )
        print(f"[DEBUG] Após interaction.response.edit_message (Game Subcategory Select).")


# Nova View para seleção de marca de giftcard
class GiftcardBrandSelectView(discord.ui.View):
    def __init__(self, bot_instance):
        super().__init__(timeout=180)
        self.bot = bot_instance
        
        giftcard_brands = set()
        for product_name, details in config.PRODUCTS.items():
            if details.get('category') == 'giftcard':
                giftcard_brands.add(product_name)
        
        options = []
        for brand_name in sorted(list(giftcard_brands)):
            options.append(discord.SelectOption(label=brand_name, value=brand_name))
        
        print(f"[DEBUG] GiftcardBrandSelectView: Número total de marcas geradas: {len(options)}.")

        if options:
            self.add_item(
                discord.ui.Select(
                    placeholder="Selecione uma marca de Giftcard...",
                    min_values=1,
                    max_values=1,
                    options=options[:25],
                    custom_id="giftcard_brand_select"
                )
            )
        else:
            print(f"[ERROR] GiftcardBrandSelectView: Nenhuma marca de giftcard encontrada.")
            self.add_item(discord.ui.Button(label="Nenhum tipo de jogo encontrado.", style=discord.ButtonStyle.red, disabled=True))

    @discord.ui.select(custom_id="giftcard_brand_select")
    async def select_brand_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        print(f"[DEBUG] GiftcardBrandSelectView: select_brand_callback por {interaction.user.name}.")
        selected_brand = select.values[0]
        
        products_in_brand_flat = {}
        if selected_brand in config.PRODUCTS and 'prices' in config.PRODUCTS[selected_brand]:
            for item_name, item_price in config.PRODUCTS[selected_brand]['prices'].items():
                products_in_brand_flat[item_name] = item_price
        
        embed = discord.Embed(
            title=f"🛒 Selecione um Giftcard ({selected_brand})",
            description="Use o menu abaixo para escolher o giftcard que deseja comprar.",
            color=config.ROSE_COLOR
        )
        print(f"[DEBUG] Antes de interaction.response.edit_message (Giftcard Brand Select).")
        await interaction.response.edit_message(
            embed=embed, 
            view=ProductSelectView(self.bot, products_in_brand_flat, "Giftcard", parent_category_filter="giftcard")
        )
        print(f"[DEBUG] Após interaction.response.edit_message (Giftcard Brand Select).")


# Classe principal do Cog para Jogos
class JogosCog(commands.Cog):
    def __init__(self, bot: discord.Client):
        self.bot = bot
        self.db = bot.db

    @discord.app_commands.command(name="jogos", description="Compre itens para outros jogos (Valorant, Free Fire, etc.).")
    async def games_command(self, interaction: discord.Interaction):
        print(f"[DEBUG] Comando /jogos recebido de {interaction.user.name}.")
        embed = discord.Embed(
            title="🎮 Selecione o Tipo de Jogo",
            description="Use o menu abaixo para escolher o tipo de jogo que você busca.",
            color=config.ROSE_COLOR
        )
        print(f"[DEBUG] Antes de interaction.response.send_message (Games Command).")
        await interaction.response.send_message(embed=embed, view=GameSubcategorySelectView(self.bot), ephemeral=True)
        print(f"[DEBUG] Após interaction.response.send_message (Games Command).")

# Classe principal do Cog para Giftcard
class GiftcardCog(commands.Cog):
    def __init__(self, bot: discord.Client):
        self.bot = bot
        self.db = bot.db

    @discord.app_commands.command(name="giftcard", description="Compre Giftcards (PlayStation, Xbox, Google Play, Apple).")
    async def giftcard_command(self, interaction: discord.Interaction):
        print(f"[DEBUG] Comando /giftcard recebido de {interaction.user.name}.")
        embed = discord.Embed(
            title="💳 Selecione a Marca do Giftcard",
            description="Use o menu abaixo para escolher a marca de Giftcard que você deseja comprar.",
            color=config.ROSE_COLOR
        )
        print(f"[DEBUG] Antes de interaction.response.send_message (Giftcard Command).")
        await interaction.response.send_message(embed=embed, view=GiftcardBrandSelectView(self.bot), ephemeral=True)
        print(f"[DEBUG] Após interaction.response.send_message (Giftcard Command).")


# Cog para Listeners Comuns (Botões de Ticket, Gamepass, etc.)
class CommonListenersCog(commands.Cog):
    def __init__(self, bot: discord.Client):
        self.bot = bot
        self.db = bot.db

    # Listener para o botão "Voltar para Categorias" (para menus de 2o nível)
    @commands.Cog.listener("on_interaction")
    async def on_back_to_parent_category_button(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.component and interaction.data.get("custom_id").startswith("back_to_parent_category_"):
            print(f"[DEBUG] Botão 'Voltar para Categorias' clicado por {interaction.user.name}.")
            parent_category_filter = interaction.data["custom_id"].replace("back_to_parent_category_", "")
            
            bot_instance = interaction.client
            
            if parent_category_filter == "jogos":
                embed = discord.Embed(
                    title="🎮 Selecione o Tipo de Jogo",
                    description="Use o menu abaixo para escolher o tipo de jogo que você busca.",
                    color=config.ROSE_COLOR
                )
                print(f"[DEBUG] Antes de interaction.response.edit_message (Voltar Jogos).")
                await interaction.response.edit_message(embed=embed, view=GameSubcategorySelectView(bot_instance))
                print(f"[DEBUG] Após interaction.response.edit_message (Voltar Jogos).")
            elif parent_category_filter == "giftcard":
                embed = discord.Embed(
                    title="💳 Selecione a Marca do Giftcard",
                    description="Use o menu abaixo para escolher a marca de Giftcard que você deseja comprar.",
                    color=config.ROSE_COLOR
                )
                print(f"[DEBUG] Antes de interaction.response.edit_message (Voltar Giftcard).")
                await interaction.response.edit_message(embed=embed, view=GiftcardBrandSelectView(bot_instance))
                print(f"[DEBUG] Após interaction.response.edit_message (Voltar Giftcard).")
            else:
                print(f"[DEBUG] Antes de interaction.response.send_message (Voltar Erro).")
                await interaction.response.send_message("Não foi possível voltar para a categoria anterior.", ephemeral=True)
                print(f"[DEBUG] Após interaction.response.send_message (Voltar Erro).")
            print(f"[DEBUG] Redirecionado para seleção de categoria pai: {parent_category_filter}.")


    # Listener para o botão "Pegar Ticket"
    @commands.Cog.listener("on_interaction")
    async def on_interaction_ticket_button(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.component and interaction.data.get("custom_id") == "get_cart_ticket":
            print(f"[DEBUG] Botão 'Pegar Ticket' clicado por {interaction.user.name}.")
            if interaction.channel.type != discord.ChannelType.private_thread:
                print(f"[DEBUG] Interação de ticket fora de thread privada, ignorando.")
                return

            user_id = interaction.user.id
            try:
                cart_info = await interaction.client.db.fetch_one(
                    "SELECT cart_product_name FROM users WHERE user_id = $1 AND cart_thread_id = $2",
                    user_id, interaction.channel.id
                )

                if not cart_info:
                    print(f"[DEBUG] Carrinho não ativo ou não iniciado por {user_id}.")
                    print(f"[DEBUG] Antes de interaction.response.send_message (Ticket Erro - Carrinho).")
                    await interaction.response.send_message("Este não é um carrinho ativo ou você não o iniciou.", ephemeral=True)
                    print(f"[DEBUG] Após interaction.response.send_message (Ticket Erro - Carrinho).")
                    return
                
                product_name = cart_info['cart_product_name']
                admin_role = interaction.guild.get_role(config.ADMIN_ROLE_ID)

                if admin_role:
                    embed = discord.Embed(
                        title="🎫 Ticket Solicitado!",
                        description=f"{admin_role.mention}, o usuário {interaction.user.name} solicitou ajuda para a compra de **{product_name}**.\n\n"
                                    "Um atendente estará com você em breve.",
                        color=config.ROSE_COLOR
                    )
                    print(f"[DEBUG] Enviando notificação de ticket para admin e {interaction.user.name}.")
                    print(f"[DEBUG] Antes de interaction.response.send_message (Ticket Sucesso).")
                    await interaction.response.send_message(embed=embed)
                    print(f"[DEBUG] Após interaction.response.send_message (Ticket Sucesso).")
                else:
                    print(f"[WARNING] Cargo de Admin ({config.ADMIN_ROLE_ID}) não encontrado para notificar ticket.")
                    print(f"[DEBUG] Antes de interaction.response.send_message (Ticket Erro - Admin).")
                    await interaction.response.send_message("Não foi possível encontrar o cargo de administrador para notificar.", ephemeral=True)
                    print(f"[DEBUG] Após interaction.response.send_message (Ticket Erro - Admin).")
            except Exception as e:
                print(f"[ERROR] Erro em on_interaction_ticket_button para {interaction.user.name}: {e}")
                error_embed = discord.Embed(
                    title="Erro no Ticket",
                    description=f"Ocorreu um erro ao solicitar o ticket. Erro: `{e}`",
                    color=config.ROSE_COLOR
                )
                if interaction.response.is_done():
                    await interaction.followup.send(embed=error_embed, ephemeral=True)
                else:
                    await interaction.response.send_message(embed=error_embed, ephemeral=True)
                print(f"[DEBUG] Mensagem de erro de ticket enviada.")


    # Listener para o botão "Já criei e desativei preços regionais"
    @commands.Cog.listener("on_interaction")
    async def on_interaction_gamepass_confirm_button(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.component and interaction.data.get("custom_id") == "gamepass_created_confirm":
            print(f"[DEBUG] Botão 'Gamepass Confirmada' clicado por {interaction.user.name}.")
            if interaction.channel.type != discord.ChannelType.private_thread:
                print(f"[DEBUG] Interação de gamepass fora de thread privada, ignorando.")
                return

            user_id = interaction.user.id
            try:
                cart_info = await interaction.client.db.fetch_one(
                    "SELECT cart_product_name, cart_quantity FROM users WHERE user_id = $1 AND cart_thread_id = $2",
                    user_id, interaction.channel.id
                )

                if not cart_info:
                    print(f"[DEBUG] Carrinho não ativo ou não iniciado por {user_id}.")
                    print(f"[DEBUG] Antes de interaction.response.send_message (Gamepass Confirmar Erro - Carrinho).")
                    await interaction.response.send_message("Este não é um carrinho ativo ou você não o iniciou.", ephemeral=True)
                    print(f"[DEBUG] Após interaction.response.send_message (Gamepass Confirmar Erro - Carrinho).")
                    return

                await interaction.client.db.execute(
                    "UPDATE users SET cart_status = $1 WHERE user_id = $2 AND cart_thread_id = $3",
                    'gamepass_confirmed', user_id, interaction.channel.id
                )
                print(f"[DEBUG] Status do carrinho atualizado para 'gamepass_confirmed' para {user_id}.")

                embed = discord.Embed(
                    title="✅ Gamepass Confirmada!",
                    description="Ótimo! Agora, por favor, **envie o link da sua Gamepass** neste chat. Verificaremos o valor para prosseguir com o pagamento.",
                    color=config.ROSE_COLOR
                )
                print(f"[DEBUG] Antes de interaction.response.edit_message (Gamepass Confirmar Sucesso).")
                await interaction.response.edit_message(embed=embed, view=None)
                print(f"[DEBUG] Após interaction.response.edit_message (Gamepass Confirmar Sucesso).")

            except Exception as e:
                print(f"[ERROR] Erro em on_interaction_gamepass_confirm_button (confirmar) para {interaction.user.name}: {e}")
                error_embed = discord.Embed(
                    title="Erro na Gamepass",
                    description=f"Ocorreu um erro ao confirmar a Gamepass. Erro: `{e}`",
                    color=config.ROSE_COLOR
                )
                if interaction.response.is_done():
                    await interaction.followup.send(embed=error_embed, ephemeral=True)
                else:
                    await interaction.response.send_message(embed=error_embed, ephemeral=True)
                print(f"[DEBUG] Mensagem de erro de gamepass enviada.")

    elif interaction.type == discord.InteractionType.component and interaction.data.get("custom_id") == "gamepass_help":
        print(f"[DEBUG] Botão 'Preciso de ajuda com a Gamepass' clicado por {interaction.user.name}.")
        if interaction.channel.type != discord.ChannelType.private_thread:
            print(f"[DEBUG] Interação de ajuda de gamepass fora de thread privada, ignorando.")
            return

        user_id = interaction.user.id
        try:
            cart_info = await interaction.client.db.fetch_one(
                "SELECT cart_product_name FROM users WHERE user_id = $1 AND cart_thread_id = $2",
                user_id, interaction.channel.id
            )

            if not cart_info:
                print(f"[DEBUG] Carrinho não ativo ou não iniciado por {user_id}.")
                print(f"[DEBUG] Antes de interaction.response.send_message (Gamepass Ajuda Erro - Carrinho).")
                await interaction.response.send_message("Este não é um carrinho ativo ou você não o iniciou.", ephemeral=True)
                print(f"[DEBUG] Após interaction.response.send_message (Gamepass Ajuda Erro - Carrinho).")
                return

            admin_role = interaction.guild.get_role(config.ADMIN_ROLE_ID)
            if admin_role:
                embed = discord.Embed(
                    title="🆘 Ajuda com Gamepass Solicitada!",
                    description=f"{admin_role.mention}, o usuário {interaction.user.name} precisa de ajuda para configurar a Gamepass. Por favor, auxilie-o.",
                    color=config.ROSE_COLOR
                )
                print(f"[DEBUG] Enviando notificação de ajuda de gamepass para admin e {interaction.user.name}.")
                print(f"[DEBUG] Antes de interaction.response.send_message (Gamepass Ajuda Sucesso).")
                await interaction.response.send_message(embed=embed)
                print(f"[DEBUG] Após interaction.response.send_message (Gamepass Ajuda Sucesso).")
                print(f"[DEBUG] Antes de interaction.message.edit (Gamepass Ajuda).")
                await interaction.message.edit(view=None)
                print(f"[DEBUG] Após interaction.message.edit (Gamepass Ajuda).")
            else:
                print(f"[WARNING] Cargo de Admin ({config.ADMIN_ROLE_ID}) não encontrado para notificar ajuda de gamepass.")
                print(f"[DEBUG] Antes de interaction.response.send_message (Gamepass Ajuda Erro - Admin).")
                await interaction.response.send_message("Não foi possível encontrar o cargo de administrador para notificar.", ephemeral=True)
                print(f"[DEBUG] Após interaction.response.send_message (Gamepass Ajuda Erro - Admin).")
        except Exception as e:
            print(f"[ERROR] Erro em on_interaction_gamepass_confirm_button (ajuda) para {interaction.user.name}: {e}")
            error_embed = discord.Embed(
                title="Erro na Ajuda da Gamepass",
                description=f"Ocorreu um erro ao solicitar ajuda para a Gamepass. Erro: `{e}`",
                color=config.ROSE_COLOR
            )
            if interaction.response.is_done():
                await interaction.followup.send(embed=error_embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
            print(f"[DEBUG] Mensagem de erro de gamepass enviada.")


# Função setup para adicionar o cog ao bot
async def setup(bot: commands.Bot):
    await bot.add_cog(RobuxCog(bot))
