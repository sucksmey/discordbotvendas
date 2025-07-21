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
