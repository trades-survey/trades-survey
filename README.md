# Registre des élus actionnaires

Site statique qui publie les participations dans des sociétés déclarées à la HATVP
par les députés, les sénateurs et les membres du gouvernement, et leurs écarts d'une
déclaration à l'autre.

Chaque lundi, GitHub Actions (`.github/workflows/site.yml`) :
1. télécharge l'open data HATVP (`scripts/fetch_hatvp.sh`, licence Etalab) ;
2. extrait les participations (`scripts/extract_participations.py`) et les mouvements
   (`scripts/compute_mouvements.py`) ;
3. archive les CSV de la semaine dans `data/out/` ;
4. construit `public/index.html` (`site/build.py` + `site/template.html`) et le publie sur GitHub Pages,
   dès que la variable de dépôt `EDITEUR_CONTACT` (mentions légales) est renseignée.

Règle juridique appliquée dans le code : déclarations d'intérêts pour tous, déclarations
de patrimoine pour les seuls membres du gouvernement. Les DSP des parlementaires ne sont
jamais lues ni republiées (`site/build.py` s'arrête si une telle ligne apparaît).

Conformité (RGPD, transparence, LCEN, licence Etalab) : `site/check_conformite.py` contrôle chaque build
et bloque archivage et publication en cas de manquement. Détail et variables à renseigner avant la mise en
ligne : `docs/CONFORMITE.md`. Les polices sont auto-hébergées dans `site/fonts/` (licence SIL OFL).

Un « mouvement » est un écart entre deux déclarations successives, pas une transaction datée.

Construire en local : `bash scripts/fetch_hatvp.sh`, puis les commandes du workflow.
Feuille de route : `ROADMAP.md`.
