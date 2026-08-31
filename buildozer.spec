[app]
title = DM Soundboard
package.name = dmsoundboard
package.domain = org.dmtools

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = 1.0

requirements = python3,kivy==2.3.1,plyer

orientation = portrait
fullscreen = 0

# Permissions: reading media files from device storage to pick audio, and
# keeping the screen usable while a session is running.
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,READ_MEDIA_AUDIO

android.api = 34
# preadv()/pwritev() (used by CPython's remote-debugging support, compiled
# in by default) are only declared in Android's libc from API 24 onward.
# API 23 fails to build with an implicit-declaration error; 24 covers
# effectively all real-world devices (Android 7.0, released 2016+) so
# there's no meaningful compatibility trade-off.
android.minapi = 24
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a, armeabi-v7a

# Avoid Android 10+ scoped storage issues for the simple file picker approach.
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
