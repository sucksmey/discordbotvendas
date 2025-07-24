# cogs/admin_cog.py
import discord
from discord.ext import commands
from discord import option
import datetime

import config

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(
        name="entregue",
        description="Finaliza um pedido e notifica o cliente e os logs.",
        guild_ids=[config.GUILD_ID]
    )
    @option("cliente", description="O cliente que recebeu o pedido.")
    @option("entregador", description="O membro da equipe que fez a entrega.")
    @option("atendente", description="O membro da equipe que atendeu o pedido.")
    @option("valor", description="O valor da compra.")
    @commands.has_any_role(*config.ATTENDANT_ROLE_IDS)
    async def entregue(self, ctx: discord.ApplicationContext, cliente: discord.Member, entregador: discord.Member, atendente: discord.Member, valor: float):
        
        # 1. Enviar DM para o cliente
        try:
            dm_embed = discord.Embed(
                title="🎉 Pedido Entregue!",
                description=f"Olá, {cliente.display_name}! Seus Robux foram entregues com sucesso.\n\n"
                            f"Você pode verificar o saldo pendente clicando no link abaixo:\n"
                            f"[Verificar Robux Pendentes]({config.PENDING_ROBUX_URL})",
                color=config.EMBED_COLOR
            )
            dm_embed.set_footer(text="Agradecemos a sua preferência!")
            await cliente.send(embed=dm_embed)
        except discord.Forbidden:
            await ctx.respond("Não foi possível enviar a DM para o cliente (provavelmente estão fechadas).", ephemeral=True)

        # 2. Enviar log de entrega
        log_channel = self.bot.get_channel(config.DELIVERY_LOG_CHANNEL_ID)
        if log_channel:
            log_embed = discord.Embed(
                title="✅ Compra Aprovada e Entregue!",
                color=0x28a745, # Verde sucesso
                timestamp=datetime.datetime.now()
            )
            log_embed.add_field(name="Cliente", value=cliente.mention, inline=True)
            log_embed.add_field(name="Valor Pago", value=f"R$ {valor:.2f}", inline=True)
            log_embed.add_field(name="Atendido por", value=atendente.mention, inline=False)
            log_embed.add_field(name="Entregue por", value=entregador.mention, inline=True)
            
            # Lógica de VIP e Fidelidade (Exemplo simples)
            vip_role = ctx.guild.get_role(config.VIP_ROLE_ID)
            if vip_role in cliente.roles:
                log_embed.add_field(name="Status VIP", value="⭐ Cliente VIP!", inline=False)
            else:
                log_embed.add_field(name="Status VIP", value="Não é VIP. Recomende a compra do VIP para benefícios exclusivos!", inline=False)
            
            await log_channel.send(embed=log_embed)

        await ctx.respond(f"O pedido de {cliente.mention} foi marcado como entregue com sucesso!", ephemeral=True)


def setup(bot):
    bot.add_cog(AdminCog(bot))
