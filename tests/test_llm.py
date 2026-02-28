from aio.config.schema import Config
from aio.llm.client import LLMClient, LlamaCppClient
from aio.llm.router import get_client


def test_router_returns_mock_client_by_default():
    client = get_client(Config())
    assert isinstance(client, LLMClient)
    assert not isinstance(client, LlamaCppClient)


def test_router_returns_llama_cpp_client():
    client = get_client(Config(model_provider="llama_cpp"))
    assert isinstance(client, LlamaCppClient)
