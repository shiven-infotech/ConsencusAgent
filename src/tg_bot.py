import os
import telebot
from telebot import types
from dotenv import load_dotenv
from src.coach import (
    generate_simple_sentence,
    evaluate_sentence_humor,
    classify_and_answer_message,
    analyze_custom_line
)

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=env_path)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
IS_BOT_DUMMY = False
if not BOT_TOKEN:
    print("WARNING: TELEGRAM_BOT_TOKEN is not set in src/.env! Please add it.")
    BOT_TOKEN = "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ"  # Dummy token to allow decorators to load
    IS_BOT_DUMMY = True

# Initialize bot client
bot = telebot.TeleBot(BOT_TOKEN) if BOT_TOKEN else None

# In-memory user states
# Schema: { chat_id: { 'difficulty': str, 'category': str, 'prompt': str, 'context_hint': str, 'hints': List[str], 'history': List[str], 'step': str } }
user_states = {}

# Helper: Send mode selection
def send_mode_selection(chat_id):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("📚 Training Mode", callback_data="mode_training"),
        types.InlineKeyboardButton("📝 Test Mode", callback_data="mode_test")
    )
    
    welcome_text = (
        "🧠 <b>Welcome to your Wit, Banter & English Coach!</b>\n\n"
        "Please choose a mode to start:\n\n"
        "📚 <b>Training Mode</b>: Learn humor passively. I will show you a random sentence and immediately display witty replies and better phrasings.\n\n"
        "📝 <b>Test Mode</b>: Practice active wit. I will give you a sentence, wait for your reply, and then evaluate it."
    )
    bot.send_message(chat_id, welcome_text, parse_mode="HTML", reply_markup=keyboard)

# Helper: Deliver Training slide
def deliver_training_slide(chat_id):
    state = user_states.setdefault(chat_id, {})
    bot.send_chat_action(chat_id, 'typing')
    
    history = state.setdefault('history', [])
    try:
        sentence = generate_simple_sentence(history)
        state['history'].append(sentence)
        if len(state['history']) > 30:
            state['history'].pop(0)
            
        # Immediately run analysis
        res = analyze_custom_line(sentence)
        
        # Format Interpretations
        interp_text = f"💬 <b>TRAINING: \"{sentence}\"</b>\n\n💡 <b>Interpretations:</b>\n"
        for interp in res.interpretations:
            interp_text += f"• {interp}\n"
            
        # Format Funny Sayings
        express_text = "\n🗣️ <b>Witty Ways to Say It:</b>\n"
        for i, item in enumerate(res.funny_express, 1):
            express_text += f"{i}. <i>\"{item.text}\"</i> ({item.technique})\n"
            
        # Format Funny Replies
        replies_text = "\n🔥 <b>Witty Replies:</b>\n"
        for i, item in enumerate(res.funny_replies, 1):
            replies_text += f"{i}. <i>\"{item.text}\"</i> ({item.technique})\n"
            
        # Format Better versions
        better_text = "\n💡 <b>Better Ways to Say It:</b>\n"
        for alt in res.better_versions:
            better_text += f"• <i>\"{alt}\"</i>\n"

        full_response = f"{interp_text}{express_text}{replies_text}{better_text}"
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(
            types.InlineKeyboardButton("Next Prompt ⚡", callback_data="action_next"),
            types.InlineKeyboardButton("Change Mode ⚙️", callback_data="action_reset")
        )
        
        bot.send_message(chat_id, full_response, parse_mode="HTML", reply_markup=keyboard)
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error in Training: {str(e)}\n\nTry sending /start to reset.")

# Helper: Deliver Test challenge
def deliver_test_challenge(chat_id):
    state = user_states.setdefault(chat_id, {})
    bot.send_chat_action(chat_id, 'typing')
    
    history = state.setdefault('history', [])
    try:
        sentence = generate_simple_sentence(history)
        state['prompt'] = sentence
        state['step'] = 'waiting_for_reply'
        state['history'].append(sentence)
        if len(state['history']) > 30:
            state['history'].pop(0)
            
        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(
            types.InlineKeyboardButton("Skip Challenge ⏭️", callback_data="action_next"),
            types.InlineKeyboardButton("Change Mode ⚙️", callback_data="action_reset")
        )
        
        msg_text = (
            f"📝 <b>TEST CHALLENGE</b>\n"
            f"💬 <b>\"{sentence}\"</b>\n\n"
            "👉 Send a funny misinterpretation or banter reply to this line!"
        )
        bot.send_message(chat_id, msg_text, parse_mode="HTML", reply_markup=keyboard)
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error in Test Challenge: {str(e)}\n\nTry sending /start to reset.")

# Commands
@bot.message_handler(commands=['start'])
def command_start(message):
    chat_id = message.chat.id
    user_states[chat_id] = {
        'mode': 'training',
        'prompt': '',
        'history': [],
        'step': ''
    }
    send_mode_selection(chat_id)

@bot.message_handler(commands=['humor', 'h', 'banter', 'bn', 'betterversion', 'bt'])
def command_analyze(message):
    chat_id = message.chat.id
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(chat_id, "Usage: /h <your sentence> or /bn <your sentence> or /bt <your sentence>")
        return
    line = parts[1]
    process_custom_line_analysis(chat_id, line)

# Helper: Custom Line Analysis Processor
def process_custom_line_analysis(chat_id, line):
    bot.send_chat_action(chat_id, 'typing')
    try:
        res = analyze_custom_line(line)
        
        # Format Interpretations
        interp_text = f"💡 <b>Interpretations for: \"{line}\"</b>\n"
        for interp in res.interpretations:
            interp_text += f"• {interp}\n"
            
        # Format Funny Sayings
        express_text = "\n🗣️ <b>Witty Ways to Say It:</b>\n"
        for i, item in enumerate(res.funny_express, 1):
            express_text += f"{i}. <i>\"{item.text}\"</i> ({item.technique})\n"
            
        # Format Funny Replies
        replies_text = "\n🔥 <b>Witty Replies:</b>\n"
        for i, item in enumerate(res.funny_replies, 1):
            replies_text += f"{i}. <i>\"{item.text}\"</i> ({item.technique})\n"
            
        # Format Better versions
        better_text = "\n💡 <b>Better Ways to Say It:</b>\n"
        for alt in res.better_versions:
            better_text += f"• <i>\"{alt}\"</i>\n"

        full_response = f"{interp_text}{express_text}{replies_text}{better_text}"
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(types.InlineKeyboardButton("Next ⚡", callback_data="action_next"))
        
        bot.send_message(chat_id, full_response, parse_mode="HTML", reply_markup=keyboard)
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Analysis failed: {str(e)}")

# Helper: Safe Callback Query Answer
def safe_answer_callback(call_id, text=None, show_alert=False):
    try:
        bot.answer_callback_query(call_id, text=text, show_alert=show_alert)
    except Exception:
        pass

# Callbacks
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    data = call.data
    state = user_states.setdefault(chat_id, {})
    
    if data == "mode_training":
        state['mode'] = 'training'
        safe_answer_callback(call.id, "Mode set: Training")
        deliver_training_slide(chat_id)
    elif data == "mode_test":
        state['mode'] = 'test'
        safe_answer_callback(call.id, "Mode set: Test")
        deliver_test_challenge(chat_id)
    elif data == "action_next":
        safe_answer_callback(call.id, "Loading next...")
        if state.get('mode') == 'test':
            deliver_test_challenge(chat_id)
        else:
            deliver_training_slide(chat_id)
    elif data == "action_reset":
        safe_answer_callback(call.id, "Resetting mode...")
        send_mode_selection(chat_id)

# Message handler (for user replies and questions)
@bot.message_handler(func=lambda msg: not msg.text.startswith('/'))
def handle_text_messages(message):
    chat_id = message.chat.id
    state = user_states.setdefault(chat_id, {})

    # If the user is currently replying to a practice prompt sentence
    if state.get('step') == 'waiting_for_reply' and state.get('prompt'):
        user_reply = message.text
        prompt_text = state.get('prompt')
        bot.send_chat_action(chat_id, 'typing')

        try:
            eval_result = evaluate_sentence_humor(prompt_text, user_reply)

            # Format Interpretations
            interp_text = "💡 <b>Interpretations:</b>\n"
            for interp in eval_result.interpretations:
                interp_text += f"• {interp}\n"
                
            # Format Funny Sayings
            express_text = "\n🗣️ <b>Witty Ways to Say It:</b>\n"
            for i, item in enumerate(eval_result.funny_express, 1):
                express_text += f"{i}. <i>\"{item.text}\"</i> ({item.technique})\n"
                
            # Format Funny Replies
            replies_text = "\n🔥 <b>Witty Replies:</b>\n"
            for i, item in enumerate(eval_result.funny_replies, 1):
                replies_text += f"{i}. <i>\"{item.text}\"</i> ({item.technique})\n"
                
            # Format Better versions
            better_text = "\n💡 <b>Better Ways to Say It:</b>\n"
            for alt in eval_result.better_versions:
                better_text += f"• <i>\"{alt}\"</i>\n"

            full_response = f"{interp_text}{express_text}{replies_text}{better_text}"

            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(
                types.InlineKeyboardButton("Next Challenge ⚡", callback_data="action_next"),
                types.InlineKeyboardButton("Change Mode ⚙️", callback_data="action_reset")
            )

            bot.send_message(chat_id, full_response, parse_mode="HTML", reply_markup=keyboard)
            state['step'] = 'completed'
        except Exception as e:
            bot.send_message(chat_id, f"⚠️ Evaluation failed: {str(e)}\n\nPlease try again.")
        return

    # If they send any other statement or ask a question
    bot.send_chat_action(chat_id, 'typing')
    try:
        classification = classify_and_answer_message(message.text)
        
        if classification.is_question:
            # Answer question directly
            bot.send_message(chat_id, classification.direct_answer)
        else:
            # Treat as custom line input and immediately output the analysis
            process_custom_line_analysis(chat_id, message.text)
            
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Processing failed: {str(e)}")

if __name__ == "__main__":
    if IS_BOT_DUMMY or not BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN environment variable not set. Exiting.")
    else:
        print("Bot Antigravity is polling... Press Ctrl+C to stop.")
        bot.infinity_polling()
