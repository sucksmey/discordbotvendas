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
        self.bot = bot_instance # Armazena a instância do bot para acessar bot.db
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
            await self.bot.db.execute( # Acessa o DB via bot.db
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
                            # Chama o fluxo para Robux novamente
                            await self.bot.get_cog("RobuxCog").robux_command.callback(self.bot.get_cog("RobuxCog"), interaction_button)
                    
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


# Classe principal do Cog para Robux
class RobuxCog(commands.Cog):
    def __init__(self, bot: discord.Client):
        self.bot = bot
        self.db = bot.db

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

    # Método _create_new_cart movido para RobuxCog, pois é específico do fluxo de compra
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


# Função setup para adicionar o cog ao bot
async def setup(bot: commands.Bot):
    await bot.add_cog(RobuxCog(bot))
