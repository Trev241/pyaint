from pyaint import Window, Bot

import keyboard

def on_key(event):
    bot.terminate = True

bot = Bot()
keyboard.on_press(on_key)
window = Window('pyaint', bot, 650, 550, 5, 5)