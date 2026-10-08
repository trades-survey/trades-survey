# Registre des élus actionnaires

Site statique qui publie les participations dans des sociétés déclarées à la HATVP
par les députés, les sénateurs et les membres du gouvernement, et leurs écarts d'une
déclaration à l'autre.

Chaque lundi, GitHub Actions (`.github/workflows/site.yml`) :
1. télécharge l'open data HATVP (`scripts/fetch_hatvp.sh`, licence Etalab) ;
2. extrait les participations (`scripts/extract_participations.py`) et les mouvements
   (`scripts/compute_mouvements.py`) ;
3. archive les CSV de la semaine dans `data/out/` ;
4. récupère le groupe politique des députés et sénateurs (`scripts/fetch_groupes.py`, open data Assemblée et Sénat) ;
   télécharge la liste officielle Euronext (`scripts/fetch_euronext.py`) pour vérifier chaque ISIN : un code
   qu'Euronext attribue à une autre société est retiré, un code confirmé est marqué vérifié ;
5. construit le site (`site/build.py`, `site/template.html`, `site/pages.py`) et le publie sur GitHub Pages,
   dès que la variable de dépôt `EDITEUR_CONTACT` (mentions légales) est renseignée.

Le site construit dans `public/` comprend l'accueil (listes, filtres et recherche ; l'état des filtres et du tri est dans
l'adresse, par exemple `#elus?cat=depute&dep=69&tri=-v`), une page statique par élu (`elus/<id>.html`) et par société
(`societes/<id>.html`), les exports `donnees/*.csv` et `donnees/registre.json`, un flux RSS des mouvements (`flux.xml`)
et un `sitemap.xml`. La variable de dépôt `SITE_URL` donne l'adresse publique utilisée par le flux et le sitemap
(par défaut `https://trades-survey.github.io/trades-survey/`).

Règle juridique appliquée dans le code : déclarations d'intérêts pour tous, déclarations
de patrimoine pour les seuls membres du gouvernement. Les DSP des parlementaires ne sont
jamais lues ni republiées (`site/build.py` s'arrête si une telle ligne apparaît).

Conformité (RGPD, transparence, LCEN, licence Etalab) : `site/check_conformite.py` contrôle chaque build
et bloque archivage et publication en cas de manquement. Détail et variables à renseigner avant la mise en
ligne : `docs/CONFORMITE.md`. Les polices sont auto-hébergées dans `site/fonts/` (licence SIL OFL).

Un « mouvement » est un écart entre deux déclarations successives, pas une transaction datée. Quand le nombre de titres
n'a pas changé, l'écart est classé « variation de valeur » (effet du cours) et masqué par défaut.

Construire en local : `bash scripts/fetch_hatvp.sh`, puis les commandes du workflow.
Feuille de route : `ROADMAP.md`.
