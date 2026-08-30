"""
DM Soundboard (Kivy / Android edition)
=======================================
Same behavior as the desktop Tkinter version, rebuilt with Kivy so it can be
packaged into an Android APK with Buildozer.

Tile types:
  - Music     -> looped, only ONE can play at a time
  - Ambience  -> looped, MULTIPLE can play at once
  - SFX       -> plays once (drum-pad style), retriggerable/overlappable

Run on desktop for testing:
    pip install kivy plyer
    python main.py

Build for Android:
    See buildozer.spec + README.md in this folder.
"""

import os
import json
import uuid
import shutil

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.core.audio import SoundLoader
from kivy.clock import Clock
from kivy.metrics import dp

TYPE_COLORS = {
    "Music": (0.23, 0.37, 0.63, 1),
    "Ambience": (0.23, 0.56, 0.35, 1),
    "SFX": (0.63, 0.40, 0.23, 1),
}
TYPE_COLORS_ACTIVE = {
    "Music": (0.43, 0.59, 0.91, 1),
    "Ambience": (0.37, 0.81, 0.54, 1),
    "SFX": (0.91, 0.63, 0.37, 1),
}
REMOVE_COLOR = (0.45, 0.18, 0.18, 1)


def copy_into_storage(local_path, dest_dir):
    """Copy a picked audio file into the app's own persistent storage.

    Doing this (rather than remembering the original path) means the tile
    keeps working even if the source file moves, and avoids Android content-
    URI permission expiry across app restarts.
    """
    os.makedirs(dest_dir, exist_ok=True)
    ext = os.path.splitext(local_path)[1]
    if not ext or len(ext) > 6:
        ext = ".mp3"
    dest = os.path.join(dest_dir, uuid.uuid4().hex + ext)
    shutil.copy(local_path, dest)
    return dest


class Tile:
    def __init__(self, tile_id, name, ttype, path, volume=1.0):
        self.id = tile_id
        self.name = name
        self.type = ttype  # "Music" | "Ambience" | "SFX"
        self.path = path
        self.volume = volume

        self.sound = None       # persistent Sound for Music/Ambience
        self.sfx_sounds = []    # list of concurrently-playing Sound objs for SFX
        self.playing = False

        # widget refs
        self.play_btn = None
        self.row_widget = None

    def to_dict(self):
        return {"id": self.id, "name": self.name, "type": self.type,
                "path": self.path, "volume": self.volume}


class SoundboardApp(App):
    title = "DM Soundboard"

    def build(self):
        self.tiles = []
        self.current_music_tile = None
        self.master_volume = 1.0
        self.grids = {}

        root = BoxLayout(orientation="vertical")

        # ---- top bar ----
        top = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(56),
                         padding=dp(6), spacing=dp(6))
        add_btn = Button(text="+ Add Tile")
        add_btn.bind(on_release=self.open_add_dialog)
        stop_btn = Button(text="Stop All", background_color=(0.5, 0.18, 0.18, 1))
        stop_btn.bind(on_release=self.stop_all)
        vol_label = Label(text="Vol", size_hint_x=None, width=dp(36))
        self.master_slider = Slider(min=0, max=1, value=1, size_hint_x=None, width=dp(120))
        self.master_slider.bind(value=lambda inst, val: self.on_master_volume(val))

        top.add_widget(add_btn)
        top.add_widget(stop_btn)
        top.add_widget(Label())  # spacer
        top.add_widget(vol_label)
        top.add_widget(self.master_slider)
        root.add_widget(top)

        # ---- tabs: Music / Ambience / SFX ----
        tabs = TabbedPanel(do_default_tab=False, size_hint_y=1)
        for ttype in ["Music", "Ambience", "SFX"]:
            tab = TabbedPanelItem(text=ttype)
            scroll = ScrollView()
            grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(8), padding=dp(8))
            grid.bind(minimum_height=grid.setter("height"))
            scroll.add_widget(grid)
            tab.add_widget(scroll)
            tabs.add_widget(tab)
            self.grids[ttype] = grid
        root.add_widget(tabs)

        self.load_config()
        return root

    # ------------------------------------------------------------ tile widgets

    def create_tile_widget(self, tile):
        row = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(92),
                         spacing=dp(4))

        top_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(52),
                             spacing=dp(6))
        play_btn = Button(text=tile.name, background_normal="",
                           background_color=TYPE_COLORS[tile.type], bold=True)
        play_btn.bind(on_release=lambda inst, t=tile: self.toggle_tile(t))

        remove_btn = Button(text="X", size_hint_x=None, width=dp(44),
                             background_normal="", background_color=REMOVE_COLOR)
        remove_btn.bind(on_release=lambda inst, t=tile: self.confirm_remove(t))

        top_row.add_widget(play_btn)
        top_row.add_widget(remove_btn)

        vol_slider = Slider(min=0, max=1, value=tile.volume, size_hint_y=None, height=dp(28))
        vol_slider.bind(value=lambda inst, val, t=tile: self.on_tile_volume(t, val))

        row.add_widget(top_row)
        row.add_widget(vol_slider)

        tile.play_btn = play_btn
        tile.row_widget = row
        self.grids[tile.type].add_widget(row)

    def confirm_remove(self, tile):
        content = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(12))
        content.add_widget(Label(text=f"Remove '{tile.name}'?"))
        btn_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        yes_btn = Button(text="Remove", background_color=REMOVE_COLOR)
        no_btn = Button(text="Cancel")
        btn_row.add_widget(yes_btn)
        btn_row.add_widget(no_btn)
        content.add_widget(btn_row)

        popup = Popup(title="Confirm", content=content, size_hint=(0.75, 0.35))

        def do_remove(*_a):
            self.remove_tile(tile)
            popup.dismiss()

        yes_btn.bind(on_release=do_remove)
        no_btn.bind(on_release=popup.dismiss)
        popup.open()

    def remove_tile(self, tile):
        self.stop_tile(tile)
        if self.current_music_tile is tile:
            self.current_music_tile = None
        if tile in self.tiles:
            self.tiles.remove(tile)
        if tile.row_widget is not None:
            self.grids[tile.type].remove_widget(tile.row_widget)
        self.save_config()

    def update_tile_visual(self, tile):
        if tile.play_btn is not None:
            tile.play_btn.background_color = (
                TYPE_COLORS_ACTIVE[tile.type] if tile.playing else TYPE_COLORS[tile.type]
            )

    # ------------------------------------------------------------ playback

    def toggle_tile(self, tile):
        if tile.type == "Music":
            if self.current_music_tile is tile and tile.playing:
                self.stop_tile(tile)
                self.current_music_tile = None
            else:
                if self.current_music_tile is not None:
                    self.stop_tile(self.current_music_tile)
                self.play_loop_tile(tile)
                self.current_music_tile = tile

        elif tile.type == "Ambience":
            if tile.playing:
                self.stop_tile(tile)
            else:
                self.play_loop_tile(tile)

        else:  # SFX
            self.play_sfx(tile)

    def play_loop_tile(self, tile):
        if tile.sound is None:
            tile.sound = SoundLoader.load(tile.path)
        if tile.sound is None:
            self.show_error(f"Could not load '{tile.name}'.\n{tile.path}")
            return
        tile.sound.loop = True
        tile.sound.volume = tile.volume * self.master_volume
        tile.sound.play()
        tile.playing = True
        self.update_tile_visual(tile)

    def stop_tile(self, tile):
        if tile.sound is not None:
            tile.sound.stop()
        for s in tile.sfx_sounds:
            s.stop()
        tile.sfx_sounds = []
        tile.playing = False
        self.update_tile_visual(tile)

    def play_sfx(self, tile):
        sound = SoundLoader.load(tile.path)
        if sound is None:
            self.show_error(f"Could not load '{tile.name}'.\n{tile.path}")
            return
        sound.volume = tile.volume * self.master_volume

        def _on_state(_inst, value):
            if value == "stop":
                if sound in tile.sfx_sounds:
                    tile.sfx_sounds.remove(sound)
                if not tile.sfx_sounds:
                    tile.playing = False
                    self.update_tile_visual(tile)

        sound.bind(state=_on_state)
        tile.sfx_sounds.append(sound)
        tile.playing = True
        self.update_tile_visual(tile)
        sound.play()

    def stop_all(self, *_args):
        for tile in list(self.tiles):
            self.stop_tile(tile)
        self.current_music_tile = None

    def on_master_volume(self, val):
        self.master_volume = val
        for tile in self.tiles:
            if tile.sound is not None and tile.playing:
                tile.sound.volume = tile.volume * val
            for s in tile.sfx_sounds:
                s.volume = tile.volume * val

    def on_tile_volume(self, tile, val):
        tile.volume = val
        if tile.sound is not None:
            tile.sound.volume = val * self.master_volume
        for s in tile.sfx_sounds:
            s.volume = val * self.master_volume
        self.save_config()

    # ------------------------------------------------------------ add tile

    def open_add_dialog(self, *_args):
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))

        name_input = TextInput(hint_text="Tile name", multiline=False,
                                size_hint_y=None, height=dp(44))
        type_spinner = Spinner(text="Music", values=["Music", "Ambience", "SFX"],
                                size_hint_y=None, height=dp(44))
        file_label = Label(text="(no file selected)", size_hint_y=None, height=dp(30))
        browse_btn = Button(text="Browse...", size_hint_y=None, height=dp(44))

        state = {"path": None}

        def on_selected(selection):
            def _update(_dt):
                if selection:
                    state["path"] = selection[0]
                    file_label.text = os.path.basename(selection[0])
                    if not name_input.text.strip():
                        name_input.text = os.path.splitext(os.path.basename(selection[0]))[0]
            Clock.schedule_once(_update, 0)

        def do_browse(*_a):
            try:
                from plyer import filechooser
                filechooser.open_file(
                    on_selection=on_selected,
                    filters=[("Audio", "*.mp3", "*.wav", "*.ogg", "*.flac", "*.m4a")],
                )
            except Exception as e:
                file_label.text = f"File picker error: {e}"

        browse_btn.bind(on_release=do_browse)

        btn_row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        add_btn = Button(text="Add", background_color=(0.23, 0.56, 0.35, 1))
        cancel_btn = Button(text="Cancel")
        btn_row.add_widget(add_btn)
        btn_row.add_widget(cancel_btn)

        content.add_widget(name_input)
        content.add_widget(type_spinner)
        content.add_widget(file_label)
        content.add_widget(browse_btn)
        content.add_widget(btn_row)

        popup = Popup(title="Add Tile", content=content, size_hint=(0.9, 0.6))

        def do_add(*_a):
            if not name_input.text.strip() or not state["path"]:
                file_label.text = "Please choose a name and a file."
                return
            dest_dir = os.path.join(self.user_data_dir, "audio")
            try:
                dest = copy_into_storage(state["path"], dest_dir)
            except Exception as e:
                file_label.text = f"Could not import file: {e}"
                return
            tile = Tile(uuid.uuid4().hex, name_input.text.strip(), type_spinner.text, dest)
            self.tiles.append(tile)
            self.create_tile_widget(tile)
            self.save_config()
            popup.dismiss()

        add_btn.bind(on_release=do_add)
        cancel_btn.bind(on_release=popup.dismiss)
        popup.open()

    def show_error(self, message):
        content = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(12))
        content.add_widget(Label(text=message))
        ok_btn = Button(text="OK", size_hint_y=None, height=dp(44))
        content.add_widget(ok_btn)
        popup = Popup(title="Error", content=content, size_hint=(0.85, 0.4))
        ok_btn.bind(on_release=popup.dismiss)
        popup.open()

    # ------------------------------------------------------------ persistence

    @property
    def config_path(self):
        return os.path.join(self.user_data_dir, "soundboard_config.json")

    def load_config(self):
        if not os.path.exists(self.config_path):
            return
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return
        for d in data.get("tiles", []):
            tile = Tile(
                tile_id=d.get("id", uuid.uuid4().hex),
                name=d.get("name", "Unnamed"),
                ttype=d.get("type", "SFX"),
                path=d.get("path", ""),
                volume=d.get("volume", 1.0),
            )
            self.tiles.append(tile)
            self.create_tile_widget(tile)

    def save_config(self):
        data = {"tiles": [t.to_dict() for t in self.tiles]}
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def on_stop(self):
        self.stop_all()


if __name__ == "__main__":
    SoundboardApp().run()
