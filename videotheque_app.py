"""Ma Vidéothèque v2 : plusieurs dossiers, catégories (Films, Séries, Enfants, Spectacles)."""
import glob
import json
import re
import os
import platform
import shutil
import sqlite3
import subprocess
import time
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import quote, urlparse

import requests

# ---------- CHEMINS ----------
if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
    RESSOURCES = sys._MEIPASS
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    RESSOURCES = APP_DIR

def mode_portable():
    """Vrai si l'appli tourne en version portable (fichier portable.flag à côté de l'exe)."""
    return os.path.exists(os.path.join(APP_DIR, "portable.flag"))


def choisir_dossier_donnees():
    """Prend la base qui contient le plus de fiches : Bureau/Videotheque ou dossier de l'appli.
    En mode portable, utilise toujours le dossier donnees placé à côté de l'exe."""
    dossier_appli = os.path.join(APP_DIR, "donnees")
    if mode_portable():
        return dossier_appli
    candidats = [os.path.join(os.path.expanduser("~"), "Desktop", "Videotheque"),
                 dossier_appli]
    meilleur, nb_max = None, -1
    for dossier in candidats:
        base = os.path.join(dossier, "videotheque.db")
        if not os.path.exists(base):
            continue
        try:
            con = sqlite3.connect(base)
            nb = con.execute("SELECT COUNT(*) FROM media").fetchone()[0]
            con.close()
        except sqlite3.Error:
            nb = 0
        if nb > nb_max:
            meilleur, nb_max = dossier, nb
    return meilleur or candidats[1]


DATA_DIR = choisir_dossier_donnees()
COVERS_DIR = os.path.join(DATA_DIR, "jaquettes")
DB_PATH = os.path.join(DATA_DIR, "videotheque.db")
os.makedirs(COVERS_DIR, exist_ok=True)

# ---------- CONFIGURATION ----------
TMDB_KEY_DEFAUT = os.environ.get("TMDB_KEY", "")
OMDB_KEY = ""  # optionnel
VIDEO_EXT = (".mp4", ".mkv", ".avi", ".mov", ".wmv", ".m4v")
HEADERS = {"User-Agent": "VideothequePerso/2.0"}
PORT = 8765
CATEGORIES = ("Films", "Séries", "Enfants", "Spectacles")


def vlc_windows():
    candidats = []
    for var in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
        base = os.environ.get(var)
        if base:
            candidats.append(os.path.join(base, "VideoLAN", "VLC", "vlc.exe"))
    candidats += [r"C:\Program Files\VideoLAN\VLC\vlc.exe",
                  r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"]
    try:
        import winreg
        for racine in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for sous in (r"SOFTWARE\VideoLAN\VLC", r"SOFTWARE\WOW6432Node\VideoLAN\VLC"):
                try:
                    with winreg.OpenKey(racine, sous) as cle:
                        dossier, _ = winreg.QueryValueEx(cle, "InstallDir")
                        candidats.append(os.path.join(dossier, "vlc.exe"))
                except OSError:
                    pass
    except ImportError:
        pass
    trouve = shutil.which("vlc")
    if trouve:
        candidats.insert(0, trouve)
    return next((c for c in candidats if os.path.isfile(c)), None)


def trouver_vlc_portable():
    """Cherche vlc.exe dans le dossier de l'appli, puis dans ses sous-dossiers (ex. VLC\\vlc-3.0.20\\)."""
    nom = "vlc.exe" if platform.system() == "Windows" else "VLC"
    racine_mac = os.path.join("VLC.app", "Contents", "MacOS", "VLC")
    candidats = [os.path.join(APP_DIR, "VLC", nom), os.path.join(APP_DIR, nom)]
    if platform.system() != "Windows":
        candidats.append(os.path.join(APP_DIR, "VLC", racine_mac))
    trouve = next((c for c in candidats if os.path.isfile(c)), None)
    if trouve:
        return trouve
    for profondeur in ("*", "*/*"):
        for c in glob.glob(os.path.join(APP_DIR, profondeur, nom)):
            if os.path.isfile(c) and "vlc" in c.lower():
                return c
    return None


def trouver_lecteurs():
    """VLC installé sur le PC et VLC portable (dossier VLC à côté de l'appli)."""
    systeme = platform.system()
    if systeme == "Windows":
        pc = vlc_windows()
    elif systeme == "Darwin" and os.path.exists("/Applications/VLC.app/Contents/MacOS/VLC"):
        pc = "/Applications/VLC.app/Contents/MacOS/VLC"
    else:
        pc = shutil.which("vlc")
    portable = None
    indique = lire_reglages().get("vlc_chemin", "")
    if indique and os.path.isfile(indique):
        portable = indique
    else:
        portable = trouver_vlc_portable()
    return {"vlc_pc": pc, "vlc_portable": portable}


def init_db():
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS media (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titre TEXT, type TEXT, annee TEXT, genre TEXT, acteurs TEXT,
                synopsis TEXT, jaquette TEXT, fichier TEXT UNIQUE, tmdb_id INTEGER
            )""")
        con.execute("""
            CREATE TABLE IF NOT EXISTS reglages (
                cle TEXT PRIMARY KEY,
                valeur TEXT
            )""")
        con.execute("""
            CREATE TABLE IF NOT EXISTS dossiers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chemin TEXT UNIQUE NOT NULL,
                categorie TEXT NOT NULL
            )""")
        for col in ("titre_original", "realisateur", "duree", "pays", "note", "tagline",
                    "backdrop", "bande_annonce", "source", "categorie", "titre_recherche", "derniere_lecture"):
            try:
                con.execute(f"ALTER TABLE media ADD COLUMN {col} TEXT")
            except sqlite3.OperationalError:
                pass
        try:
            con.execute("ALTER TABLE media ADD COLUMN vu INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        for col, typ in (("serie_nom", "TEXT"), ("saison", "INTEGER"), ("episode", "INTEGER")):
            try:
                con.execute(f"ALTER TABLE media ADD COLUMN {col} {typ}")
            except sqlite3.OperationalError:
                pass
        con.execute("UPDATE media SET categorie='Films' WHERE categorie IS NULL OR categorie=''")


def db_rows(sql, params=()):
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        return [dict(r) for r in con.execute(sql, params).fetchall()]


def db_run(sql, params=()):
    with sqlite3.connect(DB_PATH) as con:
        con.execute(sql, params)


# ---------- SOURCES D'INFORMATIONS ----------
def telecharger(url, nom):
    chemin = os.path.join(COVERS_DIR, nom)
    if not os.path.exists(chemin):
        with open(chemin, "wb") as f:
            f.write(requests.get(url, timeout=10).content)
    return nom


def normaliser(texte):
    return " ".join(re.sub(r"[^\w\s]", " ", (texte or "").lower()).split())


def cle_tmdb():
    """Clé TMDB saisie par l'utilisateur dans les paramètres (sinon variable d'environnement)."""
    return lire_reglages().get("tmdb_cle") or TMDB_KEY_DEFAUT


def tmdb_get(url, params):
    """Appel TMDB avec réessai si l'API demande de ralentir."""
    if not cle_tmdb():
        raise requests.RequestException("Clé TMDB absente : ajoute-la dans ⚙ Paramètres.")
    for essai in range(4):
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 429:
            time.sleep(2 + essai * 2)
            continue
        r.raise_for_status()
        return r.json()
    raise requests.RequestException("TMDB est saturé, réessaie dans une minute.")


def chercher_candidats(titre, annee, serie):
    candidats = []
    for langue in ("fr-FR", "en-US"):
        for genre in (("tv", "movie") if serie else ("movie", "tv")):
            params = {"api_key": cle_tmdb(), "query": titre, "language": langue}
            if annee:
                params["year" if genre == "movie" else "first_air_date_year"] = annee
            r = tmdb_get(f"https://api.themoviedb.org/3/search/{genre}", params)
            for x in r.get("results", [])[:8]:
                x["media_type"] = genre
                candidats.append(x)
        if candidats:
            break
    return candidats


def tmdb_infos(titre, annee="", serie=False):
    res = chercher_candidats(titre, annee, serie)
    if not res:
        return None

    def annee_de(x):
        return (x.get("release_date") or x.get("first_air_date") or "")[:4]

    cible = normaliser(titre)
    res = sorted(res, key=lambda x: (
        bool(annee) and annee_de(x) != annee,
        normaliser(x.get("title") or x.get("name")) != cible,
    ))
    item = res[0]
    kind = item["media_type"]
    d = tmdb_get(f"https://api.themoviedb.org/3/{kind}/{item['id']}",
                 {"api_key": cle_tmdb(), "language": "fr-FR", "append_to_response": "credits,videos"})

    crew = d.get("credits", {}).get("crew", [])
    if kind == "movie":
        pays = ", ".join(p["name"] for p in d.get("production_countries", []))
        duree = str(d.get("runtime") or "")
    else:
        pays = ", ".join(d.get("origin_country", []))
        duree = str((d.get("episode_run_time") or [""])[0])
    videos = d.get("videos", {}).get("results", [])

    jaquette = backdrop = None
    if d.get("poster_path"):
        jaquette = telecharger("https://image.tmdb.org/t/p/w342" + d["poster_path"],
                               f"{item['id']}_{kind}.jpg")
    if d.get("backdrop_path"):
        backdrop = telecharger("https://image.tmdb.org/t/p/w780" + d["backdrop_path"],
                               f"{item['id']}_{kind}_fond.jpg")

    en_overview = ""
    if not d.get("overview"):
        en = tmdb_get(f"https://api.themoviedb.org/3/{kind}/{item['id']}",
                      {"api_key": cle_tmdb(), "language": "en-US"})
        en_overview = en.get("overview") or ""
    note = d.get("vote_average") or 0
    return {
        "titre": d.get("title") or d.get("name") or titre,
        "titre_original": d.get("original_title") or d.get("original_name") or "",
        "type": "Film" if kind == "movie" else "Série",
        "annee": annee_de(d) or annee,
        "genre": ", ".join(g["name"] for g in d.get("genres", [])),
        "acteurs": ", ".join(a["name"] for a in d.get("credits", {}).get("cast", [])[:8]),
        "realisateur": ", ".join(c["name"] for c in crew if c.get("job") == "Director"),
        "duree": duree,
        "pays": pays,
        "note": f"TMDB {note:.1f}/10" if note else "",
        "tagline": d.get("tagline") or "",
        "synopsis": d.get("overview") or en_overview,
        "jaquette": jaquette,
        "backdrop": backdrop,
        "bande_annonce": next((f"https://www.youtube.com/watch?v={v['key']}" for v in videos
                               if v.get("site") == "YouTube" and v.get("type") == "Trailer"), ""),
        "tmdb_id": item["id"],
        "source": "TMDB",
    }


def wikipedia_resume(titre):
    try:
        r = requests.get("https://fr.wikipedia.org/api/rest_v1/page/summary/"
                         + quote(titre.replace(" ", "_")), headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json().get("extract", "")
    except requests.RequestException:
        pass
    return ""


def omdb_note(titre, annee=""):
    if not OMDB_KEY:
        return ""
    try:
        d = requests.get("https://www.omdbapi.com/",
                         params={"apikey": OMDB_KEY, "t": titre, "y": annee}, timeout=10).json()
        if d.get("Response") == "True" and d.get("imdbRating") not in (None, "N/A"):
            return f"IMDb {d['imdbRating']}/10"
    except requests.RequestException:
        pass
    return ""


def chercher_infos(titre, annee="", serie=False):
    info = {"titre": titre, "type": "Film", "annee": annee, "source": ""}
    sources = []
    try:
        tmdb = tmdb_infos(titre, annee, serie)
    except requests.RequestException:
        tmdb = None
    if tmdb:
        info.update({k: v for k, v in tmdb.items() if v not in (None, "")})
        sources.append("TMDB")
    if not info.get("synopsis"):
        resume = wikipedia_resume(info["titre"])
        if resume:
            info["synopsis"] = resume
            sources.append("Wikipédia")
    imdb = omdb_note(info.get("titre_original") or info["titre"], info.get("annee", ""))
    if imdb:
        info["note"] = f"{info.get('note')}  ·  {imdb}" if info.get("note") else imdb
        sources.append("OMDb")
    info["source"] = " + ".join(sources) or "Aucune"
    return info


ENREGISTREMENT_INFOS = ("titre", "titre_original", "type", "annee", "genre", "acteurs", "realisateur",
                        "duree", "pays", "note", "tagline", "synopsis", "jaquette", "backdrop",
                        "bande_annonce", "tmdb_id", "source")


def appliquer_infos(fid, info):
    colonnes = [c for c in ENREGISTREMENT_INFOS if c in info]
    sql = "UPDATE media SET " + ", ".join(f"{c}=?" for c in colonnes) + " WHERE id=?"
    db_run(sql, [info[c] for c in colonnes] + [fid])


def nettoyer_titre(nom):
    nom = re.sub(r"[._]", " ", nom)
    nom = re.split(r"\b(480p|720p|1080p|2160p|4k|x264|x265|h264|h265|hevc|bluray|brrip|bdrip|"
                   r"webrip|web-dl|hdtv|dvdrip|french|truefrench|multi|vostfr|vff)\b", nom, flags=re.I)[0]
    nom = re.sub(r"\(?\b(19|20)\d{2}\b\)?", " ", nom)
    return " ".join(nom.split())


PATRONS_EPISODE = [
    re.compile(r"^(?P<serie>.+?)[ ._-]*S(?P<s>\d{1,2})[ ._-]*E(?P<e>\d{1,3})", re.I),
    re.compile(r"^(?P<serie>.+?)[ ._-]+(?P<s>\d{1,2})x(?P<e>\d{2,3})\b", re.I),
]


def analyser_episode(nom):
    """Renvoie (nom de la série, saison, épisode) ou None si ce n'est pas un épisode."""
    for patron in PATRONS_EPISODE:
        m = patron.search(nom)
        if m:
            serie = nettoyer_titre(m.group("serie"))
            if serie:
                return serie, int(m.group("s")), int(m.group("e"))
    return None


def nom_depuis_fichier(chemin):
    nom = os.path.splitext(os.path.basename(chemin))[0]
    titre = nettoyer_titre(nom)
    trouve = re.search(r"(?<!\d)((?:19|20)\d{2})(?!\d)", nom)
    annee = trouve.group(1) if trouve else ""
    return titre, annee


# ---------- ACTIONS ----------
def url_couverture(chemin):
    if not chemin:
        return ""
    nom = os.path.basename(chemin)  # gère aussi les anciens chemins complets
    return f"/covers/{nom}" if os.path.exists(os.path.join(COVERS_DIR, nom)) else ""


def lister_films():
    lignes = db_rows("SELECT * FROM media ORDER BY titre COLLATE NOCASE, saison, episode")
    resultat, groupes = [], {}
    for f in lignes:
        f["jaquette_url"] = url_couverture(f.get("jaquette"))
        f["backdrop_url"] = url_couverture(f.get("backdrop"))
        f["vu"] = bool(f.get("vu"))
        f["categorie"] = f.get("categorie") or "Films"
        if f.get("serie_nom"):
            cle = f["serie_nom"].lower()
            if cle not in groupes:
                groupes[cle] = {**f, "est_serie": True, "episodes": []}
                resultat.append(groupes[cle])
            groupes[cle]["episodes"].append({"id": f["id"], "saison": f["saison"] or 1,
                                             "episode": f["episode"] or 0, "fichier": f["fichier"],
                                             "vu": f["vu"], "derniere": f.get("derniere_lecture")})
        else:
            f["est_serie"] = False
            f["episodes"] = []
            resultat.append(f)
    for g in groupes.values():
        g["episodes"].sort(key=lambda e: (e["saison"], e["episode"]))
        g["nb_episodes"] = len(g["episodes"])
        g["vu"] = all(e["vu"] for e in g["episodes"])
        g["id"] = g["episodes"][0]["id"]
    return resultat


def ids_concernes(fid, tout):
    if not tout:
        return [fid]
    ligne = db_rows("SELECT serie_nom FROM media WHERE id=?", (fid,))
    if not ligne or not ligne[0]["serie_nom"]:
        return [fid]
    return [r["id"] for r in db_rows("SELECT id FROM media WHERE serie_nom=?", (ligne[0]["serie_nom"],))]


def completer_fiche(fid):
    ligne = db_rows("SELECT id, titre, annee, serie_nom FROM media WHERE id=?", (fid,))[0]
    if ligne["serie_nom"]:
        info = chercher_infos(ligne["serie_nom"], "")
        ids = ids_concernes(fid, True)
    else:
        info = chercher_infos(ligne["titre"], ligne["annee"] or "")
        ids = [fid]
    for i in ids:
        appliquer_infos(i, info)
    return info["source"]


def lister_dossiers():
    return db_rows("SELECT * FROM dossiers ORDER BY categorie, chemin")


def ajouter_dossier(chemin, categorie):
    chemin = os.path.normpath(chemin.strip().strip('"'))
    if categorie not in CATEGORIES:
        raise ValueError("Catégorie inconnue.")
    if not os.path.isdir(chemin):
        raise ValueError("Ce dossier n'existe pas.")
    try:
        db_run("INSERT INTO dossiers (chemin, categorie) VALUES (?, ?)", (chemin, categorie))
    except sqlite3.IntegrityError:
        raise ValueError("Ce dossier est déjà dans la liste.")


def recherche_serie(serie):
    rows = db_rows("SELECT titre_recherche FROM media WHERE serie_nom=? "
                   "AND titre_recherche IS NOT NULL AND titre_recherche<>'' LIMIT 1", (serie,))
    return rows[0]["titre_recherche"] if rows else serie


def info_serie_existante(serie_nom):
    rows = db_rows("SELECT * FROM media WHERE serie_nom=? AND synopsis IS NOT NULL AND synopsis<>'' LIMIT 1",
                   (serie_nom,))
    if not rows:
        return None
    return {k: rows[0][k] for k in ENREGISTREMENT_INFOS if k in rows[0]}


def scanner_dossier(dossier_id):
    rows = db_rows("SELECT * FROM dossiers WHERE id=?", (dossier_id,))
    if not rows:
        raise ValueError("Dossier introuvable.")
    dossier = rows[0]
    if not os.path.isdir(dossier["chemin"]):
        raise ValueError(f"Dossier introuvable sur le disque : {dossier['chemin']}")
    ajoutes = 0
    for racine, _, fichiers in os.walk(dossier["chemin"]):
        for nom in fichiers:
            if not nom.lower().endswith(VIDEO_EXT):
                continue
            chemin = os.path.normpath(os.path.join(racine, nom))
            if db_rows("SELECT id FROM media WHERE fichier=?", (chemin,)):
                continue
            analyse = analyser_episode(os.path.splitext(nom)[0])
            if analyse:
                serie, saison, episode = analyse
                info = info_serie_existante(serie) or chercher_infos(recherche_serie(serie), "", serie=True)
                db_run("INSERT INTO media (fichier, titre, categorie, serie_nom, saison, episode) "
                       "VALUES (?, ?, ?, ?, ?, ?)",
                       (chemin, info["titre"], dossier["categorie"], serie, saison, episode))
            else:
                titre, annee = nom_depuis_fichier(chemin)
                info = chercher_infos(titre, annee)
                db_run("INSERT INTO media (fichier, titre, categorie) VALUES (?, ?, ?)",
                       (chemin, info["titre"], dossier["categorie"]))
            fid = db_rows("SELECT id FROM media WHERE fichier=?", (chemin,))[0]["id"]
            appliquer_infos(fid, info)
            ajoutes += 1
    return ajoutes


def scanner_tous():
    total = 0
    for d in lister_dossiers():
        if os.path.isdir(d["chemin"]):
            total += scanner_dossier(d["id"])
    return total


def lire_reglages():
    return {r["cle"]: r["valeur"] for r in db_rows("SELECT cle, valeur FROM reglages")}


def ecrire_reglage(cle, valeur):
    db_run("INSERT INTO reglages (cle, valeur) VALUES (?, ?) "
           "ON CONFLICT(cle) DO UPDATE SET valeur=excluded.valeur", (cle, valeur))


def lecteur_choisi():
    """Lecteur demandé par l'utilisateur, ou le suivant disponible si celui-ci manque."""
    lecteurs = trouver_lecteurs()
    choix = lire_reglages().get("lecteur", "vlc_pc")
    ordre = [choix] + [x for x in ("vlc_pc", "vlc_portable", "defaut") if x != choix]
    for nom in ordre:
        if nom == "defaut" or lecteurs.get(nom):
            return nom
    return "defaut"


def lancer_vlc(fid):
    rows = db_rows("SELECT fichier FROM media WHERE id=?", (fid,))
    if not rows:
        raise ValueError("Fiche introuvable.")
    chemin = rows[0]["fichier"]
    if not os.path.exists(chemin):
        raise ValueError(f"Fichier introuvable : {chemin}")
    lecteur = lecteur_choisi()
    if lecteur in ("vlc_pc", "vlc_portable"):
        subprocess.Popen([trouver_lecteurs()[lecteur], "--fullscreen", "--no-qt-privacy-ask",
                          "--started-from-file", chemin], cwd=os.path.dirname(chemin))
        return lecteur
    systeme = platform.system()
    if systeme == "Windows":
        os.startfile(chemin)
    elif systeme == "Darwin":
        subprocess.Popen(["open", chemin])
    else:
        subprocess.Popen(["xdg-open", chemin])
    return "defaut"


def statut_reglages():
    reglages = lire_reglages()
    lecteurs = trouver_lecteurs()
    return {
        "langue": reglages.get("langue"),
        "premier_lancement": not reglages.get("langue"),
        "base": DB_PATH,
        "tmdb_ok": bool(cle_tmdb()),
        "vlc_chemin": reglages.get("vlc_chemin", ""),
        "version": "11",
        "lecteur": reglages.get("lecteur", "vlc_pc"),
        "lecteur_actif": lecteur_choisi(),
        "lecteurs": {"vlc_pc": bool(lecteurs["vlc_pc"]), "vlc_portable": bool(lecteurs["vlc_portable"]),
                     "defaut": True},
    }


def requete_pour(ligne):
    """Titre et année à chercher pour une ligne de la base."""
    if ligne.get("serie_nom"):
        return ligne.get("titre_recherche") or ligne["serie_nom"], "", True
    if ligne.get("fichier"):
        titre, annee = nom_depuis_fichier(ligne["fichier"])
        if titre:
            return titre, annee, False
    return ligne.get("titre") or "", ligne.get("annee") or "", False


def completer_fiche(fid):
    ligne = db_rows("SELECT * FROM media WHERE id=?", (fid,))[0]
    titre, annee, serie = requete_pour(ligne)
    info = chercher_infos(titre, annee, serie)
    for i in ids_concernes(fid, serie):
        appliquer_infos(i, info)
    return info["source"]


def completer_manquants():
    lignes = db_rows("SELECT * FROM media WHERE synopsis IS NULL OR synopsis='' "
                     "OR jaquette IS NULL OR jaquette=''")
    deja_faits, reussis, echecs = set(), 0, 0
    for ligne in lignes:
        if ligne["id"] in deja_faits:
            continue
        try:
            titre, annee, serie = requete_pour(ligne)
            info = chercher_infos(titre, annee, serie)
            for i in ids_concernes(ligne["id"], serie):
                appliquer_infos(i, info)
                deja_faits.add(i)
            if info.get("source") != "Aucune":
                reussis += 1
            else:
                echecs += 1
        except Exception as e:  # une fiche en erreur ne bloque pas les autres
            print(f"Erreur pour {ligne.get('fichier')} : {e}")
            echecs += 1
        time.sleep(0.4)  # évite de dépasser la limite de TMDB
    return {"completes": reussis, "echecs": echecs}


def supprimer_fiches(fid, tout, avec_fichier):
    """Retire les fiches de la base. Si avec_fichier, supprime aussi les vidéos et jaquettes orphelines."""
    ids = ids_concernes(fid, tout)
    marque = ",".join("?" * len(ids))
    lignes = db_rows(f"SELECT id, fichier, jaquette, backdrop FROM media WHERE id IN ({marque})", ids)
    a_retirer, erreurs = [], []
    for ligne in lignes:
        chemin = ligne["fichier"]
        if avec_fichier and chemin and os.path.isfile(chemin):
            if not chemin.lower().endswith(VIDEO_EXT):
                erreurs.append(f"Fichier non vidéo ignoré : {chemin}")
                continue
            try:
                os.remove(chemin)
            except OSError as e:
                erreurs.append(f"{os.path.basename(chemin)} : {e.strerror or e}")
                continue
        a_retirer.append(ligne)

    for ligne in a_retirer:
        db_run("DELETE FROM media WHERE id=?", (ligne["id"],))

    noms_images = {os.path.basename(n) for l in a_retirer for n in (l["jaquette"], l["backdrop"]) if n}
    for nom in noms_images:
        encore = db_rows("SELECT id FROM media WHERE jaquette=? OR backdrop=?", (nom, nom))
        chemin_image = os.path.join(COVERS_DIR, nom)
        if not encore and os.path.isfile(chemin_image):
            try:
                os.remove(chemin_image)
            except OSError:
                pass

    if erreurs:
        raise ValueError("Certains fichiers n'ont pas pu être supprimés (ferme VLC s'il les lit) :\n"
                         + "\n".join(erreurs))
    return {"ok": True, "supprimes": len(a_retirer)}


def continuer_regarder():
    elements = []
    for f in lister_films():
        if f["est_serie"]:
            eps = f["episodes"]
            joues = [e for e in eps if e.get("derniere")]
            if not joues:
                continue
            dernier = max(joues, key=lambda e: e["derniere"])
            suivant = next((e for e in eps if (e["saison"], e["episode"]) > (dernier["saison"], dernier["episode"])
                            and not e["vu"]), None) or next((e for e in eps if not e["vu"]), None)
            if not suivant:
                continue
            elements.append({"id": f["id"], "titre": f["titre"], "jaquette_url": f["jaquette_url"],
                             "categorie": f["categorie"], "est_serie": True,
                             "lecture_id": suivant["id"], "date": dernier["derniere"],
                             "saison": suivant["saison"], "episode": suivant["episode"]})
        elif f.get("derniere_lecture") and not f["vu"]:
            elements.append({"id": f["id"], "titre": f["titre"], "jaquette_url": f["jaquette_url"],
                             "categorie": f["categorie"], "est_serie": False,
                             "lecture_id": f["id"], "date": f["derniere_lecture"]})
    elements.sort(key=lambda e: e["date"], reverse=True)
    return elements[:12]


# ---------- SERVEUR HTTP ----------
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _json(self, code, data):
        corps = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def _fichier(self, chemin, type_mime):
        if not os.path.isfile(chemin):
            self.send_error(404)
            return
        with open(chemin, "rb") as f:
            corps = f.read()
        self.send_response(200)
        self.send_header("Content-Type", type_mime)
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def do_GET(self):
        chemin = urlparse(self.path).path
        if chemin in ("/", "/index.html"):
            return self._fichier(os.path.join(RESSOURCES, "index.html"), "text/html; charset=utf-8")
        if chemin == "/api/continuer":
            return self._json(200, continuer_regarder())
        if chemin == "/api/films":
            return self._json(200, lister_films())
        if chemin == "/api/dossiers":
            return self._json(200, lister_dossiers())
        if chemin == "/api/reglages":
            return self._json(200, statut_reglages())
        if chemin.startswith("/covers/"):
            return self._fichier(os.path.join(COVERS_DIR, os.path.basename(chemin)), "image/jpeg")
        self.send_error(404)

    def do_POST(self):
        longueur = int(self.headers.get("Content-Length", 0))
        donnees = json.loads(self.rfile.read(longueur) or b"{}")
        chemin = urlparse(self.path).path
        try:
            if chemin == "/api/continuer-retirer":
                # Retire le film ou la série du bandeau « Continuer à regarder » (fichiers conservés)
                for cible in ids_concernes(int(donnees["id"]), donnees.get("tout")):
                    db_run("UPDATE media SET derniere_lecture=NULL WHERE id=?", (cible,))
                return self._json(200, {"ok": True})
            if chemin == "/api/reglages":
                if "langue" in donnees:
                    if donnees["langue"] not in ("fr", "en", "nl"):
                        raise ValueError("Langue inconnue.")
                    ecrire_reglage("langue", donnees["langue"])
                if "tmdb_cle" in donnees:
                    ecrire_reglage("tmdb_cle", (donnees["tmdb_cle"] or "").strip())
                if "vlc_chemin" in donnees:
                    chemin = (donnees["vlc_chemin"] or "").strip().strip('"')
                    if chemin and (not os.path.isfile(chemin) or not chemin.lower().endswith(".exe")):
                        raise ValueError("Ce fichier n'existe pas. Indique le chemin de vlc.exe.")
                    ecrire_reglage("vlc_chemin", chemin)
                if "lecteur" in donnees:
                    if donnees["lecteur"] not in ("vlc_pc", "vlc_portable", "defaut"):
                        raise ValueError("Lecteur inconnu.")
                    ecrire_reglage("lecteur", donnees["lecteur"])
                return self._json(200, statut_reglages())
            if chemin == "/api/dossiers/ajouter":
                ajouter_dossier(donnees["chemin"], donnees["categorie"])
                return self._json(200, {"ok": True})
            if chemin == "/api/dossiers/supprimer":
                db_run("DELETE FROM dossiers WHERE id=?", (int(donnees["id"]),))
                return self._json(200, {"ok": True})
            if chemin == "/api/serie-recherche":
                fid = int(donnees["id"])
                titre = (donnees.get("titre") or "").strip()
                if not titre:
                    raise ValueError("Indique un titre.")
                ligne = db_rows("SELECT serie_nom FROM media WHERE id=?", (fid,))
                if not ligne or not ligne[0]["serie_nom"]:
                    raise ValueError("Cette fiche n'est pas une série.")
                db_run("UPDATE media SET titre_recherche=? WHERE serie_nom=?",
                       (titre, ligne[0]["serie_nom"]))
                return self._json(200, {"source": completer_fiche(fid)})
            if chemin == "/api/infos-manquantes":
                return self._json(200, completer_manquants())
            if chemin == "/api/scan":
                return self._json(200, {"ajoutes": scanner_dossier(int(donnees["id"]))})
            if chemin == "/api/scan-tous":
                return self._json(200, {"ajoutes": scanner_tous()})
            if chemin == "/api/update":
                fid = int(donnees["id"])
                champs = {k: donnees[k] for k in CHAMPS_EDITABLES if k in donnees}
                if "vu" in champs:
                    champs["vu"] = int(bool(champs["vu"]))
                if champs:
                    sql = "UPDATE media SET " + ", ".join(f"{k}=?" for k in champs) + " WHERE id=?"
                    for cible in ids_concernes(fid, donnees.get("tout")):
                        db_run(sql, list(champs.values()) + [cible])
                return self._json(200, {"ok": True})
            if chemin == "/api/infos":
                fid = int(donnees["id"])
                return self._json(200, {"source": completer_fiche(fid)})
            if chemin == "/api/lancer":
                lecteur = lancer_vlc(int(donnees["id"]))
                db_run("UPDATE media SET derniere_lecture=datetime('now','localtime') WHERE id=?",
                       (int(donnees["id"]),))
                return self._json(200, {"ok": True, "lecteur": lecteur})
            if chemin == "/api/supprimer":
                return self._json(200, supprimer_fiches(int(donnees["id"]),
                                                        donnees.get("tout"), donnees.get("fichier")))
            self.send_error(404)
        except (ValueError, KeyError, IndexError, sqlite3.Error, requests.RequestException) as e:
            self._json(400, {"erreur": str(e)})


def migrer_series():
    for ligne in db_rows("SELECT id, fichier FROM media WHERE serie_nom IS NULL OR serie_nom=''"):
        analyse = analyser_episode(os.path.splitext(os.path.basename(ligne["fichier"]))[0])
        if analyse:
            db_run("UPDATE media SET serie_nom=?, saison=?, episode=? WHERE id=?",
                   (analyse[0], analyse[1], analyse[2], ligne["id"]))


def main():
    init_db()
    migrer_series()
    serveur = None
    for port in range(PORT, PORT + 11):
        try:
            serveur = HTTPServer(("127.0.0.1", port), Handler)
            break
        except OSError:
            continue
    if serveur is None:
        raise SystemExit("Aucun port libre. Ferme les anciennes fenêtres de Ma Vidéothèque et relance.")
    url = f"http://127.0.0.1:{serveur.server_address[1]}/"
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    print(f"Ma Vidéothèque lancée : {url}  (Ctrl+C pour quitter)")
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
