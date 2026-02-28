import io
from contextlib import redirect_stdout
from unittest.mock import patch

from aio.cli import main


def test_init_command():
    assert main(["init"]) == 0


class _FakeClient:
    def complete(self, prompt: str) -> str:
        return f"done:{prompt}"

    def stream_complete(self, prompt: str):
        yield "part1-"
        yield f"part2:{prompt}"


@patch("aio.cli.get_client", return_value=_FakeClient())
def test_ask_command_non_stream(mock_get_client):
    out = io.StringIO()
    with redirect_stdout(out):
        code = main(["ask", "hello"])
    assert code == 0
    assert "done:hello" in out.getvalue()
    assert mock_get_client.called


@patch("aio.cli.get_client", return_value=_FakeClient())
def test_ask_command_stream(mock_get_client):
    out = io.StringIO()
    with redirect_stdout(out):
        code = main(["ask", "hello", "--stream"])
    assert code == 0
    assert "part1-part2:hello" in out.getvalue()
    assert mock_get_client.called
