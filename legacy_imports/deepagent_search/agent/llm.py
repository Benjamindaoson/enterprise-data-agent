import os

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

load_dotenv()


llm = init_chat_model(
    model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
    model_provider="openai",
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    api_key=os.getenv("DEEPSEEK_API_KEY"),
)


if __name__ == "__main__":
    response = llm.invoke("请用一句话回复：DeepSeek 连接测试成功。")
    print(response.content)