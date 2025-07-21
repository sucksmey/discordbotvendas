# cogs/purchase.py

import discord
from discord.ext import commands
import config
import uuid # Para gerar IDs únicos de pedido
import asyncio # Para simular um delay

# --- Modals ---
class RobloxNicknameModal(discord.ui.Modal, title="Informe seu Nickname no Roblox"):
    def __init__(self, db, product_name, selected_quantity, total_price):
        super().__init__()
        self.db = db
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
        user_id = interaction.user.id
        nickname = self.roblox_nickname.value

        # Atualiza o nickname no carrinho do usuário no DB
        await self.db.execute(
            "UPDATE users SET roblox_nickname = $1, cart_status = $2 WHERE user_id = $3 AND cart_thread_id IS NOT NULL",
            nickname, 'nickname_informed', user_id
        )

        embed = discord.Embed(
            title="✅ Nickname Salvo!",
            description=f"Seu nickname `{nickname}` foi salvo. Agora, vamos criar a Gamepass para receber seus {self.selected_quantity}!",
            color=config.ROSE_COLOR
        )

        # Tutorial da Gamepass e botões de confirmação
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

        # View com botões para Gamepass
        gamepass_confirm_view = discord.ui.View(timeout=300) # 5 minutos para confirmar
        gamepass_confirm_view.add_item(discord.ui.Button(label="Já criei e desativei preços regionais", style=discord.ButtonStyle.success, custom_id="gamepass_created_confirm"))
        gamepass_confirm_view.add_item(discord.ui.Button(label="Preciso de ajuda com a Gamepass", style=discord.ButtonStyle.danger, custom_id="gamepass_help"))

        await interaction.response.send_message(embeds=[embed, gamepass_tutorial_embed], view=gamepass_confirm_view, ephemeral=False)


# --- Views ---
class RobuxQuantitySelectView(discord.ui.View):
    def __init__(self, db, product_name):
        super().__init__(timeout=180)
        self.db = db
        self.product_name = product_name

        options = []
        # Ordena as quantidades de Robux numericamente para a exibição
        sorted_quantities = sorted(config.PRODUCTS[product_name]['prices'].items(), key=lambda x: int(x[0].split(' ')[0]))
        
        for qty_str, price in sorted_quantities:
            options.append(
                discord.SelectOption(
                    label=f"{qty_str} - R${price:.2f}",
                    value=qty_str # O valor real que será passado, ex: "100 Robux"
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
        selected_quantity_str = select.values[0] # Ex: "100 Robux"
        total_price = config.PRODUCTS[self.product_name]['prices'][selected_quantity_str]
        user_id = interaction.user.id

        # Atualiza o carrinho no DB com a quantidade e preço
        await self.db.execute(
            "UPDATE users SET cart_product_name = $1, cart_quantity = $2, cart_status = $3 WHERE user_id = $4 AND cart_thread_id IS NOT NULL",
            self.product_name, selected_quantity_str, 'quantity_selected', user_id
        )

        embed = discord.Embed(
            title=f"💎 {selected_quantity_str} selecionados!",
            description=f"O valor total é de **R${total_price:.2f}**.\n\nAgora, por favor, informe seu nickname no Roblox para prosseguir.",
            color=config.ROSE_COLOR
        )
        
        # Envia a mensagem e exibe o modal para o nickname
        await interaction.response.send_modal(RobloxNicknameModal(self.db, self.product_name, selected_quantity_str, total_price))


class ProductSelectView(discord.ui.View):
    def __init__(self, db):
        super().__init__(timeout=180)
        self.db = db

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
        selected_product_name = select.values[0]
        product_details = config.PRODUCTS[selected_product_name]
        user_id = interaction.user.id

        current_cart = await self.db.fetch_one(
            "SELECT cart_thread_id, cart_product_name FROM users WHERE user_id = $1 AND cart_thread_id IS NOT NULL",
            user_id
        )

        if current_cart:
            existing_thread_id = current_cart['cart_thread_id']
            existing_thread = interaction.guild.get_thread(existing_thread_id)
            
            if existing_thread:
                embed = discord.Embed(
                    title="🛒 Carrinho em Andamento!",
                    description=f"Você já possui um carrinho em andamento! [Clique aqui para acessá-lo]({existing_thread.jump_url}).",
                    color=config.ROSE_COLOR
                )
                await interaction.response.edit_message(embed=embed, view=None) 
            else:
                await self.db.execute("UPDATE users SET cart_thread_id = NULL, cart_product_name = NULL, cart_quantity = NULL, cart_status = NULL, roblox_nickname = NULL WHERE user_id = $1", user_id)
                await self._create_new_cart(interaction, selected_product_name, product_details)
        else:
            await self._create_new_cart(interaction, selected_product_name, product_details)

    async def _create_new_cart(self, interaction: discord.Interaction, selected_product_name: str, product_details: dict):
        user = interaction.user
        guild = interaction.guild
        
        parent_channel = guild.get_channel(config.CARRINHO_EM_ANDAMENTO_CHANNEL_ID)
        if not parent_channel:
            embed = discord.Embed(
                title="Erro",
                description="Não foi possível encontrar o canal de carrinhos. Por favor, contate um administrador.",
                color=config.ROSE_COLOR
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        thread_name = f"carrinho-{user.name}-{str(uuid.uuid4())[:4]}"
        
        try:
            new_thread = await parent_channel.create_thread(
                name=thread_name,
                type=discord.ChannelType.private_thread,
                auto_archive_duration=1440,
                invitable=True
            )
            
            await new_thread.add_user(user)
            
            admin_role = guild.get_role(config.ADMIN_ROLE_ID)
            if admin_role:
                # Adiciona todos os admins à thread
                for member in admin_role.members:
                    await new_thread.add_user(member)

            # Salva o carrinho no banco de dados
            await self.db.execute(
                """
                INSERT INTO users (user_id, cart_thread_id, cart_product_name, cart_status, roblox_nickname)
                VALUES ($1, $2, $3, $4, NULL) -- Resetar nickname para novo carrinho
                ON CONFLICT (user_id) DO UPDATE
                SET cart_thread_id = $2, cart_product_name = $3, cart_status = $4, roblox_nickname = NULL, last_cart_update = CURRENT_TIMESTAMP
                """,
                user.id, new_thread.id, selected_product_name, 'in_progress'
            )

            embed = discord.Embed(
                title=f"🛒 Carrinho Iniciado para {selected_product_name}!",
                description=f"Seu carrinho foi criado em {new_thread.mention}.\nPor favor, continue a conversa lá.",
                color=config.ROSE_COLOR
            )
            await interaction.response.edit_message(embed=embed, view=None)

            # Mensagem inicial na thread do carrinho
            thread_embed = discord.Embed(
                title=f"Bem-vindo(a) ao seu Carrinho para {selected_product_name}!",
                description=f"Olá {user.mention}! Por favor, aguarde as instruções ou clique em 'Pegar Ticket' para chamar um atendente.",
                color=config.ROSE_COLOR
            )
            ticket_button_view = discord.ui.View()
            ticket_button_view.add_item(discord.ui.Button(label="Pegar Ticket", style=discord.ButtonStyle.primary, custom_id="get_cart_ticket"))
            
            await new_thread.send(embed=thread_embed, view=ticket_button_view)
            
            # Notifica o canal de logs de "carrinho em andamento"
            logs_channel = guild.get_channel(config.CARRINHO_EM_ANDAMENTO_CHANNEL_ID)
            if logs_channel and logs_channel.id != new_thread.id:
                 log_embed = discord.Embed(
                    title="Carrinho em Andamento!",
                    description=f"**Usuário:** {user.mention}\n**Produto:** {selected_product_name}\n**Carrinho:** {new_thread.mention}\n**Status:** Iniciado",
                    color=config.ROSE_COLOR
                 )
                 await logs_channel.send(embed=log_embed)

            if product_details['type'] == 'automatized':
                # Próximo passo para Robux: selecionar a quantidade
                await new_thread.send(
                    embed=discord.Embed(
                        title="Selecione a Quantidade de Robux",
                        description="Escolha a quantidade de Robux que deseja comprar.",
                        color=config.ROSE_COLOR
                    ),
                    view=RobuxQuantitySelectView(self.db, selected_product_name) # Passa o DB para a próxima view
                )

            elif product_details['type'] == 'manual':
                admin_role = guild.get_role(config.ADMIN_ROLE_ID)
                await new_thread.send(f"{admin_role.mention}, um atendimento manual é necessário para esta compra. Aguarde um momento por favor.")

        except Exception as e:
            print(f"Erro ao criar carrinho/thread: {e}")
            error_embed = discord.Embed(
                title="Erro ao Iniciar Carrinho",
                description=f"Ocorreu um erro ao criar seu carrinho. Por favor, tente novamente ou contate um administrador. Erro: `{e}`",
                color=config.ROSE_COLOR
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True) # Use followup se a interação já foi respondida

# Classe principal do Cog
class Purchase(commands.Cog):
    def __init__(self, bot: commands.Bot, db):
        self.bot = bot
        self.db = db

    # Comando de barra para iniciar o processo de compra
    @discord.app_commands.command(name="comprar", description="Inicia o processo de compra de produtos.")
    async def buy_command(self, interaction: discord.Interaction):
        current_cart = await self.db.fetch_one(
            "SELECT cart_thread_id, cart_product_name FROM users WHERE user_id = $1 AND cart_thread_id IS NOT NULL",
            interaction.user.id
        )

        if current_cart:
            existing_thread_id = current_cart['cart_thread_id']
            existing_thread = interaction.guild.get_thread(existing_thread_id)
            
            if existing_thread:
                embed = discord.Embed(
                    title="🛒 Você já tem um carrinho!",
                    description=f"Você já possui um carrinho em andamento! [Clique aqui para acessá-lo]({existing_thread.jump_url}).\n\nDeseja iniciar uma **nova compra**?",
                    color=config.ROSE_COLOR
                )
                
                class NewPurchaseOptionView(discord.ui.View):
                    def __init__(self, db_instance, original_interaction):
                        super().__init__(timeout=60)
                        self.db = db_instance
                        self.user_id = original_interaction.user.id
                        self.original_interaction = original_interaction # Guarda a interação original

                    @discord.ui.button(label="Iniciar Nova Compra", style=discord.ButtonStyle.green, custom_id="start_new_purchase")
                    async def start_new_purchase_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                        # Limpa o carrinho anterior e inicia um novo fluxo
                        await self.db.execute("UPDATE users SET cart_thread_id = NULL, cart_product_name = NULL, cart_quantity = NULL, cart_status = NULL, roblox_nickname = NULL WHERE user_id = $1", self.user_id)
                        
                        embed = discord.Embed(
                            title="🛒 Selecione um Produto para a Nova Compra",
                            description="Use o menu abaixo para escolher o produto que deseja comprar.",
                            color=config.ROSE_COLOR
                        )
                        # Edita a mensagem da interação do botão (não a original do slash command)
                        await interaction.response.edit_message(embed=embed, view=ProductSelectView(self.db))
                
                # A resposta inicial é com a view do botão "Iniciar Nova Compra"
                await interaction.response.send_message(embed=embed, view=NewPurchaseOptionView(self.db, interaction), ephemeral=True)
                return 
            else:
                await self.db.execute("UPDATE users SET cart_thread_id = NULL, cart_product_name = NULL, cart_quantity = NULL, cart_status = NULL, roblox_nickname = NULL WHERE user_id = $1", interaction.user.id)

        embed = discord.Embed(
            title="🛒 Selecione um Produto",
            description="Use o menu abaixo para escolher o produto que deseja comprar.",
            color=config.ROSE_COLOR
        )
        await interaction.response.send_message(embed=embed, view=ProductSelectView(self.db), ephemeral=True)

    # Listener para o botão "Pegar Ticket"
    @commands.Cog.listener("on_interaction")
    async def on_interaction_ticket_button(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.component and interaction.data.get("custom_id") == "get_cart_ticket":
            if interaction.channel.type != discord.ChannelType.private_thread:
                # Ignora se não for em uma thread de carrinho
                return

            user_id = interaction.user.id
            cart_info = await self.db.fetch_one(
                "SELECT cart_product_name FROM users WHERE user_id = $1 AND cart_thread_id = $2",
                user_id, interaction.channel.id
            )

            if not cart_info:
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
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message("Não foi possível encontrar o cargo de administrador para notificar.", ephemeral=True)


    # Listener para o botão "Já criei e desativei preços regionais"
    @commands.Cog.listener("on_interaction")
    async def on_interaction_gamepass_confirm_button(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.component and interaction.data.get("custom_id") == "gamepass_created_confirm":
            if interaction.channel.type != discord.ChannelType.private_thread:
                return

            user_id = interaction.user.id
            cart_info = await self.db.fetch_one(
                "SELECT cart_product_name, cart_quantity FROM users WHERE user_id = $1 AND cart_thread_id = $2",
                user_id, interaction.channel.id
            )

            if not cart_info:
                await interaction.response.send_message("Este não é um carrinho ativo ou você não o iniciou.", ephemeral=True)
                return

            # Altera o status para 'gamepass_confirmed' e pede o link
            await self.db.execute(
                "UPDATE users SET cart_status = $1 WHERE user_id = $2 AND cart_thread_id = $3",
                'gamepass_confirmed', user_id, interaction.channel.id
            )

            embed = discord.Embed(
                title="✅ Gamepass Confirmada!",
                description="Ótimo! Agora, por favor, **envie o link da sua Gamepass** neste chat. Verificaremos o valor para prosseguir com o pagamento.",
                color=config.ROSE_COLOR
            )
            # Remove a view dos botões da gamepass
            await interaction.response.edit_message(embed=embed, view=None)

        elif interaction.type == discord.InteractionType.component and interaction.data.get("custom_id") == "gamepass_help":
            if interaction.channel.type != discord.ChannelType.private_thread:
                return

            user_id = interaction.user.id
            cart_info = await self.db.fetch_one(
                "SELECT cart_product_name FROM users WHERE user_id = $1 AND cart_thread_id = $2",
                user_id, interaction.channel.id
            )

            if not cart_info:
                await interaction.response.send_message("Este não é um carrinho ativo ou você não o iniciou.", ephemeral=True)
                return

            admin_role = interaction.guild.get_role(config.ADMIN_ROLE_ID)
            if admin_role:
                embed = discord.Embed(
                    title="🆘 Ajuda com Gamepass Solicitada!",
                    description=f"{admin_role.mention}, o usuário {interaction.user.mention} precisa de ajuda para configurar a Gamepass. Por favor, auxilie-o.",
                    color=config.ROSE_COLOR
                )
                await interaction.response.send_message(embed=embed)
                # Opcional: Remover os botões para evitar mais cliques desnecessários
                await interaction.message.edit(view=None)
            else:
                await interaction.response.send_message("Não foi possível encontrar o cargo de administrador para notificar.", ephemeral=True)


# Função setup para adicionar o cog ao bot
async def setup(bot: commands.Bot):
    await bot.add_cog(Purchase(bot, bot.db))
