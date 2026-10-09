#!/usr/bin/env python3
"""Lot Ouvert : génère le site statique à partir des données ouvertes du BOAMP.
Aucune dépendance. Lancé chaque nuit par GitHub Actions (.github/workflows/site.yml)."""
import datetime as dt, html, json, os, re, sys, unicodedata, urllib.error, urllib.parse, urllib.request
from collections import defaultdict
from pathlib import Path

SITE = "Lot Ouvert"
BASE = os.environ.get("SITE_URL", "https://example.github.io/lot-ouvert").rstrip("/")
OUT = Path("_site")
JOURS = 75            # fenêtre de publication examinée
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
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def fetch(depuis):
    """Essaie plusieurs formes de requête, de la plus légère à la plus simple."""
    fx = os.environ.get("BOAMP_FIXTURE")
    if fx:
        return json.load(open(fx, encoding="utf-8"))
    date = f"dateparution >= date'{depuis.isoformat()}'"
    deps = " or ".join(f'code_departement = "{c}"' for c in DEPS)
    sel = "idweb,objet,nomacheteur,dateparution,datelimitereponse,code_departement,descripteur_libelle,type_marche,nature,nature_libelle,procedure_libelle,url_avis"
    essais = [
        ("export filtré", f"{API}/exports/json?" + urllib.parse.urlencode({"where": f"{date} and ({deps})", "select": sel, "limit": -1})),
        ("export sans select", f"{API}/exports/json?" + urllib.parse.urlencode({"where": f"{date} and ({deps})", "limit": -1})),
    ]
    for nom, url in essais:
        try:
            data = http_json(url)
            print(f"[données] {nom} : {len(data)} enregistrements")
            if data:
                print("[données] champs :", ", ".join(sorted(data[0].keys())))
                return data
        except urllib.error.HTTPError as e:
            print(f"[données] {nom} : HTTP {e.code} {e.read()[:400]!r}")
        except Exception as e:  # réseau, JSON
            print(f"[données] {nom} : {e!r}")
    # dernier recours : un département à la fois, par pages de 100
    out = []
    for c in DEPS:
        off = 0
        while off < 9900:
            url = f"{API}/records?" + urllib.parse.urlencode({"where": date, "refine": f"code_departement:{c}", "limit": 100, "offset": off, "order_by": "dateparution desc"})
            try:
                page = http_json(url).get("results", [])
            except urllib.error.HTTPError as e:
                print(f"[données] pages {c} : HTTP {e.code} {e.read()[:400]!r}")
                break
            out += page
            if len(page) < 100:
                break
            off += 100
    print(f"[données] pagination : {len(out)} enregistrements")
    if out:
        print("[données] champs :", ", ".join(sorted(out[0].keys())))
    return out


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
    }


# ---------- rendu ----------
def page(chemin, titre, desc, corps, index=True, fil=()):
    canon = f"{BASE}/{chemin}".rstrip("/") + "/" if chemin else BASE + "/"
    prof = chemin.count("/") + 1 if chemin else 0
    rel = "../" * prof
    crumbs = "".join(f'<a href="{rel}{u}">{E(t)}</a> › ' for t, u in fil)
    doc = f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(titre)}</title><meta name="description" content="{E(desc)}">
<meta name="google-site-verification" content="Bn20ldA-SUhsySdq8ciYJMOjD6Uqmb6ymF6bQsDG6r8">
<link rel="canonical" href="{E(canon)}">{'' if index else '<meta name="robots" content="noindex,follow">'}
<link rel="stylesheet" href="{rel}style.css"></head><body>
<header class="top"><a class="brand" href="{rel or './'}">{SITE}</a><span>marchés publics ouverts · {REGION}</span></header>
<main><nav class="fil">{crumbs}</nav>
{corps}
</main>
{f'<script src="{rel}alerte.js" defer></script>' if ALERTES else ''}
<footer><p>Données : Bulletin officiel des annonces des marchés publics (BOAMP), données ouvertes de la DILA. Mise à jour du {fr(TODAY)}. Seul l'avis publié sur boamp.fr fait foi.</p>
<p><a href="{rel}a-propos/">À propos et mentions légales</a></p></footer></body></html>"""
    d = OUT / chemin
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(doc, encoding="utf-8")
    if index:
        SITEMAP.append(canon)


def carte(a):
    r = a["reste"]
    etat = f"J-{r}"
    tags = "".join(f"<li>{E(m)}</li>" for m in a["metiers"][:6])
    lieux = ", ".join(f"{DEPS[c][0]} ({c})" for c in a["deps"])
    meta = " · ".join(x for x in (a["type"], a["procedure"], lieux) if x)
    return f"""<article class="avis{' urgent' if r <= 7 else ''}">
<div class="limite"><b>{etat}</b><span>remise le {fr(a['limite'])}</span></div>
<div class="txt"><h3>{E(a['objet'])}</h3><p class="ach">{E(a['acheteur'])}</p><p class="meta">{E(meta)}</p>
{f'<ul class="tags">{tags}</ul>' if tags else ''}
<p class="src"><a href="{E(a['url'])}" rel="nofollow noopener">Avis officiel n° {E(a['id'])} sur boamp.fr</a>{f" · publié le {fr(a['paru'])}" if a['paru'] else ''}</p></div></article>"""


def bloc_liste(avis):
    if not avis:
        return '<p class="vide">Aucun avis ouvert aujourd\'hui dans cette rubrique. La page est mise à jour chaque matin.</p>'
    return "\n".join(carte(a) for a in sorted(avis, key=lambda a: (a["limite"], a["id"])))


def liens(items):
    """items : (libellé, url, nombre)"""
    return '<ul class="liens">' + "".join(f'<li><a href="{u}">{E(t)}</a> <span>{n}</span></li>' for t, u, n in items) + "</ul>"


def formulaire(dep, metier_slug, metier, prep):
    if not ALERTES:
        return ""
    return f"""<form class="alerte" data-dep="{dep}" data-metier="{metier_slug}" novalidate>
<h2>Recevoir ces annonces par e-mail</h2>
<p>Un e-mail par semaine au plus, seulement quand un nouvel avis « {E(metier)} » paraît {prep}. Gratuit.</p>
<div class="champ"><label for="al-email">Votre adresse e-mail</label><input id="al-email" name="email" type="email" autocomplete="email" required>
<input name="site" type="text" tabindex="-1" autocomplete="off" class="pot" aria-hidden="true"><button type="submit">Créer l'alerte</button></div>
<p class="etat" role="status"></p>
<p class="petit">Votre adresse sert uniquement à envoyer cette alerte. Chaque e-mail contient un lien de désinscription.</p></form>"""


def n_avis(n):
    return f"{n} avis ouvert{'s' if n > 1 else ''}"


CSS = """:root{--bg:#f2f5f4;--surface:#fff;--ink:#13272a;--muted:#566769;--line:#d3dcda;--accent:#0c6b5d;--marker:#ffe066;--marker-ink:#13272a;--warn:#8a4b00}
@media (prefers-color-scheme:dark){:root{--bg:#0f1b1d;--surface:#17272a;--ink:#e6eeec;--muted:#9db0ae;--line:#2c4144;--accent:#4fc3ad;--marker:#e9c93a;--warn:#f0b35c;color-scheme:dark}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--accent)}main,header.top,footer{max-width:60rem;margin-inline:auto;padding-inline:1.1rem}
header.top{display:flex;gap:.8rem;align-items:baseline;flex-wrap:wrap;padding-block:1.1rem;border-bottom:1px solid var(--line)}
.brand{font-weight:800;font-size:1.3rem;color:var(--ink);text-decoration:none;letter-spacing:-.01em}header.top span{color:var(--muted);font-size:.85rem}
main{padding-block:1.4rem 3rem;display:flex;flex-direction:column;gap:1.6rem}.fil{font-size:.85rem;color:var(--muted);min-height:1em}
h1{font-size:clamp(1.6rem,4.5vw,2.4rem);line-height:1.12;margin:0;letter-spacing:-.02em;text-wrap:balance}h2{font-size:1.25rem;margin:0}
.chapo{color:var(--muted);max-width:44rem;margin:0}.compte{font-family:ui-monospace,Menlo,Consolas,monospace;background:var(--marker);color:var(--marker-ink);padding:.05em .4em;border-radius:2px;white-space:nowrap}
section{display:flex;flex-direction:column;gap:.9rem}
.avis{display:grid;grid-template-columns:8.5rem minmax(0,1fr);gap:1rem;background:var(--surface);border:1px solid var(--line);padding:1rem}
.limite{display:flex;flex-direction:column;gap:.15rem}.limite b{font:700 1.35rem ui-monospace,Menlo,Consolas,monospace}.limite span{font-size:.8rem;color:var(--muted)}
.urgent .limite b{color:var(--warn)}.txt{min-width:0;display:flex;flex-direction:column;gap:.3rem}
.avis h3{margin:0;font-size:1.02rem;line-height:1.35;overflow-wrap:anywhere}.avis p{margin:0}.ach{font-weight:600;font-size:.92rem}.meta,.src{font-size:.84rem;color:var(--muted)}
.tags{list-style:none;margin:.2rem 0;padding:0;display:flex;flex-wrap:wrap;gap:.35rem}.tags li{font-size:.76rem;border:1px solid var(--line);padding:.05rem .45rem;border-radius:99px}
.liens{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(15rem,1fr));gap:.35rem 1.5rem}
.liens li{display:flex;justify-content:space-between;gap:.6rem;border-bottom:1px solid var(--line);padding-block:.3rem}.liens span{font-family:ui-monospace,Menlo,Consolas,monospace;color:var(--muted);font-size:.85rem}
.vide{background:var(--surface);border:1px dashed var(--line);padding:1rem;color:var(--muted);margin:0}
footer{border-top:1px solid var(--line);padding-block:1.2rem 2.5rem;font-size:.82rem;color:var(--muted)}footer p{margin:.3rem 0}
.alerte{border:2px solid var(--ink);background:var(--surface);padding:1.2rem;display:flex;flex-direction:column;gap:.6rem}.alerte p{margin:0}
.champ{display:flex;gap:.6rem;flex-wrap:wrap;align-items:end}.champ label{flex-basis:100%;font-weight:600;font-size:.9rem}
.champ input[type=email]{flex:1 1 14rem;min-width:0;font:inherit;padding:.6rem .7rem;border:1px solid var(--line);background:var(--bg);color:var(--ink);border-radius:3px}
.alerte button,.bouton{font:600 1rem inherit;font-family:inherit;background:var(--accent);color:var(--bg);border:0;border-radius:3px;padding:.65rem 1.1rem;cursor:pointer}
.pot{position:absolute;left:-999rem}.etat{font-weight:600;min-height:1.4em}.petit{font-size:.8rem;color:var(--muted)}
@media (max-width:34rem){.avis{grid-template-columns:minmax(0,1fr)}.limite{flex-direction:row;align-items:baseline;gap:.7rem}}"""


MENTION_ALERTES = ("Si vous créez une alerte, votre adresse e-mail est enregistrée avec le métier et le département choisis, dans le seul but de vous envoyer cette alerte. "
    "Elle est stockée chez Supabase et les e-mails partent par Brevo. Elle est supprimée dès que vous vous désinscrivez, et au bout de 7 jours si vous ne confirmez pas l'inscription."
    + (f" Pour toute demande concernant vos données : {E(CONFIG['contact_email'])}." if CONFIG.get("contact_email") else ""))

JS = r"""(function(){
var URL="__URL__",KEY="__KEY__",H={"apikey":KEY,"Authorization":"Bearer "+KEY,"Content-Type":"application/json"};
document.querySelectorAll("form.alerte").forEach(function(f){
  f.addEventListener("submit",function(e){
    e.preventDefault();
    var etat=f.querySelector(".etat"),email=f.email.value.trim().toLowerCase();
    if(f.site.value){return;}
    if(!/^[^@\s]+@[^@\s]+\.[a-z]{2,}$/.test(email)){etat.textContent="Cette adresse e-mail n'est pas valide.";f.email.focus();return;}
    etat.textContent="Enregistrement…";
    fetch(URL+"/rest/v1/lo_abonnes",{method:"POST",headers:Object.assign({"Prefer":"return=minimal"},H),
      body:JSON.stringify({email:email,dep:f.dataset.dep,metier:f.dataset.metier})})
    .then(function(r){
      if(r.status===201){etat.textContent="C'est noté. Un e-mail de confirmation vous sera envoyé dans l'heure : cliquez sur son lien pour activer l'alerte.";f.email.value="";}
      else if(r.status===409){etat.textContent="Cette adresse est déjà inscrite à cette alerte.";}
      else{etat.textContent="L'inscription n'a pas fonctionné. Réessayez dans quelques minutes.";}
    }).catch(function(){etat.textContent="Connexion impossible. Vérifiez votre réseau et réessayez.";});
  });
});
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
    global TODAY, SITEMAP
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
    if len(tous) < int(os.environ.get("MIN_AVIS", "20")):
        sys.exit("Trop peu d'avis exploitables : le site en ligne est laissé tel quel.")

    OUT.mkdir(exist_ok=True)
    (OUT / "style.css").write_text(CSS, encoding="utf-8")
    (OUT / ".nojekyll").write_text("")

    # métiers = descripteurs du BOAMP vus sur la fenêtre (pages stables même quand une rubrique est vide un jour)
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
    for a in ouverts:
        for c in a["deps"]:
            par_dep[c].append(a)
            for m in a["metiers"]:
                par_combo[(c, slug(m))].append(a)
        for m in a["metiers"]:
            par_met[slug(m)].append(a)

    dslug = {c: slug(n) for c, (n, _) in DEPS.items()}
    tri_met = sorted(metiers, key=lambda s: (-len(par_met[s]), metiers[s]))

    # accueil
    corps = f"""<h1>Les marchés publics ouverts en {REGION}, par métier et par département</h1>
<p class="chapo"><span class="compte">{n_avis(len(ouverts))}</span> au {fr(TODAY)}. Chaque matin, les avis du Bulletin officiel sont triés par date limite de remise des offres. Consultation gratuite, sans inscription.</p>
<section><h2>Par département</h2>{liens([(f"{DEPS[c][0]} ({c})", f"{dslug[c]}/", len(par_dep[c])) for c in DEPS])}</section>
<section><h2>Par métier</h2>{liens([(metiers[s], f"metier/{s}/", len(par_met[s])) for s in tri_met if par_met[s]])}</section>
<section><h2>À remettre en premier</h2>{bloc_liste(sorted(ouverts, key=lambda a: a['limite'])[:15])}</section>"""
    page("", f"Appels d'offres en {REGION} : {n_avis(len(ouverts))} | {SITE}",
         f"Les marchés publics ouverts en {REGION}, triés par métier, département et date limite. Mis à jour chaque matin à partir du BOAMP.", corps)

    # départements
    for c, (nom, prep) in DEPS.items():
        av = par_dep[c]
        mets = sorted({s for (cc, s) in combos_vus if cc == c}, key=lambda s: (-len(par_combo[(c, s)]), metiers[s]))
        corps = f"""<h1>Appels d'offres {prep} ({c})</h1>
<p class="chapo"><span class="compte">{n_avis(len(av))}</span> au {fr(TODAY)}, classés par date limite de remise des offres.</p>
<section><h2>Par métier {prep}</h2>{liens([(metiers[s], f"{s}/", len(par_combo[(c, s)])) for s in mets if par_combo[(c, s)]]) if av else ''}</section>
<section><h2>Tous les avis ouverts</h2>{bloc_liste(av)}</section>"""
        page(dslug[c], f"Appels d'offres {nom} ({c}) : {n_avis(len(av))} | {SITE}",
             f"Marchés publics ouverts {prep} au {fr(TODAY)} : objet, acheteur, date limite et lien vers l'avis officiel.", corps,
             index=bool(av), fil=[("Accueil", "")])
        for s in mets:
            cv = par_combo[(c, s)]
            m = metiers[s]
            corps = f"""<h1>Appels d'offres {E(m.lower())} {prep} ({c})</h1>
<p class="chapo"><span class="compte">{n_avis(len(cv))}</span> au {fr(TODAY)}. Voir aussi <a href="../../metier/{s}/">{E(m.lower())} dans toute la région</a>.</p>
<section>{bloc_liste(cv)}</section>
{formulaire(c, s, m, prep)}"""
            page(f"{dslug[c]}/{s}", f"Appels d'offres {m.lower()} {nom} ({c}) : {n_avis(len(cv))} | {SITE}",
                 f"Marchés publics « {m} » ouverts {prep} au {fr(TODAY)}, classés par date limite.", corps,
                 index=bool(cv), fil=[("Accueil", ""), (nom, f"{dslug[c]}/")])

    # métiers (région)
    for s in tri_met:
        av, m = par_met[s], metiers[s]
        deps = [(f"{DEPS[c][0]} ({c})", f"../../{dslug[c]}/{s}/", len(par_combo[(c, s)])) for c in DEPS if par_combo[(c, s)]]
        corps = f"""<h1>Appels d'offres {E(m.lower())} en {REGION}</h1>
<p class="chapo"><span class="compte">{n_avis(len(av))}</span> au {fr(TODAY)}, classés par date limite de remise des offres.</p>
{f'<section><h2>Par département</h2>{liens(deps)}</section>' if deps else ''}
<section>{bloc_liste(av)}</section>"""
        page(f"metier/{s}", f"Appels d'offres {m.lower()} en {REGION} : {n_avis(len(av))} | {SITE}",
             f"Marchés publics « {m} » ouverts en {REGION} au {fr(TODAY)}, classés par date limite.", corps,
             index=bool(av), fil=[("Accueil", "")])

    page("a-propos", f"À propos | {SITE}", f"D'où viennent les données de {SITE} et qui édite le site.",
         f"""<h1>À propos de {SITE}</h1>
<section><h2>Les données</h2><p class="chapo">Les avis affichés proviennent des données ouvertes du Bulletin officiel des annonces des marchés publics (BOAMP), diffusées par la Direction de l'information légale et administrative (DILA). Ils sont récupérés une fois par jour, puis triés par département et par mot-clé du BOAMP. Le site ne modifie pas leur contenu. Un avis peut avoir été rectifié ou annulé depuis la dernière mise à jour : vérifiez toujours l'avis officiel sur boamp.fr avant de répondre. Tous les marchés publics ne sont pas publiés au BOAMP.</p></section>
<section><h2>Mentions légales</h2><p class="chapo">Site édité à titre personnel, sans publicité. {MENTION_ALERTES if ALERTES else "Aucune donnée personnelle n'est collectée."} Hébergement : GitHub Pages, GitHub Inc., 88 Colin P. Kelly Jr. Street, San Francisco, CA 94107, États-Unis.</p></section>""",
         fil=[("Accueil", "")])

    if ALERTES:
        for chemin, titre, action, attente in (
            ("alerte/confirmer", "Confirmation de votre alerte", "confirmer", "Confirmation en cours…"),
            ("alerte/desinscription", "Désinscription", "desinscrire", "Désinscription en cours…")):
            page(chemin, f"{titre} | {SITE}", titre,
                 f'<h1>{titre}</h1><p class="chapo etat" data-action="{action}" role="status">{attente}</p><p><a href="../../">Retour aux marchés ouverts</a></p>', index=False)
        (OUT / "alerte.js").write_text(JS.replace("__URL__", CONFIG["supabase_url"].rstrip("/")).replace("__KEY__", CONFIG["supabase_anon_key"]), encoding="utf-8")

    (OUT / "404.html").write_text(f'<!doctype html><html lang="fr"><meta charset="utf-8"><title>Page introuvable | {SITE}</title><meta name="robots" content="noindex"><link rel="stylesheet" href="{BASE}/style.css"><main><h1>Page introuvable</h1><p><a href="{BASE}/">Retour aux marchés ouverts</a></p></main></html>', encoding="utf-8")
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>{E(u)}</loc><lastmod>{TODAY.isoformat()}</lastmod></url>\n" for u in SITEMAP) + "</urlset>\n", encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
    Path("data").mkdir(exist_ok=True)
    Path("data/etat.json").write_text(json.dumps({"date": TODAY.isoformat(), "recus": len(brut), "retenus": len(tous), "ouverts": len(ouverts), "pages_indexables": len(SITEMAP)}, indent=1) + "\n")
    print(f"[site] {len(SITEMAP)} pages indexables écrites dans {OUT}/")


if __name__ == "__main__":
    main()
