"""Autoclicker that toggles with CTRL+P and stops on any key press."""
from __future__ import annotations

import random
import threading
from typing import Optional, Set

from pynput import keyboard, mouse


CLICK_INTERVAL_MIN = 0.02
CLICK_INTERVAL_MAX = 0.03


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
        print("Auto-clicking started. Press any key to stop.")

    def stop(self) -> None:
        if not self._clicking:
            return

        self._stop_event.set()
        if self._click_thread is not None:
            self._click_thread.join()
            self._click_thread = None

        self._clicking = False
        print("Auto-clicking stopped. Press CTRL+P to start again.")

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
    """Listen for CTRL+P to start and any other key to stop the clicker."""

    CTRL_KEYS = {keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r}

    def __init__(self, clicker: AutoClicker) -> None:
        self._clicker = clicker
        self._pressed_keys: Set[keyboard.Key | keyboard.KeyCode] = set()
        self._ignored_keys: Set[keyboard.Key | keyboard.KeyCode] = set()

    def on_press(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        self._pressed_keys.add(key)

        if not self._clicker.clicking and self._is_start_combo():
            self._ignored_keys = set(self._pressed_keys)
            self._clicker.start()
            return

        if self._clicker.clicking and key not in self._ignored_keys:
            self._clicker.stop()

    def on_release(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        self._pressed_keys.discard(key)
        self._ignored_keys.discard(key)

    def _is_start_combo(self) -> bool:
        has_ctrl = any(ctrl in self._pressed_keys for ctrl in self.CTRL_KEYS)
        return has_ctrl and any(
            isinstance(key, keyboard.KeyCode) and key.char == "p"
            for key in self._pressed_keys
        )


def main() -> None:
    clicker = AutoClicker()
    listener = HotkeyListener(clicker)

    print("Press CTRL+P to start auto-clicking. Press any key to stop.")

    with keyboard.Listener(
        on_press=listener.on_press, on_release=listener.on_release
    ) as kb_listener:
        try:
            kb_listener.join()
        except KeyboardInterrupt:
            pass
        finally:
            clicker.stop()
            print("Exiting.")


if __name__ == "__main__":
    main()
