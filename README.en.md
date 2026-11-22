# Ma Vidéothèque — My Video Library

[Français](README.md) | **English** | [Nederlands](README.nl.md)

Local app to organize your movies, series, cartoons and shows.
It reads your video files from your own folders, fetches posters and summaries,
and plays movies in VLC or in the default Windows player.

## Download

Three files are available in the **Releases** tab of this repository:

| File | Description |
| --- | --- |
| `Setup_MaVideotheque.exe` | Classic installer with **VLC included** (Start menu, desktop shortcut and uninstaller). |
| `MaVideotheque_Portable.zip` | **Recommended.** Unzip anywhere (USB stick included). VLC is included. No installation, no data written elsewhere. |
| `Videotheque.exe` | The app alone. Useful if VLC is already installed on the PC. |

> Windows may show "Unknown publisher": click **More info** then **Run anyway**.
> The exe is not digitally signed.

## Features

- Movies, Series, Kids and Shows tabs, with genre filters
- Series grouped by season and episode, next-episode playback
- "Continue watching" and watched-movie tracking
- Info from TMDB, Wikipedia and (optional) OMDb
- Interface in French, English and Dutch
- Fullscreen playback with VLC (installed or portable)

## First launch

Choose your language and video player. You can change these settings at any time
with the ⚙ button in the top left. Then add your movie folders in the settings
and click "Scan all folders".

A free TMDB key is required for posters and summaries:
https://www.themoviedb.org (Settings > API). Paste it in ⚙ Settings.

## Data

Records are stored in a SQLite database:

- **Portable version**: in `donnees` next to `Videotheque.exe`
  (always takes priority thanks to the `portable.flag` file).
- **Installed version**: in `Desktop\Videotheque` if that folder exists,
  otherwise in a `donnees` folder next to the exe.

This data is never sent anywhere else.

## Video player

Search order: VLC installed on the PC, portable VLC (the `VLC` folder next to
the app, or the path set in the settings), then the system default player.

## Run from source

```bash
pip install -r requirements.txt
python videotheque_app.py
```

## Build the executables

Requirements: Python 3.10+ with `pip`.

```bat
build_exe.bat
```

Produces `dist\Videotheque.exe` (single file, no console).

```bat
package_portable.bat
```

Produces `MaVideotheque_Portable\` and `MaVideotheque_Portable.zip`
(portable VLC included if present in `VLC\` or `vlc-3.0.21\`).

For the installer: open `installer.iss` with
[Inno Setup](https://jrsoftware.org/isinfo.php) then compile (F9).
VLC is included automatically when the `VLC\` or `vlc-3.0.21\` folder is present.

GitHub Releases are also generated automatically by
`.github/workflows/build-release.yml` when a `v*` tag is pushed.

## License

Application: to be completed by the author.

VLC is distributed under the **GPLv2+** license (see `VLC\COPYING.txt`).
Source code: https://www.videolan.org/vlc/
