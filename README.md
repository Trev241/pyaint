# pyaint
## What is it?
pyaint is a simple bot written in Python that can automatically draw images by taking control of your mouse. It works on MS Paint, Clip Studio Paint, skribbl (with the risk of being kicked) or essentially any image editing software as long as there is support for a brush, a color palette grid and a canvas. 

## Demo

You can watch the bot in action [here](https://youtu.be/qXfUc9KuVlg) and [here](https://youtu.be/kj0iqZkIG1k).

## Features

- Compatible with almost any drawing application software
- Draw images from either your computer or the internet
- Produce images with near perfect color accuracy with the help of custom colors (supported only in MS Paint)

## Dependencies

Here are all the libraries used in this project

- [PyAutoGUI]
- [Pillow]
- [pynput]
- [keyboard]

## How do I run it?

pyaint requires [Python](https://www.python.org) v3+ to run.

Open your shell in the root directory of the project and then run the command below to install the required dependencies.

```sh
pip install -r ./requirements.txt
```

Then simply run `main.py`.

```sh
python main.py
```

## How do I use it?

There are a number of options that you can tweak when using the bot which makes it difficult to give an overall guide. Nevertheless, the most basic steps to operate the bot would be to
1. Click on "Setup".
2. (Optional) Click on "Inspect" to see if the tools were correctly identified on the screen. Repeat the first step if necessary.
3. Provide an image by entering either a link or file path in the space given.
4. Finally, click on "Start". If things go out of hand, press ESC to stop the bot and regain control.

Even if you do not intend on using MS Paint, the steps for using the bot should still relatively stay the same.

## Development

Suggestions or contributions to the project are welcome.

## License

GPL 3.0

[//]: # (These are reference links used in the body of this note and get stripped out when the markdown processor does its job. There is no need to format nicely because it shouldn't be seen. Thanks SO - http://stackoverflow.com/questions/4823468/store-comments-in-markdown-syntax)
   [PyAutoGUI]: <https://pypi.org/project/PyAutoGUI/>
   [Pillow]: <https://pypi.org/project/Pillow/>
   [pynput]: <https://pypi.org/project/pynput/>
   [keyboard]: <https://pypi.org/project/keyboard/>