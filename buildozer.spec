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
# Building a single architecture avoids a python-for-android issue where
# building two archs in one run reuses the same temp build venv across
# both passes without resetting it, occasionally corrupting pip's own
# internals partway through the second arch (ImportError referencing
# pip._internal.exceptions). arm64-v8a alone covers the overwhelming
# majority of real Android devices from the last ~8 years; armeabi-v7a
# (32-bit ARM) only matters for pre-2015 hardware.
android.archs = arm64-v8a

# Avoid Android 10+ scoped storage issues for the simple file picker approach.
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
