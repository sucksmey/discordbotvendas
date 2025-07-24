# config.py
import discord

# --- IDs PRINCIPAIS ---
GUILD_ID = 897650833888534588  # ID do seu servidor

# --- IDs DE CARGOS ---
ATTENDANT_ROLE_IDS = [1385360600665686087, 1379126175317622965] # IDs dos cargos de atendente
VIP_ROLE_ID = 1070823913308827678 # ID do cargo VIP

# --- IDs DE CANAIS ---
PURCHASE_CHANNEL_ID = 1380180725369798708      # Canal onde o botão de compra inicial aparece
ADMIN_NOTIF_CHANNEL_ID = 1394112959436820520   # Canal para notificar admins sobre novo pedido
ATTENDANCE_LOG_CHANNEL_ID = 1385371013226827986 # Canal para logar quem está atendendo
DELIVERY_LOG_CHANNEL_ID = 1394349518933463193   # Canal para logar entregas
REVIEW_CHANNEL_ID = 1380180935302975620         # Canal para enviar as avaliações

# --- CONFIGURAÇÕES DE EMBEDS ---
EMBED_COLOR = 0xFF69B4  # Cor rosa para as embeds

# --- PREÇOS ---
# (valor em R$)
ROBUX_PRICES = {
    100: 4.50, 200: 8.20, 300: 12.60, 400: 17.60, 500: 21.50,
    600: 25.40, 700: 29.30, 800: 33.20, 900: 37.10, 1000: 41.00
}

# (valor em R$)
GAMEPASS_PRICE_PER_1000 = 39.00

# --- MENSAGENS E LINKS ---
TUTORIAL_VIDEO_URL = "http://www.youtube.com/watch?v=B-LQU3J24pI"
PENDING_ROBUX_URL = "https://www.roblox.com/transactions"

# --- FUNÇÕES AUXILIARES DE PREÇO ---
def calculate_robux_price(amount: int) -> float:
    """Calcula o preço para uma quantidade de Robux."""
    base_price_1000 = ROBUX_PRICES[1000]
    price_per_robux = base_price_1000 / 1000
    return round(amount * price_per_robux, 2)

def calculate_gamepass_price(amount: int) -> float:
    """Calcula o preço para uma quantidade de Robux via Gamepass."""
    price_per_robux = GAMEPASS_PRICE_PER_1000 / 1000
    return round(amount * price_per_robux, 2)

def get_gamepass_value(robux_amount: int) -> int:
    """Calcula o valor que deve ser colocado na Gamepass (com a taxa de 30%)."""
    return int(robux_amount / 0.7)
