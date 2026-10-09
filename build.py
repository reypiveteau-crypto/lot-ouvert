#!/usr/bin/env python3
"""Lot Ouvert : génère le site statique à partir des données ouvertes du BOAMP.
Aucune dépendance. Lancé chaque nuit par GitHub Actions (.github/workflows/site.yml)."""
import datetime as dt, html, json, os, re, sys, unicodedata, urllib.error, urllib.parse, urllib.request
from collections import defaultdict
from pathlib import Path
import statistics
import extraire

SITE = "Lot Ouvert"
BASE = os.environ.get("SITE_URL", "https://example.github.io/lot-ouvert").rstrip("/")
OUT = Path("_site")
JOURS = 75            # fenêtre de publication examinée pour les avis de marché
HISTORIQUE = 730      # fenêtre des résultats de marché (attributions)
API = "https://boamp-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/boamp"
REGION = "Bourgogne-Franche-Comté"
DEPS = {  # code: (nom, préposition + nom)
    "21": ("Côte-d'Or", "en Côte-d'Or"), "25": ("Doubs", "dans le Doubs"), "39": ("Jura", "dans le Jura"),
    "58": ("Nièvre", "dans la Nièvre"), "70": ("Haute-Saône", "en Haute-Saône"),
    "71": ("Saône-et-Loire", "en Saône-et-Loire"), "89": ("Yonne", "dans l'Yonne"),
    "90": ("Territoire de Belfort", "dans le Territoire de Belfort"),
}
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


def export(where, select=None):
    p = {"where": where, "limit": -1}
    if select:
        p["select"] = select
    return http_json(f"{API}/exports/json?" + urllib.parse.urlencode(p))


def fetch(depuis, nature="APPEL_OFFRE"):
    """Avis de marché (ou résultats) parus depuis une date dans les départements suivis, contenu détaillé compris."""
    fx = os.environ.get("BOAMP_FIXTURE")
    if fx:
        data = json.load(open(fx, encoding="utf-8"))
        if isinstance(data, dict):
            return data["marches" if nature == "APPEL_OFFRE" else "attributions"]
        return data if nature == "APPEL_OFFRE" else []
    deps = " or ".join(f'code_departement = "{c}"' for c in DEPS)
    where = f"dateparution >= date'{depuis.isoformat()}' and nature = \"{nature}\" and ({deps})"
    sel = "idweb,objet,nomacheteur,dateparution,datelimitereponse,code_departement,descripteur_libelle,type_marche,nature,nature_libelle,procedure_libelle,famille_libelle,titulaire,url_avis,donnees"
    for nom, s_ in (("avec détails", sel), ("sans détails", sel.replace(",donnees", ""))):
        try:
            data = export(where, s_)
            print(f"[données] {nature} {nom} : {len(data)} enregistrements")
            if data:
                return data
        except urllib.error.HTTPError as e:
            print(f"[données] {nature} {nom} : HTTP {e.code} {e.read()[:400]!r}")
        except Exception as e:  # réseau, JSON
            print(f"[données] {nature} {nom} : {e!r}")
    return []


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
    }


def normaliser_resultat(rec):
    """Un résultat de marché (avis d'attribution) : qui a gagné, combien d'offres, quel montant, quand c'est publié."""
    r = {re.sub(r"[^a-z]", "", k.lower()): v for k, v in rec.items()}
    idweb, objet, paru = str(r.get("idweb") or "").strip(), " ".join(html.unescape(str(r.get("objet") or "")).split()), parse_date(r.get("dateparution"))
    if not (idweb and objet and paru):
        return None
    d = extraire.details_attribution(r.get("donnees"))
    vus, gagnants = set(), []
    for g in liste(r.get("titulaire")) + d.get("titulaires", []):
        g = " ".join(html.unescape(g).split())
        if g and slug(g) not in vus and len(g) < 120 and not slug(g).startswith(("inconnu", "non-renseigne", "sans-objet")):
            vus.add(slug(g))
            gagnants.append(g)
    url = str(r.get("urlavis") or "")
    if not url.startswith("https://www.boamp.fr/"):
        url = "https://www.boamp.fr/pages/avis/?q=" + urllib.parse.quote(f'idweb:"{idweb}"')
    return {"id": idweb, "objet": objet, "acheteur": " ".join(html.unescape(str(r.get("nomacheteur") or "")).split()), "paru": paru,
            "deps": [c for c in (x.zfill(2) for x in liste(r.get("codedepartement"))) if c in DEPS],
            "metiers": [slug(m) for m in liste(r.get("descripteurlibelle"))], "gagnants": gagnants, "texte": d.get("texte", ""),
            "offres": d.get("offres", []), "montant": d.get("montant"), "url": url, "siret": extraire.siret_acheteur(r.get("donnees"))}


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
<nav aria-label="Navigation principale"><a href="{rel}#departements">Départements</a><a href="{rel}metiers/">Métiers</a><a href="{rel}a-propos/">À propos</a>{f'<a class="inscrire" href="{rel}inscription/">Alertes gratuites</a>' if ALERTES else ''}</nav></div></header>
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


def ligne_resultat(r):
    if r["gagnants"]:
        qui = f"<p class=\"gagne\">Attribué à <b>{E(', '.join(r['gagnants'][:6]))}</b>{' et d’autres entreprises' if len(r['gagnants']) > 6 else ''}</p>"
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
    lignes = "".join(f"<tr><td>{E(forme[k])}</td><td class='n'>{compte[k]}</td><td>{E(dernier[k]['acheteur'])}, {MOIS_C[dernier[k]['paru'].month - 1]} {dernier[k]['paru'].year}</td></tr>" for k in top)
    offres = [r["offres"][0] for r in res if r["offres"]]
    stat = ""
    if len(offres) >= 3:
        med = int(statistics.median(offres))
        stat = f'<p class="repere"><b>{med}</b><span>offre{"s" if med > 1 else ""} reçue{"s" if med > 1 else ""} par marché, en médiane, sur les {len(offres)} résultats qui donnent ce chiffre</span></p>'
    return f"""<section id="titulaires" class="bloc"><h2>Qui a remporté les marchés « {E(m)} » {prep}</h2>
<p class="intro">{len(res)} résultat{'s' if len(res) > 1 else ''} publié{'s' if len(res) > 1 else ''} depuis 24 mois. Ce sont les entreprises que vous aurez le plus de chances de retrouver en face de vous.</p>
{stat}
<div class="tablo"><table><thead><tr><th>Entreprise retenue</th><th class="n">Marchés</th><th>Dernier marché remporté</th></tr></thead><tbody>{lignes}</tbody></table></div>
<p class="note">D'après les résultats publiés au Bulletin officiel. Tous les marchés attribués n'y sont pas publiés.</p></section>"""


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
        histo = f'<p class="intro">{len(hist)} résultat{"s" if len(hist) > 1 else ""} publié{"s" if len(hist) > 1 else ""} par cet acheteur depuis 24 mois. Regardez qui il a retenu et combien d\'entreprises avaient répondu.</p>'
        if memes:
            histo += f'<h3 class="sous">Dans le même métier</h3><ul class="resultats">{"".join(ligne_resultat(x) for x in memes[:10])}</ul>'
        reste_n = max(0, 12 - len(memes[:10]))
        if autres and reste_n:
            histo += f'<h3 class="sous">{"Ses autres marchés" if memes else "Ses derniers marchés"}</h3><ul class="resultats">{"".join(ligne_resultat(x) for x in autres[:reste_n])}</ul>'
        vus = len(memes[:10]) + len(autres[:reste_n])
        if len(hist) > vus:
            histo += f'<p class="note">Les {vus} plus utiles sur {len(hist)} sont affichés.</p>'
    else:
        histo = '<p class="vide">Aucun résultat publié au Bulletin officiel par cet acheteur depuis 24 mois. Cela ne veut pas dire qu\'il n\'a rien attribué : tous les résultats n\'y sont pas publiés.</p>'
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
<a class="bouton second" href="{E(a['url'])}" rel="nofollow noopener">Lire l'avis officiel</a><p class="note">Avis n° {E(a['id'])} sur boamp.fr{f", publié le {fr(a['paru'])}" if a['paru'] else ''}.</p></aside>
<div class="f-corps">
<section class="bloc"><h2>L'essentiel de l'annonce</h2><dl class="essentiel">{essentiel}</dl></section>
<section class="bloc"><h2>Ce que cet acheteur a déjà attribué</h2>{histo}</section>
{classement}
{f'<section class="bloc"><h2>Annonces du même type</h2><p class="rubriques">{rubriques}</p></section>' if rubriques else ''}
</div></div>"""
    fil = [("Accueil", "")] + ([(DEPS[a["deps"][0]][0], f"{dslug[a['deps'][0]]}/")] if a["deps"] else [])
    page(f"avis/{a['id']}", f"{court(a['objet'])} | {SITE}", court(f"{a['acheteur']} : à remettre avant le {fr(a['limite'])}. L'essentiel de l'annonce, le dossier à télécharger et les marchés déjà attribués par cet acheteur.", 158), corps, fil=fil, large=True)


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


MENTION_ALERTES = ("Si vous créez une alerte, votre adresse e-mail est enregistrée avec le métier et le département choisis, dans le seul but de vous envoyer cette alerte. "
    "Elle est stockée chez Supabase et les e-mails partent par Brevo. Elle est supprimée dès que vous vous désinscrivez, et au bout de 7 jours si vous ne confirmez pas l'inscription."
    + (f" Pour toute demande concernant vos données : {E(CONFIG['contact_email'])}." if CONFIG.get("contact_email") else ""))

JS = r"""(function(){
var URL="__URL__",KEY="__KEY__",H={"apikey":KEY,"Authorization":"Bearer "+KEY,"Content-Type":"application/json"};
document.querySelectorAll("form.alerte").forEach(function(f){
  f.addEventListener("submit",function(e){
    e.preventDefault();
    var etat=f.querySelector(".etat"),email=f.email.value.trim().toLowerCase();
    var dep=f.dataset.dep||(f.dep?f.dep.value:""),metier=f.dataset.metier||(f.metier?f.metier.value:"");
    if(!metier){etat.textContent="Choisissez votre métier dans la liste.";f.metier.focus();return;}
    if(!dep){etat.textContent="Choisissez votre département dans la liste.";f.dep.focus();return;}
    if(f.site.value){return;}
    if(!/^[^@\s]+@[^@\s]+\.[a-z]{2,}$/.test(email)){etat.textContent="Cette adresse e-mail n'est pas valide.";f.email.focus();return;}
    etat.textContent="Enregistrement…";
    fetch(URL+"/rest/v1/lo_abonnes",{method:"POST",headers:Object.assign({"Prefer":"return=minimal"},H),
      body:JSON.stringify({email:email,dep:dep,metier:metier})})
    .then(function(r){
      if(r.status===201){etat.textContent="C'est noté. Un e-mail de confirmation vous sera envoyé dans l'heure : cliquez sur son lien pour activer l'alerte.";f.email.value="";}
      else if(r.status===409){etat.textContent="Cette adresse est déjà inscrite à cette alerte.";}
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
    if(conf){a.textContent=v?"Votre alerte est active. Vous recevrez un e-mail quand un nouvel avis paraîtra.":"Ce lien n'est plus valable : l'inscription a expiré ou a été supprimée.";}
    else{a.textContent=v?"Vous êtes désinscrit. Votre adresse a été supprimée.":"Cette alerte était déjà supprimée.";}
  }).catch(function(){a.textContent="L'opération n'a pas abouti. Réessayez dans quelques minutes.";});
}
})();"""


def main():
    global TODAY, SITEMAP, HIST, RES_COMBO
    TODAY = dt.datetime.now(dt.timezone(dt.timedelta(hours=1))).date()
    SITEMAP = []
    brut = fetch(TODAY - dt.timedelta(days=JOURS))
    vus, tous = set(), []
    for rec in brut:
        a = normaliser(rec, TODAY)
        if a and a["id"] not in vus:
            vus.add(a["id"])
            tous.append(a)
    ouverts = [a for a in tous if a["reste"] >= 0]
    print(f"[site] {len(brut)} reçus, {len(tous)} avis de marché retenus, {len(ouverts)} ouverts")

    # résultats de marché des 24 derniers mois : qui a gagné quoi, chez quel acheteur
    resultats, vus_r = [], set()
    for rec in fetch(TODAY - dt.timedelta(days=HISTORIQUE), "ATTRIBUTION"):
        r = normaliser_resultat(rec)
        if r and r["id"] not in vus_r:
            vus_r.add(r["id"])
            resultats.append(r)
    par_siret, par_nom, RES_COMBO = defaultdict(list), defaultdict(list), defaultdict(list)
    for r in resultats:
        if r["siret"]:
            par_siret[r["siret"]].append(r)
        par_nom[slug(r["acheteur"])].append(r)
        for c in r["deps"]:
            for m in r["metiers"]:
                RES_COMBO[(c, m)].append(r)
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
<p>{len(ouverts)} annonces de mairies, d'écoles, d'hôpitaux et de collectivités sont ouvertes aujourd'hui en {REGION}. Pour chacune : la date limite, le dossier à télécharger, et les entreprises que l'acheteur a retenues les fois précédentes.</p></div>
<form class="trouver" role="search"><h2>Trouver les annonces pour mon métier</h2>
<label for="t-metier">Votre métier ou votre activité<input id="t-metier" type="search" autocomplete="off" placeholder="peinture, électricité, nettoyage, espaces verts…"></label>
<label for="t-dep">Votre département<select id="t-dep"><option value="">Toute la région</option>{options}</select></label>
<ul class="propos" aria-live="polite"></ul>
<noscript><p>Sans JavaScript, choisissez un département ou un métier dans les listes plus bas.</p></noscript></form></div>
{BANDEAU("") if ALERTES else ''}
<ol class="etapes"><li><b>Choisissez votre métier</b><span>Vous voyez seulement les annonces qui vous concernent, de la plus urgente à la plus lointaine.</span></li>
<li><b>Lisez la fiche</b><span>Montant, lots, critères de notation, et qui a gagné les marchés précédents de cet acheteur.</span></li>
<li><b>Téléchargez le dossier</b><span>Un lien direct vers les documents à remplir, sur la plateforme de l'acheteur.</span></li></ol>
<section class="bloc" id="departements"><h2>Par département</h2>{liens([(f"{DEPS[c][0]}", f"{dslug[c]}/", len(par_dep[c])) for c in DEPS], "deps")}</section>
<section class="bloc"><h2>Les métiers les plus demandés</h2>{liens([(metiers[s], f"metier/{s}/", len(par_met[s])) for s in actifs[:24]])}
<p><a class="suite" href="metiers/">Voir les {len(actifs)} métiers</a></p></section>
<section class="bloc"><h2>À remettre dans les 7 jours</h2><p class="intro">{len(semaine)} annonce{'s' if len(semaine) > 1 else ''} arrive{'nt' if len(semaine) > 1 else ''} à échéance cette semaine.</p>{bloc_liste(sorted(semaine, key=lambda a: a['limite'])[:20], filtres=False)}</section>"""
    page("", f"Appels d'offres en {REGION} : {n_avis(len(ouverts))} | {SITE}",
         f"Les marchés publics ouverts en {REGION}, triés par métier et par département, avec le dossier à télécharger et les entreprises déjà retenues par chaque acheteur.", corps, large=True)

    # tous les métiers
    page("metiers", f"Appels d'offres par métier en {REGION} | {SITE}", f"Les {len(actifs)} métiers et activités qui ont des annonces de marchés publics ouvertes en {REGION}.",
         f"""<h1>Tous les métiers</h1>
<p class="intro">{len(actifs)} métiers et activités ont au moins une annonce ouverte aujourd'hui en {REGION}.</p>
<label class="cherche" for="f-metier"><span>Filtrer la liste</span><input id="f-metier" type="search" placeholder="peinture, voirie, assurance…"></label>
{liens([(metiers[s], f"../metier/{s}/", len(par_met[s])) for s in sorted(actifs, key=lambda s: slug(metiers[s]))])}""", fil=[("Accueil", "")])

    # départements
    for c, (nom, prep) in DEPS.items():
        av = par_dep[c]
        mets = sorted({s for (cc, s) in combos_vus if cc == c}, key=lambda s: (-len(par_combo[(c, s)]), metiers[s]))
        corps = f"""<h1>Appels d'offres {prep}</h1>
<p class="intro">{n_avis(len(av))} au {fr(TODAY)}, de la plus urgente à la plus lointaine.</p>
<section class="bloc"><h2>Affiner par métier</h2>{liens([(metiers[s], f"{s}/", len(par_combo[(c, s)])) for s in mets if par_combo[(c, s)]]) if av else ''}</section>
<section class="bloc"><h2>Toutes les annonces {prep}</h2>{bloc_liste(av, "../")}</section>
{BANDEAU("../", d=c) if ALERTES else ''}"""
        page(dslug[c], f"Appels d'offres {nom} ({c}) : {n_avis(len(av))} | {SITE}",
             f"Marchés publics ouverts {prep} au {fr(TODAY)} : date limite, dossier à télécharger et entreprises déjà retenues par chaque acheteur.", corps,
             index=bool(av), fil=[("Accueil", "")])
        for s in mets:
            cv = par_combo[(c, s)]
            m = metiers[s]
            corps = f"""<h1>Appels d'offres « {E(m)} » {prep}</h1>
<p class="intro">{n_avis(len(cv))} au {fr(TODAY)}. Voir aussi <a href="../../metier/{s}/">« {E(m)} » dans toute la région</a>.</p>
<section class="bloc">{bloc_liste(cv, "../../")}</section>
{bloc_classement(c, s, m, prep)}
{formulaire(c, s, m, prep)}"""
            page(f"{dslug[c]}/{s}", f"Appels d'offres {m.lower()} {nom} ({c}) : {n_avis(len(cv))} | {SITE}",
                 f"Marchés publics « {m} » ouverts {prep} au {fr(TODAY)}, et les entreprises qui ont remporté les précédents.", corps,
                 index=bool(cv) or bool(RES_COMBO.get((c, s))), fil=[("Accueil", ""), (nom, f"{dslug[c]}/")])

    for a in ouverts:
        page_avis(a, metiers, dslug)

    # métiers (région)
    for s in tri_met:
        av, m = par_met[s], metiers[s]
        deps = [(DEPS[c][0], f"../../{dslug[c]}/{s}/", len(par_combo[(c, s)])) for c in DEPS if par_combo[(c, s)]]
        corps = f"""<h1>Appels d'offres « {E(m)} » en {REGION}</h1>
<p class="intro">{n_avis(len(av))} au {fr(TODAY)}, de la plus urgente à la plus lointaine.</p>
{f'<section class="bloc"><h2>Par département</h2>{liens(deps, "deps")}</section>' if deps else ''}
<section class="bloc">{bloc_liste(av, "../../")}</section>
{BANDEAU("../../", m=s) if ALERTES else ''}"""
        page(f"metier/{s}", f"Appels d'offres {m.lower()} en {REGION} : {n_avis(len(av))} | {SITE}",
             f"Marchés publics « {m} » ouverts en {REGION} au {fr(TODAY)}, classés par date limite.", corps,
             index=bool(av), fil=[("Accueil", ""), ("Métiers", "metiers/")])

    page("a-propos", f"À propos | {SITE}", f"D'où viennent les données de {SITE} et qui édite le site.",
         f"""<h1>À propos de {SITE}</h1>
<section class="bloc"><h2>À quoi sert ce site</h2><p class="intro">Quand une mairie, une école ou un hôpital a besoin de travaux, d'un service ou de fournitures, il publie une annonce et toute entreprise peut proposer ses services. {SITE} range ces annonces par métier et par département, et ajoute à chacune ce que l'acheteur a déjà attribué par le passé.</p></section>
<section class="bloc"><h2>D'où viennent les données</h2><p class="intro">Les annonces et les résultats de marché affichés proviennent des données ouvertes du Bulletin officiel des annonces des marchés publics (BOAMP), diffusées par la Direction de l'information légale et administrative (DILA). Ils sont récupérés une fois par jour. Le site ne modifie pas leur contenu : les montants, critères, lots, entreprises retenues et nombres d'offres sont repris tels que l'acheteur les a publiés, et restent absents quand l'avis ne les donne pas.</p>
<p class="intro">Les marchés d'un même acheteur sont rapprochés par son numéro SIRET ou, à défaut, par son nom exact : l'historique peut donc être incomplet. Tous les marchés publics ne sont pas publiés au BOAMP. Un avis peut avoir été rectifié ou annulé depuis la dernière mise à jour : vérifiez toujours l'avis officiel sur boamp.fr avant de répondre.</p></section>
<section class="bloc"><h2>Mentions légales</h2><p class="intro">Site édité à titre personnel, sans publicité. {MENTION_ALERTES if ALERTES else "Aucune donnée personnelle n'est collectée."} Hébergement : GitHub Pages, GitHub Inc., 88 Colin P. Kelly Jr. Street, San Francisco, CA 94107, États-Unis.</p></section>""",
         fil=[("Accueil", "")])

    if ALERTES:
        opt_m = "".join(f'<option value="{s_}">{E(metiers[s_])}</option>' for s_ in sorted(metiers, key=lambda x: slug(metiers[x])))
        opt_d = "".join(f'<option value="{c}">{E(DEPS[c][0])} ({c})</option>' for c in DEPS)
        page("inscription", f"Alertes gratuites par e-mail | {SITE}", f"Recevez par e-mail les nouvelles annonces de marchés publics de votre métier en {REGION}. Gratuit.",
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
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>{E(u)}</loc><lastmod>{TODAY.isoformat()}</lastmod></url>\n" for u in SITEMAP) + "</urlset>\n", encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
    Path("data").mkdir(exist_ok=True)
    Path("data/etat.json").write_text(json.dumps({"date": TODAY.isoformat(), "recus": len(brut), "retenus": len(tous), "ouverts": len(ouverts), "resultats": len(resultats), "avec_historique": len(HIST), "pages_indexables": len(SITEMAP)}, indent=1) + "\n")
    print(f"[site] {len(SITEMAP)} pages indexables écrites dans {OUT}/")


if __name__ == "__main__":
    main()
