import os
from typing import List, Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=env_path)

# Define Schemas

class HumorStyleAlternatives(BaseModel):
    style: str = Field(description="Humor style/category name, e.g. Deadpan, Absurd, Sarcastic, Dry, Clever, Wordplay, Observational, Self-deprecating, Friendly tease, Dark.")
    examples: List[str] = Field(description="Exactly 3 alternative misinterpretation replies matching this humor style.")

class EvaluationResult(BaseModel):
    alternatives: List[HumorStyleAlternatives] = Field(description="List of 2 to 3 humor styles, each with 3 alternative responses demonstrating how to reply.")

class GeneratedPrompt(BaseModel):
    prompt: str = Field(description="The short everyday sentence, message, or scenario text.")
    type: str = Field(description="The category of the prompt (e.g. everyday, text_message, dating_app, workplace, family, headline, awkward_situation).")
    difficulty: str = Field(description="The difficulty level (simple, intermediate, expert).")
    context_hint: str = Field(description="A short context context description for the scenario (e.g. 'A text from your boss', 'During a dinner date', 'In a quiet elevator').")
    possible_interpretations: List[str] = Field(description="2-3 literal vs. alternative interpretations of the phrase (used as hints).")

# Initialize Gemini Client
def get_client() -> genai.Client:
    project_id = os.getenv("GCP_PROJECT_ID") or None
    location = os.getenv("GCP_LOCATION") or "us-central1"
    
    # Support specifying service account credential files relative to the src/ directory or project root
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if credentials_path:
        if not os.path.isabs(credentials_path):
            base_dir = os.path.dirname(__file__)
            src_relative_path = os.path.abspath(os.path.join(base_dir, credentials_path))
            project_relative_path = os.path.abspath(os.path.join(base_dir, "..", credentials_path))
            if os.path.exists(src_relative_path):
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = src_relative_path
            elif os.path.exists(project_relative_path):
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = project_relative_path
            else:
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath(credentials_path)
        else:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

    # Authenticate via Vertex AI. Make sure to authenticate local environment with gcloud or credentials file.
    return genai.Client(
        vertexai=True,
        project=project_id,
        location=location
    )

def generate_coaching_prompt(difficulty: str, category: str, history: List[str] = []) -> GeneratedPrompt:
    client = get_client()
    
    history_str = ", ".join([f"'{h}'" for h in history]) if history else "None"
    
    system_prompt = (
        "You are a master Humor & Misinterpretation Coach. Your goal is to generate one single, everyday, short sentence or dialogue scenario "
        "for the user to misinterpret. Do NOT include any jokes or solutions in the response, only the prompt, context hint, and possible interpretations.\n\n"
        "Rules for Difficulty:\n"
        "- simple: Obvious double meanings, simple verbs/nouns (e.g., 'I lost my keys', 'Can you hold this?', 'I'm seeing someone').\n"
        "- intermediate: Idioms, ambiguous wording, text messages (WhatsApp, DMs), or context-dependent phrases.\n"
        "- expert: Complex social/dating/workplace scenarios, hidden assumptions, office emails, family awkwardness, newspaper headlines, product names, or signs.\n\n"
        "Rules for Category:\n"
        f"- Generate a prompt matching the requested category: {category} (or random if 'any').\n"
        "Category definitions:\n"
        "- everyday: everyday conversations, simple statements.\n"
        "- text_message: short DMs, texts, chat messages.\n"
        "- dating_app: dating app profiles, messages, icebreakers.\n"
        "- workplace: emails, office talk, boss requests.\n"
        "- headline: newspaper titles, news snippets, public signs.\n"
        "- banter: witty remarks, playful teasing, verbal sparring.\n"
        "- scenario: awkward or interesting social scenario descriptions.\n"
        "Ensure the prompt is natural and something a real person would say or write.\n"
        f"History (do NOT repeat these prompts): {history_str}"
    )
    
    user_prompt = f"Generate a new prompt for difficulty: {difficulty}, category: {category}."
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.7,
            response_mime_type="application/json",
            response_schema=GeneratedPrompt,
        )
    )
    
    return response.parsed

def evaluate_user_response(prompt_text: str, context_hint: str, user_response: str, allowed_styles: List[str] = []) -> EvaluationResult:
    client = get_client()
    
    style_guideline = ""
    if allowed_styles:
        style_guideline = f"Make sure the alternative responses match some of these styles: {', '.join(allowed_styles)}."
    
    system_prompt = (
        "You are a master Humor & Misinterpretation Coach.\n"
        f"The user was prompted with: '{prompt_text}' (Context: '{context_hint}')\n"
        f"The user replied with: '{user_response}'\n\n"
        "Your task is to generate alternative misinterpretations for this prompt in 2 or 3 distinct humor styles "
        "(e.g., Deadpan, Absurd, Sarcastic, Dry, Clever, Wordplay, Observational, Self-deprecating, Friendly tease, Dark).\n"
        "For each selected humor style, generate exactly 3 funny example responses demonstrating how to misinterpret the prompt.\n"
        f"{style_guideline}\n"
        "Do not include any explanations of the mechanism or why they are funny, only generate the humor style and the 3 text examples."
    )
    
    user_prompt = f"Evaluate my response: '{user_response}'"
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.7,
            response_mime_type="application/json",
            response_schema=EvaluationResult,
        )
    )
    
    return response.parsed

# Daily Convo schemas & helpers

class TypoCheck(BaseModel):
    original: str = Field(description="The incorrect word, punctuation, or phrase as typed by the user.")
    corrected: str = Field(description="The corrected version.")
    explanation: str = Field(description="A brief explanation of why it was wrong (e.g. spelling, capitalization, subject-verb agreement).")

class WritingAlternative(BaseModel):
    phrase: str = Field(description="An alternative, more natural or advanced way to write their response.")
    reason: str = Field(description="Why this alternative is better (e.g. more natural, uses advanced vocabulary, better flow).")

class ConvoAnalysisResponse(BaseModel):
    typos: List[TypoCheck] = Field(description="List of typos or grammar mistakes identified in the user's message. Empty if none.")
    better_alternatives: List[WritingAlternative] = Field(description="2-3 suggestions for how the user could write their response more naturally or professionally.")
    reply: str = Field(description="A natural, engaging reply to the user's message to keep the conversation going.")

def generate_convo_starter() -> str:
    client = get_client()
    system_prompt = (
        "You are a friendly English conversation coach. Generate a single, warm conversation starter question "
        "about a common daily life topic (e.g., travel, hobbies, food, music, work, movies). Keep it to 1 or 2 sentences max. "
        "Do not include any other text, greetings, or markdown formatting."
    )
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Generate a conversation starter.",
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.8,
        )
    )
    return response.text.strip()

def analyze_convo_turn(chat_history: List[dict]) -> ConvoAnalysisResponse:
    client = get_client()
    
    # Format the conversation history
    history_str = ""
    for msg in chat_history[:-1]:
        role_label = "User" if msg["role"] == "user" else "Coach"
        history_str += f"{role_label}: {msg['content']}\n"
    
    latest_user_message = chat_history[-1]["content"] if chat_history else ""
    
    system_prompt = (
        "You are a friendly, helpful English conversation partner and coach.\n"
        "The user is talking with you to practice their conversational English, improve their vocabulary, and reduce typos.\n\n"
        "Your task is to analyze the user's latest response and:\n"
        "1. Identify any typos (spelling, capitalization, missing words, punctuation, basic grammar errors). Provide the original error, the correction, and a short explanation.\n"
        "2. Provide 2-3 better or more natural alternatives for how they could express the same thought, explaining why each is an improvement.\n"
        "3. Write a warm, engaging, conversational reply (1-2 sentences) to the user's message to keep the conversation going on the current topic.\n\n"
        "Be encouraging, concise, and helpful."
    )
    
    user_prompt = f"Conversation History:\n{history_str}\nUser's latest reply: '{latest_user_message}'\n\nPlease evaluate my reply, suggest alternatives, and give your next reply."
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.7,
            response_mime_type="application/json",
            response_schema=ConvoAnalysisResponse,
        )
    )
    return response.parsed

# Simplified sentence-based wit & banter coach

class HumorPhrase(BaseModel):
    text: str = Field(description="The short, punchy witty line.")
    technique: str = Field(description="The humor technique used (from the list of 20 techniques, e.g. Exaggeration, Sarcasm, Personification, etc.).")

class CustomLineAnalysisResponse(BaseModel):
    interpretations: List[str] = Field(description="2-3 different ways this sentence can be interpreted (literal meaning vs playful/banter angles).")
    funny_express: List[HumorPhrase] = Field(description="Up to 5 short, witty ways to say, ask, or express this same idea funny. Label each with its technique.")
    funny_replies: List[HumorPhrase] = Field(description="Up to 5 short, witty banter replies to this sentence. Label each with its technique.")
    better_versions: List[str] = Field(description="Up to 5 improved, more natural, or more sophisticated ways to write the original line.")

def generate_simple_sentence(history: List[str] = []) -> str:
    client = get_client()
    history_str = ", ".join([f"'{h}'" for h in history]) if history else "None"
    system_prompt = (
        "You are a master Wit and Banter Coach. Generate a single, short, extremely simple, day-to-day spoken sentence (just the sentence) "
        "that is very common in daily conversation (e.g., 'I am hungry', 'I lost my keys', 'I have a meeting', 'The weather is nice', 'I need some coffee', 'I am tired').\n"
        "Do NOT include any greetings, punctuation formatting, or context. Just the sentence.\n"
        f"History (do NOT repeat these sentences): {history_str}"
    )
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Generate a sentence.",
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.8,
        )
    )
    return response.text.strip().strip('"').strip("'")

def evaluate_sentence_humor(prompt_text: str, user_response: str) -> CustomLineAnalysisResponse:
    client = get_client()
    system_prompt = (
        "You are a master Wit, Banter, and humor technique coach.\n"
        f"The user gave the prompt/sentence: '{prompt_text}'\n"
        f"The user tried to reply with: '{user_response}'\n\n"
        "Your task is to analyze the prompt and generate:\n"
        "1. 2-3 different interpretations of the prompt (literal vs double meaning/playful/banter angles).\n"
        "2. Up to 5 (aim for exactly 5) short, punchy, and highly creative ways to SAY, ASK, or EXPRESS this same idea funny (funny_express).\n"
        "3. Up to 5 (aim for exactly 5) short, punchy, and highly creative banter/humor replies TO this prompt (funny_replies).\n"
        "4. Up to 5 (aim for exactly 5) better, more natural, or more sophisticated ways to express the original prompt (better_versions).\n\n"
        "For each funny expression and funny reply, choose a humor technique from this list of 20 techniques and assign it:\n"
        "- Misinterpretation\n"
        "- Literal Interpretation\n"
        "- Exaggeration\n"
        "- Understatement\n"
        "- Callback\n"
        "- Role Reversal\n"
        "- False Confidence\n"
        "- Fake Expertise\n"
        "- Comparison\n"
        "- Escalation\n"
        "- Wordplay\n"
        "- Deadpan\n"
        "- Sarcasm\n"
        "- Self-Deprecation\n"
        "- Observation\n"
        "- Incongruity\n"
        "- Personification\n"
        "- Benign Roast\n"
        "- Rule of Three\n"
        "- Misdirection\n\n"
        "CRITICAL RULE: Keep every single reply/expression extremely simple, short (under 4-7 words), and highly effective for real-life conversations. Avoid long setups, theatrical phrases, or complex vocabulary. The humor must be instant, conversational, simple, and punchy."
    )
    
    user_prompt = f"Analyze prompt: '{prompt_text}' and reply: '{user_response}'"
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.7,
            response_mime_type="application/json",
            response_schema=CustomLineAnalysisResponse,
        )
    )
    return response.parsed

def analyze_custom_line(line: str) -> CustomLineAnalysisResponse:
    return evaluate_sentence_humor(line, "")

class MessageClassification(BaseModel):
    is_question: bool = Field(description="True if the message is a question or a general conversational query/remark. False if it is a simple sentence/statement they want to practice humor/banter on.")
    direct_answer: str = Field(description="If is_question is True, provide the direct helpful answer. If False, leave this empty.")

def classify_and_answer_message(message: str) -> MessageClassification:
    client = get_client()
    system_prompt = (
        "You are an expert communication coach and classification assistant.\n"
        "Your job is to look at the user's message and classify whether it is a question/general remark, "
        "or a simple sentence/statement they want to practice humor/banter on.\n\n"
        "Rules:\n"
        "- If it is a question or a general conversational query (e.g. 'how to be funny', 'how are you?', 'tell me a joke', 'what is banter?'), "
        "set is_question to True, and provide a direct, helpful, and friendly answer (under 3-4 sentences) in direct_answer.\n"
        "- If it is just a simple sentence or statement (e.g. 'I am eating an apple', 'I need a new car', 'My phone is broken'), "
        "set is_question to False, and leave direct_answer empty."
    )
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=message,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.7,
            response_mime_type="application/json",
            response_schema=MessageClassification,
        )
    )
    return response.parsed


