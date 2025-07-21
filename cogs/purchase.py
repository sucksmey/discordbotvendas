# cogs/purchase.py

import discord
from discord.ext import commands
import config

# Um View (visualização) que contém o Select (menu suspenso) para escolher o produto
class ProductSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180) # Timeout de 3 minutos

        options = []
        for product_name, details in config.PRODUCTS.items():
            # Limita as opções iniciais a um número razoável se houver muitos produtos
            # Ou filtra para os mais relevantes para o primeiro menu
            options.append(
                discord.SelectOption(
                    label=product_name,
                    description=f"Compre {product_name}",
                    emoji=details["emoji"]
                )
            )
        
        # Adiciona o menu suspenso à view
        self.add_item(
            discord.ui.Select(
                placeholder="Selecione um produto...",
                min_values=1,
                max_values=1,
                options=options,
                custom_id="product_select" # ID único para identificar essa interação
            )
        )

    # Callback para quando uma opção do menu suspenso é selecionada
    @discord.ui.select(custom_id="product_select")
    async def select_product_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        selected_product_name = select.values[0] # Pega o valor selecionado (nome do produto)
        product_details = config.PRODUCTS[selected_product_name]
        
        embed = discord.Embed(
            title=f"Produto Selecionado: {product_details['emoji']} {selected_product_name}",
            color=config.ROSE_COLOR
        )

        if product_details['type'] == 'automatized':
            # Se for Robux (automatizado), vamos pedir para o usuário escolher a quantidade
            embed.description = "Você selecionou um produto com fluxo de compra automatizado. Agora, selecione a quantidade desejada de Robux:"
            # Para o Robux, precisaremos de um novo Select para as quantidades
            # Por enquanto, apenas confirmamos
            await interaction.response.send_message(embed=embed, ephemeral=True)
            # Em breve: Chamar a função para iniciar o fluxo de Robux com quantidades
        elif product_details['type'] == 'manual':
            # Se for outro jogo (manual), vamos iniciar o atendimento com um admin
            embed.description = "Você selecionou um produto que requer atendimento manual. Um atendente será notificado para te ajudar!"
            
            # Crie a thread privada e chame o admin
            await interaction.response.send_message(embed=embed, ephemeral=True)
            # Em breve: Chamar a função para criar a thread, notificar admin, etc.

# Classe principal do Cog
class Purchase(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Comando de barra para iniciar o processo de compra
    @discord.app_commands.command(name="comprar", description="Inicia o processo de compra de produtos.")
    async def buy_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🛒 Selecione um Produto",
            description="Use o menu abaixo para escolher o produto que deseja comprar.",
            color=config.ROSE_COLOR
        )
        
        # Envia a mensagem com o menu suspenso
        await interaction.response.send_message(embed=embed, view=ProductSelectView(), ephemeral=True)


# Função setup para adicionar o cog ao bot
async def setup(bot: commands.Bot):
    await bot.add_cog(Purchase(bot))
