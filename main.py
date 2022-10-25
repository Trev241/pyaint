from bot import Bot
from ui.window import Window

import keyboard

def on_key(event):
    if event.name == 'esc':
        bot.terminate = True

if __name__ == '__main__':
    keyboard.on_press(on_key)

    bot = Bot()
    Window('pyaint', bot, 800, 550, 5, 5)
