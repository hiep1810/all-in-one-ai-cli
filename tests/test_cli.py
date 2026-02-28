from aio.cli import main


def test_init_command():
    assert main(["init"]) == 0
