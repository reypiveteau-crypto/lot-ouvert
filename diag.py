"""Diagnostic ponctuel : enregistre un échantillon brut des données BOAMP pour voir les champs disponibles."""
import json, urllib.parse, urllib.request, urllib.error
API = "https://boamp-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/boamp"
def get(chemin, **p):
    url = f"{API}/{chemin}?" + urllib.parse.urlencode(p)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "lot-ouvert/1.0"}), timeout=120) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"erreur": e.code, "detail": e.read()[:500].decode("utf-8", "replace"), "url": url}
def court(v, n=1500):
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    return s if len(s) <= n else s[:n] + f"…[{len(s)} car.]"
out = {}
out["natures"] = get("records", select="nature,nature_libelle,count(*) as n", group_by="nature,nature_libelle", where="dateparution >= date'2026-07-01' and code_departement = \"21\"", limit=50)
out["familles"] = get("records", select="famille,famille_libelle,count(*) as n", group_by="famille,famille_libelle", where="dateparution >= date'2026-07-01' and code_departement = \"21\"", limit=50)
for nom, w in (("marche", 'nature = "APPEL_OFFRE"'), ("attribution", 'nature = "ATTRIBUTION"')):
    r = get("records", where=f"dateparution >= date'2026-08-01' and code_departement = \"21\" and {w}", limit=4, order_by="dateparution desc")
    out[nom] = [{k: court(v) for k, v in rec.items() if k != "donnees"} for rec in r.get("results", [])] if "results" in r else r
    out[nom + "_donnees"] = [court(rec.get("donnees"), 9000) for rec in r.get("results", [])[:2]] if "results" in r else None
deps = " or ".join(f'code_departement = "{c}"' for c in ("21","25","39","58","70","71","89","90"))
out["volume_attributions_24_mois"] = get("records", select="count(*) as n", where=f"dateparution >= date'2024-10-01' and nature = \"ATTRIBUTION\" and ({deps})")
out["volume_avec_titulaire"] = get("records", select="count(*) as n", where=f"dateparution >= date'2024-10-01' and nature = \"ATTRIBUTION\" and titulaire is not null and ({deps})")
json.dump(out, open("data/diag.json", "w"), ensure_ascii=False, indent=1)
print("ok", {k: (len(v) if isinstance(v, list) else v if not isinstance(v, dict) else list(v)[:3]) for k, v in out.items()})
