# cogs/vip_cog.py
import discord
from discord.ext import commands
from discord.ui import View, Button
import asyncio
import os

import config
from utils.logger import log_dm

class VipPurchaseView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Comprar VIP", style=discord.ButtonStyle.primary, custom_id="buy_vip", emoji="💎")
    async def buy_vip_callback(self, button_obj: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user = interaction.user
        
        thread_name = f"💎 VIP - {user.display_name}"
        thread = await interaction.channel.create_thread(name=thread_name, type=discord.ChannelType.private_thread)
        await thread.add_user(user)

        await interaction.followup.send(f"Seu atendimento para comprar VIP foi iniciado aqui: {thread.mention}", ephemeral=True)

        embed = discord.Embed(
            title="💎 Compra de Acesso VIP",
            description=f"Olá, {user.mention}! Você está prestes a se tornar um membro VIP da **IsraBuy**.\n\n"
                        f"**Valor:** `R$ {config.VIP_PRICE:.2f}`\n\n"
                        "Por favor, realize o pagamento via PIX para a chave abaixo e envie o comprovante aqui no chat.",
            color=0xFFD700 # Dourado
        )
        embed.add_field(name="Chave PIX (Aleatória)", value="b1a2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6") # <<< TROCAR PELA SUA CHAVE REAL

        qr_code_file_path = "assets/qrcode.png"
        if os.path.exists(qr_code_file_path):
            qr_code_file = discord.File(qr_code_file_path, filename="qrcode.png")
            embed.set_image(url="attachment://qrcode.png")
            await thread.send(user.mention, file=qr_code_file, embed=embed)
        else:
            await thread.send(user.mention, embed=embed)

        try:
            msg_receipt = await self.bot.wait_for('message', check=lambda m: m.author == user and m.channel == thread and m.attachments, timeout=600.0)
            
            await thread.send("✅ Comprovante recebido! Nossa equipe já foi notificada para confirmar sua assinatura VIP.")

            admin_channel = self.bot.get_channel(config.ADMIN_NOTIF_CHANNEL_ID)
            admin_view = View(timeout=None)
            admin_view.add_item(Button(label="Confirmar VIP", style=discord.ButtonStyle.success, custom_id=f"confirm_vip_{thread.id}_{user.id}"))
            
            admin_embed = discord.Embed(
                title="🔔 Nova Compra de VIP!",
                description=f"O cliente {user.mention} enviou um comprovante para a compra do VIP.",
                color=0xFFD700
            )
            await admin_channel.send(embed=admin_embed, view=admin_view)

        except asyncio.TimeoutError:
            await thread.send("Sua compra de VIP expirou por inatividade.")
            await asyncio.sleep(10)
            await thread.edit(archived=True, locked=True)

class VipCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(VipPurchaseView(bot=self.bot))
        print("View de compra de VIP registrada.")

    @commands.slash_command(
        name="iniciarvendasvip",
        description="Cria o painel para compra do acesso VIP.",
        guild_ids=[config.GUILD_ID]
    )
    @commands.has_any_role(*config.ATTENDANT_ROLE_IDS)
    async def start_vip_sales(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(
            title="💎 Torne-se um Membro VIP!",
            description=(
                "Tenha acesso a benefícios exclusivos em nossa loja!\n\n"
                f"✨ **Benefício Principal:** Compre pacotes de **1.000 Robux por apenas R$ {config.VIP_ROBUX_DEAL_PRICE:.2f}**, até {config.VIP_DEAL_USES_PER_MONTH}x por mês!\n"
                "✨ **Prioridade:** Atendimento prioritário em suas compras.\n"
                "✨ **Exclusividade:** Acesso a promoções e sorteios exclusivos para membros VIP.\n\n"
                f"**Valor da Assinatura:** `R$ {config.VIP_PRICE:.2f}` (pagamento único)"
            ),
            color=0xFFD700
        )
        embed.set_footer(text="Clique no botão abaixo para adquirir seu acesso VIP!")

        channel = self.bot.get_channel(config.VIP_PURCHASE_CHANNEL_ID)
        if channel:
            await channel.send(embed=embed, view=VipPurchaseView(bot=self.bot))
            await ctx.respond("Painel de vendas VIP criado com sucesso!", ephemeral=True)
        else:
            await ctx.respond("Canal de compra de VIP não encontrado!", ephemeral=True)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        custom_id = interaction.data.get("custom_id", "")
        if custom_id.startswith("confirm_vip_"):
            user_roles = [role.id for role in interaction.user.roles]
            if not any(role_id in config.ATTENDANT_ROLE_IDS for role_id in user_roles):
                return await interaction.response.send_message("Você não tem permissão para confirmar VIP.", ephemeral=True)

            await interaction.response.defer()
            
            parts = custom_id.split("_")
            thread_id, user_id = int(parts[2]), int(parts[3])
            
            admin = interaction.user
            member = interaction.guild.get_member(user_id)
            thread = self.bot.get_channel(thread_id)
            
            vip_role = interaction.guild.get_role(config.VIP_ROLE_ID)

            if member and vip_role:
                await member.add_roles(vip_role, reason=f"VIP ativado por {admin.display_name}")
                await database.set_vip_status(member.id, True)

                confirm_embed = discord.Embed(
                    title="💎 VIP Ativado!",
                    description=f"Parabéns, {member.mention}! Seu acesso VIP foi ativado por {admin.mention}. Aproveite seus novos benefícios!",
                    color=0xFFD700
                )
                if thread:
                    await thread.send(embed=confirm_embed)
                
                dm_embed = discord.Embed(
                    title="🎉 Bem-vindo(a) ao Clube VIP!",
                    description="Sua assinatura VIP foi ativada com sucesso. Você já pode usufruir de todos os benefícios exclusivos da IsraBuy!",
                    color=0xFFD700
                )
                await log_dm(self.bot, member, embed=dm_embed)
            
            original_message = await interaction.original_response()
            await original_message.edit(content=f"VIP confirmado para {member.mention} por {admin.mention}!", view=None)
            
            if thread:
                await asyncio.sleep(5)
                await thread.edit(archived=True, locked=True)

def setup(bot):
    bot.add_cog(VipCog(bot))
