# cogs/sales_cog.py
import discord
from discord.ext import commands
from discord.ui import View, Button, button
import asyncio
import re

import config
from utils.logger import log_command, log_dm

# --- Funções Auxiliares ---
def parse_robux_amount(text: str) -> int:
    """Extrai um número de uma string, lidando com 'k' e outros caracteres."""
    text = text.lower().replace('robux', '').strip()
    text = text.replace('.', '') # Remove pontos de milhar
    text = text.replace(',', '.') # Substitui vírgula por ponto para float

    if 'k' in text:
        return int(float(text.replace('k', '')) * 1000)
    
    numeric_part = re.sub(r'[^0-9]', '', text)
    return int(numeric_part) if numeric_part else 0

# --- Views (Componentes de UI) ---
class GamepassCreationView(View):
    def __init__(self, bot, thread, required_value):
        super().__init__(timeout=None)
        self.bot = bot
        self.thread = thread
        self.required_value = required_value

    @button(label="Sim, sei criar", style=discord.ButtonStyle.success, custom_id="knows_gamepass")
    async def knows_callback(self, button_obj: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.defer()
        embed = discord.Embed(
            title="Ótimo!",
            description=f"Por favor, crie a Gamepass com o valor exato de **{self.required_value} Robux** para receber a quantia correta.\n\n"
                        f"Após criar, envie o link ou o ID da sua Gamepass aqui no chat.",
            color=config.EMBED_COLOR
        )
        await self.thread.send(embed=embed)
        self.stop()

    @button(label="Não, preciso de ajuda", style=discord.ButtonStyle.danger, custom_id="needs_help_gamepass")
    async def needs_help_callback(self, button_obj: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.defer()
        embed = discord.Embed(
            title="Sem problemas! Siga o tutorial",
            description=f"Para criar sua Gamepass, assista ao vídeo abaixo. É bem simples!\n\n"
                        f"Você deve criar a Gamepass com o valor exato de **{self.required_value} Robux**.\n\n"
                        f"**IMPORTANTE:** Lembre-se de **DESATIVAR OS PREÇOS REGIONAIS** nas configurações da sua Gamepass para que a entrega funcione!",
            color=config.EMBED_COLOR
        )
        await self.thread.send(embed=embed)
        await self.thread.send(config.TUTORIAL_VIDEO_URL)
        await self.thread.send("Após criar, envie o link ou o ID da sua Gamepass aqui no chat.")
        self.stop()

class InitialPurchaseView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @button(label="Comprar Robux", style=discord.ButtonStyle.success, custom_id="buy_robux")
    async def buy_robux_callback(self, button_obj: discord.ui.Button, interaction: discord.Interaction):
        await self.start_robux_purchase(interaction)

    @button(label="Ver Tabela de Preços", style=discord.ButtonStyle.secondary, custom_id="show_prices")
    async def show_prices_callback(self, button_obj: discord.ui.Button, interaction: discord.Interaction):
        await log_command(self.bot, interaction, is_button=True, button_id="Ver Tabela de Preços")
        embed = discord.Embed(
            title="Tabela de Preços - Robux",
            description="Confira nossos valores competitivos!",
            color=config.EMBED_COLOR
        )
        for amount, price in config.ROBUX_PRICES.items():
            embed.add_field(name=f"{amount} Robux", value=f"R$ {price:.2f}", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


    async def start_robux_purchase(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        channel = interaction.channel
        user = interaction.user
        
        try:
            thread_name = f"🛒-{user.display_name}"
            if len(thread_name) > 100:
                thread_name = thread_name[:97] + "..."

            thread = await channel.create_thread(
                name=thread_name,
                type=discord.ChannelType.private_thread
            )
            await thread.add_user(user)

        except discord.Forbidden:
             await interaction.followup.send("Não tenho permissão para criar tópicos neste canal. Por favor, contate um administrador.", ephemeral=True)
             return
        except Exception as e:
            print(f"Erro ao criar thread: {e}")
            await interaction.followup.send("Ocorreu um erro ao iniciar sua compra. Tente novamente.", ephemeral=True)
            return
            
        await interaction.followup.send(f"Seu carrinho foi criado! Continue sua compra aqui: {thread.mention}", ephemeral=True)
        
        welcome_embed = discord.Embed(
            title=f"👋 Olá, {user.display_name}!",
            description="Bem-vindo(a) ao seu carrinho de compras da **IsraBuy**.\n\nPara começar, por favor, me informe seu **nickname no Roblox**.",
            color=config.EMBED_COLOR
        )
        await thread.send(user.mention, embed=welcome_embed)

        def check(m):
            return m.author == user and m.channel == thread

        try:
            msg_nickname = await self.bot.wait_for('message', check=check, timeout=300.0)
            nickname = msg_nickname.content

            await thread.send(f"Entendido, **{nickname}**! Agora, qual a **quantidade de Robux** que você deseja comprar? (Ex: 1000 ou 1k)")
            msg_amount = await self.bot.wait_for('message', check=check, timeout=300.0)
            amount = parse_robux_amount(msg_amount.content)

            if not (100 <= amount <= 10000):
                await thread.send("Desculpe, a quantidade deve ser entre 100 e 10.000 Robux. Por favor, inicie a compra novamente.")
                await asyncio.sleep(5)
                await thread.delete()
                return

            price = config.calculate_robux_price(amount)
            discount = 0.0
            
            new_customer_role = interaction.guild.get_role(config.NEW_CUSTOMER_ROLE_ID)
            if new_customer_role and new_customer_role in user.roles:
                discount = price * (config.NEW_CUSTOMER_DISCOUNT_PERCENT / 100)
                price -= discount

            payment_embed = discord.Embed(title="✅ Pedido Resumido", color=config.EMBED_COLOR)
            description = f"**Nickname:** `{nickname}`\n**Quantidade:** `{amount}` Robux\n"

            if discount > 0:
                 description += (
                    f"**Subtotal:** `R$ {(price + discount):.2f}`\n"
                    f"**Desconto ({config.NEW_CUSTOMER_DISCOUNT_PERCENT}%):** `-R$ {discount:.2f}`\n"
                    f"**Valor a pagar:** `R$ {price:.2f}`\n\n"
                 )
            else:
                description += f"**Valor a pagar:** `R$ {price:.2f}`\n\n"
            
            description += "Por favor, realize o pagamento via PIX. Após o pagamento, **envie o comprovante** aqui no chat (.png, .jpg ou .pdf)."
            payment_embed.description = description
            payment_embed.add_field(name="Chave PIX (Aleatória)", value="b1a2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6")

            await thread.send(embed=payment_embed)
            msg_receipt = await self.bot.wait_for('message', check=lambda m: m.author == user and m.channel == thread and m.attachments, timeout=600.0)
            
            await thread.send("✅ Comprovante recebido! Nossa equipe já foi notificada.")

            admin_channel = self.bot.get_channel(config.ADMIN_NOTIF_CHANNEL_ID)
            admin_view = View(timeout=None)
            admin_view.add_item(Button(label="Atender Pedido", style=discord.ButtonStyle.primary, custom_id=f"attend_order_{thread.id}_{user.id}_{price}_{amount}"))
            
            admin_embed = discord.Embed(
                title="🔔 Novo Pedido Recebido!",
                description=f"O cliente **{user.mention}** enviou um comprovante para **{amount} Robux** no valor de **R$ {price:.2f}**.",
                color=0x00BFFF
            )
            await admin_channel.send(embed=admin_embed, view=admin_view)

            receipt_embed = discord.Embed(
                description=f"{user.mention}, recebemos seu comprovante! A forma de entrega é através de Gamepass, você sabe criar uma?",
                color=config.EMBED_COLOR
            )
            required_value = config.get_gamepass_value(amount)
            await thread.send(embed=receipt_embed, view=GamepassCreationView(self.bot, thread, required_value))

            msg_gamepass_link = await self.bot.wait_for('message', check=check, timeout=300.0)
            
            await thread.send(
                "**⚠️ ATENÇÃO!**\nOs **preços regionais** precisam estar **DESATIVADOS**.\n\nVocê confirma que desativou?"
            )
            await self.bot.wait_for('message', check=check, timeout=300.0)

            await thread.send("Obrigado pela confirmação! Um atendente já está com seu pedido.")

        except asyncio.TimeoutError:
            await thread.send("Seu pedido expirou. Esta thread será arquivada.")
            await asyncio.sleep(10)
            await thread.edit(archived=True, locked=True)
        except Exception as e:
            print(f"Erro no fluxo de compra: {e}")
            await thread.send("Ocorreu um erro inesperado no seu carrinho. Contate um administrador.")

class SalesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        """Este método é chamado quando o bot está pronto. É o lugar seguro para registrar views persistentes."""
        self.bot.add_view(InitialPurchaseView(bot=self.bot))
        print("View de vendas persistente registrada.")

    @commands.command(name="iniciarvendas")
    @commands.has_any_role(*config.ATTENDANT_ROLE_IDS)
    async def start_sales(self, ctx):
        """Cria o painel inicial de vendas."""
        embed = discord.Embed(
            title="🛒 Central de Pedidos da IsraBuy",
            description="Nossa loja oferece os melhores produtos com os melhores preços do Brasil!\n\n"
                        "**Como Comprar:**\n"
                        "Clique no botão **Comprar Robux** para iniciar o processo de compra!",
            color=config.EMBED_COLOR
        )
        
        purchase_channel = self.bot.get_channel(config.PURCHASE_CHANNEL_ID)
        if purchase_channel:
            await purchase_channel.send(
                embed=embed,
                view=InitialPurchaseView(bot=self.bot)
            )
        await ctx.send("Painel de vendas criado com sucesso!", ephemeral=True)


    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        custom_id = interaction.data.get("custom_id", "")
        if custom_id.startswith("attend_order_"):
            # Valida se o usuário tem o cargo para atender
            user_roles = [role.id for role in interaction.user.roles]
            if not any(role_id in config.ATTENDANT_ROLE_IDS for role_id in user_roles):
                await interaction.response.send_message("Você não tem permissão para atender pedidos.", ephemeral=True)
                return

            await interaction.response.defer()
            
            parts = custom_id.split("_")
            thread_id, user_id, price, amount = int(parts[2]), int(parts[3]), float(parts[4]), int(parts[5])
            
            attendant = interaction.user
            user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
            
            log_channel = self.bot.get_channel(config.ATTENDANCE_LOG_CHANNEL_ID)
            log_embed = discord.Embed(
                description=f"Atendente {attendant.mention} está cuidando do pedido de {user.mention} (Valor: R$ {price:.2f})",
                color=0x32CD32
            )
            await log_channel.send(embed=log_embed)
            
            thread = self.bot.get_channel(thread_id)
            if thread:
                await thread.add_user(attendant)
                await thread.send(f"Olá! Eu sou {attendant.mention} e vou finalizar a sua entrega. Já estou verificando tudo!")

            original_message = await interaction.original_response()
            await original_message.edit(content=f"Pedido assumido por {attendant.mention}!", view=None)

def setup(bot):
    bot.add_cog(SalesCog(bot))
