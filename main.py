"""Autoclicker that can target custom hotkeys for Opera compatibility."""
from __future__ import annotations

import argparse
import random
import threading
from dataclasses import dataclass
from typing import Optional, Sequence, Set

from pynput import keyboard, mouse


CLICK_INTERVAL_MIN = 0.02
CLICK_INTERVAL_MAX = 0.03


class HotkeyParseError(ValueError):
    """Raised when a hotkey string cannot be interpreted."""


def _char_keycodes(character: str) -> Set[keyboard.KeyCode]:
    """Return the possible `KeyCode` objects for a printable character."""

    if len(character) != 1:
        raise HotkeyParseError(f"Expected a single character, got {character!r}")

    lower = keyboard.KeyCode.from_char(character.lower())
    upper = keyboard.KeyCode.from_char(character.upper())
    if lower == upper:
        return {lower}
    return {lower, upper}


def _alias_keys(name: str) -> Set[keyboard.Key | keyboard.KeyCode]:
    """Return the set of acceptable keys for an alias."""

    key_name = name.lower()
    alias_map = {
        "ctrl": {keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r},
        "control": {keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r},
        "alt": {keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r},
        "option": {keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r},
        "shift": {keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r},
        "cmd": {keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r},
        "win": {keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r},
        "super": {keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r},
        "meta": {keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r},
        "space": {keyboard.Key.space},
        "spacebar": {keyboard.Key.space},
        "enter": {keyboard.Key.enter},
        "return": {keyboard.Key.enter},
        "esc": {keyboard.Key.esc},
        "escape": {keyboard.Key.esc},
        "tab": {keyboard.Key.tab},
        "backspace": {keyboard.Key.backspace},
        "delete": {keyboard.Key.delete},
        "del": {keyboard.Key.delete},
        "home": {keyboard.Key.home},
        "end": {keyboard.Key.end},
        "pageup": {keyboard.Key.page_up},
        "page_up": {keyboard.Key.page_up},
        "pagedown": {keyboard.Key.page_down},
        "page_down": {keyboard.Key.page_down},
        "insert": {keyboard.Key.insert},
        "pause": {keyboard.Key.pause},
        "break": {keyboard.Key.pause},
        "capslock": {keyboard.Key.caps_lock},
        "caps_lock": {keyboard.Key.caps_lock},
        "scrolllock": {keyboard.Key.scroll_lock},
        "scroll_lock": {keyboard.Key.scroll_lock},
        "printscreen": {keyboard.Key.print_screen},
        "print_screen": {keyboard.Key.print_screen},
        "menu": {keyboard.Key.menu},
        "apps": {keyboard.Key.menu},
        "left": {keyboard.Key.left},
        "right": {keyboard.Key.right},
        "up": {keyboard.Key.up},
        "down": {keyboard.Key.down},
    }

    if key_name.startswith("f") and key_name[1:].isdigit():
        number = int(key_name[1:])
        if 1 <= number <= 24:
            try:
                key = getattr(keyboard.Key, f"f{number}")
            except AttributeError as exc:
                raise HotkeyParseError(f"Unknown key in hotkey: {name!r}") from exc
            return {key}
    if key_name in alias_map:
        return alias_map[key_name]
    if len(key_name) == 1:
        return _char_keycodes(key_name)
    raise HotkeyParseError(f"Unknown key in hotkey: {name!r}")


@dataclass(frozen=True)
class Hotkey:
    """A parsed hotkey combination."""

    requirements: Sequence[Set[keyboard.Key | keyboard.KeyCode]]
    display_parts: Sequence[str]

    @classmethod
    def parse(cls, combo: str) -> "Hotkey":
        parts = [part.strip() for part in combo.split("+") if part.strip()]
        if not parts:
            raise HotkeyParseError("Hotkey cannot be empty")

        requirements: list[Set[keyboard.Key | keyboard.KeyCode]] = []
        display_parts: list[str] = []
        for part in parts:
            keys = _alias_keys(part)
            requirements.append(keys)
            display_parts.append(part.upper())

        return cls(tuple(requirements), tuple(display_parts))

    def matches(self, pressed: Set[keyboard.Key | keyboard.KeyCode]) -> bool:
        return all(any(option in pressed for option in requirement) for requirement in self.requirements)

    def describe(self) -> str:
        return " + ".join(self.display_parts)


class AutoClicker:
    """Handle starting and stopping a randomized auto-click loop."""

    def __init__(self) -> None:
        self._mouse = mouse.Controller()
        self._stop_event = threading.Event()
        self._click_thread: Optional[threading.Thread] = None
        self._clicking = False

    def start(self) -> None:
        if self._clicking:
            return

        self._stop_event.clear()
        self._click_thread = threading.Thread(target=self._click_loop, daemon=True)
        self._click_thread.start()
        self._clicking = True

    def stop(self) -> None:
        if not self._clicking:
            return

        self._stop_event.set()
        if self._click_thread is not None:
            self._click_thread.join()
        self._click_thread = None

        self._clicking = False

    def _click_loop(self) -> None:
        while not self._stop_event.is_set():
            self._mouse.click(mouse.Button.left)
            delay = random.uniform(CLICK_INTERVAL_MIN, CLICK_INTERVAL_MAX)
            if self._stop_event.wait(delay):
                break

    @property
    def clicking(self) -> bool:
        return self._clicking


class HotkeyListener:
    """Listen for hotkey combinations to toggle or exit the clicker."""

    def __init__(self, clicker: AutoClicker, toggle: Hotkey, exit_hotkey: Hotkey | None) -> None:
        self._clicker = clicker
        self._toggle = toggle
        self._exit = exit_hotkey
        self._pressed_keys: Set[keyboard.Key | keyboard.KeyCode] = set()
        self._toggle_active = False
        self._exit_active = False

    def on_press(self, key: keyboard.Key | keyboard.KeyCode) -> bool | None:
        self._pressed_keys.add(key)

        if self._exit and self._exit.matches(self._pressed_keys):
            if not self._exit_active:
                self._exit_active = True
                self._clicker.stop()
                print("Exit hotkey pressed. Exiting.")
                return False

        if self._toggle.matches(self._pressed_keys) and not self._toggle_active:
            self._toggle_active = True
            if self._clicker.clicking:
                self._clicker.stop()
                print(
                    f"Auto-clicking stopped. Press {self._toggle.describe()} to start again."
                )
            else:
                self._clicker.start()
                print(f"Auto-clicking started. Press {self._toggle.describe()} to stop.")

        return None

    def on_release(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        self._pressed_keys.discard(key)
        if self._toggle_active and not self._toggle.matches(self._pressed_keys):
            self._toggle_active = False
        if self._exit_active and (not self._exit or not self._exit.matches(self._pressed_keys)):
            self._exit_active = False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Auto clicker with configurable hotkeys")
    parser.add_argument(
        "--toggle",
        default="ctrl+alt+p",
        help="Hotkey used to start or stop auto-clicking (default: ctrl+alt+p)",
    )
    parser.add_argument(
        "--exit",
        default="ctrl+alt+q",
        help="Hotkey used to exit the program. Use 'none' to disable (default: ctrl+alt+q)",
    )
    return parser


def _parse_required_hotkey(parser: argparse.ArgumentParser, value: str) -> Hotkey:
    try:
        return Hotkey.parse(value)
    except HotkeyParseError as exc:
        parser.error(str(exc))


def _parse_optional_hotkey(parser: argparse.ArgumentParser, value: str) -> Hotkey | None:
    if value.lower() == "none":
        return None
    return _parse_required_hotkey(parser, value)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    toggle_hotkey = _parse_required_hotkey(parser, args.toggle)
    exit_hotkey = _parse_optional_hotkey(parser, args.exit)

    clicker = AutoClicker()
    listener = HotkeyListener(clicker, toggle_hotkey, exit_hotkey)

    print(f"Press {toggle_hotkey.describe()} to start or stop auto-clicking.")
    if exit_hotkey:
        print(f"Press {exit_hotkey.describe()} to exit the program.")
    print("Press CTRL+C in the terminal to exit as well.")

    with keyboard.Listener(
        on_press=listener.on_press, on_release=listener.on_release
    ) as kb_listener:
        try:
            kb_listener.join()
        except (KeyboardInterrupt, keyboard.Listener.StopException):
            pass
        finally:
            clicker.stop()
            print("Exiting.")


if __name__ == "__main__":
    main()
