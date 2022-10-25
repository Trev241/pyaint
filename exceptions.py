class NoToolError(Exception):
    pass

class CorruptConfigError(Exception):
    pass

class NoPaletteError(NoToolError):
    pass

class NoCanvasError(NoToolError):
    pass

class NoCustomColorsError(NoToolError):
    pass
