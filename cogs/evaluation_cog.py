# cogs/evaluation_cog.py
import discord
from discord.ext import commands
from discord.ui import View, Modal, InputText, button

import config

# --- Formulário Modal (O que abre ao clicar no botão) ---
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
        
        # Adiciona o nome do atendente se possível (exemplo, pode ser adaptado)
        # embed.add_field(name="Atendido por", value="Nome do Atendente", inline=True)
        
        await review_channel.send(embed=embed)
        await interaction.response.send_message("Obrigado pela sua avaliação!", ephemeral=True)


# --- View com o Botão de Avaliação ---
class ReviewButtonView(View):
    def __init__(self, bot):
        super().__init__(timeout=None) # Botão persistente
        self.bot = bot

    @button(label="Avaliar Atendimento", style=discord.ButtonStyle.success, custom_id="review_button", emoji="⭐")
    async def review_button_callback(self, button_obj: discord.ui.Button, interaction: discord.Interaction):
        # Abre o formulário (Modal) quando o botão é clicado
        modal = ReviewModal(bot=self.bot)
        await interaction.response.send_modal(modal)


# --- Cog de Avaliação ---
class EvaluationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Registra a view com o botão para que ele funcione após reinícios do bot
        self.bot.add_view(ReviewButtonView(bot=self.bot))
        print("View de avaliação registrada.")

    @commands.slash_command(
        name="avaliacao",
        description="Envia um painel para o cliente avaliar o atendimento.",
        guild_ids=[config.GUILD_ID]
    )
    @commands.has_any_role(*config.ATTENDANT_ROLE_IDS) # Apenas admins podem usar este comando
    async def post_review_panel(self, ctx: discord.ApplicationContext):
        """
        Este comando agora posta a mensagem com o botão de avaliação no canal onde for usado.
        """
        embed = discord.Embed(
            title="⭐ Avalie sua Experiência!",
            description="Ficamos felizes em te atender! Por favor, clique no botão abaixo para deixar sua avaliação sobre a sua última compra. Seu feedback é muito importante para nós!",
            color=config.EMBED_COLOR
        )
        embed.set_footer(text="Agradecemos a sua preferência!")
        
        # Envia a mensagem com o botão no canal atual
        await ctx.send(embed=embed, view=ReviewButtonView(bot=self.bot))
        
        # Confirma para o admin que a ação foi concluída
        await ctx.respond("Painel de avaliação enviado com sucesso!", ephemeral=True)

def setup(bot):
    bot.add_cog(EvaluationCog(bot))
