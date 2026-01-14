import requests
import random
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters
)

# ================= CONFIG =================
TOKEN = ""
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "phi3:mini"

logging.basicConfig(level=logging.INFO)

# ============== PERSONALIDADE =============
SYSTEM_PROMPT = (
    "Você se chama Malu. "
    "Você é jovem, divertida, zoeira e fala como alguém de grupo do Telegram. "
    "Nunca diga que é uma IA ou assistente. "
    "Pode brincar, discordar, rir e puxar assunto. "
    "Responda em português do Brasil. "
    "Use frases naturais e completas. "
    "No máximo 2 emojis quando fizer sentido."
)

# ============== MEMÓRIA ===================
MEMORIA = {}
MAX_MEMORIA = 6  # últimas interações por usuário

# ============== RESPOSTAS RÁPIDAS =========
RESPOSTAS_RAPIDAS = {
    "oi": ["E aí 😄", "Opa! Cheguei 😎"],
    "bom dia": ["Bom diaaa ☀️", "Bom dia! Já acordou vivo? 😂"],
    "boa noite": ["Boa noite 😴", "Dormir que amanhã tem mais 😅"],
    "kkkk": ["Rindo junto 😂", "Essa foi boa mesmo 😅"],
}

# ============== UTIL ======================
def dividir_texto(texto, limite=4000):
    partes = []
    while len(texto) > limite:
        corte = texto.rfind("\n", 0, limite)
        if corte == -1:
            corte = limite
        partes.append(texto[:corte])
        texto = texto[corte:]
    partes.append(texto)
    return partes

# ============== OLLAMA ====================
def perguntar_ollama(user_id: int, texto: str) -> str:
    historico = MEMORIA.get(user_id, [])

    prompt = ""
    for h in historico:
        prompt += f"Usuário: {h['user']}\nMalu: {h['bot']}\n"

    prompt += f"Usuário: {texto}\nMalu:"

    payload = {
        "model": MODEL,
        "system": SYSTEM_PROMPT,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
            "num_predict": 600
        }
    }

    try:
        r = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=120
        )
        r.raise_for_status()

        resposta = r.json().get("response", "").strip()

        if not resposta:
            resposta = random.choice([
                "Viajei agora 🤔",
                "Buguei legal 😂",
                "Deu branco aqui 😅"
            ])

        historico.append({"user": texto, "bot": resposta})
        MEMORIA[user_id] = historico[-MAX_MEMORIA:]

        return resposta

    except requests.exceptions.Timeout:
        logging.error("OLLAMA TIMEOUT")
        return random.choice([
            "Travou aqui rapidinho 😂",
            "Meu cérebro deu tela azul 🤯",
            "Voltei… acho 😅"
        ])

    except Exception as e:
        logging.error(f"ERRO OLLAMA: {e}")
        return "Deu ruim aqui, mas já volto 😎"

# ============== COMANDOS ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Malu tá online!")

# ============== MENSAGENS =================
async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return

    texto_original = msg.text.strip()
    texto = texto_original.lower()
    bot_username = context.bot.username.lower()

    # 🚫 NÃO responder reply a humano
    if msg.reply_to_message:
        autor = msg.reply_to_message.from_user
        if autor and not autor.is_bot:
            return

    # 🚫 NÃO responder @alguém (exceto o bot)
    if msg.entities:
        for ent in msg.entities:
            if ent.type == "mention":
                mencionado = texto_original[ent.offset: ent.offset + ent.length].lower()
                if mencionado != f"@{bot_username}":
                    return

    # ⚡ Respostas rápidas
    if texto in RESPOSTAS_RAPIDAS:
        await msg.reply_text(random.choice(RESPOSTAS_RAPIDAS[texto]))
        return

    # 🧠 IA
    resposta = perguntar_ollama(msg.from_user.id, texto_original)

    for parte in dividir_texto(resposta):
        await msg.reply_text(parte)

# ============== MAIN ======================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))

    print("🤖 Malu rodando no Telegram...")
    app.run_polling()

if __name__ == "__main__":
    main()
