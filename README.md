# DM Soundboard — Android Edition

Same app as the desktop version, rebuilt with **Kivy** (Tkinter doesn't run on
Android) so it can be packaged into an `.apk`.

## Why you're not getting a ready-made .apk

Building an Android APK requires the Android SDK/NDK toolchain, which has to
be downloaded from Google's servers and then run through a real compile step
(20–60 minutes, several GB). I don't have network access to Google's Android
hosts from where I run, so I can't produce the compiled file directly — but
everything needed to build it yourself, with **no Android Studio install**,
is in this folder. Pick either path below.

## Option A — GitHub Actions (recommended, no local setup at all)

1. Create a new GitHub repo and push this whole folder to it (the
   `.github/workflows/build-apk.yml` file must stay at that path).
2. Go to the repo's **Actions** tab — a build will start automatically (or
   click "Run workflow" to trigger it manually).
3. Wait for it to finish (~20–30 min on the free tier), then open the
   completed run and download the **dm-soundboard-apk** artifact — that's
   your `.apk`.
4. Copy it to your Android phone (email, cloud drive, USB — anything) and
   open it. You'll need to allow "install unknown apps" for whatever app you
   used to open the file, since it isn't from the Play Store.

## Option B — Build it yourself on a Linux machine (or WSL on Windows)

```bash
pip install buildozer cython
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf \
    libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev \
    libtinfo5 cmake libffi-dev libssl-dev

cd dm_soundboard_android
buildozer android debug
```

The first run downloads the Android SDK/NDK automatically (this is the slow,
multi-GB part) and drops the finished file in `bin/dmsoundboard-1.0-debug.apk`.
Every build after the first is much faster since the SDK/NDK stay cached.

Buildozer only works on Linux/macOS (WSL2 works fine on Windows) — it can't
build Android packages on native Windows.

## Using the app

Behavior is identical to the desktop version:

- **Music** — looped, only one plays at a time.
- **Ambience** — looped, any number play together.
- **SFX** — one-shot, retriggerable, can overlap itself.
- Tabs across the top switch between the three tile types.
- **+ Add Tile** → name it, pick a type, browse for a file.
- Tap a tile to play/stop it; the **X** removes it; each tile has its own
  volume slider, plus a master volume slider up top.
- Picked audio files are copied into the app's private storage, so tiles
  keep working across restarts regardless of where the original file was.

## Known trade-off vs. the desktop version

The desktop build uses `pygame.mixer.Sound`, which loops with zero gap
because it replays a fully-decoded buffer in memory. Android's audio stack
(via Kivy's `SoundLoader`) generally loops well for **`.ogg` and `.wav`**
files too, but MP3 looping on Android can have a very small gap due to
encoder padding — a long-standing Android platform quirk, not something this
app's code controls. **If gapless looping matters for a track, use `.ogg` or
`.wav` rather than `.mp3`.**

## If something needs adjusting after you build

I tested all of the app's logic (tile add/remove, exclusive music, concurrent
ambience, overlapping SFX, save/load) headlessly on desktop Kivy before
handing this off, so the core behavior is solid. The one part I could not
test end-to-end, because it requires an actual Android device/emulator, is
the file picker's interaction with Android's storage permissions across
different Android versions (11+ uses scoped storage, which varies quite a
bit by manufacturer). If "Browse..." misbehaves on your specific phone, that
is the part to look at — `plyer.filechooser` is the file used, and swapping
in `android4kivy`'s `SharedStorage` API is the usual fix if the default
picker has trouble on your device.

## Optional: an app icon

Buildozer uses a default icon if you don't supply one. To use your own, add
a PNG (square, e.g. 512×512) as `icon.png` in this folder and add this line
under `[app]` in `buildozer.spec`:

```
icon.filename = %(source.dir)s/icon.png
```
