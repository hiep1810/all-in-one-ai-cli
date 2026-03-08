# Implementation Plan: Provider Expansion & Context Refactor

## 1. Goal Description

Before tackling the complex Iterative "Chain of Thought" Agent Loop (P0), we must first lay the architectural groundwork: 
1. **Rich Context Support**: Refactor the `LLMClient` interface to accept and maintain a full list of conversational message objects (`[{"role": "user", "content": "..."}]`) instead of a single string prompt.
2. **First-Class Providers**: Add robust integrations for `openai` and `anthropic` alongside our existing `llama_cpp` REST client, giving the agent access to top-tier reasoning capabilities capable of multi-step tool execution.

## 2. Approach

1.  **Refactor `LLMClient` Base Class**:
    *   Change `def complete(self, prompt: str) -> str:` to `def chat(self, messages: list[dict]) -> str:`
    *   Change `def stream_complete(self, prompt: str) -> Iterator[str]:` to `def stream_chat(self, messages: list[dict]) -> Iterator[str]:`
2.  **Add `OpenAIClient` and `AnthropicClient`**:
    *   Install `openai` and `anthropic` to the poetry/pip dependencies.
    *   Create adapters in `src/aio/llm/client.py` using their respective official Python SDKs.
    *   Update `src/aio/llm/router.py` to route based on `config.model_provider == "openai"`, etc.
3.  **Update TUI Chat Logic (`src/aio/tui/app.py`)**:
    *   Currently, the `_handle_chat_background` method calls `client.complete(prompt)`.
    *   We will update this to maintain the contextual chat history by passing the `self.command_history` (or a dedicated `chat_history`) converted into the generic `messages` format before firing the completion.
4.  **Update Configuration Setup**:
    *   Ensure `$OPENAI_API_KEY` and `$ANTHROPIC_API_KEY` can be picked up from the environment or configured via `\config set`.

## 3. Implementation Steps

1.  **Dependency Updates**: Run `pip install openai anthropic`.
2.  **`LLMClient` Updates (`src/aio/llm/client.py`)**:
    *   Modify the abstract signatures.
    *   Update `LlamaCppClient` so `_payload` directly forwards the new `messages` list instead of constructing it.
    *   Create `OpenAIClient` leveraging `from openai import OpenAI`.
    *   Create `AnthropicClient` leveraging `import anthropic`.
3.  **Router Update (`src/aio/llm/router.py`)**:
    *   Return instances matching `config.model_provider`.
4.  **TUI Hook Update (`src/aio/tui/app.py`)**:
    *   Add `self.conversation_messages = [{"role": "system", "content": "You are a helpful CLI AI assistant."}]` to `AIOConsole.__init__`.
    *   In `_handle_chat_background`, append `{"role": "user", "content": raw_prompt}`, call `client.stream_chat(self.conversation_messages)`, stream the result to the UI, and finally append the full AI response as `{"role": "assistant", "content": result_text}` to the history array.

## 4. Verification Plan

*   **Manual Verification**:
    1.  Test `llama_cpp` to ensure the refactor did not break the existing local execution.
    2.  Set `\config set model_provider openai`. Set `\config set model_name gpt-4o-mini`. Export `OPENAI_API_KEY`.
    3.  Type a message like "Hello, I am testing the new OpenAI integration".
    4.  Verify the stream streams properly into the TUI.
    5.  Type "What did I just say?". Verify the contextual history passes properly into the OpenAI client and it understands the immediate past!

## 5. User Review Required

Does this prioritization—building the OpenAI/Anthropic integrations and standardizing the message context schema **before** attempting the Iterative Tool-use loop—align with your roadmap expectations?
