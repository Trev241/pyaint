from bot import Bot
from ui.window import Window

from pynput import keyboard as pynput_keyboard

bot = Bot()

def on_pynput_key(key):
    try:
        # Handle ESC key for termination
        if key == pynput_keyboard.Key.esc:
            bot.terminate = True
            return

        # Handle pause/resume when bot is actively drawing
        if bot.drawing:
            # Get key name for pause key comparison
            key_name = None
            if hasattr(key, 'char') and key.char:
                key_name = key.char.lower()
            elif hasattr(key, 'name'):
                key_name = key.name.lower()
            else:
                key_name = str(key).lower().replace('key.', '')

            # Check if it matches the pause key
            if key_name == bot.pause_key.lower():
                bot.paused = not bot.paused
                print(f"Pause toggled: {bot.paused}")
                return

    except Exception as e:
        print(f"Keyboard error: {e}")

if __name__ == '__main__':
    # Start pynput keyboard listener in background
    pynput_listener = pynput_keyboard.Listener(on_press=on_pynput_key)
    pynput_listener.start()

    try:
        Window('pyaint', bot, 800, 550, 5, 5)
    finally:
        # Stop listener when done
        pynput_listener.stop()
