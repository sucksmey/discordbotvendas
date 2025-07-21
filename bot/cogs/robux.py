# cogs/robux.py

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
                    "**8.** Ative `Item for Sale` (Item à Venda) e **defina o preço exato de Robux:** `R$ {int(self.total_price * 0.7)}` Robux (o Roblox tira 30%).\n"
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
            
            print(f"[DEBUG] Antes de interaction.response.send_modal (Robux Quantity).")
            await interaction.response.send_modal(RobloxNicknameModal(self.bot, self.product_name, selected_quantity_str, total_price))
            print(f"[DEBUG] Após interaction.response.send_modal (Robux Quantity).")

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
                            await self.bot.get_cog("RobuxCog").robux_command.callback(self.bot.get_cog("RobuxCog"), interaction_button) # Chama o comando /robux
                    
                    print(f"[DEBUG] Antes de interaction.response.send_message (Robux Existente).")
                    await interaction.response.send_message(embed=embed, view=NewPurchaseOptionView(self.bot, interaction), ephemeral=True)
                    print(f"[DEBUG] Após interaction.response.send_message (Robux Existente).")
                    return
                else:
                    await self.bot.db.execute("UPDATE users SET cart_thread_id = NULL, cart_product_name = NULL, cart_quantity = NULL, cart_status = NULL, roblox_nickname = NULL WHERE user_id = $1", user_id)

            product_name = "Robux"
            print(f"[DEBUG] Antes de _create_new_cart (Robux Main View).")
            # _create_new_cart precisa ser acessível do RobuxCog
            await self.bot.get_cog("RobuxCog")._create_new_cart(
                interaction,
                product_name,
                config.PRODUCTS[product_name]
            )
            print(f"[DEBUG] Após _create_new_cart (Robux Main View).")
            
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
            print(f"[DEBUG] Antes de interaction.response.send_message (Consultar Valores Erro).")
            return await interaction.response.send_message(embed=embed, ephemeral=True)
            print(f"[DEBUG] Após interaction.response.send_message (Consultar Valores Erro).")

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

        print(f"[DEBUG] Antes de interaction.response.send_message (Consultar Valores Sucesso).")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        print(f"[DEBUG] Após interaction.response.send_message (Consultar Valores Sucesso).")


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


# Classe principal do Cog
class Purchase(commands.Cog):
    def __init__(self, bot: discord.Client):
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
        print(f"[DEBUG] Antes de interaction.response.send_message (Robux Command).")
        await interaction.response.send_message(embed=embed, view=RobuxMainView(self.bot), ephemeral=False)
        print(f"[DEBUG] Após interaction.response.send_message (Robux Command).")


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


    # Função unificada para lidar com o primeiro nível de seleção (não é mais usada diretamente pelos comandos slash)
    async def _handle_product_category_command(self, interaction: discord.Interaction, products_dict_flat: dict, category_filter: str, category_name: str):
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
                    print(f"[DEBUG] Antes de interaction.response.send_message (handle_category_command Existente).")
                    await interaction.response.send_message(embed=embed, view=NewPurchaseOptionView(self.bot, interaction, category_filter, category_name), ephemeral=True)
                    print(f"[DEBUG] Após interaction.response.send_message (handle_category_command Existente).")
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
            print(f"[DEBUG] Antes de interaction.response.send_message (handle_category_command Novo).")
            await interaction.response.send_message(embed=embed, view=ProductSelectView(self.bot, products_dict_flat, category_name, parent_category_filter=category_filter), ephemeral=True)
            print(f"[DEBUG] Após interaction.response.send_message (handle_category_command Novo).")

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
async def on_interaction_ticket_button(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component and interaction.data.get("custom_id") == "get_cart_ticket":
        print(f"[DEBUG] Botão 'Pegar Ticket' clicado por {interaction.user.name}.")
        if interaction.channel.type != discord.ChannelType.private_thread:
            print(f"[DEBUG] Interação de ticket fora de thread privada, ignorando.")
            return

        user_id = interaction.user.id
        try:
            # Pega o product_name do DB
            cart_info = await interaction.client.db.fetch_one( # Acessa o DB via interaction.client.db
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
async def on_interaction_gamepass_confirm_button(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component and interaction.data.get("custom_id") == "gamepass_created_confirm":
        print(f"[DEBUG] Botão 'Gamepass Confirmada' clicado por {interaction.user.name}.")
        if interaction.channel.type != discord.ChannelType.private_thread:
            print(f"[DEBUG] Interação de gamepass fora de thread privada, ignorando.")
            return

        user_id = interaction.user.id
        try:
            cart_info = await interaction.client.db.fetch_one( # Acessa o DB via interaction.client.db
                "SELECT cart_product_name, cart_quantity FROM users WHERE user_id = $1 AND cart_thread_id = $2",
                user_id, interaction.channel.id
            )

            if not cart_info:
                print(f"[DEBUG] Carrinho não ativo ou não iniciado por {user_id}.")
                print(f"[DEBUG] Antes de interaction.response.send_message (Gamepass Confirmar Erro - Carrinho).")
                await interaction.response.send_message("Este não é um carrinho ativo ou você não o iniciou.", ephemeral=True)
                print(f"[DEBUG] Após interaction.response.send_message (Gamepass Confirmar Erro - Carrinho).")
                return

            await interaction.client.db.execute( # Acessa o DB via interaction.client.db
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
            cart_info = await interaction.client.db.fetch_one( # Acessa o DB via interaction.client.db
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
    # Registrar os listeners diretamente no bot
    bot.add_listener(on_back_to_parent_category_button)
    bot.add_listener(on_interaction_ticket_button)
    bot.add_listener(on_interaction_gamepass_confirm_button)
    await bot.add_cog(Purchase(bot))
