# cogs/calculator_cog.py
import discord
from discord.ext import commands
import re
import config

class CalculatorCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def parse_input(self, content: str):
        content_lower = content.lower()
        # Se tiver "robux", é Robux. Qualquer outra coisa (reais, r$, ou nada) é tratado como BRL.
        is_robux = 'robux' in content_lower
        
        cleaned_content = content.replace('.', '').replace(',', '.')
        numeric_part = re.sub(r'[^\d.]', '', cleaned_content)
        
        try:
            value = float(numeric_part)
        except (ValueError, TypeError):
            return None, None

        if is_robux:
            return int(value), 'ROBUX'
        else:
            return value, 'BRL'

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.channel.id != config.CALCULATOR_CHANNEL_ID:
            return

        value, currency = self.parse_input(message.content)

        if value is None:
            # Ignora mensagens sem valor numérico para não poluir o chat.
            return

        embed = discord.Embed(title="🧮 Calculadora IsraBuy", color=config.EMBED_COLOR)

        if currency == 'BRL':
            price_per_robux = config.ROBUX_PRICES[1000] / 1000
            robux_amount = int(value / price_per_robux)
            embed.description = f"Com **R$ {value:.2f}** você pode comprar aproximadamente **{robux_amount} Robux**."
            await message.reply(embed=embed, delete_after=60)

        elif currency == 'ROBUX':
            if value < 100:
                await message.reply("O valor mínimo para cálculo é de **100 Robux**.", delete_after=10)
                return
            
            brl_amount = config.calculate_robux_price(value)
            embed.description = f"**{value} Robux** custam **R$ {brl_amount:.2f}**."
            await message.reply(embed=embed, delete_after=60)

def setup(bot):
    bot.add_cog(CalculatorCog(bot))
