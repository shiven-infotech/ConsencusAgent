import os
import telebot
from telebot import types
from dotenv import load_dotenv
from coach import generate_coaching_prompt, evaluate_user_response

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=env_path)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    print("WARNING: TELEGRAM_BOT_TOKEN is not set in src/.env! Please add it.")

# Initialize bot client
bot = telebot.TeleBot(BOT_TOKEN) if BOT_TOKEN else None

# In-memory user states
# Schema: { chat_id: { 'difficulty': str, 'category': str, 'prompt': str, 'context_hint': str, 'hints': List[str], 'history': List[str], 'step': str } }
user_states = {}

CAT_LABELS = {
    'everyday': 'Everyday Talk',
    'text_message': 'Text Message',
    'dating_app': 'Dating App',
    'workplace': 'Workplace',
    'headline': 'News Headline'
}

DIFF_LABELS = {
    'simple': '🟢 Simple',
    'intermediate': '🟡 Intermediate',
    'expert': '🔴 Expert'
}

# Helper: Start difficulty selection
def send_difficulty_selection(chat_id):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("🟢 Simple", callback_data="diff_simple"),
        types.InlineKeyboardButton("🟡 Intermediate", callback_data="diff_intermediate")
    )
    keyboard.row(
        types.InlineKeyboardButton("🔴 Expert", callback_data="diff_expert")
    )
    
    welcome_text = (
        "🧠 <b>Welcome to the Humor & Misinterpretation Coach!</b>\n\n"
        "I am Coach Antigravity. I'll help you improve your conversational wit and ability to create funny misinterpretations in real conversations.\n\n"
        "To get started, choose your training difficulty level:"
    )
    bot.send_message(chat_id, welcome_text, parse_mode="HTML", reply_markup=keyboard)

# Helper: Start category selection
def send_category_selection(chat_id):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("💬 Everyday Talk", callback_data="cat_everyday"),
        types.InlineKeyboardButton("📱 Text Message", callback_data="cat_text_message")
    )
    keyboard.row(
        types.InlineKeyboardButton("🔥 Dating App", callback_data="cat_dating_app"),
        types.InlineKeyboardButton("💼 Workplace", callback_data="cat_workplace")
    )
    keyboard.row(
        types.InlineKeyboardButton("📰 News Headline", callback_data="cat_headline")
    )
    
    bot.send_message(
        chat_id, 
        "Great! Now select a scenario category to practice:", 
        reply_markup=keyboard
    )

# Helper: Deliver prompt
def deliver_new_prompt(chat_id):
    state = user_states.get(chat_id)
    if not state:
        send_difficulty_selection(chat_id)
        return

    bot.send_chat_action(chat_id, 'typing')
    
    difficulty = state.get('difficulty', 'simple')
    category = state.get('category', 'everyday')
    history = state.setdefault('history', [])

    try:
        # Call Gemini prompt generation
        prompt_data = generate_coaching_prompt(difficulty, category, history)
        
        # Save to state
        state['prompt'] = prompt_data.prompt
        state['context_hint'] = prompt_data.context_hint
        state['hints'] = prompt_data.possible_interpretations
        state['step'] = 'waiting_for_reply'
        state['history'].append(prompt_data.prompt)

        # Form inline action buttons
        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(types.InlineKeyboardButton("💡 Show Hints", callback_data="show_hints"))

        # Send Prompt Box
        prompt_header = CAT_LABELS.get(category, category.replace('_', ' ').capitalize())
        prompt_text = (
            f"🔔 <b>NEW SCENARIO ({prompt_header})</b>\n"
            f"📍 <i>Context: {prompt_data.context_hint}</i>\n\n"
            f"💬 <b>\"{prompt_data.prompt}\"</b>\n\n"
            f"👉 Send your funny misinterpretation as a text message reply!"
        )
        bot.send_message(chat_id, prompt_text, parse_mode="HTML", reply_markup=keyboard)

    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error generating prompt: {str(e)}\n\nTry sending /start to reset.")

# Commands
@bot.message_handler(commands=['start'])
def command_start(message):
    chat_id = message.chat.id
    user_states[chat_id] = {
        'difficulty': 'simple',
        'category': 'everyday',
        'prompt': '',
        'context_hint': '',
        'hints': [],
        'history': [],
        'step': 'difficulty'
    }
    send_difficulty_selection(chat_id)

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

    if data.startswith("diff_"):
        diff = data.split("_")[1]
        state['difficulty'] = diff
        safe_answer_callback(call.id, f"Difficulty set: {DIFF_LABELS.get(diff, diff)}")
        send_category_selection(chat_id)

    elif data.startswith("cat_"):
        cat = data.split("_")[1]
        state['category'] = cat
        state['history'] = []
        safe_answer_callback(call.id, f"Category set: {CAT_LABELS.get(cat, cat)}")
        deliver_new_prompt(chat_id)

    elif data == "show_hints":
        hints = state.get('hints', [])
        if hints:
            alert_text = "💡 Hints (Literal vs Double Meaning):\n\n" + "\n\n".join(f"• {h}" for h in hints)
            safe_answer_callback(call.id, text=alert_text, show_alert=True)
        else:
            safe_answer_callback(call.id, text="No hints available for this round.")

    elif data == "action_next":
        safe_answer_callback(call.id, "Loading next scenario...")
        deliver_new_prompt(chat_id)

    elif data == "action_reset":
        safe_answer_callback(call.id, "Resetting settings...")
        send_difficulty_selection(chat_id)

# Message handler (for user replies)
@bot.message_handler(func=lambda msg: True)
def handle_text_messages(message):
    chat_id = message.chat.id
    state = user_states.get(chat_id)

    if not state or state.get('step') != 'waiting_for_reply':
        # If user sends a message outside the game flow, greet them
        send_difficulty_selection(chat_id)
        return

    user_reply = message.text
    prompt_text = state.get('prompt')
    context_hint = state.get('context_hint')

    bot.send_chat_action(chat_id, 'typing')

    try:
        # Call Gemini evaluation
        eval_result = evaluate_user_response(
            prompt_text=prompt_text,
            context_hint=context_hint,
            user_response=user_reply
        )

        # Format alternative jokes
        eval_text = "💡 <b>Alternative Angles</b>\n\n"
        
        for alt in eval_result.alternatives:
            eval_text += f"⚡ <b>{alt.style}</b>\n"
            for i, example in enumerate(alt.examples, 1):
                eval_text += f"{i}. <i>\"{example}\"</i>\n"
            eval_text += "\n"

        # Form inline action buttons
        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(
            types.InlineKeyboardButton("Next Scenario ⚡", callback_data="action_next"),
            types.InlineKeyboardButton("Change Settings ⚙️", callback_data="action_reset")
        )

        # Send evaluation
        bot.send_message(chat_id, eval_text, parse_mode="HTML", reply_markup=keyboard)
        state['step'] = 'completed'

    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Evaluation failed: {str(e)}\n\nPlease try again.")

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN environment variable not set. Exiting.")
    else:
        print("Bot Antigravity is polling... Press Ctrl+C to stop.")
        bot.infinity_polling()
