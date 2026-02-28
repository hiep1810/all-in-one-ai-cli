# all-in-one-ai-cli

Scaffold for an all-in-one AI agent CLI.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
aio init
aio config show
aio config set model_provider llama_cpp
aio tui
aio ask "hello"
aio tool run fs.search --arg root=. --arg query=TODO
aio agent run "fix failing tests"
```

## Use llama.cpp locally (localhost)

Run llama.cpp server in OpenAI-compatible mode (example command may vary by your build):

```bash
./server -m /path/to/model.gguf --host 127.0.0.1 --port 8080
```

Then set `.aio/config.yaml`:

```yaml
model_provider: llama_cpp
model_name: your-model-name
model_base_url: http://127.0.0.1:8080
model_timeout_seconds: 60
tui_theme: neon
safety_level: confirm
```

Now `aio ask "hello"` will send requests to `POST /v1/chat/completions` on your local llama.cpp server.

## Commands

- `aio init`
- `aio config show`
- `aio config set <key> <value>`
- `aio tui`
- `aio ask "..."`
- `aio chat "..." --session default`
- `aio tool run <name> --arg k=v`
- `aio tool run <name> --arg k=v --approve-risky`
- `aio agent run "..." --approve-risky`
- `aio workflow run workflows/bugfix.yml`
- `aio replay <logfile>`

## Terminal UI

Run:

```bash
aio tui
```

Inside the UI, type commands and press Enter:

- `hello` (plain text = AI chat)
- `\\help`
- `\\agent fix failing tests`
- `\\tool fs.search root=. query=TODO`
- `\\tool shell.exec cmd='echo hi' --approve-risky`
- `\\history 20`
- `\\clear`
- `\\save`
- `\\copylast`
- `\\config show`
- `\\config set model_provider llama_cpp`
- `\\config set tui_theme matrix`
- `\\exit`

Tips:

- Press `Tab` to autocomplete `\\commands`.
- Plain chat uses provider streaming when available (`llama.cpp` OpenAI-compatible stream).
- In `confirm` safety mode, risky `\\tool`/`\\agent` commands prompt `Approve risky action? [y/N]`.

TUI themes:

- `neon` (default)
- `minimal`
- `matrix`

## Safety levels

Set in `.aio/config.yaml`:

- `off`: allow all tools
- `confirm`: placeholder for interactive approval flow
- `strict`: blocks shell tools

## Next steps

- Replace mock LLM client with real provider adapters.
- Add approval prompts for destructive operations.
- Expand workflow parser and execution engine.
