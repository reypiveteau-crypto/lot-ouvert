"""Diagnostic ponctuel n°3 : enregistre un échantillon réel complet pour les tests locaux."""
import json, urllib.parse, urllib.request
API = "https://boamp-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/boamp"
def export(where, limit):
    url = f"{API}/exports/json?" + urllib.parse.urlencode({"where": where, "limit": limit, "order_by": "dateparution desc"})
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "lot-ouvert/1.0"}), timeout=300) as r:
        return json.load(r)
out = {"marches": export("dateparution >= date'2026-08-01' and nature = \"APPEL_OFFRE\" and code_departement = \"21\"", 160),
       "attributions": export("dateparution >= date'2024-10-01' and nature = \"ATTRIBUTION\" and code_departement = \"21\"", 450)}
json.dump(out, open("data/echantillon.json", "w"), ensure_ascii=False)
print({k: len(v) for k, v in out.items()})
