# config.py

import os
from discord import Color # Importar Color para usar cores personalizadas

# --- IDs Essenciais ---
GUILD_ID = 897650833888534588 # ID do seu servidor
ADMIN_ROLE_ID = 1379126175317622965 # ID do cargo de Administrador
VIP_ROLE_ID = 1070823913308827678
CLIENT_ROLE_ID = 1380201405691727923
COMPRE_AQUI_CHANNEL_ID = 1380180725369798708 # Canal onde o comando /comprar será usado E onde as threads serão criadas
CATEGORY_VENDAS_ID = 1382399986725163140 # Categoria geral para canais de vendas (usada como referência, não diretamente aqui)
CATEGORY_ENTREGUES_ID = 1392174310453411961
LOGS_COMPRAS_CHANNEL_ID = 1382340441579720846 # Canal para logs de todas as compras
TRANSCRIPT_CHANNEL_ID = 1382342395068289156
REVIEW_CHANNEL_ID = 1380180935302975620 # Canal para avaliações dos clientes
ROBUX_DELIVERY_USER_ID = 314200274933907456 # ID do usuário que faz as entregas de Robux (ou cargo)
PUBLIC_LOGS_CHANNEL_ID = 1394349518933463193 # Canal para logs públicos, tipo "nova compra aprovada"
CARRINHO_EM_ANDAMENTO_CHANNEL_ID = COMPRE_AQUI_CHANNEL_ID # <<< AGORA APONTA PARA O MESMO CANAL!

# --- IDs de Fidelidade e Sorteio ---
LOYALTY_NOTIFICATION_CHANNEL_ID = 1380180609653018735 # Canal para notificações de fidelidade
GIVEAWAY_CHANNEL_ID = 1394123636109217922 # <<< ID do canal de sorteios
LOYALTY_ROLE_10 = 1394109025246773340
LOYALTY_ROLE_50 = 1394109339316392047
LOYALTY_ROLE_100 = 1394113545280557067

# --- Configurações de Pagamento ---
PIX_KEY_MANUAL = "israbuyshop@gmail.com"
VIP_PRICE = 6.00

# --- Cores ---
ROSE_COLOR = Color.from_rgb(255, 192, 203) # Cor rosa padrão para embeds

# --- Produtos e Preços ---
# Adicionado 'type' para diferenciar produtos de "compra automatizada" e "atendimento manual"
# 'automatized' = fluxo de Robux
# 'manual' = fluxo de atendimento por admin
PRODUCTS = {
    "Robux": {
        "emoji": "💎",
        "type": "automatized",
        "prices": { "100 Robux": 4.50, "200 Robux": 8.10, "300 Robux": 12.70, "400 Robux": 17.60, "500 Robux": 21.50, "600 Robux": 25.40, "700 Robux": 29.30, "800 Robux": 33.20, "900 Robux": 37.10, "1000 Robux": 41.00 },
        "vip_prices": { "1000 Robux": 36.90 }
    },
    "Valorant": {"emoji": "💢", "type": "manual", "prices": {"400 VP": 19.00, "475 VP": 21.90, "505 VP": 23.00, "815 VP": 35.00, "1000 VP": 41.90, "1305 VP": 53.00, "1700 VP": 67.00, "1810 VP": 73.00, "2050 VP": 78.90, "2175 VP": 85.90, "2205 VP": 87.00, "2720 VP": 103.00, "3085 VP": 116.00, "3225 VP": 123.00, "3650 VP": 135.90, "4025 VP": 153.00, "4450 VP": 163.00}},
    "League of Legends": {"emoji": "💥", "type": "manual", "prices": {"485 RP": 19.00, "575 RP": 21.90, "610 RP": 23.00, "1020 RP": 35.00, "1380 RP": 44.90, "1650 RP": 53.00, "1865 RP": 60.90, "2125 RP": 67.00, "2260 RP": 73.00, "2670 RP": 85.00, "2800 RP": 86.90, "3355 RP": 103.00, "3805 RP": 116.00, "4500 RP": 135.90, "5005 RP": 153.00, "5445 RP": 163.00, "5795 RP": 173.00, "6500 RP": 192.90, "6710 RP": 203.00, "11240 RP": 323.00, "13500 RP": 382.90}},
    "Free Fire": {"emoji": "🔥", "type": "manual", "prices": {"100 Diamantes + 10% Bônus": 6.49, "310 Diamantes + 10% Bônus": 15.99, "520 Diamantes + 10% Bônus": 22.99, "1060 Diamantes + 10% Bônus": 46.99, "2180 Diamantes + 10% Bônus": 89.99, "5600 Diamantes + 10% Bônus": 211.99}},
    "Mobile Legends": {"emoji": "⭐", "type": "manual", "prices": {"Pase de Super Valor": 5.00, "78 Diamantes + 8 Bonus": 7.25, "Pase Semanal": 9.00, "156 Diamantes + 16 Bonus": 13.50, "234 Diamantes + 23 Bonus": 19.67, "172 Diamantes + Pase Semanal": 21.50, "Twilight Pass": 42.25, "625 Diamantes + 81 Bonus": 51.00, "1860 Diamantes + 335 Bonus": 151.00, "3099 Diamantes + 589 Bonus": 251.00, "4649 Diamantes + 883 Bonus": 376.00, "7740 Diamantes + 1548 Bonus": 626.00}},
    "PlayStation Store": {"emoji": "🎮", "type": "manual", "prices": {"R$35": 37.00, "R$60": 62.00, "R$100": 102.00, "R$250": 252.00, "R$300": 302.00, "R$350": 352.00, "R$360": 362.00, "R$400": 402.00, "R$500": 502.00}},
    "Xbox Store": {"emoji": "🛒", "type": "manual", "prices": {"R$50": 52.00, "R$100": 102.00, "R$150": 152.00, "R$200": 202.00, "R$250": 252.00, "R$300": 302.00, "R$400": 402.00}},
    "Genshin Impact": {"emoji": "🌈", "type": "manual", "prices": {"60 Cristal Gênesis": 8.03, "330 Cristal Gênesis": 28.72, "Bênção da Lua Nova": 28.72, "1090 Cristal Gênesis": 80.41, "2240 Cristal Gênesis": 170.84, "3880 Cristal Gênesis": 261.27, "8080 Cristal Gênesis": 519.62}},
    "Honkai Star Rail": {"emoji": "✨", "type": "manual", "prices": {"60 Fragmentos Oníricos": 6.90, "330 Fragmentos Oníricos": 26.90, "Express Supply Pass": 26.90, "2240 Fragmentos Oníricos": 151.90, "3880 Fragmentos Oníricos": 251.90, "8080 Fragmentos Oníricos": 501.90}},
    "Honor of Kings": {"emoji": "👑", "type": "manual", "prices": {"88 Fichas": 7.69, "Pase Semanal": 7.75, "257 Fichas": 19.19, "Pase Semanal Plus": 19.19, "432 Fichas": 30.68, "605 Fichas": 42.18, "865 Fichas": 59.43, "1308 Fichas": 88.17, "2616 Fichas": 174.39, "4580 Fichas": 289.36, "9160 Fichas": 576.77}},
    "Marvel Rivals": {"emoji": "🦸", "type": "manual", "prices": {"100 TRELIÇAS": 5.90, "500 TRELIÇAS": 25.50, "1000 TRELIÇAS": 50.00, "2180 TRELIÇAS": 99.00, "5680 TRELIÇAS": 246.00, "11680 TRELIÇAS": 491.00}},
    "Google Play": {"emoji": "📱", "type": "manual", "prices": {"R$16.90": 17.90, "R$30": 31.00, "R$40": 41.00, "R$50": 51.00, "R$70": 71.00, "R$80": 81.00, "R$100": 101.00, "R$139.90": 140.90, "R$250": 251.00}},
    "Xbox Fortnite": {"emoji": "🕹️", "type": "manual", "prices": {"Pacote Lendas Menta (Xbox)": 100.00}},
    "Apple": {"emoji": "🍎", "type": "manual", "prices": {"R$20": 22.00, "R$50": 52.00, "R$150": 152.00, "R$200": 202.00}},
}

# --- Variáveis de Ambiente ---
# Isso vai carregar as variáveis do arquivo .env
# Certifique-se de que BOT_TOKEN e MERCADOPAGO_ACCESS_TOKEN estejam no seu .env
BOT_TOKEN = os.getenv("BOT_TOKEN")
MERCADOPAGO_ACCESS_TOKEN = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL") # URL de conexão com o PostgreSQL no Railway
