# utils/logger.py
import discord
import config

async def log_dm(bot, user, **kwargs):
    log_channel = bot.get_channel(config.GENERAL_LOG_CHANNEL_ID)
    try:
        await user.send(**kwargs)
        if log_channel:
            await log_channel.send(f"ℹ️ DM enviada com sucesso para {user.mention}.")
    except discord.Forbidden:
        if log_channel:
            await log_channel.send(f"⚠️ Falha ao enviar DM para {user.mention} (DM fechada).")
    except Exception as e:
        if log_channel:
            await log_channel.send(f"🔥 Erro desconhecido ao enviar DM para {user.mention}: `{e}`")

async def log_command(bot, interaction, **kwargs):
    log_channel = bot.get_channel(config.GENERAL_LOG_CHANNEL_ID)
    if not log_channel: return
    user = interaction.user
    if kwargs.get('is_button', False):
        log_message = f"ℹ️ O usuário {user.mention} clicou no botão `{kwargs.get('button_id', 'N/A')}`."
    else:
        log_message = f"ℹ️ O usuário {user.mention} usou o comando `/{interaction.command.name}`."
    await log_channel.send(log_message)
