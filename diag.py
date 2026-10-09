"""Diagnostic ponctuel n°2 : taux de réussite de l'extraction par format d'avis."""
import json, collections, urllib.parse, urllib.request
import extraire
API = "https://boamp-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/boamp"
deps = " or ".join(f'code_departement = "{c}"' for c in ("21","25","39","58","70","71","89","90"))
def export(where):
    url = f"{API}/exports/json?" + urllib.parse.urlencode({"where": where, "limit": -1, "select": "idweb,famille,nature,nomacheteur,titulaire,donnees"})
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "lot-ouvert/1.0"}), timeout=300) as r:
        return json.load(r)
out = {}
for nom, where, fn in (("marche", f"dateparution >= date'2026-08-20' and nature = \"APPEL_OFFRE\" and ({deps})", extraire.details_marche),
                       ("attribution", f"dateparution >= date'2026-04-01' and nature = \"ATTRIBUTION\" and ({deps})", extraire.details_attribution)):
    recs = export(where)
    stats, ex, vides, tailles = collections.defaultdict(collections.Counter), collections.defaultdict(list), {}, 0
    for r in recs:
        tailles += len(r.get("donnees") or "")
        s = f"{r.get('famille')}/{extraire.schema(r.get('donnees'))}"
        d = fn(r.get("donnees"))
        stats[s]["_total"] += 1
        stats[s]["_avec_titulaire"] += bool(r.get("titulaire"))
        for k in d:
            stats[s][k] += 1
        if len(ex[s]) < 4 and d:
            ex[s].append({"idweb": r["idweb"], **d})
        if s not in vides or (not d and len(vides[s]) < 400):
            vides[s] = sorted(extraire.cles(extraire.charger(r.get("donnees"))))[:400]
    out[nom] = {"n": len(recs), "octets_donnees": tailles, "stats": stats, "exemples": ex, "cles_par_format": vides}
    brut = collections.defaultdict(list)
    for r in recs:
        s = f"{r.get('famille')}/{extraire.schema(r.get('donnees'))}"
        if "EFORMS" not in s and len(brut[s]) < 2:
            brut[s].append((r.get("donnees") or "")[:6000])
    out[nom]["brut_non_eforms"] = brut
json.dump(out, open("data/diag.json", "w"), ensure_ascii=False, indent=1)
print({k: (v["n"], v["octets_donnees"]) for k, v in out.items()})
