"""Autoclicker that can target custom hotkeys for Opera compatibility."""

import argparse
import random
import threading

from pynput import keyboard, mouse


CLICK_INTERVAL_MIN = 0.02
CLICK_INTERVAL_MAX = 0.03


class HotkeyParseError(ValueError):
    """Raised when a hotkey string cannot be interpreted."""


def _char_keycodes(character):
    """Return the possible `KeyCode` objects for a printable character."""

    if len(character) != 1:
        raise HotkeyParseError("Expected a single character, got {0!r}".format(character))

    lower = keyboard.KeyCode.from_char(character.lower())
    upper = keyboard.KeyCode.from_char(character.upper())
    if lower == upper:
        return {lower}
    return {lower, upper}


def _alias_keys(name):
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
                key = getattr(keyboard.Key, "f{0}".format(number))
            except AttributeError:
                raise HotkeyParseError("Unknown key in hotkey: {0!r}".format(name))
            return {key}
    if key_name in alias_map:
        return alias_map[key_name]
    if len(key_name) == 1:
        return _char_keycodes(key_name)
    raise HotkeyParseError("Unknown key in hotkey: {0!r}".format(name))


class Hotkey(object):
    """A parsed hotkey combination."""

    def __init__(self, requirements, display_parts):
        self.requirements = tuple(requirements)
        self.display_parts = tuple(display_parts)

    @classmethod
    def parse(cls, combo):
        parts = [part.strip() for part in combo.split("+") if part.strip()]
        if not parts:
            raise HotkeyParseError("Hotkey cannot be empty")

        requirements = []
        display_parts = []
        for part in parts:
            keys = _alias_keys(part)
            requirements.append(keys)
            display_parts.append(part.upper())

        return cls(tuple(requirements), tuple(display_parts))

    def matches(self, pressed):
        for requirement in self.requirements:
            matched = False
            for option in requirement:
                if option in pressed:
                    matched = True
                    break
            if not matched:
                return False
        return True

    def describe(self):
        return " + ".join(self.display_parts)


class AutoClicker(object):
    """Handle starting and stopping a randomized auto-click loop."""

    def __init__(self):
        self._mouse = mouse.Controller()
        self._stop_event = threading.Event()
        self._click_thread = None
        self._clicking = False

    def start(self):
        if self._clicking:
            return

        self._stop_event.clear()
        self._click_thread = threading.Thread(target=self._click_loop, daemon=True)
        self._click_thread.start()
        self._clicking = True

    def stop(self):
        if not self._clicking:
            return

        self._stop_event.set()
        if self._click_thread is not None:
            self._click_thread.join()
        self._click_thread = None

        self._clicking = False

    def _click_loop(self):
        while not self._stop_event.is_set():
            self._mouse.click(mouse.Button.left)
            delay = random.uniform(CLICK_INTERVAL_MIN, CLICK_INTERVAL_MAX)
            if self._stop_event.wait(delay):
                break

    @property
    def clicking(self):
        return self._clicking


class HotkeyListener(object):
    """Listen for hotkey combinations to toggle or exit the clicker."""

    def __init__(self, clicker, toggle, exit_hotkey):
        self._clicker = clicker
        self._toggle = toggle
        self._exit = exit_hotkey
        self._pressed_keys = set()
        self._toggle_active = False
        self._exit_active = False

    def on_press(self, key):
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
                    "Auto-clicking stopped. Press {0} to start again.".format(
                        self._toggle.describe()
                    )
                )
            else:
                self._clicker.start()
                print(
                    "Auto-clicking started. Press {0} to stop.".format(
                        self._toggle.describe()
                    )
                )

        return None

    def on_release(self, key):
        self._pressed_keys.discard(key)
        if self._toggle_active and not self._toggle.matches(self._pressed_keys):
            self._toggle_active = False
        if self._exit_active and (not self._exit or not self._exit.matches(self._pressed_keys)):
            self._exit_active = False


def build_parser():
    parser = argparse.ArgumentParser(description="Auto clicker with configurable hotkeys")
    parser.add_argument(
        "--toggle",
        default="m",
        help="Hotkey used to start or stop auto-clicking (default: m)",
    )
    parser.add_argument(
        "--exit",
        default="ctrl+alt+q",
        help="Hotkey used to exit the program. Use 'none' to disable (default: ctrl+alt+q)",
    )
    return parser


def _parse_required_hotkey(parser, value):
    try:
        return Hotkey.parse(value)
    except HotkeyParseError as exc:
        parser.error(str(exc))


def _parse_optional_hotkey(parser, value):
    if value.lower() == "none":
        return None
    return _parse_required_hotkey(parser, value)


def main():
    parser = build_parser()
    args = parser.parse_args()

    toggle_hotkey = _parse_required_hotkey(parser, args.toggle)
    exit_hotkey = _parse_optional_hotkey(parser, args.exit)

    clicker = AutoClicker()
    listener = HotkeyListener(clicker, toggle_hotkey, exit_hotkey)

    print("Press {0} to start or stop auto-clicking.".format(toggle_hotkey.describe()))
    if exit_hotkey:
        print("Press {0} to exit the program.".format(exit_hotkey.describe()))
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
