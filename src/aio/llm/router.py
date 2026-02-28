from aio.config.schema import Config
from aio.llm.client import LLMClient, LlamaCppClient


def get_client(config: Config) -> LLMClient:
    if config.model_provider == "llama_cpp":
        return LlamaCppClient(config)
    return LLMClient(config)
