# cogs/user_cog.py
import discord
from discord.ext import commands
from discord.ui import View, Button

import config
import database
from utils.logger import log_command # (Precisaremos criar este utilitário)

class HistoryView(View):
    def __init__(self, bot, user):
        super().__init__(timeout=None)
        self.bot = bot
        self.user = user

    @discord.ui.button(label="Ver Minhas Compras", style=discord.ButtonStyle.primary, custom_id="show_history")
    async def button_callback(self, button, interaction):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("Você só pode ver seu próprio histórico!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        history = await database.get_purchase_history(self.user.id)
        
        if not history:
            await interaction.followup.send("Você ainda não tem compras registradas.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"Seu Histórico de Compras",
            color=config.EMBED_COLOR
        )
        embed.set_author(name=self.user.display_name, icon_url=self.user.display_avatar.url)
        
        description = ""
        for record in history:
            # Formata a data para o fuso horário de São Paulo
            purchase_date = record['purchase_date'].astimezone(datetime.timezone(datetime.timedelta(hours=-3)))
            description += (
                f"**Produto:** {record['product_name']}\n"
                f"**Valor:** R$ {record['price_brl']}\n"
                f"**Data:** {purchase_date.strftime('%d/%m/%Y às %H:%M')}\n---\n"
            )
        
        embed.description = description
        await interaction.followup.send(embed=embed, ephemeral=True)


class UserCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="historico", description="Mostra seu histórico de compras na loja.")
    async def historico(self, ctx: discord.ApplicationContext):
        await log_command(self.bot, ctx) # Loga o uso do comando
        embed = discord.Embed(title="Área do Cliente", description="Clique no botão abaixo para consultar seu histórico de compras.", color=config.EMBED_COLOR)
        await ctx.respond(embed=embed, view=HistoryView(self.bot, ctx.author), ephemeral=True)

    @commands.slash_command(name="fidelidade", description="Verifica seu progresso no programa de fidelidade.")
    async def fidelidade(self, ctx: discord.ApplicationContext):
        await log_command(self.bot, ctx) # Loga o uso do comando
        user_data = await database.get_user_data(ctx.author.id)
        purchase_count = user_data['purchase_count'] if user_data else 0
        
        admin_cog = self.bot.get_cog('AdminCog')
        embed = admin_cog.create_loyalty_embed(ctx.author, purchase_count)

        await ctx.respond(embed=embed, ephemeral=True)

def setup(bot):
    bot.add_cog(UserCog(bot))
