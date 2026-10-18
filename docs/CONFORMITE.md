# Conformité du site

Le site est contrôlé automatiquement à chaque construction (`site/check_conformite.py`, lancé par
le workflow après `site/build.py`). Si une règle n'est pas respectée, le workflow s'arrête : rien
n'est archivé ni publié. `tests/test_conformite.py` vérifie que le contrôle détecte bien chaque cas.

## Ce qui est vérifié à chaque build

| Règle | Fondement | Contrôle |
|---|---|---|
| Aucune déclaration de patrimoine d'un élu non ministre | Art. LO 135-2 code électoral, loi 2013-907 (45 000 € d'amende) | type de déclaration de chaque ligne et de chaque lien |
| Seuls les champs prévus sont publiés (pas de date de naissance, commentaire, adresse) | RGPD art. 5, 1, c (minimisation) | liste blanche des champs embarqués |
| Activité du conjoint : activité et employeur seulement, tirés d'une déclaration d'intérêts (jamais le nom ni le commentaire) | RGPD art. 5, 1, c ; le conjoint est un tiers, la HATVP publie ces champs sans son nom | liste blanche des champs et type de déclaration |
| Aucune donnée occultée par la HATVP | Choix de la HATVP, minimisation | recherche de « [Données non publiées] » |
| Pas d'année de naissance dans les adresses des fiches | Minimisation | identifiants des élus |
| Liens sources uniquement vers hatvp.fr ; liens sortants vers les fiches Pappers des sociétés (simple navigation) | Exactitude (art. 5, 1, d) | liens des fiches et des PDF, domaines des liens, format des SIREN |
| Aucune ressource tierce (polices, scripts, images) | RGPD art. 44 et jurisprudence Google Fonts : l'IP du visiteur ne doit pas partir chez un tiers | balises et CSS de la page |
| Aucun cookie, stockage navigateur ou mesure d'audience | Art. 82 loi Informatique et libertés (pas de bandeau à prévoir) | recherche des API et traceurs |
| Mentions légales, information RGPD, droit de réponse, CNIL | LCEN art. 6 III et IV, RGPD art. 14 | présence des textes |
| Attribution de la source et date de mise à jour | Licence ouverte Etalab 2.0 | pied de page et date des données |
| Aucune ressource tierce ni connexion sortante, même si le code change | RGPD art. 32 | politique de sécurité (CSP) dans chaque page ; HTTPS imposé par GitHub Pages |
| Groupe politique pour les seuls députés et sénateurs en exercice | RGPD art. 9, 2, e : appartenance rendue publique par l'élu et publiée par son assemblée | catégorie de l'élu portant un groupe |
| Activités et mandats tirés des seules déclarations d'intérêts, sans commentaire ; rémunération reprise seulement sous forme d'années et de montants entiers | Minimisation ; la DSP des parlementaires ne peut être republiée | liste blanche et type de déclaration |
| Amendements, votes et délai de dépôt pour les seuls députés ; commission pour les seuls parlementaires | Minimisation, exactitude | catégorie de l'élu |
| Répertoire des représentants d'intérêts : organisations seulement, pas les noms des dirigeants ou collaborateurs | Minimisation | liste blanche des champs |
| Aucune qualification pénale ou déontologique dans le texte écrit par le site (« conflit d'intérêts », « corruption »…) : les rapprochements sont des liens à examiner | Diffamation (loi de 1881), exactitude | recherche dans `site/template.html`, `site/pages.py` et `site/seo.py` |
| Liens sortants limités à hatvp.fr, pappers.fr, assemblee-nationale.fr, legifrance.gouv.fr, data.economie.gouv.fr, annuaire-entreprises.data.gouv.fr ; adresses du site lui-même (`SITE_URL`) et vocabulaire schema.org dans les métadonnées de référencement, jamais chargés par le navigateur | Exactitude | domaines des liens ; seule balise `<link>` absolue admise : l'adresse canonique de la page sur le site |
| Accueil jamais exclu des moteurs de recherche | Transparence (visibilité du site) | absence de `noindex` dans l'accueil |
| Sociétés au Registre national des entreprises : élus seulement (jamais le conjoint), société, SIREN, forme, fonction et dates de la société ; rapprochement sur nom, premier prénom et mois de naissance (non publié), sans dirigeant à date de naissance inconnue | Minimisation, exactitude (homonymes) | liste blanche des champs, format des SIREN |
| Exports CSV sans date de naissance, commentaire ni donnée du conjoint | Minimisation | liste blanche des colonnes de `public/donnees/*.csv` |

Le contrôle porte sur l'accueil (`index.html` et ses données réduites), sur les données complètes (`donnees/registre.json`), sur chaque page statique (fiches `elus/*.html` et `societes/*.html`, index, méthode, page introuvable) et sur les en-têtes des exports CSV.

Avant la mise en ligne sur GitHub Pages, `--publication` exige en plus que l'éditeur et l'adresse de contact soient renseignés.

## À faire par l'éditeur avant la mise en ligne

1. Dans GitHub, *Settings > Secrets and variables > Actions > Variables*, créer :
   - `EDITEUR_NOM` : nom et prénom de l'éditeur, directeur de la publication ;
   - `EDITEUR_CONTACT` : adresse e-mail qui reçoit les demandes (droits RGPD, corrections, droit de réponse) ;
   - `EDITEUR_ANONYME` (facultatif) : `1` pour ne pas afficher le nom de l'éditeur (LCEN art. 6 III 2, éditeur non professionnel). L'identité doit alors être à jour chez l'hébergeur (le compte GitHub qui publie le site), et `EDITEUR_NOM` peut rester vide. `EDITEUR_CONTACT` reste obligatoire : utiliser une adresse qui ne contient pas le nom ;
   - `SITE_URL` (facultatif) : adresse publique du site, si elle change (nom de domaine propre) ;
   - `GOOGLE_SITE_VERIFICATION`, `BING_SITE_VERIFICATION` (facultatifs) : jeton de la balise de vérification de Google Search Console et de Bing Webmaster Tools, pour y déclarer le site et son sitemap ;
   - `INDEXNOW_KEY` (facultatif) : clé IndexNow (8 à 128 lettres, chiffres ou tirets, publique par nature) ; chaque publication signale alors à Bing et aux moteurs IndexNow les pages modifiées dans la semaine ;
   - `HEBERGEUR` (facultatif) : coordonnées de l'hébergeur, si celles par défaut dans `site/build.py` (GitHub Pages) changent ou sont inexactes.
2. Répondre aux demandes reçues à cette adresse : un mois pour les droits RGPD, trois jours pour publier un droit de réponse.

## Registre des traitements (RGPD art. 30)

- **Traitement :** publication des participations financières déclarées par les responsables publics.
- **Responsable :** l'éditeur (`EDITEUR_NOM`, `EDITEUR_CONTACT`).
- **Finalité :** information du public, transparence de la vie publique.
- **Base légale :** intérêt légitime (art. 6, 1, f). Les données sont rendues publiques par la loi et librement réutilisables (licence Etalab, open data HATVP).
- **Personnes concernées :** députés, sénateurs, membres du gouvernement, députés européens, élus locaux soumis à déclaration ; leurs conjoints, partenaires de PACS ou concubins, pour leur seule activité professionnelle (sans nom).
- **Données :** identité (nom, prénom), fonction, mandat et département d'élection, groupe politique des parlementaires en exercice, participations (société, titres, part du capital, valeur), dates et liens des déclarations ; activité et employeur du conjoint tels que publiés par la HATVP (ni nom, ni commentaire, ni croisement avec d'autres sources, ni recherche par employeur ou au Registre national des entreprises). Sociétés dont l'élu est dirigeant au Registre national des entreprises (nom, SIREN, forme juridique, dernière fonction inscrite, dates de création et de fermeture), rapprochées sur le nom, le premier prénom et le mois de naissance ; affichées comme lien à examiner, sans conclure à une omission dans la déclaration. Patrimoine : membres du gouvernement uniquement. Activités, fonctions et mandats de la déclaration d'intérêts (intitulé, organisme, dates, rémunération déclarée par année, que la HATVP publie et dont la connaissance participe au contrôle des intérêts des responsables publics ; jamais le commentaire). Commission permanente, date d'entrée en fonction, amendements et votes nominatifs des députés citant une société qu'ils détiennent. Décrets de déport des ministres (Journal officiel). Les données sur les sociétés (lobbying, marchés publics, cours) ne sont pas des données personnelles.
- **Source :** open data HATVP (`declarations.xml`, `liste.csv`), téléchargé chaque lundi ; groupes politiques : open data de l'Assemblée nationale et du Sénat (licence ouverte), rapprochés par nom et date de naissance (non publiée) ; répertoire des représentants d'intérêts (HATVP) ; amendements et scrutins (open data de l'Assemblée nationale) ; données essentielles de la commande publique (data.economie.gouv.fr) ; Journal officiel (DILA) ; Registre national des entreprises (INPI), par l'API Recherche d'entreprises de la DINUM (licence ouverte) ; cours Euronext.
- **Destinataires :** public. Sous-traitant : GitHub (hébergement GitHub Pages, dépôt public et exécution des mises à jour, États-Unis, cadre UE-États-Unis).
- **Durée :** affichage aligné sur le fichier HATVP de la semaine ; archives hebdomadaires dans le dépôt public pour la traçabilité des corrections.
- **Sécurité :** site statique sans base de données ni formulaire, HTTPS imposé par GitHub Pages, aucun secret dans le dépôt.

## Ce qui reste hors du contrôle automatique

- **Diffamation (étape 4, croisement avec l'activité parlementaire) :** présenter des faits sourcés côte à côte, jamais « conflit d'intérêts ». À ajouter au contrôle quand l'étape 4 sera construite (liste de termes interdits).
- **Alertes par e-mail (étape 3) :** collecter des adresses d'abonnés crée un nouveau traitement (consentement, désinscription, mise à jour de la page de mentions). Le contrôle actuel bloque tout appel réseau et tout formulaire : il faudra l'adapter délibérément.
- **Avis d'un juriste :** ce dispositif couvre les règles connues ; il ne remplace pas une relecture par un avocat avant le lancement public.
