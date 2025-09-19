# ClickClick

A small Python auto-clicker that toggles with a configurable hotkey. By default it
starts and stops with **CTRL + ALT + P**, which avoids the built-in print shortcut
in browsers such as Opera.

## Setup

1. Create a virtual environment (optional but recommended).
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the script:

```bash
python main.py
```

- Press **CTRL + ALT + P** to begin or stop left-clicking.
- While the auto-clicker is running, it clicks roughly every 20-30 milliseconds with a random interval.
- Press **CTRL + ALT + Q** to exit the program, or press `Ctrl+C` in the terminal.
- Supply different hotkeys if the defaults conflict with your workflow (see below).

## Opera / custom hotkeys

Opera reserves **CTRL + P** for printing, so the application now uses
**CTRL + ALT + P** to toggle auto-clicking and **CTRL + ALT + Q** to exit. You can
use any combination of modifier keys plus letters, numbers, or function keys by
passing command-line arguments. Some examples:

```bash
# Toggle with F6 and exit with F7
python main.py --toggle f6 --exit f7

# Toggle with CTRL+SHIFT+S and disable the exit hotkey (use Ctrl+C to quit)
python main.py --toggle ctrl+shift+s --exit none
```

Use lowercase names for the keys and join them with `+`. Supported names include
`ctrl`, `alt`, `shift`, `cmd`, `win`, `option`, `tab`, `space`, `enter`, the
arrow keys, and the function keys `f1` through `f24` in addition to single
characters (`a`, `1`, etc.).

Press `Ctrl+C` in the terminal to exit the program entirely.
