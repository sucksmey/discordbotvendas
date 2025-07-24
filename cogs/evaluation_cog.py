# cogs/evaluation_cog.py
import discord
from discord.ext import commands
from discord.ui import Modal, InputText
import datetime

import config
import database

# --- Formulário Modal (O que abre ao clicar no botão) ---
class ReviewModal(Modal):
    def __init__(self, bot, purchase_data: dict):
        super().__init__(title="Avalie sua Última Compra")
        self.bot = bot
        self.purchase_data = purchase_data # Armazena os dados da compra
        self.add_item(InputText(label="Nota de 0 a 10", placeholder="Ex: 10", min_length=1, max_length=2))
        self.add_item(InputText(label="Deixe seu comentário", style=discord.InputTextStyle.long, placeholder="Gostei muito do atendimento...", required=False))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        nota = self.children[0].value
        comentario = self.children[1].value or "Nenhum comentário."
        user = interaction.user

        review_channel = self.bot.get_channel(config.REVIEW_CHANNEL_ID)
        if not review_channel:
            return await interaction.followup.send("Canal de avaliações não configurado.", ephemeral=True)

        try:
            # Buscar membros (atendente e entregador) para poder mencioná-los
            attendant = await self.bot.fetch_user(self.purchase_data['attendant_id'])
            deliverer = await self.bot.fetch_user(self.purchase_data['deliverer_id'])
        except discord.NotFound:
            return await interaction.followup.send("Não foi possível encontrar os dados do atendente ou entregador.", ephemeral=True)


        embed = discord.Embed(
            title="🌟 Nova Avaliação de Cliente!",
            description=f"**Comentário:**\n*'{comentario}'*",
            color=config.EMBED_COLOR,
            timestamp=datetime.datetime.now()
        )
        embed.set_author(name=f"Avaliação de {user.display_name}", icon_url=user.display_avatar.url)
        embed.set_thumbnail(url=user.display_avatar.url)
        
        # Adicionando as informações cruciais
        embed.add_field(name="Produto Comprado", value=self.purchase_data['product_name'], inline=True)
        embed.add_field(name="Nota", value=f"**{nota}/10**", inline=True)
        embed.add_field(name="Atendido por", value=attendant.mention, inline=False)
        embed.add_field(name="Entregue por", value=deliverer.mention, inline=True)
        embed.set_footer(text=f"ID da Compra: {self.purchase_data['purchase_id']}")
        
        await review_channel.send(embed=embed)
        await interaction.followup.send("Obrigado pela sua avaliação!", ephemeral=True)


# --- Cog de Avaliação ---
class EvaluationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        custom_id = interaction.data.get("custom_id", "")
        if not custom_id.startswith("review_purchase_"):
            return

        purchase_id = int(custom_id.split("_")[2])
        
        async with database.pool.acquire() as conn:
            purchase_data = await conn.fetchrow("SELECT * FROM purchases WHERE purchase_id = $1", purchase_id)

        if not purchase_data:
            return await interaction.response.send_message("Desculpe, não encontrei os dados desta compra.", ephemeral=True)

        # Abre o formulário (Modal) e passa os dados da compra para ele
        modal = ReviewModal(bot=self.bot, purchase_data=dict(purchase_data))
        await interaction.response.send_modal(modal)


def setup(bot):
    bot.add_cog(EvaluationCog(bot))
