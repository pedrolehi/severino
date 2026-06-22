from langchain_openai import ChatOpenAI
from core.config import OPENAI_API_KEY


def get_llm():
    return ChatOpenAI(model="gpt-4o-mini", api_key=OPENAI_API_KEY, temperature=0.7)


llm = get_llm()
