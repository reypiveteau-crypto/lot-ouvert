"""Lot Ouvert : extrait les informations utiles du contenu détaillé des avis BOAMP (champ « donnees »).
Trois formats coexistent (eForms européen, FNSimple, MAPA). Rien n'est deviné : une information absente reste absente."""
import json, re


def charger(d):
    if isinstance(d, str):
        try:
            d = json.loads(d)
        except ValueError:
            return {}
    return d if isinstance(d, dict) else {}


def txt(n):
    if isinstance(n, dict):
        n = n.get("#text")
    if isinstance(n, (int, float)):
        n = str(n)
    return " ".join(n.split()) if isinstance(n, str) else ""


def trouver(n, cle):
    """Toutes les valeurs rangées sous une clé donnée, à n'importe quelle profondeur."""
    out = []
    if isinstance(n, dict):
        for k, v in n.items():
            if k == cle:
                out += v if isinstance(v, list) else [v]
            else:
                out += trouver(v, cle)
    elif isinstance(n, list):
        for v in n:
            out += trouver(v, cle)
    return out


def nombre(s):
    try:
        v = float(str(s).replace(" ", "").replace(",", "."))
        return v if v > 0 else None
    except ValueError:
        return None


def schema(d):
    d = charger(d)
    return next(iter(d), "") if d else ""


def _criteres_eforms(racine):
    out = []
    for c in trouver(racine, "cac:SubordinateAwardingCriterion"):
        if not isinstance(c, dict):
            continue
        nom = txt(c.get("cbc:Name")) or txt(c.get("cbc:Description")) or {"price": "Prix", "quality": "Qualité", "cost": "Coût"}.get(txt(c.get("cbc:AwardingCriterionTypeCode")), "")
        poids = next((nombre(txt(p)) for p in trouver(c, "efbc:ParameterNumeric") if nombre(txt(p))), None)
        code = next((txt(p) for p in trouver(c, "efbc:ParameterCode")), "")
        if nom and (nom, poids) not in [(o[0], o[1]) for o in out]:
            out.append((nom[:140], poids, "%" if code.startswith("per") else "pts" if code.startswith("poi") else ""))
    return out[:8]


def _criteres_texte(s):
    """Dans les avis simplifiés, les critères sont rédigés en texte libre : on ne garde que les lignes qui portent un poids."""
    out = []
    for nom, poids, unite in re.findall(r"([A-Za-zÀ-ÿ'’ ()/-]{3,80}?)\s*[:(]?\s*(\d{1,3}(?:[.,]\d)?)\s*(%|points?|pts)", s or "", flags=re.I):
        nom = re.sub(r"^[\s\-–•\d.)]+", "", nom).strip(" :(-")
        p = nombre(poids)
        if len(nom) >= 3 and p and p <= 100:
            out.append((nom[:140], p, "%" if unite == "%" else "pts"))
    return out[:8]


def details_marche(donnees):
    d = charger(donnees)
    r = {}
    if "EFORMS" in d:
        e = d["EFORMS"]
        m = next((nombre(txt(x)) for x in trouver(e, "cbc:EstimatedOverallContractAmount")), None)
        if m and m >= 1000:
            r["montant"] = m
        lots = [l for l in trouver(e, "cac:ProcurementProjectLot") if isinstance(l, dict)]
        noms = [txt(n) for l in lots for p in [l.get("cac:ProcurementProject")] if isinstance(p, dict) for n in [p.get("cbc:Name")] if txt(n)]
        if len(lots) > 1:
            r["lots"] = noms[:40] or [f"Lot {i + 1}" for i in range(len(lots))]
        uris = [txt(u) for ref in trouver(e, "cac:CallForTendersDocumentReference") for u in trouver(ref, "cbc:URI")]
        dce = next((u for u in uris if u.startswith("http")), "")
        if dce:
            r["dossier"] = dce
        lieu = next((txt(x.get("cbc:Description")) for x in trouver(e, "cac:RealizedLocation") if isinstance(x, dict) and txt(x.get("cbc:Description"))), "")
        if lieu:
            r["lieu"] = lieu[:200]
        for dm in trouver(e, "cbc:DurationMeasure"):
            v, u = nombre(txt(dm)), (dm.get("@unitCode", "") if isinstance(dm, dict) else "")
            if v and u in ("MONTH", "YEAR", "DAY"):
                r["duree"] = f"{int(v)} {'mois' if u == 'MONTH' else ('an' + ('s' if v > 1 else '')) if u == 'YEAR' else ('jour' + ('s' if v > 1 else ''))}"
                break
        c = _criteres_eforms(e)
        if c:
            r["criteres"] = c
    else:
        brut = json.dumps(d, ensure_ascii=False)
        for cle in ("urlProfilAch", "urlDocConsul", "urlProfilAcheteur", "adresseProfilAcheteur"):
            u = next((txt(x) for x in trouver(d, cle) if txt(x).startswith("http")), "")
            if u:
                r["dossier"] = u
                break
        for cle, nom in (("capaciteTech", "references"), ("lieuExecution", "lieu")):
            v = next((txt(x) for x in trouver(d, cle) if isinstance(x, (str, dict)) and txt(x)), "")
            if v:
                r[nom] = v[:600]
        libre = " ".join(txt(x) for cle in ("autresInformComplementaire", "criteresAttribution", "criteres", "renseignementsComplementaires") for x in trouver(d, cle) if isinstance(x, (str, dict)))
        bloc = re.search(r"crit[èe]res? d['’]attribution(.{0,700})", libre, flags=re.I | re.S)
        c = _criteres_texte(bloc.group(1) if bloc else "")
        if c:
            r["criteres"] = c
        lots = [l for x in trouver(d, "lot") for l in (x if isinstance(x, list) else [x]) if isinstance(l, dict)]
        noms = [txt(l.get("intitule")) or txt(l.get("description")) for l in lots]
        noms = [n for n in noms if n]
        if len(noms) > 1:
            r["lots"] = noms[:40]
        if re.search(r"visite[^.]{0,60}obligatoire", brut, flags=re.I):
            r["visite"] = True
    if not r.get("visite") and re.search(r"visite[^.]{0,60}obligatoire", json.dumps(d, ensure_ascii=False)[:200000], flags=re.I):
        r["visite"] = True
    return r


def details_attribution(donnees):
    d = charger(donnees)
    r = {}
    if "EFORMS" in d:
        e = d["EFORMS"]
        offres = []
        for s in trouver(e, "efac:ReceivedSubmissionsStatistics"):
            if isinstance(s, dict) and txt(s.get("efbc:StatisticsCode")) == "tenders":
                v = nombre(txt(s.get("efbc:StatisticsNumeric")))
                if v and v < 500:
                    offres.append(int(v))
        if offres:
            r["offres"] = offres
        res = next((x for x in trouver(e, "efac:NoticeResult") if isinstance(x, dict)), {})
        m = nombre(txt(res.get("cbc:TotalAmount")))
        if m and m >= 1000:
            r["montant"] = m
    else:
        for cle in ("nbOffresRecues", "nbOffreRecu", "nombreOffres", "NB_OFFRE_RECU", "nbOffres"):
            vals = [int(v) for v in (nombre(txt(x)) for x in trouver(d, cle)) if v and v < 500]
            if vals:
                r["offres"] = vals
                break
        for cle in ("montant", "montantHT", "valeur", "MONTANT", "valeurTotale"):
            vals = [v for v in (nombre(txt(x)) for x in trouver(d, cle)) if v and v >= 1000]
            if vals:
                r["montant"] = sum(vals) if cle != "valeurTotale" else vals[0]
                break
    return r


def cles(n, prefixe="", acc=None, prof=0):
    """Liste des chemins de clés d'un contenu (pour le diagnostic)."""
    acc = set() if acc is None else acc
    if isinstance(n, dict) and prof < 7:
        for k, v in n.items():
            if not k.startswith("@"):
                acc.add(prefixe + k)
                cles(v, prefixe + k + ".", acc, prof + 1)
    elif isinstance(n, list):
        for v in n[:3]:
            cles(v, prefixe, acc, prof)
    return acc
