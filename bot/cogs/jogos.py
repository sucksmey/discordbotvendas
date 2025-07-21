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

            # _create_new_cart precisa ser acessível do RobuxCog
            # Então, vamos acessá-lo pelo bot.get_cog("RobuxCog")
            await self.bot.get_cog("RobuxCog")._create_new_cart(interaction, actual_product_name_for_cart, actual_product_details_for_cart)
            
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


    # _create_new_cart não deve estar aqui, pois está em robux.py agora.
    # Removido async def _create_new_cart (interaction: discord.Interaction, selected_product_name: str, product_details: dict):
    # e todo o seu conteúdo.

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
