import discord
import config

def create_embed(title: str, description: str = "", **kwargs) -> discord.Embed:
    """
    Cria um embed com a cor rosa padrão definida em config.py.
    """
    embed = discord.Embed(
        title=title,
        description=description,
        color=config.EMBED_COLOR,
        **kwargs
    )
    return embed

def create_error_embed(description: str, title: str = "Erro!") -> discord.Embed:
    """
    Cria um embed de erro com a cor rosa padrão.
    """
    embed = discord.Embed(
        title=title,
        description=f"❌ {description}",
        color=config.EMBED_COLOR 
    )
    return embed

def create_success_embed(description: str, title: str = "Sucesso!") -> discord.Embed:
    """
    Cria um embed de sucesso com a cor rosa padrão.
    """
    embed = discord.Embed(
        title=title,
        description=f"✅ {description}",
        color=config.EMBED_COLOR 
    )
    return embed
