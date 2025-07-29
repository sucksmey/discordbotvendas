# cogs/calculator_cog.py
import discord
from discord.ext import commands
from discord.ui import View, button
import re

import config

class ConversionView(View):
    def __init__(self, value: float, original_author_id: int):
        super().__init__(timeout=60.0)
        self.value = value
        self.original_author_id = original_author_id
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.original_author_id:
            await interaction.response.send_message("Você não pode interagir com os botões de outra pessoa.", ephemeral=True)
            return False
        return True

    @button(label="Converter para Robux", style=discord.ButtonStyle.primary, emoji="💎")
    async def to_robux_callback(self, button_obj: discord.ui.Button, interaction: discord.Interaction):
        price_per_robux = config.ROBUX_PRICES[1000] / 1000
        robux_amount = int(self.value / price_per_robux)
        
        embed = discord.Embed(title="🧮 Calculadora IsraBuy", color=config.EMBED_COLOR)
        embed.description = f"💰 **R$ {self.value:.2f}** equivalem a aproximadamente **{robux_amount} Robux**."
        
        await interaction.response.edit_message(embed=embed, view=None)

    @button(label="Converter para Reais", style=discord.ButtonStyle.secondary, emoji="💰")
    async def to_brl_callback(self, button_obj: discord.ui.Button, interaction: discord.Interaction):
        brl_amount = config.calculate_robux_price(int(self.value))

        embed = discord.Embed(title="🧮 Calculadora IsraBuy", color=config.EMBED_COLOR)
        embed.description = f"💎 **{int(self.value)} Robux** custam **R$ {brl_amount:.2f}**."

        await interaction.response.edit_message(embed=embed, view=None)

    async def on_timeout(self):
        if self.message:
            for item in self.children:
                item.disabled = True
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass # A mensagem pode ter sido deletada

class CalculatorCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def parse_input(self, content: str):
        content_lower = content.lower()
        is_brl = 'reais' in content_lower or 'r$' in content_lower
        is_robux = 'robux' in content_lower
        
        cleaned_content = content.replace('.', '').replace(',', '.')
        numeric_part = re.sub(r'[^\d.]', '', cleaned_content)
        
        try:
            value = float(numeric_part)
        except (ValueError, TypeError):
            return None, None

        if is_brl:
            return value, 'BRL'
        if is_robux:
            return int(value), 'ROBUX'
        
        return value, 'AMBIGUOUS'

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.channel.id != config.CALCULATOR_CHANNEL_ID:
            return

        value, currency = self.parse_input(message.content)

        if value is None:
            help_embed = discord.Embed(title="❌ Formato Inválido", description="Use os formatos: `1000 robux`, `41 reais` ou `10.50`.", color=discord.Color.red())
            await message.reply(embed=help_embed, delete_after=15)
            return

        # VALIDAÇÃO DE VALOR MÍNIMO
        if (currency == 'BRL' and value < 4.50) or (currency == 'ROBUX' and value < 100):
             return await message.reply(f"O valor mínimo para cálculo é de **100 Robux** (R$ 4,50).")
        if currency == 'AMBIGUOUS' and value < 100:
             brl_amount = config.calculate_robux_price(int(value))
             if brl_amount < 4.50:
                 return await message.reply("O valor mínimo para cálculo é de **100 Robux** ou **R$ 4,50**.")

        embed = discord.Embed(title="🧮 Calculadora IsraBuy", color=config.EMBED_COLOR)

        if currency == 'BRL':
            price_per_robux = config.ROBUX_PRICES[1000] / 1000
            robux_amount = int(value / price_per_robux)
            embed.description = f"Com **R$ {value:.2f}** você pode comprar aproximadamente **{robux_amount} Robux**."
            await message.reply(embed=embed)

        elif currency == 'ROBUX':
            brl_amount = config.calculate_robux_price(value)
            embed.description = f"**{value} Robux** custam **R$ {brl_amount:.2f}**."
            await message.reply(embed=embed)
        
        elif currency == 'AMBIGUOUS':
            view = ConversionView(value=value, original_author_id=message.author.id)
            embed = discord.Embed(title="🤔 Qual moeda?", color=config.EMBED_COLOR)
            embed.description = f"O valor `{message.content}` que você digitou é em Reais ou Robux?\n\nEscolha uma opção abaixo para converter."
            sent_message = await message.reply(embed=embed, view=view)
            view.message = sent_message

def setup(bot):
    bot.add_cog(CalculatorCog(bot))
