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
        print(f"[DEBUG] Modal Nickname: on_submit por {interaction.user.name}")
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
            
            print(f"[DEBUG] Enviando modal para nickname para {interaction.user.name}.")
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


class ProductSelectView(discord.ui.View):
    def __init__(self, bot_instance):
        super().__init__(timeout=180)
        self.bot = bot_instance

        options = []
        for product_name, details in config.PRODUCTS.items():
            options.append(
                discord.SelectOption(
                    label=product_name,
                    description=f"Compre {product_name}",
                    emoji=details["emoji"]
                )
            )
        
        self.add_item(
            discord.ui.Select(
                placeholder="Selecione um produto...",
                min_values=1,
                max_values=1,
                options=options,
                custom_id="product_select"
            )
        )

    @discord.ui.select(custom_id="product_select")
    async def select_product_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        print(f"[DEBUG] ProductSelectView: select_product_callback por {interaction.user.name}.")
        selected_product_name = select.values[0]
        product_details = config.PRODUCTS[selected_product_name]
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
                        title="🛒 Carrinho em Andamento!",
                        description=f"Você já possui um carrinho em andamento! [Clique aqui para acessá-lo]({existing_thread.jump_url}).",
                        color=config.ROSE_COLOR
                    )
                    print(f"[DEBUG] Carrinho existente detectado, redirecionando para {existing_thread.jump_url}.")
                    
                    class NewPurchaseOptionView(discord.ui.View):
                        def __init__(self, bot_instance, original_interaction):
                            super().__init__(timeout=60)
                            self.bot = bot_instance
                            self.user_id = original_interaction.user.id
                            self.original_interaction = original_interaction 

                        @discord.ui.button(label="Iniciar Nova Compra", style=discord.ButtonStyle.green, custom_id="start_new_purchase")
                        async def start_new_purchase_button(self, interaction_button: discord.Interaction, button: discord.ui.Button):
                            print(f"[DEBUG] Botão 'Iniciar Nova Compra' clicado por {interaction_button.user.name}.")
                            await self.bot.db.execute("UPDATE users SET cart_thread_id = NULL, cart_product_name = NULL, cart_quantity = NULL, cart_status = NULL, roblox_nickname = NULL WHERE user_id = $1", self.user_id)
                            
                            embed = discord.Embed(
                                title="🛒 Selecione um Produto para a Nova Compra",
                                description="Use o menu abaixo para escolher o produto que deseja comprar.",
                                color=config.ROSE_COLOR
                            )
                            print(f"[DEBUG] Editando mensagem com nova seleção de produto para {interaction_button.user.name}.")
                            await interaction_button.response.edit_message(embed=embed, view=ProductSelectView(self.bot))
                            print(f"[DEBUG] Mensagem editada com nova seleção de produto.")
                    
                    print(f"[DEBUG] Enviando mensagem de carrinho existente com opção de nova compra para {interaction.user.name}.")
                    await interaction.response.send_message(embed=embed, view=NewPurchaseOptionView(self.bot, interaction), ephemeral=True)
                    print(f"[DEBUG] Mensagem de carrinho existente enviada.")
                    return 
                else:
                    print(f"[DEBUG] Carrinho existente mas thread não encontrada, limpando DB para {user_id}.")
                    await self.bot.db.execute("UPDATE users SET cart_thread_id = NULL, cart_product_name = NULL, cart_quantity = NULL, cart_status = NULL, roblox_nickname = NULL WHERE user_id = $1", user_id)
                    print(f"[DEBUG] DB limpo, prosseguindo para criar novo carrinho.")

            print(f"[DEBUG] Invocando _create_new_cart para {user_id}.")
            # >>> AQUI ESTAVA O ERRO DE ATRIBUTO! A função deve ser chamada dentro da própria classe
            #      e não de um objeto ProductSelectView novo, ou passar o nome e detalhes corretos.
            #      A correção está abaixo, usando o selected_product_name e product_details corretos.
            await self._create_new_cart(interaction, selected_product_name, product_details)
            
        except Exception as e:
            print(f"[CRITICAL ERROR] Erro CRÍTICO em select_product_callback (ProductSelectView) para {interaction.user.name}: {e}")
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


    # >>> ESTE MÉTODO DEVE ESTAR AQUI DENTRO, COM ESTA INDENTAÇÃO! <<<
    async def _create_new_cart(self, interaction: discord.Interaction, selected_product_name: str, product_details: dict):
        print(f"[DEBUG] _create_new_cart iniciado para {interaction.user.name}.")
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
            return await interaction.response.send_message(embed=embed, ephemeral=True)

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
                # Adiciona todos os admins à thread
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
            print(f"[DEBUG] Editando mensagem de resposta inicial para {interaction.user.name}.")
            await interaction.response.edit_message(embed=embed, view=None)
            print(f"[DEBUG] Mensagem de resposta inicial editada.")

            # Mensagem inicial na thread do carrinho
            thread_embed = discord.Embed(
                title=f"Bem-vindo(a) ao seu Carrinho para {selected_product_name}!",
                description=f"Olá {user.mention}! Por favor, aguarde as instruções ou clique em 'Pegar Ticket' para chamar um atendente.",
                color=config.ROSE_COLOR
            )
            ticket_button_view = discord.ui.View()
            ticket_button_view.add_item(discord.ui.Button(label="Pegar Ticket", style=discord.ButtonStyle.primary, custom_id="get_cart_ticket"))
            
            print(f"[DEBUG] Enviando mensagem inicial na thread para {user.name}.")
            await new_thread.send(embed=thread_embed, view=ticket_button_view)
            print(f"[DEBUG] Mensagem inicial na thread enviada.")
            
            # Notifica o canal de logs de "carrinho em andamento"
            logs_channel = guild.get_channel(config.CARRINHO_EM_ANDAMENTO_CHANNEL_ID)
            if logs_channel and logs_channel.id != new_thread.id:
                 log_embed = discord.Embed(
                    title="Carrinho em Andamento!",
                    description=f"**Usuário:** {user.mention}\n**Produto:** {selected_product_name}\n**Carrinho:** {new_thread.mention}\n**Status:** Iniciado",
                    color=config.ROSE_COLOR
                 )
                 print(f"[DEBUG] Enviando log para o canal de carrinhos em andamento ({logs_channel.name}).")
                 await logs_channel.send(embed=log_embed)
                 print(f"[DEBUG] Log enviado para canal de carrinhos em andamento.")

            if product_details['type'] == 'automatized':
                print(f"[DEBUG] Produto automatizado, enviando seleção de quantidade para {user.name}.")
                await new_thread.send(
                    embed=discord.Embed(
                        title="Selecione a Quantidade de Robux",
                        description="Escolha a quantidade de Robux que deseja comprar.",
                        color=config.ROSE_COLOR
                    ),
                    view=RobuxQuantitySelectView(self.bot, selected_product_name)
                )
                print(f"[DEBUG] Seleção de quantidade enviada.")

            elif product_details['type'] == 'manual':
                print(f"[DEBUG] Produto manual, notificando admin para {user.name}.")
                admin_role = guild.get_role(config.ADMIN_ROLE_ID)
                await new_thread.send(f"{admin_role.mention}, um atendimento manual é necessário para esta compra. Aguarde um momento por favor.")
                print(f"[DEBUG] Admin notificado para produto manual.")

        except Exception as e:
            print(f"[CRITICAL ERROR] Erro CRÍTICO em _create_new_cart para {interaction.user.name}: {e}")
            error_embed = discord.Embed(
                title="Erro ao Iniciar Carrinho",
                description=f"Ocorreu um erro ao criar seu carrinho. Por favor, tente novamente ou contate um administrador. Erro: `{e}`",
                color=config.ROSE_COLOR
            )
            if interaction.response.is_done():
                await interaction.followup.send(embed=error_embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
            print(f"[DEBUG] Mensagem de erro de carrinho enviada.")


# Classe principal do Cog
class Purchase(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = bot.db

    @discord.app_commands.command(name="comprar2", description="Inicia o processo de compra de produtos (versão 2).")
    async def buy_command(self, interaction: discord.Interaction):
        print(f"[DEBUG] Comando /comprar2 recebido de {interaction.user.name} (ID: {interaction.user.id}).")
        user_id = interaction.user.id

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
                        def __init__(self, bot_instance, original_interaction):
                            super().__init__(timeout=60)
                            self.bot = bot_instance
                            self.user_id = original_interaction.user.id
                            self.original_interaction = original_interaction 

                        @discord.ui.button(label="Iniciar Nova Compra", style=discord.ButtonStyle.green, custom_id="start_new_purchase")
                        async def start_new_purchase_button(self, interaction_button: discord.Interaction, button: discord.ui.Button):
                            print(f"[DEBUG] Botão 'Iniciar Nova Compra' clicado por {interaction_button.user.name}.")
                            await self.bot.db.execute("UPDATE users SET cart_thread_id = NULL, cart_product_name = NULL, cart_quantity = NULL, cart_status = NULL, roblox_nickname = NULL WHERE user_id = $1", self.user_id)
                            
                            embed = discord.Embed(
                                title="🛒 Selecione um Produto para a Nova Compra",
                                description="Use o menu abaixo para escolher o produto que deseja comprar.",
                                color=config.ROSE_COLOR
                            )
                            print(f"[DEBUG] Editando mensagem com nova seleção de produto para {interaction_button.user.name}.")
                            await interaction_button.response.edit_message(embed=embed, view=ProductSelectView(self.bot))
                            print(f"[DEBUG] Mensagem editada com nova seleção de produto.")
                    
                    print(f"[DEBUG] Enviando mensagem de carrinho existente com opção de nova compra para {interaction.user.name}.")
                    await interaction.response.send_message(embed=embed, view=NewPurchaseOptionView(self.bot, interaction), ephemeral=True)
                    print(f"[DEBUG] Mensagem de carrinho existente enviada.")
                    return 
                else:
                    print(f"[DEBUG] Carrinho existente mas thread não encontrada, limpando DB para {user_id}.")
                    await self.db.execute("UPDATE users SET cart_thread_id = NULL, cart_product_name = NULL, cart_quantity = NULL, cart_status = NULL, roblox_nickname = NULL WHERE user_id = $1", user_id)
                    print(f"[DEBUG] DB limpo, prosseguindo para criar novo carrinho.")

            print(f"[DEBUG] Enviando menu de seleção de produto inicial para {interaction.user.name}.")
            await interaction.response.send_message(embed=discord.Embed(
                title="🛒 Selecione um Produto",
                description="Use o menu abaixo para escolher o produto que deseja comprar.",
                color=config.ROSE_COLOR
            ), view=ProductSelectView(self.bot), ephemeral=True) # Passa a instância do bot
            print(f"[DEBUG] Mensagem de seleção de produto inicial enviada.")

        except Exception as e:
            print(f"[CRITICAL ERROR] Erro CRÍTICO em buy_command para {interaction.user.name}: {e}")
            error_embed = discord.Embed(
                title="Erro no Comando /comprar2",
                description=f"Ocorreu um erro ao iniciar o processo de compra. Por favor, tente novamente. Erro: `{e}`",
                color=config.ROSE_COLOR
            )
            if interaction.response.is_done():
                await interaction.followup.send(embed=error_embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
            print(f"[DEBUG] Mensagem de erro para /comprar2 enviada.")


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
                        description=f"{admin_role.mention}, o usuário {interaction.user.mention} solicitou ajuda para a compra de **{product_name}**.\n\n"
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
                    "SELECT cart_product_name, cart_quantity FROM users WHERE user_id = $1 AND cart_thread_id = $2",
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
                        description=f"{admin_role.mention}, o usuário {interaction.user.mention} precisa de ajuda para configurar a Gamepass. Por favor, auxilie-o.",
                        color=config.ROSE_COLOR
                    )
                    print(f"[DEBUG] Enviando notificação de ajuda de gamepass para admin e {interaction.user.name}.")
                    await interaction.response.send_message(embed=embed)
                    await interaction.message.edit(view=None) # Remove os botões após a solicitação de ajuda
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
