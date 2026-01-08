from nicegui import ui

params = {
    "pixel_size": 0,
    "delay": 0,
    "jump_delay": 0,
}


@ui.page("/")
def main():
    with ui.grid(columns="2fr 10fr").classes("w-full gap-0"):
        with ui.column():
            pixel_size_slider = ui.slider(min=0, max=10, value=params["pixel_size"])
            pixel_size_slider.on_value_change(
                lambda e: params.update({"pixel_size": e.value})
            )

    with ui.header().classes("items-center justify-between"):
        ui.label("Pyaint")


ui.run(native=True, show=False)
