from aio.config.schema import Config
from aio.llm.client import LLMClient, LlamaCppClient, parse_stream_data
from aio.llm.router import get_client


def test_router_returns_mock_client_by_default():
    client = get_client(Config())
    assert isinstance(client, LLMClient)
    assert not isinstance(client, LlamaCppClient)


def test_router_returns_llama_cpp_client():
    client = get_client(Config(model_provider="llama_cpp"))
    assert isinstance(client, LlamaCppClient)


def test_parse_stream_data_done():
    done, chunk = parse_stream_data("[DONE]")
    assert done
    assert chunk == ""


def test_parse_stream_data_delta_content():
    done, chunk = parse_stream_data('{"choices":[{"delta":{"content":"hi"}}]}')
    assert not done
    assert chunk == "hi"


def test_mock_stream_complete_falls_back_to_complete():
    client = LLMClient(Config())
    chunks = list(client.stream_complete("hello"))
    assert len(chunks) == 1
    assert "hello" in chunks[0]
