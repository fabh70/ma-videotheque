# Ma Vidéothèque

**Français** | [English](README.en.md) | [Nederlands](README.nl.md)

Application locale pour organiser tes films, séries, dessins animés et spectacles.
Elle lit tes fichiers vidéo dans tes propres dossiers, récupère les jaquettes et les
résumés, et lance les films dans VLC ou dans le lecteur par défaut de Windows.

## Téléchargement

Trois fichiers sont disponibles dans l'onglet **Releases** de ce dépôt :

| Fichier | Description |
| --- | --- |
| `MaVideotheque_Portable.zip` | **Recommandé.** À décompresser n'importe où (clé USB incluse). VLC est fourni. Aucune installation, aucune donnée écrite ailleurs. |
| `Videotheque.exe` | L'application seule. Pratique si VLC est déjà installé sur le PC. |
| `Setup_MaVideotheque.exe` | Installeur classique avec VLC inclus (menu Démarrer, raccourci Bureau et désinstalleur). |

> Windows peut afficher « Éditeur inconnu » : clique sur **Informations
> complémentaires** puis **Exécuter quand même**. L'exe n'est pas signé
> numériquement.

## Fonctionnalités

- Onglets Films, Séries, Enfants, Spectacles, avec filtres par genre
- Séries regroupées par saison et par épisode, lecture de l'épisode suivant
- « Continuer à regarder » et marquage des films vus
- Infos depuis TMDB, Wikipédia et (optionnel) OMDb
- Interface en français, anglais et néerlandais
- Lecture plein écran avec VLC (installé ou portable)

## Premier lancement

Choisis ta langue et ton lecteur vidéo. Tu peux changer ces réglages à tout moment
avec le bouton ⚙ en haut à gauche. Ajoute ensuite tes dossiers de films dans les
paramètres, puis clique sur « Scanner tous les dossiers ».

Une clé TMDB gratuite est nécessaire pour les jaquettes et les résumés :
https://www.themoviedb.org (Paramètres > API). Colle-la dans ⚙ Paramètres.

## Données

Les fiches sont enregistrées dans une base SQLite :

- **Version portable** : dans `donnees` à côté de `Videotheque.exe`
  (priorité absolue grâce au fichier `portable.flag`).
- **Version installée** : dans `Bureau\Videotheque` si ce dossier existe,
  sinon dans un dossier `donnees` à côté de l'exe.

Ces données ne sont jamais envoyées ailleurs.

## Lecteur vidéo

Ordre de recherche : VLC installé sur le PC, VLC portable (dossier `VLC` à côté de
l'appli, ou chemin indiqué dans les paramètres), puis lecteur par défaut du système.

## Lancer depuis le code source

```bash
pip install -r requirements.txt
python videotheque_app.py
```

## Construire les exécutables

Prérequis : Python 3.10+ avec `pip`.

```bat
build_exe.bat
```

Produit `dist\Videotheque.exe` (un seul fichier, sans console).

```bat
package_portable.bat
```

Produit `MaVideotheque_Portable\` et `MaVideotheque_Portable.zip`
(VLC portable inclus s'il est présent dans `VLC\` ou `vlc-3.0.21\`).

Pour l'installeur : ouvrir `installer.iss` avec
[Inno Setup](https://jrsoftware.org/isinfo.php) puis compiler (F9).

Les Releases GitHub sont aussi générées automatiquement par
`.github/workflows/build-release.yml` lorsqu'un tag `v*` est poussé.

## Licence

Application : à compléter par l'auteur.

VLC est distribué sous licence **GPLv2+** (voir `VLC\COPYING.txt`).
Code source : https://www.videolan.org/vlc/
