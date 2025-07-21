# cogs/common_listeners.py

import discord
from discord.ext import commands
import config
import asyncio # Para simular um delay
from datetime import datetime

# Listener para o botão "Voltar para Categorias" (para menus de 2o nível)
@commands.Cog.listener("on_interaction")
async def on_back_to_parent_category_button(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component and interaction.data.get("custom_id").startswith("back_to_parent_category_"):
        print(f"[DEBUG] Botão 'Voltar para Categorias' clicado por {interaction.user.name}.")
        parent_category_filter = interaction.data["custom_id"].replace("back_to_parent_category_", "")
        
        bot_instance = interaction.client
        
        # Importações locais para evitar circular dependency issues entre cogs
        from cogs.jogos import GameSubcategorySelectView
        from cogs.giftcard import GiftcardBrandSelectView

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
                await interaction.response.send_message("Este não é um carrinho ativo ou você não o iniciou.", ephemeral=True)
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
            await interaction.response.edit_message(embed=embed, view=None)

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
                await interaction.response.send_message(embed=embed, ephemeral=True)

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
                await interaction.response.send_message("Este não é um carrinho ativo ou você não o iniciou.", ephemeral=True)
                return

            admin_role = interaction.guild.get_role(config.ADMIN_ROLE_ID)
            if admin_role:
                embed = discord.Embed(
                    title="🆘 Ajuda com Gamepass Solicitada!",
                    description=f"{admin_role.mention}, o usuário {interaction.user.name} precisa de ajuda para configurar a Gamepass. Por favor, auxilie-o.",
                    color=config.ROSE_COLOR
                )
                await interaction.response.send_message(embed=embed)
                await interaction.message.edit(view=None)
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
                await interaction.response.send_message(embed=embed, ephemeral=True)


# Função setup para adicionar o cog ao bot
async def setup(bot: commands.Bot):
    # Registrar os listeners diretamente no bot
    bot.add_listener(on_back_to_parent_category_button)
    bot.add_listener(on_interaction_ticket_button)
    bot.add_listener(on_interaction_gamepass_confirm_button)
    # Este cog não terá uma classe principal, apenas listeners
