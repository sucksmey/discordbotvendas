# cogs/purchase.py

import discord
from discord.ext import commands
import config
import uuid # Para gerar IDs únicos de pedido

# View para seleção de produtos
class ProductSelectView(discord.ui.View):
    def __init__(self, db):
        super().__init__(timeout=180)
        self.db = db # Recebe a instância do banco de dados

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

        # Verifica se o usuário já possui um carrinho em andamento
        current_cart = await self.db.fetch_one(
            "SELECT cart_thread_id FROM users WHERE user_id = $1 AND cart_thread_id IS NOT NULL",
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
                # Remove os componentes para que o usuário não selecione mais produtos aqui
                await interaction.response.edit_message(embed=embed, view=None) 
            else:
                # O thread não existe mais, limpa o status do carrinho no DB
                await self.db.execute("UPDATE users SET cart_thread_id = NULL, cart_product_name = NULL, cart_quantity = NULL, cart_status = NULL WHERE user_id = $1", user_id)
                # E prossegue para criar um novo carrinho
                await self._create_new_cart(interaction, selected_product_name, product_details)
        else:
            await self._create_new_cart(interaction, selected_product_name, product_details)

    async def _create_new_cart(self, interaction: discord.Interaction, selected_product_name: str, product_details: dict):
        user = interaction.user
        guild = interaction.guild
        
        # Encontra o canal pai para criar a thread
        parent_channel = guild.get_channel(config.CARRINHO_EM_ANDAMENTO_CHANNEL_ID)
        if not parent_channel:
            embed = discord.Embed(
                title="Erro",
                description="Não foi possível encontrar o canal de carrinhos. Por favor, contate um administrador.",
                color=config.ROSE_COLOR
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        thread_name = f"carrinho-{user.name}-{str(uuid.uuid4())[:4]}" # Adiciona um UUID curto para unicidade
        
        try:
            # Cria a thread privada
            new_thread = await parent_channel.create_thread(
                name=thread_name,
                type=discord.ChannelType.private_thread,
                auto_archive_duration=1440, # 24 horas de inatividade
                invitable=True
            )
            
            # Adiciona o usuário e os admins à thread
            await new_thread.add_user(user)
            
            admin_role = guild.get_role(config.ADMIN_ROLE_ID)
            if admin_role:
                for member in admin_role.members:
                    await new_thread.add_user(member)

            # Salva o carrinho no banco de dados
            await self.db.execute(
                """
                INSERT INTO users (user_id, cart_thread_id, cart_product_name, cart_status)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id) DO UPDATE
                SET cart_thread_id = $2, cart_product_name = $3, cart_status = $4, last_cart_update = CURRENT_TIMESTAMP
                """,
                user.id, new_thread.id, selected_product_name, 'in_progress'
            )

            embed = discord.Embed(
                title=f"🛒 Carrinho Iniciado para {selected_product_name}!",
                description=f"Seu carrinho foi criado em {new_thread.mention}.\nPor favor, continue a conversa lá.",
                color=config.ROSE_COLOR
            )
            # Edita a mensagem original do comando /comprar para mostrar o link do carrinho
            await interaction.response.edit_message(embed=embed, view=None)

            # Mensagem inicial na thread do carrinho
            thread_embed = discord.Embed(
                title=f"Bem-vindo(a) ao seu Carrinho para {selected_product_name}!",
                description=f"Olá {user.mention}! Por favor, aguarde as instruções ou clique em 'Pegar Ticket' para chamar um atendente.",
                color=config.ROSE_COLOR
            )
            # Botão "Pegar Ticket" na thread
            ticket_button_view = discord.ui.View()
            ticket_button_view.add_item(discord.ui.Button(label="Pegar Ticket", style=discord.ButtonStyle.primary, custom_id="get_cart_ticket"))
            
            await new_thread.send(embed=thread_embed, view=ticket_button_view)
            
            # Notifica o canal de logs de "carrinho em andamento"
            logs_channel = guild.get_channel(config.CARRINHO_EM_ANDAMENTO_CHANNEL_ID)
            if logs_channel and logs_channel.id != new_thread.id: # Evita enviar para a própria thread
                 log_embed = discord.Embed(
                    title="Carrinho em Andamento!",
                    description=f"**Usuário:** {user.mention}\n**Produto:** {selected_product_name}\n**Carrinho:** {new_thread.mention}\n**Status:** Iniciado",
                    color=config.ROSE_COLOR
                 )
                 await logs_channel.send(embed=log_embed)

            if product_details['type'] == 'automatized':
                # Próximo passo para Robux: selecionar a quantidade
                quantity_options = []
                for qty, price in product_details['prices'].items():
                    quantity_options.append(discord.SelectOption(label=f"{qty} - R${price:.2f}", value=qty))
                
                quantity_select_view = discord.ui.View(timeout=180)
                quantity_select_view.add_item(
                    discord.ui.Select(
                        placeholder="Selecione a quantidade de Robux...",
                        options=quantity_options,
                        custom_id="robux_quantity_select"
                    )
                )
                
                await new_thread.send(
                    embed=discord.Embed(
                        title="Selecione a Quantidade de Robux",
                        description="Escolha a quantidade de Robux que deseja comprar.",
                        color=config.ROSE_COLOR
                    ),
                    view=quantity_select_view
                )

            elif product_details['type'] == 'manual':
                # Para produtos manuais, avisa o admin
                await new_thread.send(f"{admin_role.mention}, um atendimento manual é necessário para esta compra.")

        except Exception as e:
            print(f"Erro ao criar carrinho/thread: {e}")
            error_embed = discord.Embed(
                title="Erro ao Iniciar Carrinho",
                description=f"Ocorreu um erro ao criar seu carrinho. Por favor, tente novamente ou contate um administrador. Erro: `{e}`",
                color=config.ROSE_COLOR
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)


# Classe principal do Cog
class Purchase(commands.Cog):
    def __init__(self, bot: commands.Bot, db: Database):
        self.bot = bot
        self.db = db # Recebe a instância do banco de dados

    # Comando de barra para iniciar o processo de compra
    @discord.app_commands.command(name="comprar", description="Inicia o processo de compra de produtos.")
    async def buy_command(self, interaction: discord.Interaction):
        # Verifica se o usuário já possui um carrinho em andamento
        current_cart = await self.db.fetch_one(
            "SELECT cart_thread_id FROM users WHERE user_id = $1 AND cart_thread_id IS NOT NULL",
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
                
                # View com botão para iniciar nova compra
                class NewPurchaseOptionView(discord.ui.View):
                    def __init__(self, db_instance):
                        super().__init__(timeout=60)
                        self.db = db_instance
                        self.user_id = interaction.user.id

                    @discord.ui.button(label="Iniciar Nova Compra", style=discord.ButtonStyle.green, custom_id="start_new_purchase")
                    async def start_new_purchase_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                        # Limpa o carrinho anterior e inicia um novo fluxo
                        await self.db.execute("UPDATE users SET cart_thread_id = NULL, cart_product_name = NULL, cart_quantity = NULL, cart_status = NULL WHERE user_id = $1", self.user_id)
                        
                        embed = discord.Embed(
                            title="🛒 Selecione um Produto para a Nova Compra",
                            description="Use o menu abaixo para escolher o produto que deseja comprar.",
                            color=config.ROSE_COLOR
                        )
                        await interaction.response.edit_message(embed=embed, view=ProductSelectView(self.db))
                
                await interaction.response.send_message(embed=embed, view=NewPurchaseOptionView(self.db), ephemeral=True)
                return # Interrompe a execução para que não crie outro carrinho
            else:
                # O thread não existe mais, limpa o status do carrinho no DB
                await self.db.execute("UPDATE users SET cart_thread_id = NULL, cart_product_name = NULL, cart_quantity = NULL, cart_status = NULL WHERE user_id = $1", interaction.user.id)

        # Se não tem carrinho ou o antigo foi limpo, envia o menu de seleção de produto
        embed = discord.Embed(
            title="🛒 Selecione um Produto",
            description="Use o menu abaixo para escolher o produto que deseja comprar.",
            color=config.ROSE_COLOR
        )
        await interaction.response.send_message(embed=embed, view=ProductSelectView(self.db), ephemeral=True)


# Função setup para adicionar o cog ao bot
async def setup(bot: commands.Bot):
    # O bot.load_extension em main.py já passa 'db'
    await bot.add_cog(Purchase(bot, bot.db))
