# Implementation Plan: Extensible Local AI API Auto-Config (`\connect`)

## 1. Goal Description

Create a frictionless way to switch the All-In-One AI CLI brain to a local model server. Users can type `\connect <target>` to automatically route the CLI to local AI servers (llama.cpp, LM Studio, Ollama). Crucially, the presets for these endpoints will be stored in a separate, easily editable configuration file, allowing users to define their own custom targets (e.g., `vllm`, `private_gpu`).

## 2. Approach

1.  **External Connections Config**: 
    We will create a `connections.json` file inside the `.aio/` directory. This file will map user-friendly target names to their respective `url`, `provider`, and `default_model`.
2.  **Schema and Defaults**:
    Upon startup, if `.aio/connections.json` does not exist, the app will auto-generate it with standard intelligent defaults:
    *   `llama.cpp` -> `http://127.0.0.1:8080`
    *   `lmstudio` -> `http://127.0.0.1:1234`
    *   `ollama` -> `http://127.0.0.1:11434`
3.  **Command Execution**:
    We will implement a TUI slash command: `\connect <target> [model_name]`. When called, it seamlessly reads the active `connections.json`, finds the target, updates the active CLI configuration object, saves the object, and confirms the connection in the chat log.

## 3. Implementation Steps

1.  **Create Connections Manager (`src/aio/config/connections.py`)**:
    *   Create a module dedicated to loading, saving, and querying `.aio/connections.json`.
    *   Add a function `load_connection_presets() -> dict` that returns the parsed JSON strings.
    *   If the file is missing, it automatically creates it, populated with the `llama.cpp`, `lmstudio`, and `ollama` defaults.
2.  **Update Config Parsing Tooling (`app.py` & `cli.py`)**:
    *   Since these values modify `config.json`, the new target simply invokes the existing `save_config` mutation flow.
3.  **Add `\connect` Command Parsing (`src/aio/tui/app.py`)**:
    *   Inside `on_input_submitted`, add a branch for `raw.startswith("\\connect")`.
    *   Call `load_connection_presets()`.
    *   Extract the target preset (e.g., `ollama`). Accept an optional second parameter for a custom model name (e.g., `\connect ollama llama3.1:8b`).
4.  **Apply and Save Configuration**:
    *   If the target exists in the connection JSON, update the active `self.config.model_provider`, `self.config.model_base_url`, and `self.config.model_name`.
    *   Call `save_config(self.config)` to persist the change for future CLI sessions.
    *   Output a clear success message to the chat log: `[green]Successfully connected to Local AI (ollama) at http://127.0.0.1:11434[/green]`
5.  **Graceful Error Handling / Info**:
    *   If the user types `\connect` without arguments, or matches no known preset in their JSON file, dump a help message listing the available keys currently in their `connections.json`.
6.  **AutoComplete Integration**:
    *   In `src/aio/tui/app.py`, dynamically generate the `builtins` list for the auto-suggestions floating panel based on the keys available in the `load_connection_presets()` dictionary, generating suggestions like `\connect ollama`.

## 4. Verification Plan

*   **Manual Verification**:
    1.  Start the TUI. Observe that `.aio/connections.json` is generated.
    2.  Type `\co`. The visual dropdown should auto-suggest commands like `\connect ollama` pulled dynamically from the JSON file!
    3.  Type `\connect lmstudio` and hit Enter. The chat log should print a success message.
    4.  Manually open `.aio/connections.json` within the editor and add a new entry: `"mygpu": {"url": "http://192.168.1.10:8000", "provider": "llama_cpp", "default_model": "mistral"}`.
    5.  Return to the TUI input and type `\connect mygpu`. It should recognize the newly added entry instantly!

## 5. User Review Required

Is routing the mappings through an external `.aio/connections.json` file exactly what you had in mind for making it easily editable?
