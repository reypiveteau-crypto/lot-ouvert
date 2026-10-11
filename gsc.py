#!/usr/bin/env python3
"""Lot Ouvert : relève chaque matin les chiffres de Google Search Console (lecture seule) et les range dans data/google.json.
Sans le secret GSC_KEY, le script ne fait rien."""
import datetime as dt, json, os, sys, urllib.parse

CLE = os.environ.get("GSC_KEY", "").strip()
SITE = os.environ.get("SITE_URL", "").rstrip("/") + "/"
if not CLE:
    print("Search Console non configurée (secret GSC_KEY absent) : rien à faire.")
    sys.exit(0)

from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession

creds = service_account.Credentials.from_service_account_info(json.loads(CLE), scopes=["https://www.googleapis.com/auth/webmasters.readonly"])
http = AuthorizedSession(creds)
base = "https://www.googleapis.com/webmasters/v3/sites/" + urllib.parse.quote(SITE, safe="")
fin = dt.date.today() - dt.timedelta(days=1)
debut = fin - dt.timedelta(days=27)


def requete(dimensions, limite):
    r = http.post(base + "/searchAnalytics/query", json={"startDate": debut.isoformat(), "endDate": fin.isoformat(),
                                                        "dimensions": dimensions, "rowLimit": limite, "dataState": "all"}, timeout=60)
    if r.status_code != 200:
        print(f"[google] {dimensions} : HTTP {r.status_code} {r.text[:300]}")
        return None
    return [{"cle": x["keys"][0], "clics": x.get("clicks", 0), "affichages": x.get("impressions", 0),
             "position": round(x.get("position", 0), 1)} for x in r.json().get("rows", [])]


jours, recherches, pages = requete(["date"], 60), requete(["query"], 200), requete(["page"], 200)
if jours is None:
    sys.exit("Lecture de la Search Console impossible : vérifiez que le compte de service est bien ajouté comme utilisateur du site.")
plans = []
r = http.get(base + "/sitemaps", timeout=60)
if r.status_code == 200:
    for s in r.json().get("sitemap", []):
        plans.append({"adresse": s.get("path"), "lu_le": s.get("lastDownloaded"), "en_attente": s.get("isPending"), "erreurs": s.get("errors"),
                      "contenu": [{"type": c.get("type"), "soumises": c.get("submitted"), "indexees": c.get("indexed")} for c in s.get("contents", [])]})
out = {"releve_le": dt.date.today().isoformat(), "periode": [debut.isoformat(), fin.isoformat()],
       "total": {"clics": sum(j["clics"] for j in jours), "affichages": sum(j["affichages"] for j in jours)},
       "par_jour": jours, "recherches": recherches or [], "pages": [dict(p, cle=p["cle"].replace(SITE, "/")) for p in (pages or [])], "plans_du_site": plans}
os.makedirs("data", exist_ok=True)
json.dump(out, open("data/google.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"[google] {out['total']['affichages']} affichages, {out['total']['clics']} clics sur 28 jours ; {len(recherches or [])} recherches, {len(pages or [])} pages")
