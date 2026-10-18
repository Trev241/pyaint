"""Application entry point.

Run with ``python -m pyaint`` (or the root ``main.py`` shim). Starts the global
hotkey listener and opens the PySide6 main window.
"""

from pynput import keyboard as pynput_keyboard

from pyaint.bot import Bot
from pyaint.log import log
from pyaint.ui.main_window import run


def main():
    bot = Bot()

    def on_pynput_key(key):
        try:
            # ESC stops the current run.
            if key == pynput_keyboard.Key.esc:
                bot.terminate = True
                return

            # Pause/resume only while drawing.
            if bot.drawing:
                if hasattr(key, "char") and key.char:
                    key_name = key.char.lower()
                elif hasattr(key, "name"):
                    key_name = key.name.lower()
                else:
                    key_name = str(key).lower().replace("key.", "")

                if key_name == bot.pause_key.lower():
                    bot.paused = not bot.paused
                    log.info(f"Pause toggled: {bot.paused}")
        except Exception as e:
            log.info(f"Keyboard error: {e}")

    listener = pynput_keyboard.Listener(on_press=on_pynput_key)
    listener.start()

    try:
        run(bot)
    finally:
        listener.stop()


if __name__ == "__main__":
    main()
