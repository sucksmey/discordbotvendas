# cogs/evaluation_cog.py
import discord
from discord.ext import commands
from discord.ui import Modal, InputText
import config

class ReviewModal(Modal):
    def __init__(self, bot) -> None:
        super().__init__(title="Avalie nosso Atendimento")
        self.bot = bot
        self.add_item(InputText(label="Nota de 0 a 10", placeholder="Ex: 10", min_length=1, max_length=2))
        self.add_item(InputText(label="Deixe seu comentário", style=discord.InputTextStyle.long, placeholder="Gostei muito do atendimento...", required=False))

    async def callback(self, interaction: discord.Interaction):
        nota = self.children[0].value
        comentario = self.children[1].value or "Nenhum comentário."
        user = interaction.user

        review_channel = self.bot.get_channel(config.REVIEW_CHANNEL_ID)
        if not review_channel:
            return await interaction.response.send_message("Canal de avaliações não configurado.", ephemeral=True)

        embed = discord.Embed(
            title="🌟 Nova Avaliação de Cliente!",
            description=f"**Comentário:**\n*'{comentario}'*",
            color=config.EMBED_COLOR
        )
        embed.set_author(name=f"Avaliação de {user.display_name}", icon_url=user.display_avatar.url)
        embed.add_field(name="Nota", value=f"**{nota}/10**", inline=True)
        embed.set_thumbnail(url=user.display_avatar.url)
        
        await review_channel.send(embed=embed)
        await interaction.response.send_message("Obrigado pela sua avaliação!", ephemeral=True)


class EvaluationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(
        name="avaliacao",
        description="Deixe uma avaliação sobre seu último atendimento.",
        guild_ids=[config.GUILD_ID]
    )
    async def avaliacao(self, ctx: discord.ApplicationContext):
        modal = ReviewModal(bot=self.bot)
        await ctx.send_modal(modal)

def setup(bot):
    bot.add_cog(EvaluationCog(bot))
