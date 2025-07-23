import discord
from discord.ext import commands
import logging
import config
from utils.database import Database
from utils.embeds import create_embed, create_error_embed

logger = logging.getLogger('discord_bot')

class ClientAreaView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None) # A view pode ser persistente
        self.bot = bot
        self.db: Database = bot.database

    @discord.ui.button(label="Ver Minhas Compras", style=discord.ButtonStyle.blurple, custom_id="view_my_purchases")
    async def view_my_purchases_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Botão para exibir o histórico de compras do usuário."""
        await interaction.response.defer(ephemeral=True) # Acknowledge interaction, mas a resposta será enviada em follow-up

        user_id = interaction.user.id

        # Logar a ação privada
        private_log_channel = self.bot.get_channel(config.PRIVATE_ACTIONS_LOG_CHANNEL_ID)
        if private_log_channel:
            log_embed = create_embed(
                "👁️ Ação Privada Registrada",
                f"**Usuário:** {interaction.user.mention} (ID: `{user_id}`)\n"
                f"**Ação:** Consultou o histórico de compras."
            )
            await private_log_channel.send(embed=log_embed)
            logger.info(f"Usuário {interaction.user.name} ({user_id}) consultou o histórico de compras.")

        # Buscar compras no banco de dados
        # O username é puxado do objeto user do discord, pois o histórico é por user_id
        purchases = await self.db.fetch(
            "SELECT product_name, quantity_or_value, total_price, created_at FROM orders WHERE user_id = $1 ORDER BY created_at DESC LIMIT 10",
            user_id
        )

        embed = create_embed(
            f"🛒 Seu Histórico de Compras - {interaction.user.display_name}",
            "Aqui estão suas últimas compras:"
        )

        if not purchases:
            embed.description = "Você ainda não tem compras registradas."
        else:
            for purchase in purchases:
                product_name = purchase['product_name']
                quantity_or_value = purchase['quantity_or_value']
                total_price = purchase['total_price']
                created_at = purchase['created_at'].strftime("%d/%m/%Y às %H:%M") # Formata a data e hora

                embed.add_field(
                    name=f"**{product_name}**",
                    value=f"**Item:** {quantity_or_value}\n"
                          f"**Valor:** R${total_price:.2f}\n"
                          f"**Data:** {created_at}\n"
                          f"---",
                    inline=False
                )
        
        # O limite de 25 campos é para embeds. Usamos um campo por compra para o histórico.
        # Se houver muitas compras, podemos paginar ou resumir.
        if len(purchases) >= 10: # Se houver mais de 10, podemos adicionar uma nota
             embed.set_footer(text="Mostrando as 10 últimas compras. Para ver mais, contacte um admin.")

        await interaction.followup.send(embed=embed, ephemeral=True) # Envia a resposta privada

class ClientArea(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db: Database = bot.database

    # Opcional: Comando para enviar a mensagem da área do cliente (para admins)
    @commands.slash_command(name="setup_area_cliente", description="Configura a mensagem da área do cliente com o botão.", guild_ids=[config.GUILD_ID])
    @commands.has_role(config.ADMIN_ROLE_ID)
    async def setup_client_area(self, ctx: discord.ApplicationContext):
        embed = create_embed(
            "👤 Área do Cliente",
            "Clique no botão abaixo para consultar seu histórico de compras."
        )
        # Instancia a view e a envia com a mensagem
        view = ClientAreaView(self.bot)
        message = await ctx.send(embed=embed, view=view)
        view.message = message # Armazena a mensagem para a view persistente
        await ctx.respond(embed=create_success_embed("Área do cliente configurada!", "A mensagem com o botão foi enviada."), ephemeral=True)


async def setup(bot):
    await bot.add_cog(ClientArea(bot))
    # Para garantir que a view persista entre reinícios do bot
    # É importante adicionar a view aqui. Se o bot reiniciar e a mensagem já existe,
    # a view será recarregada e os botões funcionarão.
    bot.add_view(ClientAreaView(bot))
