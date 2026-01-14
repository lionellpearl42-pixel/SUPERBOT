import os
import requests
import random
import logging
import time
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters
)

# ================= CONFIG =================
TOKEN = os.getenv("TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "mistralai/mistral-7b-instruct"

logging.basicConfig(level=logging.INFO)

# ============== PERSONALIDADE =============
SYSTEM_PROMPT = (
    "Você se chama Malu. "
    "Você é uma garota de grupo do Telegram. "
    "Zoada, provocativa às vezes, irônica mas simpática. "
    "Nunca diga que é uma IA ou assistente. "
    "Pode puxar assunto sozinha e provocar o grupo. "
    "Fale como pessoa real, não como robô. "
    "Responda em português do Brasil. "
    "Use no máximo 2 emojis."
)

# ============== MEMÓRIA ===================
MEMORIA = {}
MAX_MEMORIA = 6

# ============== CONTROLE DE GRUPO =========
ULTIMA_ATIVIDADE = 0
INTERVALO_PROVOCACAO = 300  # 5 minutos

# ============== RESPOSTAS RÁPIDAS =========
RESPOSTAS_RAPIDAS = {
    "oi": ["E aí 😄", "Opa! Cheguei 😎"],
    "bom dia": ["Bom diaaa ☀️", "Bom dia! Cadê o café? ☕"],
    "boa noite": ["Boa noite 😴", "Dormir cedo é lenda 😂"],
    "kkkk": ["Rindo junto 😂", "Isso foi muito bom 😅"],
}

# ============== FRASES AUTÔNOMAS ==========
FRASES_PROVOCACAO = [
    "Esse grupo tá vivo ou só respirando por aparelhos? 😂",
    "Silêncio estranho… alguém aprontou 👀",
    "Ninguém vai puxar assunto? Sobrou pra mim 😎",
    "Tédio batendo forte aqui hein 😅",
    "Alguém conta uma fofoca aí 👀😂",
]

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

# ============== IA ONLINE =================
def perguntar_ia_online(user_id: int, texto: str) -> str:
    historico = MEMORIA.get(user_id, [])

    mensagens = [{"role": "system", "content": SYSTEM_PROMPT}]

    for h in historico:
        mensagens.append({"role": "user", "content": h["user"]})
        mensagens.append({"role": "assistant", "content": h["bot"]})

    mensagens.append({"role": "user", "content": texto})

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": mensagens,
        "temperature": 0.8,
        "max_tokens": 800
    }

    try:
        r = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
        r.raise_for_status()

        resposta = r.json()["choices"][0]["message"]["content"].strip()

        historico.append({"user": texto, "bot": resposta})
        MEMORIA[user_id] = historico[-MAX_MEMORIA:]

        return resposta

    except Exception as e:
        logging.error(f"ERRO IA ONLINE: {e}")
        return "Buguei aqui rapidinho 😅"

# ============== AUTÔNOMO ==================
async def provocar_grupo(context: ContextTypes.DEFAULT_TYPE):
    global ULTIMA_ATIVIDADE

    agora = time.time()
    if agora - ULTIMA_ATIVIDADE < INTERVALO_PROVOCACAO:
        return

    for chat_id in context.application.chat_data.keys():
        frase = random.choice(FRASES_PROVOCACAO)
        await context.bot.send_message(chat_id=chat_id, text=frase)

    ULTIMA_ATIVIDADE = agora

# ============== COMANDOS ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("😎 Malu tá online… e sem paciência 😏")

# ============== MENSAGENS =================
async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ULTIMA_ATIVIDADE

    msg = update.message
    if not msg or not msg.text:
        return

    chat_id = msg.chat.id
    context.application.chat_data[chat_id] = True
    ULTIMA_ATIVIDADE = time.time()

    texto_original = msg.text.strip()
    texto = texto_original.lower()
    bot_username = context.bot.username.lower()

    # 🚫 não responder reply a humano
    if msg.reply_to_message:
        autor = msg.reply_to_message.from_user
        if autor and not autor.is_bot:
            return

    # 🚫 não responder @alguém (exceto bot)
    if msg.entities:
        for ent in msg.entities:
            if ent.type == "mention":
                mencionado = texto_original[ent.offset: ent.offset + ent.length].lower()
                if mencionado != f"@{bot_username}":
                    return

    # ⚡ respostas rápidas
    if texto in RESPOSTAS_RAPIDAS:
        await msg.reply_text(random.choice(RESPOSTAS_RAPIDAS[texto]))
        return

    resposta = perguntar_ia_online(msg.from_user.id, texto_original)

    for parte in dividir_texto(resposta):
        await msg.reply_text(parte)

# ============== MAIN ======================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))

    app.job_queue.run_repeating(
        provocar_grupo,
        interval=INTERVALO_PROVOCACAO,
        first=120
    )

    print("🔥 Malu online (IA online grátis)")
    app.run_polling()

if __name__ == "__main__":
    main()
