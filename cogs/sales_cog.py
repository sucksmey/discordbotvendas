# cogs/sales_cog.py
import discord
from discord.ext import commands
from discord.ui import View, Button, button
import asyncio
import re

import config
from utils.logger import log_command # Supondo que o logger esteja em utils/logger.py

# --- Funções Auxiliares ---
def parse_robux_amount(text: str) -> int:
    """Extrai um número de uma string, lidando com 'k' e outros caracteres."""
    text = text.lower().replace('robux', '').strip()
    # Remove pontos de milhar
    text = text.replace('.', '')
    # Substitui vírgula por ponto para float (caso o usuário digite 1,5k)
    text = text.replace(',', '.')

    if 'k' in text:
        return int(float(text.replace('k', '')) * 1000)
    
    # Extrai apenas os números restantes
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

class SalesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(InitialPurchaseView(bot=self.bot))

    @commands.command(name="iniciarvendas")
    @commands.has_any_role(*config.ATTENDANT_ROLE_IDS)
    async def start_sales(self, ctx):
        """Cria o painel inicial de vendas."""
        embed = discord.Embed(
            title="🛒 Central de Pedidos da IsraBuy",
            description="Nossa loja oferece os melhores produtos com os melhores preços do Brasil!\n\n"
                        "**Produtos:**\n"
                        "Robux - Robux direto na sua conta, sempre cobrindo todas as taxas do Roblox!\n\n"
                        "**Como Comprar:**\n"
                        "Clique no botão **Comprar Robux** para iniciar o processo de compra!",
            color=config.EMBED_COLOR
        )
        # Se você tiver uma imagem de banner, descomente a linha abaixo
        # embed.set_image(url="attachment://banner_israbuy.png")
        
        purchase_channel = self.bot.get_channel(config.PURCHASE_CHANNEL_ID)
        if purchase_channel:
            await purchase_channel.send(
                embed=embed,
                view=InitialPurchaseView(bot=self.bot)
            )
        await ctx.send("Painel de vendas criado com sucesso!", ephemeral=True)


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
        await interaction.response.defer(ephemeral=True) # Responde ao clique inicial para evitar timeout
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
            # 1. Pegar Nickname
            msg_nickname = await self.bot.wait_for('message', check=check, timeout=300.0)
            nickname = msg_nickname.content

            # 2. Pegar Quantidade
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
            
            # 3. VERIFICAR DESCONTO PARA NOVOS CLIENTES
            new_customer_role = interaction.guild.get_role(config.NEW_CUSTOMER_ROLE_ID)
            if new_customer_role in user.roles:
                discount = price * (config.NEW_CUSTOMER_DISCOUNT_PERCENT / 100)
                price -= discount

            # 4. Confirmação e Pagamento
            payment_embed = discord.Embed(
                title="✅ Pedido Resumido",
                color=config.EMBED_COLOR
            )
            
            description = (
                f"**Nickname:** `{nickname}`\n"
                f"**Quantidade:** `{amount}` Robux\n"
            )

            if discount > 0:
                 description += (
                    f"**Subtotal:** `R$ {(price + discount):.2f}`\n"
                    f"**Desconto de primeira compra ({config.NEW_CUSTOMER_DISCOUNT_PERCENT}%):** `-R$ {discount:.2f}`\n"
                    f"**Valor a pagar:** `R$ {price:.2f}`\n\n"
                 )
            else:
                description += f"**Valor a pagar:** `R$ {price:.2f}`\n\n"
            
            description += "Por favor, realize o pagamento via PIX. Após o pagamento, **envie o comprovante** aqui no chat (.png, .jpg ou .pdf)."
            payment_embed.description = description
            
            # Enviar o PIX (qrcode ou chave)
            # Descomente a linha abaixo e coloque a imagem do qrcode na pasta /assets
            # qr_code_file = discord.File("assets/qrcode.png", filename="qrcode.png")
            # payment_embed.set_image(url="attachment://qrcode.png")
            payment_embed.add_field(name="Chave PIX (Aleatória)", value="b1a2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6") # <<< TROCAR PELA SUA CHAVE REAL

            await thread.send(embed=payment_embed) # Adicione file=qr_code_file se for usar

            # 5. Esperar Comprovante
            msg_receipt = await self.bot.wait_for('message', check=lambda m: m.author == user and m.channel == thread and m.attachments, timeout=600.0)
            
            await thread.send("✅ Comprovante recebido! Nossa equipe já foi notificada e irá verificar seu pagamento.")

            # 6. Notificar Admins
            admin_channel = self.bot.get_channel(config.ADMIN_NOTIF_CHANNEL_ID)
            admin_view = View(timeout=None)
            admin_view.add_item(Button(label="Atender Pedido", style=discord.ButtonStyle.primary, custom_id=f"attend_order_{thread.id}_{user.id}_{price}_{amount}"))
            
            admin_embed = discord.Embed(
                title="🔔 Novo Pedido Recebido!",
                description=f"O cliente **{user.mention}** enviou um comprovante para uma compra de **{amount} Robux** no valor de **R$ {price:.2f}**.\n\n"
                            f"Clique no botão abaixo para assumir o atendimento.",
                color=0x00BFFF # Azul
            )
            await admin_channel.send(embed=admin_embed, view=admin_view)

            # 7. Instruções da Gamepass
            receipt_embed = discord.Embed(
                description=f"@{user.display_name}, recebemos seu comprovante! A forma de entrega é através de Gamepass, você sabe criar uma?",
                color=config.EMBED_COLOR
            )
            required_value = config.get_gamepass_value(amount)
            await thread.send(embed=receipt_embed, view=GamepassCreationView(self.bot, thread, required_value))

            # 8. Esperar link da Gamepass e confirmar preços regionais
            msg_gamepass_link = await self.bot.wait_for('message', check=check, timeout=300.0)
            
            await thread.send(
                "**⚠️ ATENÇÃO!**\n"
                "Para garantir a entrega, os **preços regionais** da sua Gamepass precisam estar **DESATIVADOS**.\n\n"
                "Você confirma que eles estão desativados? (Responda com 'sim' ou 'confirmo')"
            )
            await self.bot.wait_for('message', check=check, timeout=300.0)

            await thread.send("Obrigado pela confirmação! Um atendente já está com seu pedido e fará a entrega dos Robux em breve. Qualquer dúvida, pode perguntar aqui.")

        except asyncio.TimeoutError:
            await thread.send("Seu pedido expirou por inatividade. Esta thread será arquivada.")
            await asyncio.sleep(10)
            await thread.edit(archived=True, locked=True)
        except Exception as e:
            print(f"Erro no fluxo de compra: {e}")
            await thread.send("Ocorreu um erro inesperado no seu carrinho. Por favor, contate um administrador.")

def setup(bot):
    bot.add_cog(SalesCog(bot))
