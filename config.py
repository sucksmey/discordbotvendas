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
INITIAL_BUYER_ROLE_ID = 1380201405691727923
SPEND_TIER_1_ROLE_ID = 1394109025246773340  # > 100 BRL
SPEND_TIER_2_ROLE_ID = 1394109339316392047  # > 200 BRL
SPEND_TIER_3_ROLE_ID = 1394113545280557067  # > 500 BRL
SPEND_TIER_4_ROLE_ID = 1385379403977986189  # > 1000 BRL

# --- IDs DE USUÁRIOS ESPECIAIS ---
LEADER_ID = 595044340691369985

# --- IDs DE CANAIS ---
PURCHASE_CHANNEL_ID = 1380180725369798708
ADMIN_NOTIF_CHANNEL_ID = 1398666575929937940
DELIVERY_LOG_CHANNEL_ID = 1394349518933463193
REVIEW_CHANNEL_ID = 1380180935302975620
AWAITING_DELIVERY_CHANNEL_ID = 1399488972706812037
FOLLOW_UP_CHANNEL_ID = 1385371013226827986
CALCULATOR_CHANNEL_ID = 1398034780783644794
GENERAL_LOG_CHANNEL_ID = 1394112959436820520

# --- CONFIGURAÇÕES GERAIS ---
EMBED_COLOR = 0xFF69B4
PIX_KEY = "israbuyshop@gmail.com"

# --- NOVO SISTEMA DE CARGOS POR GASTOS (EM REAIS) ---
SPEND_ROLES_TIERS = {
    1000: SPEND_TIER_4_ROLE_ID,
    500: SPEND_TIER_3_ROLE_ID,
    200: SPEND_TIER_2_ROLE_ID,
    100: SPEND_TIER_1_ROLE_ID
}

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
    if not isinstance(amount, int):
        try: amount = int(amount)
        except (ValueError, TypeError): return 0.0
    if amount in ROBUX_PRICES:
        return ROBUX_PRICES[amount]
    base_price_1000 = ROBUX_PRICES[1000]
    price_per_robux = base_price_1000 / 1000
    return round(amount * price_per_robux, 2)

def calculate_gamepass_price(amount: int) -> float:
    if not isinstance(amount, int):
        try: amount = int(amount)
        except (ValueError, TypeError): return 0.0
    if amount in GAMEPASS_PRICES:
        return GAMEPASS_PRICES[amount]
    price_per_1000 = GAMEPASS_PRICES.get(1000, 39.00)
    return round((amount / 1000) * price_per_1000, 2)
