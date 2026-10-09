# Lot Ouvert

Site statique des marchés publics ouverts en Bourgogne-Franche-Comté, par métier et par département.

- `build.py` récupère les avis du BOAMP (données ouvertes de la DILA) et écrit le site dans `_site/`.
- `.github/workflows/site.yml` le lance chaque matin et publie sur GitHub Pages.
- `data/etat.json` garde le compte du jour (avis reçus, ouverts, pages).

Réglage unique : Settings → Pages → Source : **GitHub Actions**.

Test local : `BOAMP_FIXTURE=tests/fixture.json python build.py`

Étendre à d'autres départements : ajouter des lignes au dictionnaire `DEPS` en haut de `build.py`.
