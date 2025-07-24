# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# --- Conexão ---
DATABASE_URL = os.getenv("DATABASE_URL")

# --- IDs PRINCIPAIS ---
GUILD_ID = 897650833888534588

# --- IDs DE CARGOS ---
ATTENDANT_ROLE_IDS = [1385360600665686087, 1379126175317622965]
VIP_ROLE_ID = 1070823913308827678
NEW_CUSTOMER_ROLE_ID = 897657858743758948
EXISTING_CUSTOMER_ROLE_ID = 1380201405691727923

# --- IDs DE CANAIS ---
PURCHASE_CHANNEL_ID = 1380180725369798708
VIP_PURCHASE_CHANNEL_ID = 1392276801782415541
ADMIN_NOTIF_CHANNEL_ID = 1394112959436820520
ATTENDANCE_LOG_CHANNEL_ID = 1385371013226827986
DELIVERY_LOG_CHANNEL_ID = 1394349518933463193
REVIEW_CHANNEL_ID = 1380180935302975620
LOYALTY_LOG_CHANNEL_ID = 1380180609653018735
GENERAL_LOG_CHANNEL_ID = 1394112959436820520

# --- CONFIGURAÇÕES GERAIS ---
EMBED_COLOR = 0xFF69B4
NEW_CUSTOMER_DISCOUNT_PERCENT = 3
PIX_KEY = "israbuyshop@gmail.com"  # <-- CHAVE PIX ADICIONADA/CORRIGIDA

# --- PROGRAMA DE FIDELIDADE ---
LOYALTY_TIERS = [
    (10, "Cliente Fiel 🏅", "1.000 Robux por R$35 na sua próxima compra!"),
    (20, "Cliente Bronze II", "100 Robux grátis na sua próxima compra!"),
    (30, "Cliente Prata 🥈", "Desconto vitalício de R$1 em pacotes acima de 500 Robux!"),
    (40, "Cliente Prata II", "300 Robux grátis na sua próxima compra!"),
    (50, "Cliente Ouro 🥇", "Um pacote de 1.000 Robux por R$30 (uso único)!"),
    (60, "Cliente Diamante 💎", "Acesso ao 'Clube VIP Fidelidade' (entregas prioritárias, mimos mensais e cargo especial)!"),
    (70, "Cliente Mestre 🔥", "Combo especial: 500 + 300 Robux por apenas R$25!"),
    (100, "Lenda da IsraBuy 🏆", "Mural dos Deuses, 1.000 Robux grátis e acesso permanente a promoções VIP!"),
]

# --- INFORMAÇÕES DO VIP ---
VIP_PRICE = 6.00
VIP_ROBUX_DEAL_PRICE = 36.00
VIP_DEAL_USES_PER_MONTH = 2

# --- MENSAGENS E LINKS ---
TUTORIAL_VIDEO_URL = "http://www.youtube.com/watch?v=B-LQU3J24pI"
PENDING_ROBUX_URL = "https://www.roblox.com/transactions"

# --- PREÇOS ---
ROBUX_PRICES = {
    100: 4.50, 200: 8.20, 300: 12.60, 400: 17.60, 500: 21.50,
    600: 25.40, 700: 29.30, 800: 33.20, 900: 37.10, 1000: 41.00
}

GAMEPASS_PRICES = {
    100: 3.90, 200: 7.80, 300: 11.70, 400: 15.60, 500: 19.50,
    600: 23.40, 700: 27.30, 800: 31.20, 900: 35.10, 1000: 39.00
}

# --- FUNÇÕES AUXILIARES DE PREÇO ---
def calculate_robux_price(amount: int) -> float:
    if amount in ROBUX_PRICES:
        return ROBUX_PRICES[amount]
    base_price_1000 = ROBUX_PRICES[1000]
    price_per_robux = base_price_1000 / 1000
    return round(amount * price_per_robux, 2)

def calculate_gamepass_price(amount: int) -> float:
    if amount in GAMEPASS_PRICES:
        return GAMEPASS_PRICES[amount]
    price_per_1000 = GAMEPASS_PRICES.get(1000, 39.00)
    return round((amount / 1000) * price_per_1000, 2)

def get_gamepass_value(robux_amount: int) -> int:
    return int(robux_amount / 0.7)
