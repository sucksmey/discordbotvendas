# cogs/test_commands.py

import discord
from discord.ext import commands
import config

class TestCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @discord.app_commands.command(name="test", description="Um comando de teste para verificar o registro de cogs.")
    async def test_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="✅ Teste de Comando!",
            description=f"O comando /test funcionou! Isso significa que o cog '{self.qualified_name}' foi carregado e o comando registrado com sucesso.",
            color=config.ROSE_COLOR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(TestCommands(bot))
