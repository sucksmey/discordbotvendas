import os

# --- IDs Essenciais ---
GUILD_ID = 897650833888534588
ADMIN_ROLE_ID = 1379126175317622965
VIP_ROLE_ID = 1070823913308827678
CLIENT_ROLE_ID = 1380201405691727923
COMPRE_AQUI_CHANNEL_ID = 1380180725369798708
CATEGORY_VENDAS_ID = 1382399986725163140 # Categoria para threads de vendas
CATEGORY_ENTREGUES_ID = 1392174310453411961 # Categoria para threads de entregues (para organização)
LOGS_COMPRAS_CHANNEL_ID = 1382340441579720846 # Logs detalhados de compras
TRANSCRIPT_CHANNEL_ID = 1382342395068289156 # Para transcrições de threads
REVIEW_CHANNEL_ID = 1380180935302975620 # Canal para avaliações dos clientes
ROBUX_DELIVERY_USER_ID = 314200274933907456 # ID de um usuário para marcar entregas (se aplicável)
PUBLIC_LOGS_CHANNEL_ID = 1394349518933463193 # Logs de compras aprovadas para visibilidade pública
CARRINHO_EM_ANDAMENTO_CHANNEL_ID = 1386049296238903336 # Canal para notificar admins sobre novos carrinhos/tickets
PRIVATE_ACTIONS_LOG_CHANNEL_ID = 1394112959436820520 # Logs de ações privadas (histórico, consultar preços)

# --- IDs de Fidelidade e Sorteio ---
LOYALTY_NOTIFICATION_CHANNEL_ID = 1380180609653018735
GIVEAWAY_CHANNEL_ID = 0 # Preencha com o ID do canal principal de sorteios (se houver, 0 por enquanto)
LOYALTY_ROLE_10 = 1394109025246773340
LOYALTY_ROLE_50 = 1394109339316392047
LOYALTY_ROLE_100 = 1394113545280557067

# --- Configurações de Pagamento ---
PIX_KEY_MANUAL = "israbuyshop@gmail.com" # Chave PIX manual de fallback (remover após integrar MP)
VIP_PRICE = 6.00 # Não usado diretamente com a nova estrutura de PRODUCTS

# --- Cores dos embeds (TODAS ROSAS, conforme solicitado) ---
EMBED_COLOR = 0xFFC0CB # Cor rosa clara (Pink) para todas as embeds

# --- Produtos e Preços (Serão carregados do DB, mas mantidos aqui para referência ou inicialização) ---
# O bot dará preferência aos dados do DB se estiverem lá.
PRODUCTS = {
    "Robux": {
        "emoji": "💎",
        "type": "robux",
        "prices": { "100 Robux": 4.50, "200 Robux": 8.10, "300 Robux": 12.70, "400 Robux": 17.60, "500 Robux": 21.50, "600 Robux": 25.40, "700 Robux": 29.30, "800 Robux": 33.20, "900 Robux": 37.10, "1000 Robux": 41.00 },
        "vip_prices": { "1000 Robux": 36.90 }
    },
    "Valorant": {"emoji": "💢", "type": "game", "prices": {"400 VP": 19.00, "475 VP": 21.90, "505 VP": 23.00, "815 VP": 35.00, "1000 VP": 41.90, "1305 VP": 53.00, "1700 VP": 67.00, "1810 VP": 73.00, "2050 VP": 78.90, "2175 VP": 85.90, "2205 VP": 87.00, "2720 VP": 103.00, "3085 VP": 116.00, "3225 VP": 123.00, "3650 VP": 135.90, "4025 VP": 153.00, "4450 VP": 163.00}},
    "League of Legends": {"emoji": "💥", "type": "game", "prices": {"485 RP": 19.00, "575 RP": 21.90, "610 RP": 23.00, "1020 RP": 35.00, "1380 RP": 44.90, "1650 RP": 53.00, "1865 RP": 60.90, "2125 RP": 67.00, "2260 RP": 73.00, "2670 RP": 85.00, "2800 RP": 86.90, "3355 RP": 103.00, "3805 RP": 116.00, "4500 RP": 135.90, "5005 RP": 153.00, "5445 RP": 163.00, "5795 RP": 173.00, "6500 RP": 192.90, "6710 RP": 203.00, "11240 RP": 323.00, "13500 RP": 382.90}},
    "Free Fire": {"emoji": "🔥", "type": "game", "prices": {"100 Diamantes + 10% Bônus": 6.49, "310 Diamantes + 10% Bônus": 15.99, "520 Diamantes + 10% Bônus": 22.99, "1060 Diamantes + 10% Bônus": 46.99, "2180 Diamantes + 10% Bônus": 89.99, "5600 Diamantes + 10% Bônus": 211.99}},
    "Mobile Legends": {"emoji": "⭐", "type": "game", "prices": {"Pase de Super Valor": 5.00, "78 Diamantes + 8 Bonus": 7.25, "Pase Semanal": 9.00, "156 Diamantes + 16 Bonus": 13.50, "234 Diamantes + 23 Bonus": 19.67, "172 Diamantes + Pase Semanal": 21.50, "Twilight Pass": 42.25, "625 Diamantes + 81 Bonus": 51.00, "1860 Diamantes + 335 Bonus": 151.00, "3099 Diamantes + 589 Bonus": 251.00, "4649 Diamantes + 883 Bonus": 376.00, "7740 Diamantes + 1548 Bonus": 626.00}},
    "PlayStation Store": {"emoji": "🎮", "type": "giftcard", "prices": {"R$35": 37.00, "R$60": 62.00, "R$100": 102.00, "R$250": 252.00, "R$300": 302.00, "R$350": 352.00, "R$360": 362.00, "R$400": 402.00, "R$500": 502.00}},
    "Xbox Store": {"emoji": "🛒", "type": "giftcard", "prices": {"R$50": 52.00, "R$100": 102.00, "R$150": 152.00, "R$200": 202.00, "R$250": 252.00, "R$300": 302.00, "R$400": 402.00}},
    "Genshin Impact": {"emoji": "🌈", "type": "game", "prices": {"60 Cristal Gênesis": 8.03, "330 Cristal Gênesis": 28.72, "Bênção da Lua Nova": 28.72, "1090 Cristal Gênesis": 80.41, "2240 Cristal Gênesis": 170.84, "3880 Cristal Gênesis": 261.27, "8080 Cristal Gênesis": 519.62}},
    "Honkai Star Rail": {"emoji": "✨", "type": "game", "prices": {"60 Fragmentos Oníricos": 6.90, "330 Fragmentos Oníricos": 26.90, "Express Supply Pass": 26.90, "2240 Fragmentos Oníricos": 151.90, "3880 Fragmentos Oníricos": 251.90, "8080 Fragmentos Oníricos": 501.90}},
    "Honor of Kings": {"emoji": "👑", "type": "game", "prices": {"88 Fichas": 7.69, "Pase Semanal": 7.75, "257 Fichas": 19.19, "Pase Semanal Plus": 19.19, "432 Fichas": 30.68, "605 Fichas": 42.18, "865 Fichas": 59.43, "1308 Fichas": 88.17, "2616 Fichas": 174.39, "4580 Fichas": 289.36, "9160 Fichas": 576.77}},
    "Marvel Rivals": {"emoji": "🦸", "type": "game", "prices": {"100 TRELIÇAS": 5.90, "500 TRELIÇAS": 25.50, "1000 TRELIÇAS": 50.00, "2180 TRELIÇAS": 99.00, "5680 TRELIÇAS": 246.00, "11680 TRELIÇAS": 491.00}},
    "Google Play": {"emoji": "📱", "type": "giftcard", "prices": {"R$16.90": 17.90, "R$30": 31.00, "R$40": 41.00, "R$50": 51.00, "R$70": 71.00, "R$80": 81.00, "R$100": 101.00, "R$139.90": 140.90, "R$250": 251.00}},
    "Xbox Fortnite": {"emoji": "🕹️", "type": "game", "prices": {"Pacote Lendas Menta (Xbox)": 100.00}},
    "Apple": {"emoji": "🍎", "type": "giftcard", "prices": {"R$20": 22.00, "R$50": 52.00, "R$150": 152.00, "R$200": 202.00}},
}

# --- Configurações do bot ---
BOT_PREFIX = "!" # Prefixo para comandos tradicionais (se for usar)
COMMAND_SYNC_GLOBAL = True # Sincronizar comandos de barra globalmente (Defina como False para testes locais rápidos)

# Tempo de expiração do carrinho em minutos (ex: 60 minutos)
CART_EXPIRATION_MINUTES = 60

# --- Configurações de Mercado Pago (preencher quando integrar) ---
# Os valores aqui serão substituídos pelas variáveis de ambiente do Railway
MERCADO_PAGO_ACCESS_TOKEN = os.getenv("MERCADO_PAGO_ACCESS_TOKEN", "SEU_MERCADO_PAGO_ACCESS_TOKEN_AQUI")
MERCADO_PAGO_WEBHOOK_URL = os.getenv("MERCADO_PAGO_WEBHOOK_URL", "SUA_URL_WEBHOOK_MERCADO_PAGO_AQUI")
