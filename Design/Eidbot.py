import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

from arabic_reshaper import ArabicReshaper
from bidi.algorithm import get_display
from PIL import ImageFont, Image, ImageDraw
import os
import json


TOKEN = '7250019509:AAFcvMGumUDPcBLdsD8qFC9X8N_fvPJLN0M'
PATH = os.path.dirname(__file__)

# Load design and font configurations
with open(os.path.join(PATH, 'design_config.json')) as f:
    design_config = json.load(f)

with open(os.path.join(PATH, 'font_config.json')) as f:
    font_config = json.load(f)

reshaper = ArabicReshaper(configuration={
    'delete_harakat': False,
    'use_unshaped_instead_of_isolated': True
})

# Global variables to store user choices
user_choices = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton(f"Design {d['id']}", callback_data=f"design_{d['id']}") for d in design_config]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Please choose a design:', reply_markup=reply_markup)

async def start_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [[KeyboardButton("/start")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text('Press the "Start" button to begin.', reply_markup=reply_markup)

async def design_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    design_id = int(query.data.split('_')[1])
    user_choices[query.from_user.id] = {'design_id': design_id}

    keyboard = [
        [InlineKeyboardButton(f"{f['font_name']}", callback_data=f"font_{f['id']}") for f in font_config]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text('Please choose a font:', reply_markup=reply_markup)

async def font_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    font_id = int(query.data.split('_')[1])
    user_choices[query.from_user.id]['font_id'] = font_id

    await query.message.reply_text('Please enter the text you want to add to the design:')

async def generate_design_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if user_id not in user_choices or 'design_id' not in user_choices[user_id] or 'font_id' not in user_choices[user_id]:
        await update.message.reply_text('Please start with /start to choose design and font.')
        return

    design_id = user_choices[user_id]['design_id']
    font_id = user_choices[user_id]['font_id']
    text = update.message.text

    design = next(obj for obj in design_config if obj['id'] == design_id)
    font = next(obj for obj in font_config if obj['id'] == font_id)

    await update.message.reply_text("Processing your request...")

    fontFile = os.path.join(PATH, font['font_name'])
    imageFile = os.path.join(PATH, design['design_name'])

    _font = ImageFont.truetype(fontFile, font['font_size'])
    image = Image.open(imageFile)

    reshaped_text = reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)

    draw = ImageDraw.Draw(image)

    # Correctly applying offsets
    x_position = image.width / 2 + design['offset_x']
    y_position = image.height / 2 + design['offset_y']

    font_color = design.get('font_color')

    draw.text((x_position, y_position), bidi_text, tuple(font_color), font=_font, anchor="ms")

    output_path = os.path.join(PATH, "output.png")
    image.save(output_path)

    name = f'font_{font_id}_design_{design_id}_{text}.png'

    await update._bot.send_document(chat_id=update.message.chat_id, document=open(output_path, 'rb'), filename=name)

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("start_button", start_button))
app.add_handler(CallbackQueryHandler(design_choice, pattern="^design_"))
app.add_handler(CallbackQueryHandler(font_choice, pattern="^font_"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_design_handler))

app.run_polling()
