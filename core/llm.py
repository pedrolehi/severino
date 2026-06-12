from langchain_openai import ChatOpenAI
from tools import tools_list
from core.config import OPENAI_API_KEY


def get_llm():
    return ChatOpenAI(model="gpt-4o-mini", api_key=OPENAI_API_KEY, temperature=0.7)


llm = get_llm()

llm_with_tools = llm.bind_tools(tools_list)
