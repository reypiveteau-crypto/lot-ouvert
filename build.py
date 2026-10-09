#!/usr/bin/env python3
"""Lot Ouvert : génère le site statique à partir des données ouvertes du BOAMP.
Aucune dépendance. Lancé chaque nuit par GitHub Actions (.github/workflows/site.yml)."""
import datetime as dt, html, json, os, re, sys, unicodedata, urllib.error, urllib.parse, urllib.request
from collections import defaultdict
from pathlib import Path
import gzip, statistics, time
from zoneinfo import ZoneInfo
import extraire

CACHE_V = 2   # à augmenter quand le format des résultats mis en cache change

SITE = "Lot Ouvert"
BASE = os.environ.get("SITE_URL", "https://example.github.io/lot-ouvert").rstrip("/")
OUT = Path("_site")
JOURS = 75            # fenêtre de publication examinée pour les avis de marché
HIST_DEBUT = dt.date(2024, 1, 1)   # résultats de marché repris depuis cette date
DEPUIS = "depuis janvier 2024"
API = "https://boamp-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/boamp"
REGION = "France"
_D = """01|Ain|dans l'Ain|ARA
02|Aisne|dans l'Aisne|HDF
03|Allier|dans l'Allier|ARA
04|Alpes-de-Haute-Provence|dans les Alpes-de-Haute-Provence|PAC
05|Hautes-Alpes|dans les Hautes-Alpes|PAC
06|Alpes-Maritimes|dans les Alpes-Maritimes|PAC
07|Ardèche|en Ardèche|ARA
08|Ardennes|dans les Ardennes|GES
09|Ariège|en Ariège|OCC
10|Aube|dans l'Aube|GES
11|Aude|dans l'Aude|OCC
12|Aveyron|dans l'Aveyron|OCC
13|Bouches-du-Rhône|dans les Bouches-du-Rhône|PAC
14|Calvados|dans le Calvados|NOR
15|Cantal|dans le Cantal|ARA
16|Charente|en Charente|NAQ
17|Charente-Maritime|en Charente-Maritime|NAQ
18|Cher|dans le Cher|CVL
19|Corrèze|en Corrèze|NAQ
2A|Corse-du-Sud|en Corse-du-Sud|COR
2B|Haute-Corse|en Haute-Corse|COR
21|Côte-d'Or|en Côte-d'Or|BFC
22|Côtes-d'Armor|dans les Côtes-d'Armor|BRE
23|Creuse|dans la Creuse|NAQ
24|Dordogne|en Dordogne|NAQ
25|Doubs|dans le Doubs|BFC
26|Drôme|dans la Drôme|ARA
27|Eure|dans l'Eure|NOR
28|Eure-et-Loir|en Eure-et-Loir|CVL
29|Finistère|dans le Finistère|BRE
30|Gard|dans le Gard|OCC
31|Haute-Garonne|en Haute-Garonne|OCC
32|Gers|dans le Gers|OCC
33|Gironde|en Gironde|NAQ
34|Hérault|dans l'Hérault|OCC
35|Ille-et-Vilaine|en Ille-et-Vilaine|BRE
36|Indre|dans l'Indre|CVL
37|Indre-et-Loire|en Indre-et-Loire|CVL
38|Isère|en Isère|ARA
39|Jura|dans le Jura|BFC
40|Landes|dans les Landes|NAQ
41|Loir-et-Cher|dans le Loir-et-Cher|CVL
42|Loire|dans la Loire|ARA
43|Haute-Loire|en Haute-Loire|ARA
44|Loire-Atlantique|en Loire-Atlantique|PDL
45|Loiret|dans le Loiret|CVL
46|Lot|dans le Lot|OCC
47|Lot-et-Garonne|dans le Lot-et-Garonne|NAQ
48|Lozère|en Lozère|OCC
49|Maine-et-Loire|dans le Maine-et-Loire|PDL
50|Manche|dans la Manche|NOR
51|Marne|dans la Marne|GES
52|Haute-Marne|en Haute-Marne|GES
53|Mayenne|en Mayenne|PDL
54|Meurthe-et-Moselle|en Meurthe-et-Moselle|GES
55|Meuse|dans la Meuse|GES
56|Morbihan|dans le Morbihan|BRE
57|Moselle|en Moselle|GES
58|Nièvre|dans la Nièvre|BFC
59|Nord|dans le Nord|HDF
60|Oise|dans l'Oise|HDF
61|Orne|dans l'Orne|NOR
62|Pas-de-Calais|dans le Pas-de-Calais|HDF
63|Puy-de-Dôme|dans le Puy-de-Dôme|ARA
64|Pyrénées-Atlantiques|dans les Pyrénées-Atlantiques|NAQ
65|Hautes-Pyrénées|dans les Hautes-Pyrénées|OCC
66|Pyrénées-Orientales|dans les Pyrénées-Orientales|OCC
67|Bas-Rhin|dans le Bas-Rhin|GES
68|Haut-Rhin|dans le Haut-Rhin|GES
69|Rhône|dans le Rhône|ARA
70|Haute-Saône|en Haute-Saône|BFC
71|Saône-et-Loire|en Saône-et-Loire|BFC
72|Sarthe|dans la Sarthe|PDL
73|Savoie|en Savoie|ARA
74|Haute-Savoie|en Haute-Savoie|ARA
75|Paris|à Paris|IDF
76|Seine-Maritime|en Seine-Maritime|NOR
77|Seine-et-Marne|en Seine-et-Marne|IDF
78|Yvelines|dans les Yvelines|IDF
79|Deux-Sèvres|dans les Deux-Sèvres|NAQ
80|Somme|dans la Somme|HDF
81|Tarn|dans le Tarn|OCC
82|Tarn-et-Garonne|dans le Tarn-et-Garonne|OCC
83|Var|dans le Var|PAC
84|Vaucluse|dans le Vaucluse|PAC
85|Vendée|en Vendée|PDL
86|Vienne|dans la Vienne|NAQ
87|Haute-Vienne|en Haute-Vienne|NAQ
88|Vosges|dans les Vosges|GES
89|Yonne|dans l'Yonne|BFC
90|Territoire de Belfort|dans le Territoire de Belfort|BFC
91|Essonne|dans l'Essonne|IDF
92|Hauts-de-Seine|dans les Hauts-de-Seine|IDF
93|Seine-Saint-Denis|en Seine-Saint-Denis|IDF
94|Val-de-Marne|dans le Val-de-Marne|IDF
95|Val-d'Oise|dans le Val-d'Oise|IDF
971|Guadeloupe|en Guadeloupe|OM
972|Martinique|en Martinique|OM
973|Guyane|en Guyane|OM
974|La Réunion|à La Réunion|OM
976|Mayotte|à Mayotte|OM"""
DEPS, REG_DE = {}, {}   # code: (nom, préposition + nom) ; code: région
for _l in _D.split("\n"):
    _c, _n, _p, _r = _l.split("|")
    DEPS[_c] = (_n, _p)
    REG_DE[_c] = _r
REGIONS = {"ARA": "Auvergne-Rhône-Alpes", "BFC": "Bourgogne-Franche-Comté", "BRE": "Bretagne", "CVL": "Centre-Val de Loire", "COR": "Corse",
           "GES": "Grand Est", "HDF": "Hauts-de-France", "IDF": "Île-de-France", "NOR": "Normandie", "NAQ": "Nouvelle-Aquitaine",
           "OCC": "Occitanie", "PDL": "Pays de la Loire", "PAC": "Provence-Alpes-Côte d'Azur", "OM": "Outre-mer"}
try:
    CONFIG = json.load(open("config.json", encoding="utf-8"))
except (OSError, ValueError):
    CONFIG = {}
ALERTES = bool(CONFIG.get("supabase_url") and CONFIG.get("supabase_anon_key"))
MOIS = "janvier février mars avril mai juin juillet août septembre octobre novembre décembre".split()
E = html.escape


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def fr(d):
    return f"{d.day}{'er' if d.day == 1 else ''} {MOIS[d.month - 1]} {d.year}"


# ---------- données ----------
def http_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "lot-ouvert/1.0 (site statique, 1 requete par jour)"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


SEL = "idweb,objet,nomacheteur,dateparution,datelimitereponse,code_departement,descripteur_libelle,type_marche,nature,nature_libelle,procedure_libelle,famille_libelle,titulaire,url_avis,donnees"
CACHE = Path("cache/resultats.json.gz")


def flux(where):
    """Lit un export BOAMP ligne par ligne, sans garder le contenu brut en mémoire. Trois essais par requête."""
    url = f"{API}/exports/jsonl?" + urllib.parse.urlencode({"where": where, "select": SEL, "limit": -1})
    for essai in range(3):
        n = 0
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "lot-ouvert/1.0 (site statique, mise a jour quotidienne)"})
            with urllib.request.urlopen(req, timeout=600) as r:
                for ligne in r:
                    if ligne.strip():
                        n += 1
                        yield json.loads(ligne)
            return
        except Exception as e:  # réseau, HTTP, JSON
            print(f"[données] essai {essai + 1} interrompu après {n} lignes : {e!r}")
            if n:               # des lignes ont déjà été rendues : on s'arrête là plutôt que de les doubler
                raise
            time.sleep(20)
    raise RuntimeError("export BOAMP indisponible")


def charger_marches(today):
    """Avis de marché parus sur la fenêtre, normalisés au fil de la lecture."""
    fx = os.environ.get("BOAMP_FIXTURE")
    if fx:
        data = json.load(open(fx, encoding="utf-8"))
        source = data["marches"] if isinstance(data, dict) else data
    else:
        source = flux(f"dateparution >= date'{(today - dt.timedelta(days=JOURS)).isoformat()}' and nature = \"APPEL_OFFRE\"")
    vus, tous, recus = set(), [], 0
    for rec in source:
        recus += 1
        a = normaliser(rec, today)
        if a and a["id"] not in vus:
            vus.add(a["id"])
            tous.append(a)
    return recus, tous


def charger_resultats(today):
    """Résultats de marché depuis HIST_DEBUT. Les jours déjà lus sont gardés en cache : seules les nouveautés sont redemandées."""
    fx = os.environ.get("BOAMP_FIXTURE")
    par_id = {}
    if fx:
        data = json.load(open(fx, encoding="utf-8"))
        for rec in (data["attributions"] if isinstance(data, dict) else []):
            r = normaliser_resultat(rec)
            if r:
                par_id[r["id"]] = r
        return list(par_id.values())
    debut = HIST_DEBUT
    if CACHE.exists():
        try:
            c = json.load(gzip.open(CACHE, "rt", encoding="utf-8"))
            if c.get("version") == CACHE_V:
                for r in c["items"]:
                    r["paru"] = dt.date.fromisoformat(r["paru"])
                    r["fin"] = dt.date.fromisoformat(r["fin"]) if r["fin"] else None
                    par_id[r["id"]] = r
                debut = max(HIST_DEBUT, dt.date.fromisoformat(c["jusqua"]) - dt.timedelta(days=4))
                print(f"[données] cache : {len(par_id)} résultats jusqu'au {c['jusqua']}")
        except Exception as e:
            print(f"[données] cache illisible, relecture complète : {e!r}")
            par_id, debut = {}, HIST_DEBUT
    jusqua, mois = debut, debut
    while mois <= today:                         # un mois par requête : un échec ne fait pas tout recommencer
        suivant = (mois.replace(day=1) + dt.timedelta(days=32)).replace(day=1)
        n = 0
        for rec in flux(f"dateparution >= date'{mois.isoformat()}' and dateparution < date'{suivant.isoformat()}' and nature = \"ATTRIBUTION\""):
            n += 1
            r = normaliser_resultat(rec)
            if r:
                par_id[r["id"]] = r
        print(f"[données] résultats {mois.isoformat()} → {suivant.isoformat()} : {n}")
        jusqua, mois = min(today, suivant - dt.timedelta(days=1)), suivant
        _sauver_cache(par_id, jusqua)            # sauvegarde à chaque mois lu
    return list(par_id.values())


def _sauver_cache(par_id, jusqua):
    CACHE.parent.mkdir(exist_ok=True)
    items = [dict(r, paru=r["paru"].isoformat(), fin=r["fin"].isoformat() if r["fin"] else None) for r in par_id.values()]
    with gzip.open(CACHE, "wt", encoding="utf-8") as f:
        json.dump({"version": CACHE_V, "jusqua": jusqua.isoformat(), "items": items}, f, ensure_ascii=False)


def liste(v):
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    s = str(v).strip()
    if s.startswith("["):
        try:
            return liste(json.loads(s))
        except ValueError:
            pass
    return [x.strip() for x in re.split(r"[;|]", s) if x.strip()]


def parse_date(v):
    if not v:
        return None
    try:
        return dt.date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def normaliser(rec, today):
    r = {re.sub(r"[^a-z]", "", k.lower()): v for k, v in rec.items()}
    nature = f"{r.get('nature') or ''} {r.get('naturelibelle') or ''}".lower()
    if any(m in nature for m in ("attribution", "rectificatif", "annulation", "résultat", "resultat", "modification")):
        return None
    limite, paru = parse_date(r.get("datelimitereponse")), parse_date(r.get("dateparution"))
    idweb, objet = str(r.get("idweb") or "").strip(), " ".join(html.unescape(str(r.get("objet") or "")).split())
    if not (idweb and objet and limite):
        return None
    if (limite - today).days > 240:   # date limite invraisemblable : erreur de saisie dans l'avis
        return None
    deps = [c for c in (d.zfill(2) for d in liste(r.get("codedepartement"))) if c in DEPS]
    if not deps:
        return None
    url = str(r.get("urlavis") or "")
    if not url.startswith("https://www.boamp.fr/"):
        url = "https://www.boamp.fr/pages/avis/?q=" + urllib.parse.quote(f'idweb:"{idweb}"')
    return {
        "id": idweb, "objet": objet, "acheteur": " ".join(html.unescape(str(r.get("nomacheteur") or "Acheteur non indiqué")).split()),
        "paru": paru, "limite": limite, "reste": (limite - today).days, "deps": deps,
        "metiers": liste(r.get("descripteurlibelle")), "type": ", ".join(t.capitalize() for t in liste(r.get("typemarche"))),
        "procedure": str(r.get("procedurelibelle") or "").strip(), "url": url,
        "famille": str(r.get("famillelibelle") or "").strip(),
        "d": extraire.details_marche(r.get("donnees")), "siret": extraire.siret_acheteur(r.get("donnees")),
        "contact": extraire.contact_acheteur(r.get("donnees")),
    }


def normaliser_resultat(rec):
    """Un résultat de marché (avis d'attribution) : qui a gagné, combien d'offres, quel montant, quand c'est publié."""
    r = {re.sub(r"[^a-z]", "", k.lower()): v for k, v in rec.items()}
    idweb, objet, paru = str(r.get("idweb") or "").strip(), " ".join(html.unescape(str(r.get("objet") or "")).split()), parse_date(r.get("dateparution"))
    if not (idweb and objet and paru):
        return None
    d = extraire.details_attribution(r.get("donnees"))
    fin = extraire.fin_contrat(r.get("donnees"), paru)
    vus, gagnants = set(), []
    for g in liste(r.get("titulaire")) + d.get("titulaires", []):
        g = " ".join(html.unescape(g).split())
        if g and slug(g) not in vus and len(g) < 120 and "@" not in g and not re.search(r"\d{9,}", g.replace(" ", "")) \
                and not slug(g).startswith(("inconnu", "non-renseigne", "sans-objet")):
            vus.add(slug(g))
            gagnants.append(g)
    url = str(r.get("urlavis") or "")
    if not url.startswith("https://www.boamp.fr/"):
        url = "https://www.boamp.fr/pages/avis/?q=" + urllib.parse.quote(f'idweb:"{idweb}"')
    return {"id": idweb, "objet": objet, "acheteur": " ".join(html.unescape(str(r.get("nomacheteur") or "")).split()), "paru": paru,
            "deps": [c for c in (x.zfill(2) for x in liste(r.get("codedepartement"))) if c in DEPS],
            "metiers": [slug(m) for m in liste(r.get("descripteurlibelle"))], "gagnants": gagnants,
            "texte": re.sub(r"(?:\+33|0)\s*[1-9](?:[\s.-]*\d{2}){4}", "", re.sub(r"\S+@\S+", "", d.get("texte", ""))),
            "offres": d.get("offres", []), "montant": d.get("montant"), "url": url, "siret": extraire.siret_acheteur(r.get("donnees")),
            "fin": fin[0] if fin else None, "duree": fin[1] if fin else ""}


def euros(m):
    return f"{int(round(m)):,}".replace(",", "\u202f") + "\u00a0€"


def mois_annee(d):
    return f"{MOIS[d.month - 1]} {d.year}"


# ---------- rendu ----------
JOURS_SEM = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]
MOIS_C = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]


def court(t, n=68):
    t = " ".join(t.split())
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0].rstrip(" ,;:-(") + "…"


def dans(r):
    return "aujourd'hui" if r == 0 else "demain" if r == 1 else f"dans {r} jours"


def page(chemin, titre, desc, corps, index=True, fil=(), large=False):
    canon = f"{BASE}/{chemin}".rstrip("/") + "/" if chemin else BASE + "/"
    prof = chemin.count("/") + 1 if chemin else 0
    rel = "../" * prof
    crumbs = " <span aria-hidden=\"true\">/</span> ".join(f'<a href="{rel}{u}">{E(t)}</a>' for t, u in fil)
    doc = f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(titre)}</title><meta name="description" content="{E(desc)}">
<meta property="og:title" content="{E(titre)}"><meta property="og:description" content="{E(desc)}"><meta property="og:type" content="website">
<meta name="google-site-verification" content="Bn20ldA-SUhsySdq8ciYJMOjD6Uqmb6ymF6bQsDG6r8">
<link rel="canonical" href="{E(canon)}">{'' if index else '<meta name="robots" content="noindex,follow">'}
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600&family=Barlow+Condensed:wght@600;700&display=swap">
<link rel="stylesheet" href="{rel}style.css"></head><body>
<a class="saut" href="#contenu">Aller au contenu</a>
<header class="tete"><div class="cadre"><a class="marque" href="{rel or './'}"><span class="pastille" aria-hidden="true"></span>{SITE}</a>
<nav aria-label="Navigation principale"><a href="{rel}#departements">Départements</a><a href="{rel}metiers/">Métiers</a><a href="{rel}relances/">Bientôt relancés</a><a href="{rel}pro/">Version Pro</a><a href="{rel}a-propos/">À propos</a>{f'<a class="inscrire" href="{rel}inscription/">Alertes gratuites</a>' if ALERTES else ''}</nav></div></header>
<main id="contenu" class="cadre{' large' if large else ''}">{f'<nav class="fil" aria-label="Fil d’Ariane">{crumbs}</nav>' if crumbs else ''}
{corps}
</main>
<script src="{rel}site.js" defer></script>{f'<script src="{rel}alerte.js" defer></script>' if ALERTES else ''}
<footer class="pied"><div class="cadre"><p><b>{SITE}</b> reprend les annonces et les résultats du Bulletin officiel des annonces des marchés publics (BOAMP), données ouvertes de la DILA. Mise à jour du {fr(TODAY)}. Seul l'avis publié sur boamp.fr fait foi.</p>
<p><a href="{rel}a-propos/">D'où viennent les données, mentions légales</a></p></div></footer></body></html>"""
    d = OUT / chemin
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(doc, encoding="utf-8")
    if index:
        SITEMAP.append(canon)


def tuile(a):
    """La date limite, présentée comme une page de calendrier : c'est l'information que tout le monde cherche en premier."""
    l, r = a["limite"], a["reste"]
    return f"""<div class="tuile{' presse' if r <= 7 else ''}"><span class="t-mois">{JOURS_SEM[l.weekday()]} {MOIS_C[l.month - 1]}</span><span class="t-jour">{l.day}</span><span class="t-reste">{dans(r)}</span></div>"""


def puces(a):
    d, p = a["d"], []
    if d.get("montant"):
        p.append(f"Estimé à {euros(d['montant'])}")
    if d.get("lots"):
        p.append(f"{len(d['lots'])} lots")
    if d.get("duree"):
        p.append(f"Durée {d['duree']}")
    if d.get("visite"):
        p.append("Visite obligatoire")
    return p


def carte(a, rel=""):
    lieux = ", ".join(DEPS[c][0] for c in a["deps"][:3]) + (f" et {len(a['deps']) - 3} autres" if len(a["deps"]) > 3 else "")
    n = len(HIST.get(a["id"], []))
    histo = f"{n} marché{'s' if n > 1 else ''} déjà attribué{'s' if n > 1 else ''} par cet acheteur" if n else ""
    p = "".join(f"<li>{E(x)}</li>" for x in puces(a))
    return f"""<article class="avis" data-type="{E(a['type'].split(',')[0].lower())}">
{tuile(a)}
<div class="corps"><h3><a href="{rel}avis/{E(a['id'])}/">{E(a['objet'])}</a></h3>
<p class="qui"><b>{E(a['acheteur'])}</b><span>{E(a['type'])}{', ' + E(lieux) if lieux else ''}</span></p>
{f'<ul class="puces">{p}</ul>' if p else ''}
{f'<p class="histo">{histo}</p>' if histo else ''}</div></article>"""


def bloc_liste(avis, rel="", filtres=True):
    if not avis:
        return '<p class="vide">Aucune annonce ouverte aujourd\'hui dans cette rubrique. La page est mise à jour chaque matin.</p>'
    cartes = "\n".join(carte(a, rel) for a in sorted(avis, key=lambda a: (a["limite"], a["id"])))
    barre = '<div class="filtres" hidden><div class="types" role="group" aria-label="Type de marché"></div><label class="cherche"><span>Chercher dans cette liste</span><input type="search" placeholder="un mot, un acheteur, une ville"></label></div><p class="vide aucun" hidden>Aucune annonce ne correspond à ces filtres.</p>' if filtres and len(avis) >= 6 else ""
    return f'<div class="liste">{barre}{cartes}</div>'


def liens(items, classe="liens"):
    """items : (libellé, url, nombre)"""
    return f'<ul class="{classe}">' + "".join(f'<li><a href="{u}"><span>{E(t)}</span><b>{n}</b></a></li>' for t, u, n in items) + "</ul>"


def n_avis(n):
    return f"{n} annonce{'s' if n > 1 else ''} ouverte{'s' if n > 1 else ''}"


def texte_libre(t):
    """Les résultats rédigés en texte libre arrivent sans retours à la ligne : on en remet un avant chaque lot."""
    t = re.sub(r"(?<=\S)\s*(?=Lot\s*(?:N\s*°|n\s*°|\d))", "\n", t)
    return "<br>".join(E(x.strip()) for x in t.split("\n") if x.strip())


def nom_lie(g, rel):
    k = slug(g)
    return f'<a href="{rel}entreprise/{k}/">{E(g)}</a>' if k in FICHES else E(g)


def ligne_resultat(r, rel="../../"):
    if r["gagnants"]:
        qui = f"<p class=\"gagne\">Attribué à <b>{', '.join(nom_lie(g, rel) for g in r['gagnants'][:6])}</b>{' et d’autres entreprises' if len(r['gagnants']) > 6 else ''}</p>"
    elif r["texte"]:
        qui = f"<p class=\"gagne libre\">{texte_libre(r['texte'])}</p>"
    else:
        qui = "<p class=\"gagne\">Entreprise retenue non indiquée dans les données</p>"
    plus = []
    if r["offres"]:
        o = r["offres"]
        plus.append(f"{o[0]} offre{'s' if o[0] > 1 else ''} reçue{'s' if o[0] > 1 else ''}" if len(set(o)) == 1 else f"{min(o)} à {max(o)} offres reçues selon les lots")
    if r["montant"]:
        plus.append(f"Montant publié : {euros(r['montant'])}")
    p = "".join(f"<li>{E(x)}</li>" for x in plus)
    return f"""<li class="res"><span class="quand">{MOIS_C[r['paru'].month - 1]} {r['paru'].year}</span><div><a href="{E(r['url'])}" rel="nofollow noopener">{E(r['objet'])}</a>
{qui}{f'<ul class="puces">{p}</ul>' if p else ''}</div></li>"""


def bloc_classement(c, s, m, prep):
    """Qui a remporté les marchés d'un métier dans un département, d'après les résultats publiés."""
    res = RES_COMBO.get((c, s), [])
    compte, forme, dernier = {}, {}, {}
    for r in res:
        for g in r["gagnants"]:
            k = slug(g)
            compte[k] = compte.get(k, 0) + 1
            forme.setdefault(k, g)
            if k not in dernier or r["paru"] > dernier[k]["paru"]:
                dernier[k] = r
    if not compte:
        return ""
    top = sorted(compte, key=lambda k: (-compte[k], forme[k]))[:10]
    lignes = "".join(f"<tr><td>{nom_lie(forme[k], '../../')}</td><td class='n'>{compte[k]}</td><td>{E(dernier[k]['acheteur'])}, {MOIS_C[dernier[k]['paru'].month - 1]} {dernier[k]['paru'].year}</td></tr>" for k in top)
    offres = [r["offres"][0] for r in res if r["offres"]]
    stat = ""
    if len(offres) >= 3:
        med = int(statistics.median(offres))
        stat = f'<p class="repere"><b>{med}</b><span>offre{"s" if med > 1 else ""} reçue{"s" if med > 1 else ""} par marché, en médiane, sur les {len(offres)} résultats qui donnent ce chiffre</span></p>'
    return f"""<section id="titulaires" class="bloc"><h2>Qui a remporté les marchés « {E(m)} » {prep}</h2>
<p class="intro">{len(res)} résultat{'s' if len(res) > 1 else ''} publié{'s' if len(res) > 1 else ''} {DEPUIS}. Ce sont les entreprises que vous aurez le plus de chances de retrouver en face de vous.</p>
{stat}
<div class="tablo"><table><thead><tr><th>Entreprise retenue</th><th class="n">Marchés</th><th>Dernier marché remporté</th></tr></thead><tbody>{lignes}</tbody></table></div>
<p class="note">D'après les résultats publiés au Bulletin officiel. Tous les marchés attribués n'y sont pas publiés.</p></section>"""


def dans_mois(fin):
    j = (fin - TODAY).days
    return "échu récemment" if j < 0 else "dans moins d'un mois" if j < 46 else f"dans {round(j / 30.44)} mois"


def carte_relance(r, rel):
    """Un marché attribué dont la période arrive à son terme : il sera probablement remis en concurrence."""
    f = r["fin"]
    lieux = ", ".join(DEPS[c][0] for c in r["deps"][:3]) + (f" et {len(r['deps']) - 3} autres" if len(r["deps"]) > 3 else "")
    p = [x for x in (f"Durée {r['duree']}" if r["duree"] else "", f"Montant publié : {euros(r['montant'])}" if r["montant"] else "",
                     (f"{r['offres'][0]} offre{'s' if r['offres'][0] > 1 else ''} reçue{'s' if r['offres'][0] > 1 else ''} la dernière fois" if r["offres"] else "")) if x]
    deja = DEJA.get(r["id"])
    return f"""<article class="avis relance" data-type="{E(DEPS[r['deps'][0]][0].lower()) if r['deps'] else ''}">
<div class="tuile fin"><span class="t-mois">{f.year}</span><span class="t-jour">{MOIS_C[f.month - 1]}</span><span class="t-reste">{dans_mois(f)}</span></div>
<div class="corps"><h3><a href="{E(r['url'])}" rel="nofollow noopener">{E(r['objet'])}</a></h3>
<p class="qui"><b>{E(r['acheteur'])}</b><span>{E(lieux)}</span></p>
<p class="tenu">{'Détenu par <b>' + ', '.join(nom_lie(g, rel) for g in r['gagnants'][:4]) + '</b>' + (' et d’autres' if len(r['gagnants']) > 4 else '') if r['gagnants'] else 'Titulaire actuel non indiqué dans les données'}</p>
{f'<ul class="puces">{"".join(f"<li>{E(x)}</li>" for x in p)}</ul>' if p else ''}
{f'<p class="histo"><a href="{rel}avis/{E(deja)}/">Une annonce de cet acheteur dans ce métier est ouverte en ce moment</a></p>' if deja else ''}</div></article>"""


def bloc_relances(liste, rel, titre, intro, maxi=8, filtres=False):
    if not liste:
        return ""
    cartes = "".join(carte_relance(r, rel) for r in liste[:maxi])
    barre = '<div class="filtres" hidden><div class="types" role="group" aria-label="Département"></div><label class="cherche"><span>Chercher dans cette liste</span><input type="search" placeholder="un mot, un acheteur, une entreprise"></label></div><p class="vide aucun" hidden>Aucun marché ne correspond à ces filtres.</p>' if filtres else ""
    suite = f'<p><a class="suite" href="{rel}relances/">Voir tous les marchés qui arrivent à échéance</a></p>' if not filtres and len(liste) > maxi else ""
    return f"""<section class="bloc" id="relances"><h2>{titre}</h2><p class="intro">{intro}</p><div class="liste">{barre}{cartes}</div>{suite}
<p class="note">Date calculée à partir de la durée ou de la date de fin publiée dans le résultat du marché. Un marché peut être reconduit sans nouvelle annonce, et la durée publiée couvre parfois déjà les reconductions : c'est un repère, pas une certitude.</p></section>"""


def lecture_rapide(a, hist, memes):
    """Trois repères pour décider vite : la concurrence habituelle, l'entreprise en place, le poids du prix."""
    lignes = []
    off = [r["offres"][0] for r in hist if r["offres"]]
    cle = next(((c, slug(m)) for m in a["metiers"] for c in a["deps"] if len([r for r in RES_COMBO.get((c, slug(m)), []) if r["offres"]]) >= 3), None)
    if len(off) >= 2:
        med = int(statistics.median(off))
        mot = "peu disputé" if med <= 2 else "disputé" if med <= 5 else "très disputé"
        lignes.append(("Concurrence", f"<b>{med} offre{'s' if med > 1 else ''}</b> en médiane chez cet acheteur, {mot}", f"sur {len(off)} de ses résultats qui donnent ce chiffre"))
    elif cle:
        o2 = [r["offres"][0] for r in RES_COMBO[cle] if r["offres"]]
        med = int(statistics.median(o2))
        lignes.append(("Concurrence", f"<b>{med} offre{'s' if med > 1 else ''}</b> en médiane dans ce métier {DEPS[cle[0]][1]}", f"sur {len(o2)} résultats, cet acheteur n'en ayant pas assez publié"))
    avec = [r for r in memes if r["gagnants"]]
    if avec:
        dernier = avec[0]
        compte = defaultdict(int)
        for r in avec[:6]:
            for g in r["gagnants"]:
                compte[slug(g)] += 1
        k = max(compte, key=compte.get)
        nomk = next(g for r in avec for g in r["gagnants"] if slug(g) == k)
        if compte[k] >= 2 and len(avec) >= 2:
            lignes.append(("Entreprise en place", f"<b>{nom_lie(nomk, '../../')}</b> a remporté {compte[k]} des {min(6, len(avec))} derniers marchés comparables", "même acheteur, même métier"))
        else:
            lignes.append(("Dernier titulaire", f"<b>{', '.join(nom_lie(g, '../../') for g in dernier['gagnants'][:3])}</b>", f"marché comparable attribué en {MOIS_C[dernier['paru'].month - 1]} {dernier['paru'].year}"))
    prix = next(((p, u) for n, p, u in a["d"].get("criteres", []) if p and re.search(r"prix|co[uû]t|financ|tarif", n, flags=re.I)), None)
    if prix:
        tot = sum(p or 0 for _, p, _ in a["d"]["criteres"])
        part = round(100 * prix[0] / tot) if tot else None
        if part:
            lignes.append(("Poids du prix", f"<b>{part} %</b> de la note" + (", le reste se joue sur votre dossier" if part < 60 else ", le prix décide presque tout"), "d'après les critères publiés" + (" pour le premier lot" if a["d"].get("criteres_premier_lot") else "")))
    if not lignes:
        return ""
    return '<section class="bloc"><h2>Lecture rapide</h2><ul class="reperes">' + "".join(f"<li><span>{t}</span><p>{v}</p><i>{n}</i></li>" for t, v, n in lignes) + '</ul><p class="note">Fonction Pro, en accès libre pendant le lancement. Ces repères décrivent le passé de cet acheteur, ils ne prédisent pas le résultat.</p></section>'


def page_avis(a, metiers, dslug):
    d, hist, r = a["d"], HIST.get(a["id"], []), a["reste"]
    dl = []
    if d.get("montant"):
        dl.append(("Montant estimé", euros(d["montant"])))
    if d.get("duree"):
        dl.append(("Durée du marché", d["duree"]))
    if d.get("lieu"):
        dl.append(("Lieu", E(d["lieu"])))
    if d.get("visite"):
        dl.append(("Visite", E(d["visite"]) if isinstance(d["visite"], str) else "Une visite obligatoire est mentionnée dans l'avis."))
    if d.get("criteres"):
        total = sum(p or 0 for _, p, _ in d["criteres"])
        crit = "".join(f"<li><span>{E(n[:1].upper() + n[1:])}</span>{f'<b>{p:g} {u}</b><i style=\"--p:{min(100, 100 * p / total if total else 0):.0f}%\"></i>' if p else ''}</li>" for n, p, u in d["criteres"])
        dl.append(("Comment l'offre sera notée" + (" (premier lot)" if d.get("criteres_premier_lot") else ""), f'<ul class="criteres">{crit}</ul>'))
    if d.get("lots"):
        L = d["lots"]
        suite = f'<details><summary>Voir les {len(L) - 6} autres lots</summary><ol class="lots" start="7">' + "".join(f"<li>{E(x)}</li>" for x in L[6:]) + "</ol></details>" if len(L) > 7 else ""
        dl.append((f"{len(L)} lots", '<ol class="lots">' + "".join(f"<li>{E(x)}</li>" for x in (L[:6] if suite else L)) + "</ol>" + suite))
    if d.get("references"):
        dl.append(("Ce que l'acheteur demande pour juger votre entreprise", E(d["references"])))
    essentiel = "".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in dl) or "<div><dt>Détails</dt><dd>Cet avis ne fournit pas d'informations détaillées exploitables. Tout est dans l'avis officiel.</dd></div>"
    lieux = ", ".join(f"{DEPS[c][0]} ({c})" for c in a["deps"])
    mes = {slug(m) for m in a["metiers"]}
    memes = [x for x in hist if set(x["metiers"]) & mes]
    autres = [x for x in hist if x not in memes]
    if hist:
        histo = f'<p class="intro">{len(hist)} résultat{"s" if len(hist) > 1 else ""} publié{"s" if len(hist) > 1 else ""} par cet acheteur {DEPUIS}. Regardez qui il a retenu et combien d\'entreprises avaient répondu.</p>'
        if memes:
            histo += f'<h3 class="sous">Dans le même métier</h3><ul class="resultats">{"".join(ligne_resultat(x) for x in memes[:10])}</ul>'
        reste_n = max(0, 12 - len(memes[:10]))
        if autres and reste_n:
            histo += f'<h3 class="sous">{"Ses autres marchés" if memes else "Ses derniers marchés"}</h3><ul class="resultats">{"".join(ligne_resultat(x) for x in autres[:reste_n])}</ul>'
        vus = len(memes[:10]) + len(autres[:reste_n])
        if len(hist) > vus:
            histo += f'<p class="note">Les {vus} plus utiles sur {len(hist)} sont affichés.</p>'
    else:
        histo = f'<p class="vide">Aucun résultat publié au Bulletin officiel par cet acheteur {DEPUIS}. Cela ne veut pas dire qu\'il n\'a rien attribué : tous les résultats n\'y sont pas publiés.</p>'
    classement = ""
    for m in a["metiers"]:
        for c in a["deps"]:
            b = bloc_classement(c, slug(m), m, DEPS[c][1])
            if b:
                classement = b
                break
        if classement:
            break
    rubriques = "".join(f'<a href="../../{dslug[c]}/{slug(m)}/">{E(m)} {DEPS[c][1]}</a>' for m in a["metiers"][:4] for c in a["deps"][:1])
    faits = "".join(f"<li>{E(x)}</li>" for x in (a["type"], a["procedure"], a["famille"]) if x)
    corps = f"""<div class="fiche">
<div class="f-tete"><h1>{E(a['objet'])}</h1><p class="f-qui"><b>{E(a['acheteur'])}</b><span>{E(lieux)}</span></p><ul class="puces">{faits}</ul></div>
<aside class="f-cote">{tuile(a)}
<p class="f-date">À remettre avant le <b>{fr(a['limite'])}</b></p>
{f'<a class="bouton" href="{E(d["dossier"])}" rel="nofollow noopener">Télécharger le dossier</a><p class="note">Les documents à lire et à remplir pour répondre, sur la plateforme de l’acheteur.</p>' if d.get('dossier') else ''}
{f'<a class="bouton second" href="../../inscription/?m={slug(a["metiers"][0])}&amp;d={a["deps"][0]}">Être prévenu des prochaines annonces</a><p class="note">Alerte gratuite par e-mail pour ce métier et ce département.</p>' if ALERTES and a["metiers"] and a["deps"] else ''}
<a class="bouton second" href="{E(a['url'])}" rel="nofollow noopener">Lire l'avis officiel</a><p class="note">Avis n° {E(a['id'])} sur boamp.fr{f", publié le {fr(a['paru'])}" if a['paru'] else ''}.</p>{f'<div class="contact"><b>Contacter l’acheteur</b>{"<span>" + E(a["contact"]["mail"]) + "</span>" if a["contact"].get("mail") else ""}{"<span>" + E(a["contact"]["tel"]) + "</span>" if a["contact"].get("tel") else ""}</div>' if a.get("contact") else ''}
<p class="pro-mini"><a href="../../pro/">Version Pro, bientôt disponible</a><span>Historique complet, suivi des concurrents, alertes quotidiennes.</span></p></aside>
<div class="f-corps">
{lecture_rapide(a, hist, memes)}
<section class="bloc"><h2>L'essentiel de l'annonce</h2><dl class="essentiel">{essentiel}</dl></section>
<section class="bloc"><h2>Ce que cet acheteur a déjà attribué</h2>{histo}</section>
{classement}
{f'<section class="bloc"><h2>Annonces du même type</h2><p class="rubriques">{rubriques}</p></section>' if rubriques else ''}
</div></div>"""
    fil = [("Accueil", "")] + ([(DEPS[a["deps"][0]][0], f"{dslug[a['deps'][0]]}/")] if a["deps"] else [])
    page(f"avis/{a['id']}", f"{court(a['objet'])} | {SITE}", court(f"{a['acheteur']} : à remettre avant le {fr(a['limite'])}. L'essentiel de l'annonce, le dossier à télécharger et les marchés déjà attribués par cet acheteur.", 158), corps, fil=fil, large=True)


# Une fiche n'est créée que pour une entreprise, jamais pour une personne : un nom qui contient un prénom courant
# et aucune forme de société est écarté.
SOCIETE = set("sarl sas sasu sa eurl sci scop scp selarl snc gie ei eirl ste societe ets etablissement etablissements entreprise entreprises groupe group "
              "association asso cabinet agence atelier ateliers bureau compagnie cie france services service travaux batiment tp btp conseil conseils "
              "formation institut centre chambre mutuelle assurance assurances banque caisse cooperative coop holding international industrie industries "
              "ingenierie architecture architectes paysage transports transport energie energies environnement solutions systemes distribution "
              "construction constructions menuiserie peinture electricite plomberie maconnerie nettoyage proprete restauration imprimerie garage "
              "laboratoire laboratoires pharmacie clinique hopital mairie commune region departement syndicat universite lycee college greta afpa".split())
PRENOMS = set("adrien agnes alain albert alexandre alexis alice aline amandine andre anne annie anthony antoine arnaud arthur audrey aurelie aurelien "
              "baptiste benjamin benoit bernard bertrand brigitte bruno camille carole caroline catherine cecile cedric celine chantal charles charlotte "
              "christelle christian christiane christine christophe claire claude claudine clement colette corinne cyril damien daniel danielle david "
              "delphine denis denise didier dominique edouard elisabeth elise elodie emilie emmanuel emmanuelle eric estelle etienne eugenie evelyne "
              "fabien fabrice fabienne florence florent florian francis franck francois francoise frederic frederique gabriel gael genevieve geoffrey "
              "georges gerald gerard ghislaine gilbert gilles guillaume guy helene henri herve hugo isabelle jacqueline jacques jean jeanne jeremie "
              "jeremy jerome joel joelle jonathan joseph josiane julie julien juliette justine karine kevin laetitia laure laurence laurent lea leon "
              "lionel loic louis louise luc lucas lucie lucien ludovic madeleine marc marcel marguerite marie marine marion martine mathieu mathilde "
              "matthieu maurice maxime melanie michel michele micheline mickael monique muriel myriam nadine nathalie nicolas nicole noel odile olivier "
              "pascal pascale patrice patricia patrick paul paulette pauline philippe pierre quentin raphael raymond regis remi remy rene renee richard "
              "robert roger roland romain samuel sandra sandrine sebastien serge simon simone solange sophie stephane stephanie suzanne sylvain sylvie "
              "theo thierry thomas valerie veronique victor vincent virginie xavier yann yannick yves yvette yvonne".split())


def est_entreprise(nom):
    mots = slug(nom).split("-")
    return bool(set(mots) & SOCIETE) or not (set(mots) & PRENOMS)


PRO_PLUS = [
    ("Les marchés bientôt relancés", "Vous voyez les marchés de votre métier dont le contrat se termine dans les douze mois, avec l'entreprise qui les détient. Vous vous préparez avant que l'annonce ne paraisse.", "relances/"),
    ("Une lecture rapide de chaque annonce", "Combien d'entreprises répondent d'habitude chez cet acheteur, qui détient le marché, et ce que pèse le prix dans la note. Vous décidez en une minute si le dossier vaut vos trois jours de travail.", ""),
    ("Le suivi de vos concurrents", "Pour chaque entreprise : les marchés remportés, chez quels acheteurs, et ceux qu'elle devra bientôt remettre en jeu.", ""),
    ("L'historique complet de chaque acheteur", "Tous ses marchés attribués depuis janvier 2024, avec les entreprises retenues, le nombre d'offres reçues et les montants publiés.", ""),
    ("Le contact direct de l'acheteur", "L'e-mail et le téléphone du service qui passe le marché, pour poser vos questions avant de répondre.", ""),
    ("Des alertes sur mesure", "Chaque matin, sur plusieurs métiers et départements, par acheteur, et quand un marché de votre métier approche de son terme. Cette fonction n'est pas encore construite.", ""),
]


def page_pro():
    plus = "".join(f"<li><b>{E(t)}</b><span>{E(d)}</span>{f'<a href=\"../{u}\">Voir un exemple</a>' if u else ''}</li>" for t, d, u in PRO_PLUS)
    attente = f"""<form class="alerte attente" novalidate><h2>Être prévenu de l'ouverture</h2>
<p class="intro">Laissez votre adresse : vous recevrez un seul e-mail, le jour où la version Pro ouvre.</p>
<div class="champ"><label for="al-email">Votre adresse e-mail</label><input id="al-email" name="email" type="email" autocomplete="email" required>
<input name="site" type="text" tabindex="-1" autocomplete="off" class="pot" aria-hidden="true"><button type="submit" class="bouton">Prévenez-moi</button></div>
<p class="etat" role="status"></p><p class="note">Sans engagement et sans paiement. Un e-mail de confirmation vous est envoyé dans l'heure.</p></form>""" if ALERTES else ""
    page("pro", f"Version Pro, bientôt disponible | {SITE}", f"La version Pro de {SITE} : historique complet des acheteurs, suivi des concurrents, alertes quotidiennes. Bientôt disponible.",
         f"""<div class="pro-tete"><p class="etiquette">Bientôt disponible</p><h1>Savoir avant les autres quels marchés vont s'ouvrir, et lesquels valent le coup</h1>
<p class="intro">Répondre à un marché public prend des jours. La version Pro vous montre les marchés de votre métier qui arrivent à échéance, qui les détient, combien d'entreprises répondent d'habitude, et ce que pèse le prix. Vous choisissez vos batailles au lieu de répondre à l'aveugle.</p>
<p class="intro"><b>{len(RELANCES)} marchés arrivent à échéance dans les douze mois</b> en France, d'après les résultats publiés. <a href="../relances/">Les voir</a></p></div>
<div class="pro-grille"><section class="bloc"><h2>Ce que la version Pro ajoute</h2><ul class="pro-plus">{plus}</ul></section>
<aside class="pro-cote"><div class="prix"><b>9 €</b><span>par mois, prix envisagé, sans engagement</span></div>
<p class="note">Le prix et la date d'ouverture ne sont pas encore fixés. Aucun paiement n'est possible pour le moment.</p>{attente}</aside></div>
<section class="bloc"><h2>Ce qui reste gratuit</h2><p class="intro">La liste des annonces par métier et par département, l'essentiel de chaque annonce, le lien vers le dossier à télécharger et une alerte par semaine. Pendant le lancement, les fonctions Pro déjà construites sont en accès libre : marchés bientôt relancés, lecture rapide, historique des acheteurs, fiches des entreprises et contacts.</p></section>""",
         fil=[("Accueil", "")])


def pages_entreprises(resultats, metiers):
    """Une fiche par entreprise retenue au moins deux fois : ce qu'elle a gagné, chez qui, dans quels métiers."""
    par = defaultdict(list)
    forme = {}
    for r in resultats:
        for g in r["gagnants"]:
            par[slug(g)].append(r)
            forme.setdefault(slug(g), g)
    for k in FICHES:
        res = sorted(par[k], key=lambda r: r["paru"], reverse=True)
        nom = forme[k]
        ach, met, dep = defaultdict(int), defaultdict(int), defaultdict(int)
        for r in res:
            ach[r["acheteur"]] += 1
            for m in r["metiers"]:
                if m in metiers:
                    met[m] += 1
            for c in r["deps"]:
                dep[c] += 1
        top_a = "".join(f"<li><span>{E(a)}</span><b>{n}</b></li>" for a, n in sorted(ach.items(), key=lambda x: -x[1])[:8])
        top_m = "".join(f"<li>{E(metiers[m])}</li>" for m, _ in sorted(met.items(), key=lambda x: -x[1])[:10])
        top_d = ", ".join(DEPS[c][0] for c, _ in sorted(dep.items(), key=lambda x: -x[1]))
        lignes = "".join(f"""<li class="res"><span class="quand">{MOIS_C[r['paru'].month - 1]} {r['paru'].year}</span><div><a href="{E(r['url'])}" rel="nofollow noopener">{E(r['objet'])}</a>
<p class="gagne">{E(r['acheteur'])}{' avec ' + ', '.join(nom_lie(g, '../../') for g in r['gagnants'][:5] if slug(g) != k) if len(r['gagnants']) > 1 else ''}</p></div></li>""" for r in res[:40])
        corps = f"""<p class="etiquette">Fonction Pro, en accès libre pendant le lancement</p>
<h1>{E(nom)}</h1>
<p class="intro">{len(res)} marchés publics remportés {DEPUIS}, d'après les résultats publiés au Bulletin officiel{', ' + E(top_d) if top_d else ''}.</p>
<div class="deux"><section class="bloc"><h2>Ses acheteurs</h2><ul class="compteurs">{top_a}</ul></section>
{f'<section class="bloc"><h2>Ses métiers</h2><ul class="puces">{top_m}</ul></section>' if top_m else ''}</div>
{bloc_relances(REL_ENT.get(k, []), "../../", "Ses marchés qui arrivent à échéance", "Les marchés détenus par cette entreprise dont la période se termine dans les douze mois : ce sont ceux qui peuvent être remis en concurrence.", 6)}
<section class="bloc"><h2>Les marchés remportés</h2><ul class="resultats">{lignes}</ul>
{f'<p class="note">Les 40 plus récents sur {len(res)} sont affichés.</p>' if len(res) > 40 else ''}
<p class="note">Entreprise identifiée par le nom publié dans les résultats : deux entreprises homonymes peuvent être confondues, et une même entreprise peut apparaître sous plusieurs écritures. Tous les marchés attribués ne sont pas publiés. Une erreur ou une demande de retrait : voir la page À propos.</p></section>"""
        page(f"entreprise/{k}", f"{court(nom, 50)} : marchés publics remportés | {SITE}", court(f"Les marchés publics remportés par {nom} en France {DEPUIS} : acheteurs, métiers et résultats publiés.", 158), corps, fil=[("Accueil", "")])


def BANDEAU(rel, m="", d=""):
    q = "&".join(x for x in (f"m={m}" if m else "", f"d={d}" if d else "") if x)
    return f"""<aside class="bandeau-alerte"><div><b>Recevez les nouvelles annonces de votre métier par e-mail</b><span>Gratuit, un e-mail par semaine au plus, désinscription en un clic.</span></div>
<a class="bouton jaune" href="{rel}inscription/{'?' + q if q else ''}">S'inscrire gratuitement</a></aside>"""


def formulaire(dep, metier_slug, metier, prep):
    if not ALERTES:
        return ""
    return f"""<form class="alerte bloc" data-dep="{dep}" data-metier="{metier_slug}" novalidate>
<h2>Recevoir ces annonces par e-mail</h2>
<p class="intro">Un e-mail par semaine au plus, seulement quand une nouvelle annonce « {E(metier)} » paraît {prep}. Gratuit.</p>
<div class="champ"><label for="al-email">Votre adresse e-mail</label><input id="al-email" name="email" type="email" autocomplete="email" required>
<input name="site" type="text" tabindex="-1" autocomplete="off" class="pot" aria-hidden="true"><button type="submit" class="bouton">Créer l'alerte</button></div>
<p class="etat" role="status"></p>
<p class="note">Votre adresse sert uniquement à envoyer cette alerte. Chaque e-mail contient un lien de désinscription.</p></form>"""


CSS = """:root{--fond:#eef1f6;--carte:#fff;--encre:#131a2b;--doux:#566078;--trait:#d3dae6;--bleu:#1c3fa8;--bleu-doux:#e3e9f8;--jaune:#ffcf1a;--sur-jaune:#231a00;--alerte:#b3260f;
--titre:"Barlow Condensed","Arial Narrow",Arial,sans-serif;--texte:"Barlow",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
@media (prefers-color-scheme:dark){:root{--fond:#0d1220;--carte:#161d2f;--encre:#e8ecf5;--doux:#9ba6bd;--trait:#293349;--bleu:#9bb6ff;--bleu-doux:#1d2947;--jaune:#ffd43b;--alerte:#ff8a73;color-scheme:dark}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--fond);color:var(--encre);font:400 1.0625rem/1.55 var(--texte)}
a{color:var(--bleu);text-underline-offset:.15em}:focus-visible{outline:3px solid var(--bleu);outline-offset:2px;border-radius:2px}
.saut{position:absolute;left:-999rem}.saut:focus{left:1rem;top:1rem;background:var(--carte);padding:.5rem .8rem;z-index:9}
.cadre{max-width:64rem;margin-inline:auto;padding-inline:1.1rem}.cadre.large{max-width:72rem}
h1,h2,h3{margin:0;text-wrap:balance}h1{font:700 clamp(2rem,5.4vw,3.2rem)/1.02 var(--titre);letter-spacing:-.005em}
h2{font:700 clamp(1.45rem,3vw,1.85rem)/1.1 var(--titre)}p{margin:0}

.tete{background:var(--carte);border-bottom:1px solid var(--trait)}.tete .cadre{display:flex;justify-content:space-between;align-items:center;gap:1rem;flex-wrap:wrap;padding-block:.8rem;max-width:72rem}
.marque{font:700 1.55rem/1 var(--titre);color:var(--encre);text-decoration:none;display:flex;align-items:center;gap:.5rem}
.pastille{width:.95rem;height:.95rem;background:var(--jaune);border:2px solid var(--encre);display:inline-block}
.tete nav{display:flex;gap:1.3rem;flex-wrap:wrap}.tete nav a{color:var(--encre);text-decoration:none;font-weight:500}.tete nav a:hover{text-decoration:underline}
main{padding-block:1.6rem 4rem;display:flex;flex-direction:column;gap:2.6rem}
.fil{font-size:.92rem;color:var(--doux)}.fil a{color:var(--doux)}
.intro{color:var(--doux);max-width:46rem}.note{font-size:.88rem;color:var(--doux)}
.bloc{display:flex;flex-direction:column;gap:1rem}.sous{font:600 1.05rem/1.2 var(--texte);margin-top:.6rem}

/* accueil */
.accueil{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,.9fr);gap:2.5rem;align-items:start}
.accueil .dit{display:flex;flex-direction:column;gap:1.1rem;padding-top:.6rem}
.accueil .dit p{font-size:1.15rem;color:var(--doux);max-width:32rem}
.trouver{background:var(--bleu);color:#fff;padding:1.4rem;display:flex;flex-direction:column;gap:.9rem}
@media (prefers-color-scheme:dark){.trouver{background:#1c3fa8}}
.trouver h2{font-size:1.5rem}.trouver label{display:flex;flex-direction:column;gap:.3rem;font-weight:500;font-size:.95rem}
.trouver input,.trouver select{font:inherit;padding:.7rem .8rem;border:2px solid transparent;border-radius:3px;background:#fff;color:#131a2b;width:100%}
.trouver input:focus-visible,.trouver select:focus-visible{outline:3px solid var(--jaune);outline-offset:1px}
.propos{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:.35rem}
.propos a{display:flex;justify-content:space-between;gap:.8rem;background:#fff;color:#131a2b;text-decoration:none;padding:.6rem .8rem;border-radius:3px;font-weight:500}
.propos a:hover,.propos a:focus-visible{background:var(--jaune);color:#231a00}.propos b{font-weight:600;white-space:nowrap}
.propos .rien{color:#fff;font-size:.95rem}
.etapes{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1.5rem;counter-reset:e}
.etapes li{counter-increment:e;display:flex;flex-direction:column;gap:.3rem;padding-left:3rem;position:relative}
.etapes li::before{content:counter(e);position:absolute;left:0;top:0;width:2.2rem;height:2.2rem;display:grid;place-items:center;background:var(--jaune);color:var(--sur-jaune);font:700 1.4rem/1 var(--titre)}
.etapes b{font-weight:600}.etapes span{color:var(--doux);font-size:.97rem}
.deps{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(13.5rem,1fr));gap:.7rem}
.deps a{display:flex;justify-content:space-between;align-items:baseline;gap:.6rem;background:var(--carte);border:1px solid var(--trait);border-left:.4rem solid var(--bleu);padding:.8rem .9rem;text-decoration:none;color:var(--encre);font-weight:600}
.deps a:hover{border-color:var(--bleu)}.deps b{font:700 1.5rem/1 var(--titre);color:var(--bleu)}
.liens{list-style:none;margin:0;padding:0;columns:3 15rem;column-gap:2rem}.liens li{break-inside:avoid}
.liens a{display:flex;justify-content:space-between;gap:.8rem;padding:.38rem 0;border-bottom:1px solid var(--trait);text-decoration:none;color:var(--encre)}
.liens a:hover span{text-decoration:underline}.liens b{font-weight:600;color:var(--doux);font-variant-numeric:tabular-nums}
.suite{font-weight:600}

/* listes d'annonces */
.liste{display:flex;flex-direction:column;gap:.7rem}
.filtres{display:flex;gap:.8rem 1.4rem;flex-wrap:wrap;align-items:end;justify-content:space-between;padding-bottom:.4rem}
.types{display:flex;gap:.4rem;flex-wrap:wrap}
.types button{font:500 .97rem var(--texte);background:var(--carte);color:var(--encre);border:1px solid var(--trait);border-radius:99px;padding:.4rem .9rem;cursor:pointer}
.types button[aria-pressed=true]{background:var(--encre);color:var(--fond);border-color:var(--encre)}
.cherche{display:flex;flex-direction:column;gap:.2rem;font-size:.88rem;color:var(--doux);flex:1 1 15rem;max-width:22rem}
.cherche input{font:inherit;font-size:1rem;padding:.5rem .7rem;border:1px solid var(--trait);border-radius:3px;background:var(--carte);color:var(--encre)}
.avis{display:grid;grid-template-columns:5.6rem minmax(0,1fr);gap:1.1rem;background:var(--carte);border:1px solid var(--trait);padding:1rem;align-items:start}
.avis:hover{border-color:var(--bleu)}
.tuile{display:flex;flex-direction:column;align-items:center;text-align:center;border:2px solid var(--encre);background:var(--carte);color:var(--encre)}
.t-mois{width:100%;background:var(--encre);color:var(--carte);font-size:.78rem;font-weight:600;padding:.12rem 0}
.t-jour{font:700 2.5rem/1 var(--titre);padding:.25rem 0 .05rem}.t-reste{font-size:.74rem;font-weight:600;padding:0 .2rem .35rem;line-height:1.15}
.tuile.presse{background:var(--jaune);color:var(--sur-jaune);border-color:var(--sur-jaune)}.tuile.presse .t-mois{background:var(--sur-jaune);color:var(--jaune)}
.corps{min-width:0;display:flex;flex-direction:column;gap:.45rem}
.avis h3{font:600 1.1rem/1.3 var(--texte);overflow-wrap:anywhere}.avis h3 a{color:var(--encre);text-decoration:none}.avis h3 a:hover{color:var(--bleu);text-decoration:underline}
.qui{display:flex;flex-direction:column;font-size:.95rem}.qui b{font-weight:600}.qui span{color:var(--doux)}
.puces{list-style:none;margin:0;padding:0;display:flex;flex-wrap:wrap;gap:.35rem}
.puces li{font-size:.86rem;font-weight:500;background:var(--bleu-doux);color:var(--encre);padding:.12rem .55rem;border-radius:3px}
.histo{font-size:.92rem;color:var(--bleu);font-weight:600}
.vide{background:var(--carte);border:1px dashed var(--trait);padding:1rem;color:var(--doux)}

/* fiche d'une annonce */
.fiche{display:grid;grid-template-columns:minmax(0,1fr) 17.5rem;gap:1.6rem 2.6rem;align-items:start}
.f-tete{grid-column:1;display:flex;flex-direction:column;gap:.7rem}.f-tete h1{font-size:clamp(1.55rem,3.6vw,2.2rem);line-height:1.08}
.f-qui{display:flex;flex-direction:column}.f-qui b{font-weight:600;font-size:1.1rem}.f-qui span{color:var(--doux)}
.f-cote{grid-column:2;grid-row:1 / span 2;position:sticky;top:1rem;background:var(--carte);border:1px solid var(--trait);padding:1.1rem;display:flex;flex-direction:column;gap:.55rem}
.f-cote .tuile{align-self:flex-start;width:6.4rem}.f-cote .t-jour{font-size:3rem}.f-date{font-size:1rem}.f-cote .note{margin-bottom:.35rem}
.f-corps{grid-column:1;display:flex;flex-direction:column;gap:2.4rem;min-width:0}
.bouton{display:block;text-align:center;font:600 1.02rem var(--texte);background:var(--bleu);color:var(--carte);border:2px solid var(--bleu);border-radius:3px;padding:.7rem 1rem;text-decoration:none;cursor:pointer}
.bouton:hover{filter:brightness(1.12)}.bouton.second{background:transparent;color:var(--bleu)}
.essentiel{margin:0;background:var(--carte);border:1px solid var(--trait)}
.essentiel>div{display:grid;grid-template-columns:13rem minmax(0,1fr);gap:.3rem 1.2rem;padding:.85rem 1.1rem;border-top:1px solid var(--trait)}.essentiel>div:first-child{border-top:0}
.essentiel dt{font-weight:600;color:var(--doux);font-size:.95rem}.essentiel dd{margin:0;overflow-wrap:anywhere}
details{margin-top:.5rem}summary{cursor:pointer;color:var(--bleu);font-weight:600}details .lots{margin-top:.4rem}
.lots{margin:0;padding-left:1.4rem;display:flex;flex-direction:column;gap:.25rem}
.criteres{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:.6rem}
.criteres li{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:.15rem 1rem}.criteres b{font-weight:600;white-space:nowrap}
.criteres i{grid-column:1 / -1;height:.45rem;background:var(--bleu-doux);position:relative;border-radius:2px;overflow:hidden}
.criteres i::after{content:"";position:absolute;inset:0 auto 0 0;width:var(--p);background:var(--bleu)}
.resultats{list-style:none;margin:0;padding:0;background:var(--carte);border:1px solid var(--trait)}
.res{display:grid;grid-template-columns:5.2rem minmax(0,1fr);gap:1rem;padding:.85rem 1.1rem;border-top:1px solid var(--trait)}.res:first-child{border-top:0}
.res>div{display:flex;flex-direction:column;gap:.35rem;min-width:0;overflow-wrap:anywhere}.quand{font-weight:600;color:var(--doux);font-size:.9rem}
.gagne.libre{font-size:.93rem;color:var(--doux)}
.repere{display:flex;align-items:center;gap:.9rem;background:var(--jaune);color:var(--sur-jaune);padding:.7rem 1rem;max-width:34rem}
.repere b{font:700 2.6rem/1 var(--titre)}.repere span{font-size:.95rem;font-weight:500}
.tablo{overflow-x:auto;background:var(--carte);border:1px solid var(--trait)}table{border-collapse:collapse;width:100%;font-size:.97rem}
th,td{text-align:left;padding:.55rem .9rem;border-top:1px solid var(--trait);vertical-align:top}thead th{border-top:0;font-size:.86rem;color:var(--doux);font-weight:600}
.n{text-align:right;font-variant-numeric:tabular-nums}td.n{font-weight:600}
.rubriques{display:flex;flex-wrap:wrap;gap:.5rem}.rubriques a{background:var(--carte);border:1px solid var(--trait);padding:.4rem .8rem;border-radius:99px;text-decoration:none;font-weight:500}

/* relances, lecture rapide, contact */
.tuile.fin .t-jour{font-size:1.55rem;padding:.5rem 0 .25rem}.tenu{font-size:.97rem}
.appel{display:flex;gap:1rem 2rem;flex-wrap:wrap;align-items:center;justify-content:space-between;background:var(--carte);border:2px solid var(--bleu);padding:1.1rem 1.3rem}
.appel div{display:flex;flex-direction:column;gap:.15rem;flex:1 1 18rem;min-width:0}.appel b{font:700 1.4rem/1.15 var(--titre)}.appel span{color:var(--doux);font-size:.97rem}
.reperes{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(14rem,1fr));gap:.7rem}
.reperes li{background:var(--carte);border:1px solid var(--trait);border-top:.35rem solid var(--jaune);padding:.8rem 1rem;display:flex;flex-direction:column;gap:.25rem}
.reperes span{font-size:.86rem;font-weight:600;color:var(--doux)}.reperes p{font-size:1.02rem;line-height:1.35}.reperes b{font-weight:600}.reperes i{font-style:normal;font-size:.82rem;color:var(--doux)}
.contact{border-top:1px solid var(--trait);padding-top:.7rem;margin-top:.3rem;display:flex;flex-direction:column;gap:.1rem;font-size:.93rem}.contact span{overflow-wrap:anywhere;user-select:all}
.pro-plus a{font-weight:600;font-size:.93rem;align-self:flex-start}
/* version pro et fiches entreprises */
.etiquette{align-self:flex-start;display:inline-block;background:var(--jaune);color:var(--sur-jaune);font-weight:600;font-size:.9rem;padding:.15rem .6rem}
.pro-tete{display:flex;flex-direction:column;gap:.9rem;max-width:50rem}
.pro-grille{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,23rem);gap:2.5rem;align-items:start}
.pro-plus{list-style:none;margin:0;padding:0;background:var(--carte);border:1px solid var(--trait)}
.pro-plus li{display:flex;flex-direction:column;gap:.15rem;padding:.9rem 1.1rem;border-top:1px solid var(--trait)}.pro-plus li:first-child{border-top:0}
.pro-plus b{font-weight:600}.pro-plus span{color:var(--doux);font-size:.97rem}
.pro-cote{display:flex;flex-direction:column;gap:.9rem}.prix{background:var(--encre);color:var(--fond);padding:1.1rem 1.3rem;display:flex;align-items:baseline;gap:.8rem;flex-wrap:wrap}
.prix b{font:700 3.2rem/1 var(--titre)}.prix span{font-size:.95rem;opacity:.85}
.pro-mini{border-top:1px solid var(--trait);padding-top:.7rem;margin-top:.3rem;display:flex;flex-direction:column;gap:.1rem;font-size:.9rem}.pro-mini a{font-weight:600}.pro-mini span{color:var(--doux)}
.deux{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:2rem;align-items:start}
.compteurs{list-style:none;margin:0;padding:0;background:var(--carte);border:1px solid var(--trait)}
.compteurs li{display:flex;justify-content:space-between;gap:1rem;padding:.5rem .9rem;border-top:1px solid var(--trait)}.compteurs li:first-child{border-top:0}.compteurs b{font-weight:600}
.alerte.attente{display:flex;flex-direction:column;gap:.6rem}.alerte.attente h2{font-size:1.4rem}
@media (max-width:56rem){.pro-grille,.deux{grid-template-columns:minmax(0,1fr)}}
/* alertes */
.tete nav .inscrire{background:var(--jaune);color:var(--sur-jaune);padding:.35rem .8rem;border-radius:3px;font-weight:600}
.bandeau-alerte{display:flex;gap:1rem 2rem;flex-wrap:wrap;align-items:center;justify-content:space-between;background:var(--encre);color:var(--fond);padding:1.1rem 1.3rem}
.bandeau-alerte div{display:flex;flex-direction:column;gap:.15rem;min-width:0;flex:1 1 18rem}.bandeau-alerte b{font:700 1.35rem/1.15 var(--titre)}.bandeau-alerte span{font-size:.95rem;opacity:.85}
.bouton.jaune{background:var(--jaune);border-color:var(--jaune);color:var(--sur-jaune)}
.inscription{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,24rem);gap:2.5rem;align-items:start}.inscription>div{display:flex;flex-direction:column;gap:1rem}
.promesses{margin:0;padding-left:1.2rem;display:flex;flex-direction:column;gap:.3rem}
.alerte.libre{display:flex;flex-direction:column;gap:.45rem}.alerte.libre label{font-weight:600;font-size:.95rem;margin-top:.5rem}
.alerte.libre select,.alerte.libre input[type=email]{font:inherit;padding:.65rem .75rem;border:1px solid var(--trait);background:var(--fond);color:var(--encre);border-radius:3px;width:100%}
.alerte.libre .bouton{margin-top:.8rem}
@media (max-width:56rem){.inscription{grid-template-columns:minmax(0,1fr)}}
.alerte{border:2px solid var(--encre);background:var(--carte);padding:1.3rem}
.champ{display:flex;gap:.6rem;flex-wrap:wrap;align-items:end}.champ label{flex-basis:100%;font-weight:600;font-size:.95rem}
.champ input[type=email]{flex:1 1 14rem;min-width:0;font:inherit;padding:.65rem .75rem;border:1px solid var(--trait);background:var(--fond);color:var(--encre);border-radius:3px}
.pot{position:absolute;left:-999rem}.etat{font-weight:600;min-height:1.4em}

.pied{border-top:1px solid var(--trait);background:var(--carte);font-size:.9rem;color:var(--doux)}.pied .cadre{padding-block:1.4rem 2.6rem;display:flex;flex-direction:column;gap:.4rem;max-width:72rem}
@media (max-width:56rem){.accueil{grid-template-columns:minmax(0,1fr)}.etapes{grid-template-columns:minmax(0,1fr)}
.fiche{grid-template-columns:minmax(0,1fr)}.f-cote{grid-column:1;grid-row:auto;position:static}}
@media (max-width:36rem){body{font-size:1rem}.avis{grid-template-columns:4.6rem minmax(0,1fr);gap:.8rem;padding:.8rem}.t-jour{font-size:2.1rem}
.essentiel>div,.res{grid-template-columns:minmax(0,1fr);gap:.2rem}.tete nav{gap:1rem;font-size:.95rem}}
@media (prefers-reduced-motion:no-preference){html{scroll-behavior:smooth}}"""

SITE_JS = r"""(function(){
function plat(s){return s.normalize("NFD").replace(/[̀-ͯ]/g,"").toLowerCase();}
// Accueil : trouver son métier et son département
var boite=document.querySelector(".trouver");
if(boite){
  var champ=boite.querySelector("#t-metier"),dep=boite.querySelector("#t-dep"),liste=boite.querySelector(".propos"),D=null;
  function montre(){
    if(!D){return;}
    var q=plat(champ.value.trim()),c=dep.value,out=[];
    if(q.length<2&&!c){liste.innerHTML="";return;}
    D.m.forEach(function(m){
      var p=plat(m.n),n=c?(m.d[c]||0):m.t;
      if(q.length>=2&&!(p.indexOf(q)>=0||(q.length>=5&&p.indexOf(q.slice(0,5))>=0))){return;}
      if(c&&!(c in m.d)){return;}
      out.push({m:m,n:n});
    });
    out.sort(function(a,b){return b.n-a.n||a.m.n.localeCompare(b.m.n);});
    var h=out.slice(0,q.length>=2?8:6).map(function(o){
      var url=c?D.d[c][1]+"/"+o.m.s+"/":"metier/"+o.m.s+"/";
      return '<li><a href="'+url+'"><span>'+o.m.n.replace(/</g,"&lt;")+(c?" "+D.d[c][2]:"")+"</span><b>"+o.n+" annonce"+(o.n>1?"s":"")+"</b></a></li>";
    }).join("");
    if(c&&q.length<2){h='<li><a href="'+D.d[c][1]+'/"><span>Toutes les annonces '+D.d[c][2]+"</span><b>"+D.d[c][3]+"</b></a></li>"+h;}
    liste.innerHTML=h||'<li class="rien">Aucun métier ne correspond. Essayez un autre mot, par exemple « peinture », « nettoyage » ou « voirie ».</li>';
  }
  fetch("index.json").then(function(r){return r.json();}).then(function(j){D=j;montre();}).catch(function(){});
  champ.addEventListener("input",montre);dep.addEventListener("change",montre);
  boite.addEventListener("submit",function(e){e.preventDefault();var a=liste.querySelector("a");if(a){location.href=a.href;}});
}
// Listes : filtrer par type de marché et par mot
document.querySelectorAll(".liste").forEach(function(L){
  var barre=L.querySelector(".filtres");if(!barre){return;}
  var cartes=[].slice.call(L.querySelectorAll(".avis")),types={},choix="",mot="",aucun=L.querySelector(".aucun");
  cartes.forEach(function(c){var t=c.dataset.type||"";if(t){types[t]=(types[t]||0)+1;}c._t=plat(c.textContent);});
  var zone=barre.querySelector(".types"),noms=Object.keys(types).sort();
  function bouton(lab,val){var b=document.createElement("button");b.type="button";b.textContent=lab;b.setAttribute("aria-pressed",val===choix);
    b.addEventListener("click",function(){choix=val;[].forEach.call(zone.children,function(x){x.setAttribute("aria-pressed","false");});b.setAttribute("aria-pressed","true");applique();});zone.appendChild(b);}
  if(noms.length>1){bouton("Tout ("+cartes.length+")","");noms.forEach(function(t){bouton(t.charAt(0).toUpperCase()+t.slice(1)+" ("+types[t]+")",t);});}
  function applique(){var n=0;cartes.forEach(function(c){var ok=(!choix||c.dataset.type===choix)&&(!mot||c._t.indexOf(mot)>=0);c.hidden=!ok;if(ok){n++;}});aucun.hidden=n>0;}
  barre.querySelector("input").addEventListener("input",function(e){mot=plat(e.target.value.trim());applique();});
  barre.hidden=false;
});
// Page des métiers : filtrer la liste
var fm=document.querySelector("#f-metier");
if(fm){var items=[].slice.call(document.querySelectorAll(".liens li"));items.forEach(function(li){li._t=plat(li.textContent);});
  fm.addEventListener("input",function(){var q=plat(fm.value.trim());items.forEach(function(li){li.hidden=q.length>0&&li._t.indexOf(q)<0;});});}
})();"""


MENTION_ALERTES = ("Si vous créez une alerte ou demandez à être prévenu de l'ouverture de la version Pro, votre adresse e-mail est enregistrée, avec le métier et le département choisis le cas échéant, dans le seul but de vous envoyer ces messages. "
    "Elle est stockée chez Supabase et les e-mails partent par Brevo. Elle est supprimée dès que vous vous désinscrivez, et au bout de 7 jours si vous ne confirmez pas l'inscription."
    + (f" Pour toute demande concernant vos données : {E(CONFIG['contact_email'])}." if CONFIG.get("contact_email") else ""))

JS = r"""(function(){
var URL="__URL__",KEY="__KEY__",H={"apikey":KEY,"Authorization":"Bearer "+KEY,"Content-Type":"application/json"};
document.querySelectorAll("form.alerte").forEach(function(f){
  f.addEventListener("submit",function(e){
    e.preventDefault();
    var etat=f.querySelector(".etat"),email=f.email.value.trim().toLowerCase();
    var pro=f.classList.contains("attente");
    var dep=pro?"00":(f.dataset.dep||(f.dep?f.dep.value:"")),metier=pro?"version-pro":(f.dataset.metier||(f.metier?f.metier.value:""));
    if(!metier){etat.textContent="Choisissez votre métier dans la liste.";f.metier.focus();return;}
    if(!dep){etat.textContent="Choisissez votre département dans la liste.";f.dep.focus();return;}
    if(f.site.value){return;}
    if(!/^[^@\s]+@[^@\s]+\.[a-z]{2,}$/.test(email)){etat.textContent="Cette adresse e-mail n'est pas valide.";f.email.focus();return;}
    etat.textContent="Enregistrement…";
    fetch(URL+"/rest/v1/lo_abonnes",{method:"POST",headers:Object.assign({"Prefer":"return=minimal"},H),
      body:JSON.stringify({email:email,dep:dep,metier:metier})})
    .then(function(r){
      if(r.status===201){etat.textContent=pro?"C'est noté. Un e-mail de confirmation vous sera envoyé dans l'heure : cliquez sur son lien pour valider votre demande.":"C'est noté. Un e-mail de confirmation vous sera envoyé dans l'heure : cliquez sur son lien pour activer l'alerte.";f.email.value="";}
      else if(r.status===409){etat.textContent=pro?"Cette adresse est déjà sur la liste.":"Cette adresse est déjà inscrite à cette alerte.";}
      else{etat.textContent="L'inscription n'a pas fonctionné. Réessayez dans quelques minutes.";}
    }).catch(function(){etat.textContent="Connexion impossible. Vérifiez votre réseau et réessayez.";});
  });
});
var libre=document.querySelector("form.alerte.libre");
if(libre){var qs=new URLSearchParams(location.search);["m","d"].forEach(function(k){var el=libre[k==="m"?"metier":"dep"],v=qs.get(k);if(v&&el.querySelector('option[value="'+v.replace(/[^a-zA-Z0-9-]/g,"")+'"]')){el.value=v;}});}
var a=document.querySelector("[data-action]");
if(a){
  var t=new URLSearchParams(location.search).get("t")||"",ok=/^[0-9a-f-]{36}$/i.test(t),conf=a.dataset.action==="confirmer";
  if(!ok){a.textContent="Ce lien est incomplet. Ouvrez-le directement depuis l'e-mail reçu.";return;}
  fetch(URL+"/rest/v1/rpc/"+(conf?"lo_confirmer":"lo_desinscrire"),{method:"POST",headers:H,body:JSON.stringify({t:t})})
  .then(function(r){return r.ok?r.json():Promise.reject();})
  .then(function(v){
    if(conf){a.textContent=v?"C'est confirmé. Vous recevrez nos e-mails à cette adresse.":"Ce lien n'est plus valable : l'inscription a expiré ou a été supprimée.";}
    else{a.textContent=v?"Vous êtes désinscrit. Votre adresse a été supprimée.":"Cette alerte était déjà supprimée.";}
  }).catch(function(){a.textContent="L'opération n'a pas abouti. Réessayez dans quelques minutes.";});
}
})();"""


def main():
    global TODAY, SITEMAP, HIST, RES_COMBO, FICHES, RELANCES, DEJA, REL_COMBO, REL_ENT, REL_DEP
    TODAY = dt.datetime.now(ZoneInfo("Europe/Paris")).date()
    SITEMAP = []
    recus, tous = charger_marches(TODAY)
    ouverts = [a for a in tous if a["reste"] >= 0]
    print(f"[site] {recus} reçus, {len(tous)} avis de marché retenus, {len(ouverts)} ouverts")
    if len(tous) < int(os.environ.get("MIN_AVIS", "500")):
        sys.exit("Trop peu d'avis exploitables : le site en ligne est laissé tel quel.")

    # résultats de marché depuis janvier 2024 : qui a gagné quoi, chez quel acheteur
    resultats = charger_resultats(TODAY)
    par_siret, par_nom, RES_COMBO = defaultdict(list), defaultdict(list), defaultdict(list)
    for r in resultats:
        if r["siret"]:
            par_siret[r["siret"]].append(r)
        par_nom[slug(r["acheteur"])].append(r)
        for c in r["deps"]:
            for m in r["metiers"]:
                RES_COMBO[(c, m)].append(r)
    nb = defaultdict(int)
    for r in resultats:
        for g in r["gagnants"]:
            nb[slug(g)] += 1
    seuil = 2
    while True:                         # on garde au plus 12 000 fiches pour rester dans la taille permise par l'hébergement
        FICHES = {k for k, n in nb.items() if n >= seuil and len(k) >= 3 and est_entreprise(k)}
        if len(FICHES) <= 12000:
            break
        seuil += 1
    print(f"[site] fiches entreprises : {len(FICHES)} (au moins {seuil} marchés remportés)")
    RELANCES = sorted((r for r in resultats if r["fin"] and r["deps"] and -30 <= (r["fin"] - TODAY).days <= 365), key=lambda r: r["fin"])
    ouv_ach = defaultdict(list)
    for a in ouverts:
        if a["siret"]:
            ouv_ach[a["siret"]].append(a)
        ouv_ach[slug(a["acheteur"])].append(a)
    DEJA, REL_COMBO, REL_ENT, REL_DEP = {}, defaultdict(list), defaultdict(list), defaultdict(list)
    for r in RELANCES:                  # une annonce ouverte du même acheteur dans le même métier : peut-être déjà la relance
        for a in ouv_ach.get(r["siret"], []) + ouv_ach.get(slug(r["acheteur"]), []):
            if set(r["metiers"]) & {slug(m) for m in a["metiers"]}:
                DEJA[r["id"]] = a["id"]
                break
        for c in r["deps"]:
            REL_DEP[c].append(r)
            for m in r["metiers"]:
                REL_COMBO[(c, m)].append(r)
        for g in r["gagnants"]:
            REL_ENT[slug(g)].append(r)
    HIST = {}
    for a in ouverts:
        h = {r["id"]: r for r in (par_siret.get(a["siret"], []) if a["siret"] else []) + par_nom.get(slug(a["acheteur"]), [])}
        if h:
            HIST[a["id"]] = sorted(h.values(), key=lambda r: r["paru"], reverse=True)
    print(f"[site] {len(resultats)} résultats de marché, {sum(1 for r in resultats if r['gagnants'] or r['texte'])} avec titulaire, {len(HIST)} avis ouverts avec historique acheteur")
    if len(tous) < int(os.environ.get("MIN_AVIS", "20")):
        sys.exit("Trop peu d'avis exploitables : le site en ligne est laissé tel quel.")

    OUT.mkdir(exist_ok=True)
    (OUT / "style.css").write_text(CSS, encoding="utf-8")
    (OUT / "site.js").write_text(SITE_JS, encoding="utf-8")
    (OUT / ".nojekyll").write_text("")

    # métiers = mots-clés du BOAMP vus sur la fenêtre (pages stables même quand une rubrique est vide un jour)
    metiers = {}
    for a in tous:
        for m in a["metiers"]:
            metiers.setdefault(slug(m), m)
    par_dep, par_met, par_combo = defaultdict(list), defaultdict(list), defaultdict(list)
    combos_vus = set()
    for a in tous:
        for c in a["deps"]:
            for m in a["metiers"]:
                combos_vus.add((c, slug(m)))
    for r in resultats:                 # un métier vu seulement dans les résultats a aussi sa page
        for c in r["deps"]:
            for m in r["metiers"]:
                if m in metiers:
                    combos_vus.add((c, m))
    combos_dep = defaultdict(set)
    for c, m in combos_vus:
        combos_dep[c].add(m)
    for a in ouverts:
        for c in a["deps"]:
            par_dep[c].append(a)
            for m in a["metiers"]:
                par_combo[(c, slug(m))].append(a)
        for m in a["metiers"]:
            par_met[slug(m)].append(a)

    dslug = {c: slug(n) for c, (n, _) in DEPS.items()}
    tri_met = sorted(metiers, key=lambda s: (-len(par_met[s]), metiers[s]))
    actifs = [s for s in tri_met if par_met[s]]

    # index pour le moteur de recherche de l'accueil
    idx = {"d": {c: [DEPS[c][0], dslug[c], DEPS[c][1], len(par_dep[c])] for c in DEPS},
           "m": [{"s": s, "n": metiers[s], "t": len(par_met[s]), "d": {c: len(par_combo[(c, s)]) for c in DEPS if par_combo[(c, s)]}} for s in actifs]}
    (OUT / "index.json").write_text(json.dumps(idx, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # accueil
    semaine = [a for a in ouverts if a["reste"] <= 7]
    options = "".join(f'<option value="{c}">{E(DEPS[c][0])} ({c})</option>' for c in DEPS)
    corps = f"""<div class="accueil">
<div class="dit"><h1>Les marchés publics à votre portée, triés par métier</h1>
<p>{len(ouverts)} annonces de mairies, d'écoles, d'hôpitaux et de collectivités sont ouvertes aujourd'hui dans toute la France. Pour chacune : la date limite, le dossier à télécharger, et les entreprises que l'acheteur a retenues les fois précédentes.</p></div>
<form class="trouver" role="search"><h2>Trouver les annonces pour mon métier</h2>
<label for="t-metier">Votre métier ou votre activité<input id="t-metier" type="search" autocomplete="off" placeholder="peinture, électricité, nettoyage, espaces verts…"></label>
<label for="t-dep">Votre département<select id="t-dep"><option value="">Toute la France</option>{options}</select></label>
<ul class="propos" aria-live="polite"></ul>
<noscript><p>Sans JavaScript, choisissez un département ou un métier dans les listes plus bas.</p></noscript></form></div>
{BANDEAU("") if ALERTES else ''}
<ol class="etapes"><li><b>Choisissez votre métier</b><span>Vous voyez seulement les annonces qui vous concernent, de la plus urgente à la plus lointaine.</span></li>
<li><b>Lisez la fiche</b><span>Montant, lots, critères de notation, et qui a gagné les marchés précédents de cet acheteur.</span></li>
<li><b>Téléchargez le dossier</b><span>Un lien direct vers les documents à remplir, sur la plateforme de l'acheteur.</span></li></ol>
<aside class="appel"><div><b>{len(RELANCES)} marchés arrivent à échéance dans les douze mois</b><span>Voyez quels contrats de votre métier vont être remis en jeu, et qui les détient aujourd'hui.</span></div><a class="bouton" href="relances/">Voir les marchés bientôt relancés</a></aside>
<section class="bloc" id="departements"><h2>Par département</h2>{"".join(f'<h3 class="sous">{E(nomr)}</h3>' + liens([(DEPS[c][0], f"{dslug[c]}/", len(par_dep[c])) for c in DEPS if REG_DE[c] == r], "deps") for r, nomr in REGIONS.items())}</section>
<section class="bloc"><h2>Les métiers les plus demandés</h2>{liens([(metiers[s], f"metier/{s}/", len(par_met[s])) for s in actifs[:24]])}
<p><a class="suite" href="metiers/">Voir les {len(actifs)} métiers</a></p></section>
<section class="bloc"><h2>À remettre dans les 7 jours</h2><p class="intro">{len(semaine)} annonce{'s' if len(semaine) > 1 else ''} arrive{'nt' if len(semaine) > 1 else ''} à échéance cette semaine.</p>{bloc_liste(sorted(semaine, key=lambda a: a['limite'])[:20], filtres=False)}</section>"""
    page("", f"Appels d'offres en France : {n_avis(len(ouverts))} | {SITE}",
         f"Les marchés publics ouverts en France, triés par métier et par département, avec le dossier à télécharger et les entreprises déjà retenues par chaque acheteur.", corps, large=True)

    # tous les métiers
    page("metiers", f"Appels d'offres par métier en France | {SITE}", f"Les {len(actifs)} métiers et activités qui ont des annonces de marchés publics ouvertes en France.",
         f"""<h1>Tous les métiers</h1>
<p class="intro">{len(actifs)} métiers et activités ont au moins une annonce ouverte aujourd'hui en France.</p>
<label class="cherche" for="f-metier"><span>Filtrer la liste</span><input id="f-metier" type="search" placeholder="peinture, voirie, assurance…"></label>
{liens([(metiers[s], f"../metier/{s}/", len(par_met[s])) for s in sorted(actifs, key=lambda s: slug(metiers[s]))])}""", fil=[("Accueil", "")])

    # départements
    for c, (nom, prep) in DEPS.items():
        av = par_dep[c]
        mets = sorted({s for s in combos_dep[c] if par_combo[(c, s)] or len(RES_COMBO.get((c, s), [])) >= 2}, key=lambda s: (-len(par_combo[(c, s)]), metiers[s]))
        corps = f"""<h1>Appels d'offres {prep}</h1>
<p class="intro">{n_avis(len(av))} au {fr(TODAY)}, de la plus urgente à la plus lointaine.</p>
<section class="bloc"><h2>Affiner par métier</h2>{liens([(metiers[s], f"{s}/", len(par_combo[(c, s)])) for s in mets if par_combo[(c, s)]]) if av else ''}</section>
{f'<aside class="appel"><div><b>{len(REL_DEP[c])} marchés arrivent à échéance {prep}</b><span>Les contrats qui se terminent dans les douze mois, et les entreprises qui les détiennent.</span></div><a class="bouton" href="relances/">Voir ces marchés</a></aside>' if REL_DEP.get(c) else ''}
<section class="bloc"><h2>Toutes les annonces {prep}</h2>{bloc_liste(av, "../")}</section>
{BANDEAU("../", d=c) if ALERTES else ''}"""
        page(dslug[c], f"Appels d'offres {nom} ({c}) : {n_avis(len(av))} | {SITE}",
             f"Marchés publics ouverts {prep} au {fr(TODAY)} : date limite, dossier à télécharger et entreprises déjà retenues par chaque acheteur.", corps,
             index=bool(av), fil=[("Accueil", "")])
        if REL_DEP.get(c):
            page(f"{dslug[c]}/relances", f"Marchés publics bientôt relancés {prep} ({c}) | {SITE}", f"{len(REL_DEP[c])} marchés publics arrivent à échéance dans les douze mois {prep} : acheteur, entreprise en place, date de fin prévue.",
                 f"""<p class="etiquette">Fonction Pro, en accès libre pendant le lancement</p><h1>Les marchés qui arrivent à échéance {prep}</h1>
{bloc_relances(REL_DEP[c], "../../", f"{len(REL_DEP[c])} marchés dans les douze mois", "Ces marchés ont été attribués et leur période se termine bientôt. L'acheteur devra souvent relancer une mise en concurrence : c'est le moment de vous préparer et de vous faire connaître, avant que l'annonce ne paraisse.", 600, True)}""",
                 fil=[("Accueil", ""), (nom, f"{dslug[c]}/")])
        for s in mets:
            cv = par_combo[(c, s)]
            m = metiers[s]
            corps = f"""<h1>Appels d'offres « {E(m)} » {prep}</h1>
<p class="intro">{n_avis(len(cv))} au {fr(TODAY)}. Voir aussi <a href="../../metier/{s}/">« {E(m)} » dans toute la France</a>.</p>
<section class="bloc">{bloc_liste(cv, "../../")}</section>
{bloc_relances(REL_COMBO.get((c, s), []), "../../", f"« {E(m)} » {prep} : les marchés qui arrivent à échéance", "Des marchés de ce métier dont la période se termine dans les douze mois. Ils peuvent être remis en concurrence.", 6)}
{bloc_classement(c, s, m, prep)}
{formulaire(c, s, m, prep)}"""
            page(f"{dslug[c]}/{s}", f"Appels d'offres {m.lower()} {nom} ({c}) : {n_avis(len(cv))} | {SITE}",
                 f"Marchés publics « {m} » ouverts {prep} au {fr(TODAY)}, et les entreprises qui ont remporté les précédents.", corps,
                 index=bool(cv) or bool(RES_COMBO.get((c, s))), fil=[("Accueil", ""), (nom, f"{dslug[c]}/")])

    for a in ouverts:
        page_avis(a, metiers, dslug)
    pages_entreprises(resultats, metiers)
    page_pro()
    page("relances", f"Marchés publics bientôt relancés en France | {SITE}", f"{len(RELANCES)} marchés publics arrivent à échéance dans les douze mois en France : acheteur, entreprise en place, date de fin prévue.",
         f"""<p class="etiquette">Fonction Pro, en accès libre pendant le lancement</p>
<h1>Les marchés qui arrivent à échéance</h1>
<p class="intro">{len(RELANCES)} marchés attribués voient leur période se terminer dans les douze mois. L'acheteur devra souvent relancer une mise en concurrence : c'est le moment de vous préparer et de vous faire connaître, avant que l'annonce ne paraisse.</p>
<section class="bloc"><h2>Choisir un département</h2>{liens([(DEPS[c][0], f"../{dslug[c]}/relances/", len(REL_DEP[c])) for c in DEPS if REL_DEP.get(c)], "deps")}</section>
{bloc_relances(RELANCES, "../", "Les 60 échéances les plus proches", "Tous départements confondus.", 60, True)}""",
         fil=[("Accueil", "")])

    # métiers (région)
    for s in tri_met:
        av, m = par_met[s], metiers[s]
        deps = [(DEPS[c][0], f"../../{dslug[c]}/{s}/", len(par_combo[(c, s)])) for c in DEPS if par_combo[(c, s)]]
        corps = f"""<h1>Appels d'offres « {E(m)} » en France</h1>
<p class="intro">{n_avis(len(av))} au {fr(TODAY)}, de la plus urgente à la plus lointaine.</p>
{f'<section class="bloc"><h2>Par département</h2>{liens(deps)}</section>' if deps else ''}
<section class="bloc">{bloc_liste(av[:300], "../../")}{f'<p class="note">Les 300 annonces les plus urgentes sont affichées. Choisissez un département pour tout voir.</p>' if len(av) > 300 else ''}</section>
{BANDEAU("../../", m=s) if ALERTES else ''}"""
        page(f"metier/{s}", f"Appels d'offres {m.lower()} en France : {n_avis(len(av))} | {SITE}",
             f"Marchés publics « {m} » ouverts en France au {fr(TODAY)}, classés par date limite.", corps,
             index=bool(av), fil=[("Accueil", ""), ("Métiers", "metiers/")])

    page("a-propos", f"À propos | {SITE}", f"D'où viennent les données de {SITE} et qui édite le site.",
         f"""<h1>À propos de {SITE}</h1>
<section class="bloc"><h2>À quoi sert ce site</h2><p class="intro">Quand une mairie, une école ou un hôpital a besoin de travaux, d'un service ou de fournitures, il publie une annonce et toute entreprise peut proposer ses services. {SITE} range ces annonces par métier et par département, et ajoute à chacune ce que l'acheteur a déjà attribué par le passé.</p></section>
<section class="bloc"><h2>D'où viennent les données</h2><p class="intro">Les annonces et les résultats de marché affichés proviennent des données ouvertes du Bulletin officiel des annonces des marchés publics (BOAMP), diffusées par la Direction de l'information légale et administrative (DILA). Ils sont récupérés une fois par jour. Le site ne modifie pas leur contenu : les montants, critères, lots, entreprises retenues et nombres d'offres sont repris tels que l'acheteur les a publiés, et restent absents quand l'avis ne les donne pas.</p>
<p class="intro">Les marchés d'un même acheteur sont rapprochés par son numéro SIRET ou, à défaut, par son nom exact : l'historique peut donc être incomplet. Les fiches d'entreprises reprennent les noms publiés dans les résultats officiels ; aucune fiche n'est créée pour une personne. Tous les marchés publics ne sont pas publiés au BOAMP. Un avis peut avoir été rectifié ou annulé depuis la dernière mise à jour : vérifiez toujours l'avis officiel sur boamp.fr avant de répondre.</p></section>
<section class="bloc"><h2>Mentions légales</h2><p class="intro">Site édité à titre personnel, sans publicité. {MENTION_ALERTES if ALERTES else "Aucune donnée personnelle n'est collectée."} Hébergement : GitHub Pages, GitHub Inc., 88 Colin P. Kelly Jr. Street, San Francisco, CA 94107, États-Unis.</p></section>""",
         fil=[("Accueil", "")])

    if ALERTES:
        opt_m = "".join(f'<option value="{s_}">{E(metiers[s_])}</option>' for s_ in sorted(metiers, key=lambda x: slug(metiers[x])))
        opt_d = "".join(f'<option value="{c}">{E(DEPS[c][0])} ({c})</option>' for c in DEPS)
        page("inscription", f"Alertes gratuites par e-mail | {SITE}", f"Recevez par e-mail les nouvelles annonces de marchés publics de votre métier en France. Gratuit.",
             f"""<div class="inscription"><div><h1>Recevez les annonces de votre métier par e-mail</h1>
<p class="intro">Choisissez votre métier et votre département. Vous recevez un e-mail quand une nouvelle annonce paraît, au plus une fois par semaine. C'est gratuit et vous pouvez vous désinscrire en un clic.</p>
<ul class="promesses"><li>Aucun mot de passe à retenir</li><li>Aucune publicité dans les e-mails</li><li>Votre adresse sert uniquement à cette alerte</li></ul></div>
<form class="alerte libre" novalidate>
<label for="al-metier">Votre métier ou votre activité</label><select id="al-metier" name="metier" required><option value="">Choisir dans la liste</option>{opt_m}</select>
<label for="al-dep">Votre département</label><select id="al-dep" name="dep" required><option value="">Choisir dans la liste</option>{opt_d}</select>
<label for="al-email">Votre adresse e-mail</label><input id="al-email" name="email" type="email" autocomplete="email" required>
<input name="site" type="text" tabindex="-1" autocomplete="off" class="pot" aria-hidden="true">
<button type="submit" class="bouton">Créer mon alerte gratuite</button>
<p class="etat" role="status"></p>
<p class="note">Pour suivre plusieurs métiers ou plusieurs départements, créez une alerte pour chacun.</p></form></div>""", fil=[("Accueil", "")])
        for chemin, titre, action, attente in (
            ("alerte/confirmer", "Confirmation de votre alerte", "confirmer", "Confirmation en cours…"),
            ("alerte/desinscription", "Désinscription", "desinscrire", "Désinscription en cours…")):
            page(chemin, f"{titre} | {SITE}", titre,
                 f'<h1>{titre}</h1><p class="intro etat" data-action="{action}" role="status">{attente}</p><p><a href="../../">Retour aux annonces</a></p>', index=False)
        (OUT / "alerte.js").write_text(JS.replace("__URL__", CONFIG["supabase_url"].rstrip("/")).replace("__KEY__", CONFIG["supabase_anon_key"]), encoding="utf-8")

    (OUT / "404.html").write_text(f'<!doctype html><html lang="fr"><meta charset="utf-8"><title>Page introuvable | {SITE}</title><meta name="robots" content="noindex"><link rel="stylesheet" href="{BASE}/style.css"><main class="cadre"><h1>Page introuvable</h1><p class="intro">Cette annonce est sans doute close. <a href="{BASE}/">Voir les annonces ouvertes</a></p></main></html>', encoding="utf-8")
    def plan(urls):
        return ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                + "".join(f"<url><loc>{E(u)}</loc><lastmod>{TODAY.isoformat()}</lastmod></url>\n" for u in urls) + "</urlset>\n")
    if len(SITEMAP) <= 45000:
        (OUT / "sitemap.xml").write_text(plan(SITEMAP), encoding="utf-8")
    else:                                # au-delà de 50 000 adresses, Google demande plusieurs fichiers
        parts = [SITEMAP[k:k + 45000] for k in range(0, len(SITEMAP), 45000)]
        for n, part in enumerate(parts, 1):
            (OUT / f"sitemap-{n}.xml").write_text(plan(part), encoding="utf-8")
        (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "".join(f"<sitemap><loc>{BASE}/sitemap-{n}.xml</loc></sitemap>\n" for n in range(1, len(parts) + 1)) + "</sitemapindex>\n", encoding="utf-8")
    poids = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
    print(f"[site] poids total : {poids / 1e6:.0f} Mo")
    if poids > 950e6:
        sys.exit("Site trop lourd pour l'hébergement (plus de 950 Mo) : le site en ligne est laissé tel quel.")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
    Path("data").mkdir(exist_ok=True)
    Path("data/etat.json").write_text(json.dumps({"date": TODAY.isoformat(), "recus": recus, "retenus": len(tous), "ouverts": len(ouverts), "resultats": len(resultats), "avec_historique": len(HIST), "fiches_entreprises": len(FICHES), "relances": len(RELANCES), "pages_indexables": len(SITEMAP), "poids_mo": round(poids / 1e6)}, indent=1) + "\n")
    print(f"[site] {len(SITEMAP)} pages indexables écrites dans {OUT}/")


if __name__ == "__main__":
    main()
