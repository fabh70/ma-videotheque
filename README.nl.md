# Ma Vidéothèque — Mijn Videotheek

[Français](README.md) | [English](README.en.md) | **Nederlands**

Lokale applicatie om je films, series, tekenfilms en voorstellingen te organiseren.
Ze leest je videobestanden in je eigen mappen, haalt posters en samenvattingen op,
en speelt films af in VLC of in de standaardspeler van Windows.

## Downloaden

Er zijn drie bestanden beschikbaar in het tabblad **Releases** van deze repository:

| Bestand | Beschrijving |
| --- | --- |
| `Setup_MaVideotheque.exe` | Klassieke installatie met **VLC inbegrepen** (Startmenu, snelkoppeling op het bureaublad en verwijderprogramma). |
| `MaVideotheque_Portable.zip` | **Aanbevolen.** Uitpakken waar je wilt (ook op een USB-stick). VLC is inbegrepen. Geen installatie, er wordt niets elders opgeslagen. |
| `Videotheque.exe` | Alleen de applicatie. Handig als VLC al op de pc is geïnstalleerd. |

> Windows kan "Onbekende uitgever" tonen: klik op **Meer informatie** en daarna op
> **Toch uitvoeren**. Het exe-bestand is niet digitaal ondertekend.

## Functies

- Tabbladen Films, Series, Kinderen en Voorstellingen, met filters per genre
- Series gegroepeerd per seizoen en aflevering, volgende aflevering afspelen
- "Verder kijken" en gezien-markering van films
- Informatie van TMDB, Wikipedia en (optioneel) OMDb
- Interface in het Frans, Engels en Nederlands
- Volledig scherm afspelen met VLC (geïnstalleerd of draagbaar)

## Eerste keer opstarten

Kies je taal en je videospeler. Je kunt deze instellingen altijd wijzigen met de
knop ⚙ linksboven. Voeg daarna je filmmappen toe in de instellingen en klik op
"Alle mappen scannen".

Een gratis TMDB-sleutel is nodig voor posters en samenvattingen:
https://www.themoviedb.org (Instellingen > API). Plak deze in ⚙ Instellingen.

## Gegevens

De fiches worden opgeslagen in een SQLite-database:

- **Draagbare versie**: in `donnees` naast `Videotheque.exe`
  (krijgt altijd voorrang dank zij het bestand `portable.flag`).
- **Geïnstalleerde versie**: in `Bureau\Videotheque` als die map bestaat,
  anders in een map `donnees` naast het exe-bestand.

Deze gegevens worden nooit ergens anders naartoe gestuurd.

## Videospeler

Zoekvolgorde: VLC geïnstalleerd op de pc, draagbare VLC (de map `VLC` naast
de applicatie, of het pad uit de instellingen), en daarna de standaardspeler
van het systeem.

## Starten vanuit de broncode

```bash
pip install -r requirements.txt
python videotheque_app.py
```

## De uitvoerbare bestanden bouwen

Vereisten: Python 3.10+ met `pip`.

```bat
build_exe.bat
```

Maakt `dist\Videotheque.exe` (één bestand, zonder consolevenster).

```bat
package_portable.bat
```

Maakt `MaVideotheque_Portable\` en `MaVideotheque_Portable.zip`
(draagbare VLC inbegrepen als die aanwezig is in `VLC\` of `vlc-3.0.21\`).

Voor de installatie: open `installer.iss` met
[Inno Setup](https://jrsoftware.org/isinfo.php) en compileer (F9).
VLC wordt automatisch inbegrepen als de map `VLC\` of `vlc-3.0.21\` aanwezig is.

GitHub Releases worden ook automatisch aangemaakt door
`.github/workflows/build-release.yml` wanneer een tag `v*` wordt gepusht.

## Licentie

Applicatie: aan te vullen door de auteur.

VLC wordt verspreid onder de **GPLv2+**-licentie (zie `VLC\COPYING.txt`).
Broncode: https://www.videolan.org/vlc/
