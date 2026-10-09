#!/usr/bin/env python3
"""Lot Ouvert : e-mails d'alerte. Deux modes, lancés par .github/workflows/alertes.yml
  confirmations : envoie le lien de confirmation aux nouvelles inscriptions (toutes les heures)
  hebdo         : envoie les nouveaux avis aux inscrits confirmés, au plus une fois par semaine chacun"""
import datetime as dt, html, json, os, sys, urllib.error, urllib.parse, urllib.request
import build

SB, SB_KEY = os.environ.get("SUPABASE_URL", "").rstrip("/"), os.environ.get("SUPABASE_SERVICE_KEY", "")
BREVO, EXP = os.environ.get("BREVO_API_KEY", ""), os.environ.get("EXPEDITEUR_EMAIL", "")
BASE = build.BASE
MAX_CONF, MAX_HEBDO = 40, 240     # l'offre gratuite de Brevo plafonne les envois quotidiens


def appel(url, methode="GET", corps=None, entetes=None):
    req = urllib.request.Request(url, method=methode, headers=entetes or {},
                                 data=None if corps is None else json.dumps(corps).encode())
    with urllib.request.urlopen(req, timeout=60) as r:
        brut = r.read()
        return json.loads(brut) if brut else None


def sb(methode, chemin, corps=None):
    return appel(f"{SB}/rest/v1/{chemin}", methode, corps,
                 {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}", "Content-Type": "application/json", "Prefer": "return=minimal"})


def envoyer(dest, sujet, texte, liens_html, token):
    stop = f"{BASE}/alerte/desinscription/?t={token}"
    pied = f"Lot Ouvert, alertes gratuites sur les marchés publics. Pour ne plus recevoir cette alerte : {stop}"
    corps_html = (f'<div style="font-family:system-ui,sans-serif;font-size:15px;line-height:1.55;color:#13272a;max-width:36rem">{liens_html}'
                  f'<p style="font-size:12px;color:#566769;border-top:1px solid #d3dcda;padding-top:10px;margin-top:24px">Lot Ouvert, alertes gratuites sur les marchés publics. '
                  f'<a href="{html.escape(stop)}">Se désinscrire</a></p></div>')
    appel("https://api.brevo.com/v3/smtp/email", "POST",
          {"sender": {"name": "Lot Ouvert", "email": EXP}, "to": [{"email": dest}], "subject": sujet,
           "textContent": f"{texte}\n\n--\n{pied}", "htmlContent": corps_html, "headers": {"List-Unsubscribe": f"<{stop}>"}},
          {"api-key": BREVO, "Content-Type": "application/json", "Accept": "application/json"})


def lieu(dep):
    return f"{build.DEPS[dep][1]} ({dep})" if dep in build.DEPS else f"dans le département {dep}"


def confirmations():
    limite = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7)).isoformat()
    sb("DELETE", "lo_abonnes?confirme=is.false&cree_le=lt." + urllib.parse.quote(limite))
    rangs = sb("GET", f"lo_abonnes?confirme=is.false&confirmation_envoyee_le=is.null&select=id,email,dep,metier,token&order=cree_le&limit={MAX_CONF}") or []
    n = 0
    for r in rangs:
        lien = f"{BASE}/alerte/confirmer/?t={r['token']}"
        nom = r["metier"].replace("-", " ")
        if r["metier"] == "version-pro":      # liste d'attente de la version Pro
            texte = (f"Bonjour,\n\nVous avez demandé à être prévenu de l'ouverture de la version Pro de Lot Ouvert.\n\n"
                     f"Pour valider votre demande, ouvrez ce lien :\n{lien}\n\nVous recevrez ensuite un seul e-mail, le jour de l'ouverture. "
                     "Si cette demande ne vient pas de vous, ignorez ce message : sans confirmation, l'adresse est supprimée au bout de 7 jours.")
            h = ("<p>Bonjour,</p><p>Vous avez demandé à être prévenu de l'ouverture de la version Pro de Lot Ouvert.</p>"
                 f'<p><a href="{html.escape(lien)}" style="background:#1c3fa8;color:#fff;padding:10px 16px;text-decoration:none;border-radius:3px;display:inline-block">Valider ma demande</a></p>'
                 "<p>Vous recevrez ensuite un seul e-mail, le jour de l'ouverture. Si cette demande ne vient pas de vous, ignorez ce message : sans confirmation, l'adresse est supprimée au bout de 7 jours.</p>")
            try:
                envoyer(r["email"], "Confirmez votre demande : version Pro de Lot Ouvert", texte, h, r["token"])
                n += 1
            except urllib.error.HTTPError as e:
                print(f"[confirmations] envoi refusé ({e.code}) : {e.read()[:200]!r}")
                if e.code in (401, 403, 429):
                    break
            sb("PATCH", f"lo_abonnes?id=eq.{r['id']}", {"confirmation_envoyee_le": dt.datetime.now(dt.timezone.utc).isoformat()})
            continue
        texte = (f"Bonjour,\n\nVous avez demandé à recevoir les nouveaux appels d'offres « {nom} » {lieu(r['dep'])}.\n\n"
                 f"Pour activer cette alerte, ouvrez ce lien :\n{lien}\n\nSi cette demande ne vient pas de vous, ignorez ce message : sans confirmation, l'adresse est supprimée au bout de 7 jours.")
        h = (f"<p>Bonjour,</p><p>Vous avez demandé à recevoir les nouveaux appels d'offres « {html.escape(nom)} » {html.escape(lieu(r['dep']))}.</p>"
             f'<p><a href="{html.escape(lien)}" style="background:#0c6b5d;color:#fff;padding:10px 16px;text-decoration:none;border-radius:3px;display:inline-block">Activer mon alerte</a></p>'
             "<p>Si cette demande ne vient pas de vous, ignorez ce message : sans confirmation, l'adresse est supprimée au bout de 7 jours.</p>")
        try:
            envoyer(r["email"], "Confirmez votre alerte Lot Ouvert", texte, h, r["token"])
        except urllib.error.HTTPError as e:
            print(f"[confirmations] envoi refusé ({e.code}) : {e.read()[:200]!r}")
            if e.code in (401, 403, 429):
                break                       # clé invalide ou plafond atteint : on réessaiera au prochain passage
        else:
            n += 1
        sb("PATCH", f"lo_abonnes?id=eq.{r['id']}", {"confirmation_envoyee_le": dt.datetime.now(dt.timezone.utc).isoformat()})
    print(f"[confirmations] {n} e-mail(s) envoyé(s) sur {len(rangs)} inscription(s) en attente")


def hebdo():
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=1))).date()
    _, tous = build.charger_marches(today)
    ouverts = [x for x in tous if x["reste"] >= 0 and x["paru"]]
    if not ouverts:
        sys.exit("Aucun avis récupéré : aucun e-mail envoyé.")
    semaine = (today - dt.timedelta(days=7)).isoformat()
    rangs = sb("GET", f"lo_abonnes?confirme=is.true&metier=neq.version-pro&or=(dernier_envoi.is.null,dernier_envoi.lte.{semaine})&select=id,email,dep,metier,token,dernier_envoi&order=dernier_envoi.nullsfirst&limit=2000") or []
    n = 0
    for r in rangs:
        if n >= MAX_HEBDO:
            break
        depuis = dt.date.fromisoformat(r["dernier_envoi"]) if r["dernier_envoi"] else today - dt.timedelta(days=7)
        neufs = sorted((a for a in ouverts if r["dep"] in a["deps"] and a["paru"] > depuis
                        and r["metier"] in (build.slug(m) for m in a["metiers"])), key=lambda a: a["limite"])
        if not neufs:
            continue                        # rien de nouveau : pas d'e-mail, on regardera de nouveau demain
        nom = next(m for m in neufs[0]["metiers"] if build.slug(m) == r["metier"])
        page = f"{BASE}/{build.slug(build.DEPS[r['dep']][0])}/{r['metier']}/" if r["dep"] in build.DEPS else BASE + "/"
        titre = f"{len(neufs)} nouvel avis" if len(neufs) == 1 else f"{len(neufs)} nouveaux avis"
        sujet = f"{titre} « {nom} » {lieu(r['dep'])}"
        lignes = [f"- {a['objet']}\n  {a['acheteur']} · remise le {build.fr(a['limite'])} (J-{a['reste']})\n  {a['url']}" for a in neufs[:20]]
        texte = f"Bonjour,\n\n{sujet} :\n\n" + "\n\n".join(lignes) + f"\n\nTous les avis ouverts de cette rubrique : {page}\nSeul l'avis publié sur boamp.fr fait foi."
        h = f"<p>Bonjour,</p><p><b>{html.escape(sujet)}</b></p>" + "".join(
            f'<p style="margin:14px 0"><a href="{html.escape(a["url"])}">{html.escape(a["objet"])}</a><br>{html.escape(a["acheteur"])}<br>'
            f'<span style="color:#566769">Remise le {build.fr(a["limite"])} (J-{a["reste"]})</span></p>' for a in neufs[:20]) + \
            f'<p><a href="{html.escape(page)}">Tous les avis ouverts de cette rubrique</a>. Seul l\'avis publié sur boamp.fr fait foi.</p>'
        try:
            envoyer(r["email"], sujet, texte, h, r["token"])
        except urllib.error.HTTPError as e:
            print(f"[hebdo] envoi refusé ({e.code}) : {e.read()[:200]!r}")
            if e.code in (401, 403, 429):
                break
            continue
        n += 1
        sb("PATCH", f"lo_abonnes?id=eq.{r['id']}", {"dernier_envoi": today.isoformat()})
    print(f"[hebdo] {n} e-mail(s) envoyé(s), {len(rangs)} inscrit(s) à servir, {len(ouverts)} avis ouverts")


if __name__ == "__main__":
    if not (SB and SB_KEY and BREVO and EXP):
        print("Alertes non configurées (secrets absents) : rien à faire.")
        sys.exit(0)
    {"confirmations": confirmations, "hebdo": hebdo}[sys.argv[1]]()
