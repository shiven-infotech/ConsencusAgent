import os
from typing import List, Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=env_path)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Set api key in environment for LangChain
if GOOGLE_API_KEY:
    os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

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

# Initialize Gemini Model
def get_model():
    if not os.environ.get("GOOGLE_API_KEY"):
        raise ValueError("GOOGLE_API_KEY environment variable is not set. Please set it in src/.env.")
    # gemini-2.5-flash is fast and highly capable for formatting outputs
    return ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.7)

def generate_coaching_prompt(difficulty: str, category: str, history: List[str] = []) -> GeneratedPrompt:
    model = get_model()
    structured_llm = model.with_structured_output(GeneratedPrompt)
    
    system_prompt = (
        "You are a master Humor & Misinterpretation Coach. Your goal is to generate one single, everyday, short sentence or dialogue scenario "
        "for the user to misinterpret. Do NOT include any jokes or solutions in the response, only the prompt, context hint, and possible interpretations.\n\n"
        "Rules for Difficulty:\n"
        "- simple: Obvious double meanings, simple verbs/nouns (e.g., 'I lost my keys', 'Can you hold this?', 'I'm seeing someone').\n"
        "- intermediate: Idioms, ambiguous wording, text messages (WhatsApp, DMs), or context-dependent phrases.\n"
        "- expert: Complex social/dating/workplace scenarios, hidden assumptions, office emails, family awkwardness, newspaper headlines, product names, or signs.\n\n"
        "Rules for Category:\n"
        "- Generate a prompt matching the requested category: {category} (or random if 'any').\n"
        "Ensure the prompt is natural and something a real person would say or write.\n"
        "History (do NOT repeat these prompts): {history_list}"
    )
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Generate a new prompt for difficulty: {difficulty}, category: {category}.")
    ])
    
    chain = prompt_template | structured_llm
    
    history_str = ", ".join([f"'{h}'" for h in history]) if history else "None"
    
    result = chain.invoke({
        "difficulty": difficulty,
        "category": category,
        "history_list": history_str
    })
    
    return result

def evaluate_user_response(prompt_text: str, context_hint: str, user_response: str, allowed_styles: List[str] = []) -> EvaluationResult:
    model = get_model()
    structured_llm = model.with_structured_output(EvaluationResult)
    
    style_guideline = ""
    if allowed_styles:
        style_guideline = f"Make sure the alternative responses match some of these styles: {', '.join(allowed_styles)}."
    
    system_prompt = (
        "You are a master Humor & Misinterpretation Coach.\n"
        "The user was prompted with: '{prompt_text}' (Context: '{context_hint}')\n"
        "The user replied with: '{user_response}'\n\n"
        "Your task is to generate alternative misinterpretations for this prompt in 2 or 3 distinct humor styles "
        "(e.g., Deadpan, Absurd, Sarcastic, Dry, Clever, Wordplay, Observational, Self-deprecating, Friendly tease, Dark).\n"
        "For each selected humor style, generate exactly 3 funny example responses demonstrating how to misinterpret the prompt.\n"
        "{style_guideline}\n"
        "Do not include any explanations of the mechanism or why they are funny, only generate the humor style and the 3 text examples."
    )
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Evaluate my response: '{user_response}'")
    ])
    
    chain = prompt_template | structured_llm
    
    result = chain.invoke({
        "prompt_text": prompt_text,
        "context_hint": context_hint,
        "user_response": user_response,
        "style_guideline": style_guideline
    })
    
    return result
