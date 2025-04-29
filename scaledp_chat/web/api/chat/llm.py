from langchain_openai import ChatOpenAI

from scaledp_chat.settings import settings

# Initialize the LangChain chat model
llm = ChatOpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.openai_base_url,
    model=settings.openai_model,
    streaming=True,
)
