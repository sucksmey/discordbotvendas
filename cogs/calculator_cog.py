# cogs/calculator_cog.py
import discord
from discord.ext import commands
import re

import config

class CalculatorCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def parse_input(self, content: str):
        """Analisa a mensagem para extrair o valor e a moeda."""
        content_lower = content.lower()
        
        # Identifica a moeda pela palavra-chave
        is_brl = 'reais' in content_lower or 'r$' in content_lower
        is_robux = 'robux' in content_lower
        
        # Limpa a string para extrair apenas o número
        # Remove pontos de milhar, substitui vírgula por ponto decimal
        cleaned_content = content.replace('.', '').replace(',', '.')
        # Remove todas as letras e símbolos, exceto o ponto decimal
        numeric_part = re.sub(r'[^\d.]', '', cleaned_content)
        
        try:
            value = float(numeric_part)
        except (ValueError, TypeError):
            return None, None # Retorna None se não conseguir converter para número

        if is_brl:
            return value, 'BRL'
        if is_robux:
            # Robux deve ser um número inteiro
            return int(value), 'ROBUX'
        
        # Se não houver palavra-chave, trata como ambíguo
        return value, 'AMBIGUOUS'

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignora mensagens do próprio bot ou de outros canais
        if message.author.bot or message.channel.id != config.CALCULATOR_CHANNEL_ID:
            return

        value, currency = self.parse_input(message.content)

        if value is None:
            # Se a entrada for inválida (ex: "abc"), envia ajuda
            help_embed = discord.Embed(
                title="❌ Formato Inválido",
                description="Por favor, digite um valor no formato correto.\n\n**Exemplos:**\n`1000 robux`\n`41 reais`\n`10.50`",
                color=discord.Color.red()
            )
            await message.reply(embed=help_embed, delete_after=15)
            return

        embed = discord.Embed(title="🧮 Calculadora IsraBuy", color=config.EMBED_COLOR)

        if currency == 'BRL':
            # Converte Reais para Robux
            price_per_robux = config.ROBUX_PRICES[1000] / 1000
            robux_amount = int(value / price_per_robux)
            embed.description = f"Com **R$ {value:.2f}** você pode comprar aproximadamente **{robux_amount} Robux**."

        elif currency == 'ROBUX':
            # Converte Robux para Reais
            brl_amount = config.calculate_robux_price(value)
            embed.description = f"**{value} Robux** custam **R$ {brl_amount:.2f}**."
        
        elif currency == 'AMBIGUOUS':
            # Se for ambíguo, mostra as duas conversões
            # Converte o valor como se fosse Reais
            price_per_robux = config.ROBUX_PRICES[1000] / 1000
            robux_amount = int(value / price_per_robux)
            
            # Converte o valor como se fosse Robux
            brl_amount = config.calculate_robux_price(int(value))

            embed.description = (
                f"O valor `{message.content}` pode ser interpretado de duas formas:\n\n"
                f"💰 **R$ {value:.2f}** equivalem a aprox. **{robux_amount} Robux**.\n"
                f"💎 **{int(value)} Robux** custam **R$ {brl_amount:.2f}**."
            )

        await message.reply(embed=embed)


def setup(bot):
    bot.add_cog(CalculatorCog(bot))
