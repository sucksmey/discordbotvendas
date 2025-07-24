# utils/logger.py
import discord
import config

async def log_dm(bot: discord.Bot, user: discord.Member, **kwargs):
    """
    Envia uma mensagem direta (DM) para um usuário e loga a ação no canal de logs.
    """
    log_channel = bot.get_channel(config.GENERAL_LOG_CHANNEL_ID)
    try:
        await user.send(**kwargs)
        if log_channel:
            await log_channel.send(f"ℹ️ DM enviada com sucesso para {user.mention}.")
    except discord.Forbidden:
        if log_channel:
            await log_channel.send(f"⚠️ Falha ao enviar DM para {user.mention} (provavelmente a DM está fechada).")
    except Exception as e:
        if log_channel:
            await log_channel.send(f"🔥 Erro desconhecido ao enviar DM para {user.mention}: `{e}`")


async def log_command(bot: discord.Bot, interaction: discord.Interaction, **kwargs):
    """
    Loga o uso de um comando de barra ou botão no canal de logs.
    """
    log_channel = bot.get_channel(config.GENERAL_LOG_CHANNEL_ID)
    if not log_channel:
        return

    is_button = kwargs.get('is_button', False)
    
    if is_button:
        button_id = kwargs.get('button_id', 'N/A')
        user = interaction.user
        log_message = f"ℹ️ O usuário {user.mention} clicou no botão `{button_id}`."
    else: # É um comando de barra (ApplicationContext)
        user = interaction.user
        command_name = interaction.command.name
        log_message = f"ℹ️ O usuário {user.mention} usou o comando `/{command_name}`."
        
    try:
        await log_channel.send(log_message)
    except Exception as e:
        print(f"Falha ao enviar log para o canal: {e}")
