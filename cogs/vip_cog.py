# cogs/vip_cog.py
import discord
from discord.ext import commands
from discord.ui import View, Button
import asyncio
import os

import config
import database
from utils.logger import log_dm

class VipCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    class VipPurchaseView(View):
        def __init__(self, cog_instance):
            super().__init__(timeout=None)
            self.cog = cog_instance

        @discord.ui.button(label="Comprar VIP", style=discord.ButtonStyle.primary, custom_id="buy_vip", emoji="💎")
        async def buy_vip_callback(self, b: discord.ui.Button, i: discord.Interaction):
            await i.response.defer(ephemeral=True)
            u = i.user
            
            active_thread_id = await database.get_active_thread(u.id)
            if active_thread_id:
                thread = self.cog.bot.get_channel(active_thread_id)
                if thread and not getattr(thread, 'archived', True):
                    view = View(); view.add_item(Button(label="Ir para o Carrinho", style=discord.ButtonStyle.link, url=thread.jump_url))
                    await i.followup.send(f"❌ Você já possui um carrinho aberto em {thread.mention}.", view=view, ephemeral=True)
                    return
                else:
                    await database.set_active_thread(u.id, None)

            t = await i.channel.create_thread(name=f"💎 VIP - {u.display_name}", type=discord.ChannelType.private_thread)
            await database.set_active_thread(u.id, t.id)

            users_to_add = {u, await i.guild.fetch_member(config.LEADER_ID)}
            for role_id in config.ATTENDANT_ROLE_IDS:
                role = i.guild.get_role(role_id)
                if role: users_to_add.update(role.members)
            for member_to_add in users_to_add:
                if member_to_add:
                    try: 
                        await t.add_user(member_to_add)
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        print(f"Não foi possível adicionar o usuário {member_to_add.id} ao tópico de VIP: {e}")

            await i.followup.send(f"Seu atendimento para VIP foi iniciado aqui: {t.mention}", ephemeral=True)
            lc = self.cog.bot.get_channel(config.ATTENDANCE_LOG_CHANNEL_ID)
            if lc: await lc.send(f"💎 Novo carrinho de **VIP** para {u.mention}.")
            e = discord.Embed(title="💎 Compra de Acesso VIP", description=f"Olá, {u.mention}! Você está prestes a se tornar VIP.\n\n**Valor:** `R$ {config.VIP_PRICE:.2f}`\n\nPague via PIX e envie o comprovante.", color=0xFFD700)
            e.add_field(name="Chave PIX", value=config.PIX_KEY)
            if os.path.exists("assets/qrcode.png"):
                qrf = discord.File("assets/qrcode.png", "qrcode.png")
                e.set_image(url="attachment://qrcode.png")
                await t.send(u.mention, file=qrf, embed=e)
            else: await t.send(u.mention, embed=e)
            try:
                await self.cog.bot.wait_for('message', check=lambda m: m.author == u and m.channel == t and m.attachments, timeout=172800.0)
                customer_role = i.guild.get_role(config.INITIAL_BUYER_ROLE_ID)
                if customer_role: await u.add_roles(customer_role, reason="Enviou comprovante de VIP")
                
                await t.send("✅ Comprovante recebido!")
                ac = self.cog.bot.get_channel(config.ADMIN_NOTIF_CHANNEL_ID)
                av = View(timeout=None)
                av.add_item(Button(label="Confirmar VIP", style=discord.ButtonStyle.success, custom_id=f"confirm_vip_{t.id}_{u.id}"))
                ae = discord.Embed(title="🔔 Nova Compra de VIP!", description=f"{u.mention} enviou comprovante para VIP.", color=0xFFD700)
                await ac.send(embed=ae, view=av)
            except asyncio.TimeoutError:
                await t.send("Sua compra expirou."); await asyncio.sleep(5)
                await database.set_active_thread(u.id, None)
                await t.edit(archived=True, locked=True)

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(self.VipPurchaseView(self))
        print("View de compra de VIP registrada.")

    @commands.slash_command(name="iniciarvendasvip", description="Cria o painel para compra do acesso VIP.", guild_ids=[config.GUILD_ID])
    @commands.has_any_role(*config.ATTENDANT_ROLE_IDS)
    async def start_vip_sales(self, ctx: discord.ApplicationContext):
        e = discord.Embed(title="💎 Torne-se Membro VIP!", color=0xFFD700,
            description=f"Tenha acesso a benefícios exclusivos!\n\n✨ **Benefício Principal:** Compre **1.000 Robux por R$ {config.VIP_ROBUX_DEAL_PRICE:.2f}**, até {config.VIP_DEAL_USES_PER_MONTH}x por mês!\n✨ **Prioridade no Atendimento**\n✨ **Promoções Exclusivas**\n\n**Valor:** `R$ {config.VIP_PRICE:.2f}` (pagamento único)")
        e.set_footer(text="Clique no botão abaixo para adquirir!")
        c = self.bot.get_channel(config.VIP_PURCHASE_CHANNEL_ID)
        if c:
            await c.send(embed=e, view=self.VipPurchaseView(self))
            await ctx.respond("Painel VIP criado!", ephemeral=True)
        else: await ctx.respond("Canal de compra VIP não encontrado!", ephemeral=True)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        cid = interaction.data.get("custom_id", "")
        if cid.startswith("confirm_vip_"):
            if not any(r.id in config.ATTENDANT_ROLE_IDS for r in interaction.user.roles):
                return await interaction.response.send_message("Sem permissão.", ephemeral=True)
            
            await interaction.response.defer()
            p = cid.split("_")
            tid, uid = int(p[2]), int(p[3])
            adm, mem, t = interaction.user, interaction.guild.get_member(uid), self.bot.get_channel(tid)
            
            await database.set_active_thread(uid, None)
            
            vr = interaction.guild.get_role(config.VIP_ROLE_ID)
            if mem and vr:
                await mem.add_roles(vr, reason=f"VIP ativado por {adm.display_name}")
                await database.set_vip_status(mem.id, True)
                ce = discord.Embed(title="💎 VIP Ativado!", description=f"Parabéns, {mem.mention}! Seu VIP foi ativado por {adm.mention}.", color=0xFFD700)
                if t: await t.send(embed=ce)
                de = discord.Embed(title="🎉 Bem-vindo(a) ao Clube VIP!", description="Sua assinatura VIP foi ativada com sucesso!", color=0xFFD700)
                await log_dm(self.bot, mem, embed=de)
            await (await interaction.original_response()).edit(content=f"VIP confirmado para {mem.mention} por {adm.mention}!", view=None)
            if t: await asyncio.sleep(5); await t.edit(archived=True, locked=True)

def setup(bot):
    bot.add_cog(VipCog(bot))
