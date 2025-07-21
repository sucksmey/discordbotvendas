# cogs/purchase.py

import discord
from discord.ext import commands
import config
import uuid
import asyncio
from datetime import datetime

# --- Modals ---
class RobloxNicknameModal(discord.ui.Modal, title="Informe seu Nickname no Roblox"):
    def __init__(self, bot_instance, product_name, selected_quantity, total_price):
        super().__init__()
        self.bot = bot_instance
        self.product_name = product_name
        self.selected_quantity = selected_quantity
        self.total_price = total_price

    roblox_nickname = discord.ui.TextInput(
        label="Seu Nickname no Roblox",
        placeholder="Digite seu nome de usuário no Roblox...",
        min_length=3,
        max_length=20,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        print(f"[DEBUG] Modal Nickname: on_submit por {interaction.user.name}.")
        user_id = interaction.user.id
        nickname = self.roblox_nickname.value

        try:
            await self.bot.db.execute(
                "UPDATE users SET roblox_nickname = $1, cart_status = $2 WHERE user_id = $3 AND cart_thread_id IS NOT NULL",
                nickname, 'nickname_informed', user_id
            )
            print(f"[DEBUG] Nickname {nickname} salvo no DB para {user_id}.")

            embed = discord.Embed(
                title="✅ Nickname Salvo!",
                description=f"Seu nickname `{nickname}` foi salvo. Agora, vamos criar a Gamepass para receber seus {self.selected_quantity}!",
                color=config.ROSE_COLOR
            )

            gamepass_tutorial_embed = discord.Embed(
                title="🎮 Passo 1: Crie sua Gamepass no Roblox",
                description=(
                    "Para receber seus Robux, você precisa criar uma Gamepass com o valor exato.\n\n"
                    "**1.** Vá para [crie.roblox.com/creations/experiences](https://create.roblox.com/creations/experiences).\n"
                    "**2.** Clique em qualquer uma das suas experiências (pode ser um jogo vazio).\n"
                    "**3.** No menu lateral esquerdo, clique em `Associated Items` (Itens Associados) e depois em `Passes`.\n"
                    "**4.** Clique em `Create a Pass` (Criar um Passe).\n"
                    "**5.** Dê um nome qualquer, uma descrição e faça upload de uma imagem.\n"
                    "**6.** Após criar, clique na Gamepass recém-criada.\n"
                    "**7.** No menu lateral esquerdo, clique em `Sales` (Vendas).\n"
                    "**8.** Ative `Item for Sale` (Item à Venda) e **defina o preço exato de Robux:** `R$ {int(self.total_price * 0.7)}` Robux (o Roblox tira 30%).\n" # PREÇO DE VENDA DA GAMEPASS (70% do total)
                    "**9.** **MUITO IMPORTANTE:** Certifique-se de que a opção de **Preços Regionais está DESATIVADA**.\n"
                    "**10.** Salve as alterações e **copie o link da sua Gamepass**."
                ),
                color=config.ROSE_COLOR
            )
            gamepass_tutorial_embed.set_footer(text="Atenção: O Roblox retira 30% do valor da Gamepass. Crie-a com o valor que você deseja receber *após* a taxa.")
            
            gamepass_confirm_view = discord.ui.View(timeout=300)
            gamepass_confirm_view.add_item(discord.ui.Button(label="Já criei e desativei preços regionais", style=discord.ButtonStyle.success, custom_id="gamepass_created_confirm"))
            gamepass_confirm_view.add_item(discord.ui.Button(label="Preciso de ajuda com a Gamepass", style=discord.ButtonStyle.danger, custom_id="gamepass_help"))

            print(f"[DEBUG] Enviando modal response para {interaction.user.name}.")
            await interaction.response.send_message(embeds=[embed, gamepass_tutorial_embed], view=gamepass_confirm_view, ephemeral=False)
            print(f"[DEBUG] Modal response enviada com sucesso para {interaction.user.name}.")

        except Exception as e:
            print(f"[ERROR] Erro em RobloxNicknameModal.on_submit para {interaction.user.name}: {e}")
            error_embed = discord.Embed(
                title="Erro no Nickname",
                description=f"Ocorreu um erro ao processar seu nickname. Por favor, tente novamente. Erro: `{e}`",
                color=config.ROSE_COLOR
            )
            if interaction.response.is_done():
                await interaction.followup.send(embed=error_embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=error_embed, ephemeral=True)


# --- Views ---
class RobuxQuantitySelectView(discord.ui.View):
    def __init__(self, bot_instance, product_name):
        super().__init__(timeout=180)
        self.bot = bot_instance
        self.product_name = product_name

        options = []
        sorted_quantities = sorted(config.PRODUCTS[product_name]['prices'].items(), key=lambda x: int(x[0].split(' ')[0]))
        
        for qty_str, price in sorted_quantities:
            options.append(
                discord.SelectOption(
                    label=f"{qty_str} - R${price:.2f}",
                    value=qty_str
                )
            )
        
        self.add_item(
            discord.ui.Select(
                placeholder="Selecione a quantidade de Robux...",
                min_values=1,
                max_values=1,
                options=options,
                custom_id="robux_quantity_select"
            )
        )

    @discord.ui.select(custom_id="robux_quantity_select")
    async def select_robux_quantity_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        print(f"[DEBUG] RobuxQuantitySelectView: select_robux_quantity_callback por {interaction.user.name}.")
        selected_quantity_str = select.values[0]
        total_price = config.PRODUCTS[self.product_name]['prices'][selected_quantity_str]
        user_id = interaction.user.id

        try:
            await self.bot.db.execute(
                "UPDATE users SET cart_product_name = $1, cart_quantity = $2, cart_status = $3 WHERE user_id = $4 AND cart_thread_id IS NOT NULL",
                self.product_name, selected_quantity_str, 'quantity_selected', user_id
            )
            print(f"[DEBUG] Quantidade {selected_quantity_str} salva no DB para {user_id}.")

            embed = discord.Embed(
                title=f"💎 {selected_quantity_str} selecionados!",
                description=f"O valor total é de **R${total_price:.2f}**.\n\nAgora, por favor, informe seu nickname no Roblox para prosseguir.",
                color=config.ROSE_COLOR
            )
            
            await interaction.response.send_modal(RobloxNicknameModal(self.bot, self.product_name, selected_quantity_str, total_price))
            print(f"[DEBUG] Modal de nickname enviado com sucesso para {interaction.user.name}.")

        except Exception as e:
            print(f"[ERROR] Erro em RobuxQuantitySelectView.select_robux_quantity_callback para {interaction.user.name}: {e}")
            error_embed = discord.Embed(
                title="Erro na Seleção",
                description=f"Ocorreu um erro ao selecionar a quantidade. Por favor, tente novamente. Erro: `{e}`",
                color=config.ROSE_COLOR
            )
            if interaction.response.is_done():
                await interaction.followup.send(embed=error_embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=error_embed, ephemeral=True)


# Nova View para o botão Comprar Robux
class RobuxMainView(discord.ui.View):
    def __init__(self, bot_instance):
        super().__init__(timeout=180)
        self.bot = bot_instance

        # Botão "Comprar Robux"
        self.add_item(discord.ui.Button(label="Comprar Robux", style=discord.ButtonStyle.green, custom_id="buy_robux_button"))
        # Botão "Consultar Valores"
        self.add_item(discord.ui.Button(label="Consultar Valores", style=discord.ButtonStyle.secondary, custom_id="consult_robux_values_button"))


    @discord.ui.button(label="Comprar Robux", style=discord.ButtonStyle.green, custom_id="buy_robux_button")
    async def buy_robux_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f"[DEBUG] Botão 'Comprar Robux' clicado por {interaction.user.name}.")
        product_name = "Robux" # Assume que é sempre "Robux"
        user_id = interaction.user.id

        try:
            current_cart = await self.bot.db.fetch_one(
                "SELECT cart_thread_id FROM users WHERE user_id = $1 AND cart_thread_id IS NOT NULL",
                user_id
            )
            if current_cart:
                existing_thread_id = current_cart['cart_thread_id']
                existing_thread = interaction.guild.get_thread(existing_thread_id)
                if existing_thread:
                    embed = discord.Embed(
                        title="🛒 Carrinho em Andamento!",
                        description=f"Você já possui um carrinho em andamento! [Clique aqui para acessá-lo]({existing_thread.jump_url}).\n\nDeseja iniciar uma **nova compra**?",
                        color=config.ROSE_COLOR
                    )
                    class NewPurchaseOptionView(discord.ui.View):
                        def __init__(self, bot_instance, original_interaction):
                            super().__init__(timeout=60)
                            self.bot = bot_instance
                            self.user_id = original_interaction.user.id
                            self.original_interaction = original_interaction
                        @discord.ui.button(label="Iniciar Nova Compra", style=discord.ButtonStyle.green, custom_id="start_new_purchase_from_robux_existing_cart")
                        async def start_new_purchase_button(self, interaction_button: discord.Interaction, button: discord.ui.Button):
                            await self.bot.db.execute("UPDATE users SET cart_thread_id = NULL, cart_product_name = NULL, cart_quantity = NULL, cart_status = NULL, roblox_nickname = NULL WHERE user_id = $1", self.user_id)
                            await self.bot.get_cog("Purchase").robux_command.callback(self.bot.get_cog("Purchase"), interaction_button)
                    await interaction.response.send_message(embed=embed, view=NewPurchaseOptionView(self.bot, interaction), ephemeral=True)
                    return
                else:
                    await self.bot.db.execute("UPDATE users SET cart_thread_id = NULL, cart_product_name = NULL, cart_quantity = NULL, cart_status = NULL, roblox_nickname = NULL WHERE user_id = $1", user_id)

            await self.bot.get_cog("Purchase")._create_new_cart(
                interaction,
                product_name,
                config.PRODUCTS[product_name]
            )
            
        except Exception as e:
            print(f"[CRITICAL ERROR] Erro CRÍTICO em RobuxMainView.buy_robux_button_callback para {interaction.user.name}: {e}")
            error_embed = discord.Embed(
                title="Erro na Compra de Robux",
                description=f"Ocorreu um erro ao iniciar a compra de Robux. Por favor, tente novamente. Erro: `{e}`",
                color=config.ROSE_COLOR
            )
            if interaction.response.is_done():
                await interaction.followup.send(embed=error_embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=error_embed, ephemeral=True)

    @discord.ui.button(label="Consultar Valores", style=discord.ButtonStyle.secondary, custom_id="consult_robux_values_button")
    async def consult_robux_values_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f"[DEBUG] Botão 'Consultar Valores' clicado por {interaction.user.name}.")
        robux_product = config.PRODUCTS.get("Robux")
        if not robux_product:
            embed = discord.Embed(title="Erro", description="Informações de Robux não encontradas.", color=config.ROSE_COLOR)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        prices_str = "\n".join([f"**{qty}**: R${price:.2f}" for qty, price in robux_product['prices'].items()])
        vip_prices_str = "\n".join([f"**VIP {qty}**: R${price:.2f}" for qty, price in robux_product['vip_prices'].items()]) if 'vip_prices' in robux_product else "Nenhum preço VIP disponível."

        embed = discord.Embed(
            title="Tabela de Preços de Robux",
            description="Aqui estão os valores de Robux disponíveis:",
            color=config.ROSE_COLOR
        )
        embed.add_field(name="Valores Padrão", value=prices_str, inline=False)
        embed.add_field(name="Valores VIP (se aplicável)", value=vip_prices_str, inline=False)
        embed.set_footer(text="Atenção: Os preços podem ter taxas incluídas ou o Roblox pode cobrar uma porcentagem na Gamepass.")

        await interaction.response.send_message(embed=embed, ephemeral=True)


# Adaptação da ProductSelectView do seu bot antigo (para itens de preço)
class ProductSelectView(discord.ui.View):
    def __init__(self, bot_instance, products_dict_flat: dict, category_name: str, parent_category_filter: str = None):
        super().__init__(timeout=180)
        self.bot = bot_instance
        self.category_name = category_name
        self.parent_category_filter = parent_category_filter # Usado para voltar à seleção de subcategoria

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

        # Adicionar botão de "Voltar" se houver uma categoria pai
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
            return await interaction.response.send_message(embed=embed, ephemeral=True)
            
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
                                await self.bot.get_cog("Purchase").robux_command.callback(self.bot.get_cog("Purchase"), interaction_button)
                            elif self.current_category_filter == "jogos":
                                await self.bot.get_cog("Purchase").games_command.callback(self.bot.get_cog("Purchase"), interaction_button)
                            elif self.current_category_filter == "giftcard":
                                await self.bot.get_cog("Purchase").giftcard_command.callback(self.bot.get_cog("Purchase"), interaction_button)
                            else:
                                await interaction_button.response.send_message("Não foi possível recarregar a categoria anterior. Por favor, use um comando de compra novamente.", ephemeral=True)

                            print(f"[DEBUG] Mensagem editada com nova seleção de produto.")
                    
                    print(f"[DEBUG] Enviando mensagem de carrinho existente com opção de nova compra para {interaction.user.name}.")
                    await interaction.response.send_message(embed=embed, view=NewPurchaseOptionView(self.bot, interaction, self.category_name, self.category_name.capitalize()), ephemeral=True) # Passa a categoria selecionada
                    print(f"[DEBUG] Mensagem de carrinho existente enviada.")
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


# Nova View para seleção de subcategoria de jogos
class GameSubcategorySelectView(discord.ui.View):
    def __init__(self, bot_instance):
        super().__init__(timeout=180)
        self.bot = bot_instance
        
        game_subcategories = set() # Usar set para garantir subcategorias únicas
        for product_name, details in config.PRODUCTS.items():
            if details.get('category') == 'jogos' and 'sub_category' in details:
                game_subcategories.add(details['sub_category'])
        
        options = []
        for sub_cat in sorted(list(game_subcategories)): # Ordenar alfabeticamente
            options.append(discord.SelectOption(label=sub_cat, value=sub_cat))
        
        print(f"[DEBUG] GameSubcategorySelectView: Número total de subcategorias geradas: {len(options)}.")

        if options:
            self.add_item(
                discord.ui.Select(
                    placeholder="Selecione um tipo de jogo...",
                    min_values=1,
                    max_values=1,
                    options=options[:25], # Limite de 25 opções
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
        
        # Coletar os produtos da subcategoria selecionada
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
        # Passa 'jogos' como category_name e selected_subcategory como parent_category_filter
        await interaction.response.edit_message(
            embed=embed, 
            view=ProductSelectView(self.bot, products_in_subcategory_flat, "Jogo", parent_category_filter="jogos") # "Jogo" como nome mais amigável
        )
        print(f"[DEBUG] Menu de seleção de jogos da subcategoria '{selected_subcategory}' enviado.")


# Nova View para seleção de marca de giftcard
class GiftcardBrandSelectView(discord.ui.View):
    def __init__(self, bot_instance):
        super().__init__(timeout=180)
        self.bot = bot_instance
        
        giftcard_brands = set() # Usar set para garantir marcas únicas
        for product_name, details in config.PRODUCTS.items():
            if details.get('category') == 'giftcard':
                giftcard_brands.add(product_name) # O nome do produto principal é a "marca"
        
        options = []
        for brand_name in sorted(list(giftcard_brands)): # Ordenar alfabeticamente
            options.append(discord.SelectOption(label=brand_name, value=brand_name))
        
        print(f"[DEBUG] GiftcardBrandSelectView: Número total de marcas geradas: {len(options)}.")

        if options:
            self.add_item(
                discord.ui.Select(
                    placeholder="Selecione uma marca de Giftcard...",
                    min_values=1,
                    max_values=1,
                    options=options[:25], # Limite de 25 opções
                    custom_id="giftcard_brand_select"
                )
            )
        else:
            print(f"[ERROR] GiftcardBrandSelectView: Nenhuma marca de giftcard encontrada.")
            self.add_item(discord.ui.Button(label="Nenhuma marca de giftcard encontrada.", style=discord.ButtonStyle.red, disabled=True))

    @discord.ui.select(custom_id="giftcard_brand_select")
    async def select_brand_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        print(f"[DEBUG] GiftcardBrandSelectView: select_brand_callback por {interaction.user.name}.")
        selected_brand = select.values[0]
        
        # Coletar os produtos da marca selecionada
        products_in_brand_flat = {}
        if selected_brand in config.PRODUCTS and 'prices' in config.PRODUCTS[selected_brand]:
            for item_name, item_price in config.PRODUCTS[selected_brand]['prices'].items():
                products_in_brand_flat[item_name] = item_price
        
        embed = discord.Embed(
            title=f"🛒 Selecione um Giftcard ({selected_brand})",
            description="Use o menu abaixo para escolher o giftcard que deseja comprar.",
            color=config.ROSE_COLOR
        )
        # Passa 'giftcard' como category_name e selected_brand como parent_category_filter
        await interaction.response.edit_message(
            embed=embed, 
            view=ProductSelectView(self.bot, products_in_brand_flat, "Giftcard", parent_category_filter="giftcard") # "Giftcard" como nome mais amigável
        )
        print(f"[DEBUG] Menu de seleção de giftcards da marca '{selected_brand}' enviado.")


# Classe principal do Cog
class Purchase(commands.Cog):
    def __init__(self, bot: discord.Client): # Ajustado para discord.Client para melhor compatibilidade com types
        self.bot = bot
        self.db = bot.db

    # Novos comandos separados por categoria
    @discord.app_commands.command(name="robux", description="Compre Robux para Roblox.")
    async def robux_command(self, interaction: discord.Interaction):
        print(f"[DEBUG] Comando /robux recebido de {interaction.user.name}.")
        embed = discord.Embed(
            title="💎 Central de Robux",
            description="Escolha uma opção para continuar.",
            color=config.ROSE_COLOR
        )
        await interaction.response.send_message(embed=embed, view=RobuxMainView(self.bot), ephemeral=False)
        print(f"[DEBUG] Mensagem de botão Comprar Robux enviada publicamente para {interaction.user.name}.")


    @discord.app_commands.command(name="jogos", description="Compre itens para outros jogos (Valorant, Free Fire, etc.).")
    async def games_command(self, interaction: discord.Interaction):
        print(f"[DEBUG] Comando /jogos recebido de {interaction.user.name}.")
        embed = discord.Embed(
            title="🎮 Selecione o Tipo de Jogo",
            description="Use o menu abaixo para escolher o tipo de jogo que você busca.",
            color=config.ROSE_COLOR
        )
        await interaction.response.send_message(embed=embed, view=GameSubcategorySelectView(self.bot), ephemeral=True)
        print(f"[DEBUG] Menu de seleção de subcategoria de jogos enviado para {interaction.user.name}.")


    @discord.app_commands.command(name="giftcard", description="Compre Giftcards (PlayStation, Xbox, Google Play, Apple).")
    async def giftcard_command(self, interaction: discord.Interaction):
        print(f"[DEBUG] Comando /giftcard recebido de {interaction.user.name}.")
        embed = discord.Embed(
            title="💳 Selecione a Marca do Giftcard",
            description="Use o menu abaixo para escolher a marca de Giftcard que você deseja comprar.",
            color=config.ROSE_COLOR
        )
        await interaction.response.send_message(embed=embed, view=GiftcardBrandSelectView(self.bot), ephemeral=True)
        print(f"[DEBUG] Menu de seleção de marca de giftcard enviado para {interaction.user.name}.")


    # Função unificada para lidar com o primeiro nível de seleção (não é mais usada diretamente pelos comandos slash)
    # Mas a lógica é similar ao que ela fazia.
    async def _handle_product_category_command(self, interaction: discord.Interaction, products_dict_flat: dict, category_filter: str, category_name: str):
        # Esta função agora é chamada INTERNAMENTE para exibir o segundo nível de menus
        user_id = interaction.user.id
        print(f"[DEBUG] _handle_product_category_command iniciado para {user_id} com categoria '{category_filter}'.")

        try:
            current_cart = await self.db.fetch_one(
                "SELECT cart_thread_id, cart_product_name FROM users WHERE user_id = $1 AND cart_thread_id IS NOT NULL",
                user_id
            )
            print(f"[DEBUG] Verificação de carrinho em andamento para {user_id}: {current_cart is not None}.")

            if current_cart:
                existing_thread_id = current_cart['cart_thread_id']
                existing_thread = interaction.guild.get_thread(existing_thread_id)
                
                if existing_thread:
                    embed = discord.Embed(
                        title="🛒 Você já tem um carrinho!",
                        description=f"Você já possui um carrinho em andamento! [Clique aqui para acessá-lo]({existing_thread.jump_url}).\n\nDeseja iniciar uma **nova compra**?",
                        color=config.ROSE_COLOR
                    )
                    print(f"[DEBUG] Carrinho existente ativo, redirecionando para {existing_thread.jump_url}.")
                    
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
                                await self.bot.get_cog("Purchase").robux_command.callback(self.bot.get_cog("Purchase"), interaction_button)
                            elif self.current_category_filter == "jogos":
                                await self.bot.get_cog("Purchase").games_command.callback(self.bot.get_cog("Purchase"), interaction_button)
                            elif self.current_category_filter == "giftcard":
                                await self.bot.get_cog("Purchase").giftcard_command.callback(self.bot.get_cog("Purchase"), interaction_button)
                            else:
                                await interaction_button.response.send_message("Não foi possível recarregar a categoria anterior. Por favor, use um comando de compra novamente.", ephemeral=True)

                            print(f"[DEBUG] Mensagem editada com nova seleção de produto.")
                    
                    print(f"[DEBUG] Enviando mensagem de carrinho existente com opção de nova compra para {interaction.user.name}.")
                    await interaction.response.send_message(embed=embed, view=NewPurchaseOptionView(self.bot, interaction, category_filter, category_name), ephemeral=True)
                    print(f"[DEBUG] Mensagem de carrinho existente enviada.")
                    return 
                else:
                    print(f"[DEBUG] Carrinho existente mas thread não encontrada, limpando DB para {user_id}.")
                    await self.db.execute("UPDATE users SET cart_thread_id = NULL, cart_product_name = NULL, cart_quantity = NULL, cart_status = NULL, roblox_nickname = NULL WHERE user_id = $1", user_id)
                    print(f"[DEBUG] DB limpo, prosseguindo para criar novo carrinho.")

            embed = discord.Embed(
                title=f"🛒 Selecione um {category_name}",
                description=f"Use o menu abaixo para escolher o {category_name} que deseja comprar.",
                color=config.ROSE_COLOR
            )
            print(f"[DEBUG] Enviando menu de seleção de {category_name} para {interaction.user.name}.")
            # AQUI: products_dict_flat é o dicionário plano de nome:preço. parent_category_filter é o nome da categoria pai.
            await interaction.response.send_message(embed=embed, view=ProductSelectView(self.bot, products_dict_flat, category_name, parent_category_filter=category_filter), ephemeral=True)
            print(f"[DEBUG] Mensagem de seleção de {category_name} enviada.")

        except Exception as e:
            print(f"[CRITICAL ERROR] Erro CRÍTICO em _handle_product_category_command para {interaction.user.name}: {e}")
            error_embed = discord.Embed(
                title=f"Erro no Comando /{category_filter}",
                description=f"Ocorreu um erro ao iniciar o processo de compra de {category_name}. Por favor, tente novamente. Erro: `{e}`",
                color=config.ROSE_COLOR
            )
            if interaction.response.is_done():
                await interaction.followup.send(embed=error_embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
            print(f"[DEBUG] Mensagem de erro para /{category_filter} enviada.")


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
                cart_info = await self.bot.db.fetch_one(
                    "SELECT cart_product_name FROM users WHERE user_id = $1 AND cart_thread_id = $2",
                    user_id, interaction.channel.id
                )

                if not cart_info:
                    print(f"[DEBUG] Carrinho não ativo ou não iniciado por {user_id}.")
                    await interaction.response.send_message("Este não é um carrinho ativo ou você não o iniciou.", ephemeral=True)
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
                    await interaction.response.send_message(embed=embed)
                    print(f"[DEBUG] Notificação de ticket enviada.")
                else:
                    print(f"[WARNING] Cargo de Admin ({config.ADMIN_ROLE_ID}) não encontrado para notificar ticket.")
                    await interaction.response.send_message("Não foi possível encontrar o cargo de administrador para notificar.", ephemeral=True)
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
                cart_info = await self.bot.db.fetch_one(
                    "SELECT cart_product_name FROM users WHERE user_id = $1 AND cart_thread_id = $2",
                    user_id, interaction.channel.id
                )

                if not cart_info:
                    print(f"[DEBUG] Carrinho não ativo ou não iniciado por {user_id}.")
                    await interaction.response.send_message("Este não é um carrinho ativo ou você não o iniciou.", ephemeral=True)
                    return

                await self.bot.db.execute(
                    "UPDATE users SET cart_status = $1 WHERE user_id = $2 AND cart_thread_id = $3",
                    'gamepass_confirmed', user_id, interaction.channel.id
                )
                print(f"[DEBUG] Status do carrinho atualizado para 'gamepass_confirmed' para {user_id}.")

                embed = discord.Embed(
                    title="✅ Gamepass Confirmada!",
                    description="Ótimo! Agora, por favor, **envie o link da sua Gamepass** neste chat. Verificaremos o valor para prosseguir com o pagamento.",
                    color=config.ROSE_COLOR
                )
                print(f"[DEBUG] Editando mensagem de gamepass confirmada para {interaction.user.name}.")
                await interaction.response.edit_message(embed=embed, view=None)
                print(f"[DEBUG] Mensagem de gamepass confirmada editada.")

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

        elif interaction.type == discord.InteractionType.component and interaction.data.get("custom_id") == "gamepass_help":
            print(f"[DEBUG] Botão 'Preciso de ajuda com a Gamepass' clicado por {interaction.user.name}.")
            if interaction.channel.type != discord.ChannelType.private_thread:
                print(f"[DEBUG] Interação de ajuda de gamepass fora de thread privada, ignorando.")
                return

            user_id = interaction.user.id
            try:
                cart_info = await self.bot.db.fetch_one(
                    "SELECT cart_product_name FROM users WHERE user_id = $1 AND cart_thread_id = $2",
                    user_id, interaction.channel.id
                )

                if not cart_info:
                    print(f"[DEBUG] Carrinho não ativo ou não iniciado por {user_id}.")
                    await interaction.response.send_message("Este não é um carrinho ativo ou você não o iniciou.", ephemeral=True)
                    return

                admin_role = interaction.guild.get_role(config.ADMIN_ROLE_ID)
                if admin_role:
                    embed = discord.Embed(
                        title="🆘 Ajuda com Gamepass Solicitada!",
                        description=f"{admin_role.mention}, o usuário {interaction.user.name} precisa de ajuda para configurar a Gamepass. Por favor, auxilie-o.",
                        color=config.ROSE_COLOR
                    )
                    print(f"[DEBUG] Enviando notificação de ajuda de gamepass para admin e {interaction.user.name}.")
                    await interaction.response.send_message(embed=embed)
                    await interaction.message.edit(view=None)
                    print(f"[DEBUG] Notificação de ajuda de gamepass enviada.")
                else:
                    print(f"[WARNING] Cargo de Admin ({config.ADMIN_ROLE_ID}) não encontrado para notificar ajuda de gamepass.")
                    await interaction.response.send_message("Não foi possível encontrar o cargo de administrador para notificar.", ephemeral=True)
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


# Função setup para adicionar o cog ao bot
async def setup(bot: commands.Bot):
    await bot.add_cog(Purchase(bot))
