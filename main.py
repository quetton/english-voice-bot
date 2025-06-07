import os
import tempfile
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import speech_recognition as sr
from gtts import gTTS
from pydub import AudioSegment
import openai

# Настройки
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # ← Получаем из переменных окружения
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")          # ← Получаем из переменных окружения

openai.api_key = OPENAI_API_KEY

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Путь к ffmpeg (автоматически доступен в GitHub Codespaces)
AudioSegment.converter = "/usr/bin/ffmpeg"
AudioSegment.ffmpeg = "/usr/bin/ffmpeg"
AudioSegment.ffprobe = "/usr/bin/ffprobe"

# --- Функции ---

def recognize_speech(file_path):
    recognizer = sr.Recognizer()
    with sr.AudioFile(file_path) as source:
        audio = recognizer.record(source)
    return recognizer.recognize_google(audio, language="en-US")

def generate_response(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

def text_to_speech(text, file_path):
    tts = gTTS(text=text, lang='en')
    tts.save(file_path)

# --- Telegram Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Отправь мне голосовое сообщение, и я отвечу тебе голосом!")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        voice_file = await update.message.voice.get_file()
        ogg_path = os.path.join(tempfile.gettempdir(), "voice.ogg")
        await voice_file.download_to_drive(ogg_path)

        wav_path = os.path.join(tempfile.gettempdir(), "voice.wav")
        AudioSegment.from_ogg(ogg_path).export(wav_path, format="wav")

        user_text = recognize_speech(wav_path)
        await update.message.reply_text(f"Вы сказали:\n\n{text}")

        ai_response = generate_response(user_text)
        await update.message.reply_text(f"Ответ ИИ:\n\n{ai_response}")

        output_audio = os.path.join(tempfile.gettempdir(), "response.mp3")
        text_to_speech(ai_response, output_audio)

        ogg_output = os.path.join(tempfile.gettempdir(), "response.ogg")
        AudioSegment.from_mp3(output_audio).export(ogg_output, format="ogg", codec="libopus")

        with open(ogg_output, 'rb') as f:
            await update.message.reply_voice(f)

    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")

# --- Запуск бота ---

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VOICE & ~filters.COMMAND, handle_voice))

    app.run_polling()
