from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList

class CommandPalette(ModalScreen[str]):
    CSS = """
    CommandPalette {
        align: center middle;
    }
    #palette-container {
        width: 60%;
        height: 60%;
        background: $surface;
        border: thick $accent;
    }
    #palette-input {
        dock: top;
    }
    """

    def __init__(self, tools: list[str]):
        super().__init__()
        self.tools = tools
        self.options = [
            r"\help", r"\clear", r"\history", r"\tools",
            r"\md open ", r"\md stash", r"\md clear",
        ] + [f"\\tool {t} " for t in tools] + [r"\agent ", r"\chat "]

    def compose(self) -> ComposeResult:
        with Vertical(id="palette-container"):
            yield Input(placeholder="Search commands...", id="palette-input")
            yield OptionList(*self.options, id="palette-list")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        search = event.value.lower()
        olist = self.query_one(OptionList)
        olist.clear_options()
        filtered = [opt for opt in self.options if search in opt.lower()]
        olist.add_options(filtered)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(str(event.option.prompt))

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss("")
        elif event.key == "down":
            olist = self.query_one(OptionList)
            if not olist.has_focus:
                olist.focus()
                
