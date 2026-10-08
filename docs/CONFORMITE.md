# Conformité du site

Le site est contrôlé automatiquement à chaque construction (`site/check_conformite.py`, lancé par
le workflow après `site/build.py`). Si une règle n'est pas respectée, le workflow s'arrête : rien
n'est archivé ni publié. `tests/test_conformite.py` vérifie que le contrôle détecte bien chaque cas.

## Ce qui est vérifié à chaque build

| Règle | Fondement | Contrôle |
|---|---|---|
| Aucune déclaration de patrimoine d'un élu non ministre | Art. LO 135-2 code électoral, loi 2013-907 (45 000 € d'amende) | type de déclaration de chaque ligne et de chaque lien |
| Seuls les champs prévus sont publiés (pas de date de naissance, commentaire, rémunération, adresse) | RGPD art. 5, 1, c (minimisation) | liste blanche des champs embarqués |
| Aucune donnée occultée par la HATVP | Choix de la HATVP, minimisation | recherche de « [Données non publiées] » |
| Pas d'année de naissance dans les adresses des fiches | Minimisation | identifiants des élus |
| Liens sources uniquement vers hatvp.fr | Exactitude (art. 5, 1, d) | liens des fiches et des PDF |
| Aucune ressource tierce (polices, scripts, images) | RGPD art. 44 et jurisprudence Google Fonts : l'IP du visiteur ne doit pas partir chez un tiers | balises et CSS de la page |
| Aucun cookie, stockage navigateur ou mesure d'audience | Art. 82 loi Informatique et libertés (pas de bandeau à prévoir) | recherche des API et traceurs |
| Mentions légales, information RGPD, droit de réponse, CNIL | LCEN art. 6 III et IV, RGPD art. 14 | présence des textes |
| Attribution de la source et date de mise à jour | Licence ouverte Etalab 2.0 | pied de page et date des données |
| Aucune ressource tierce ni connexion sortante, même si le code change | RGPD art. 32 | politique de sécurité (CSP) dans la page ; HTTPS imposé par GitHub Pages |

Avant la mise en ligne sur GitHub Pages, `--publication` exige en plus que l'éditeur et l'adresse de contact soient renseignés.

## À faire par l'éditeur avant la mise en ligne

1. Dans GitHub, *Settings > Secrets and variables > Actions > Variables*, créer :
   - `EDITEUR_NOM` : nom et prénom de l'éditeur, directeur de la publication ;
   - `EDITEUR_CONTACT` : adresse e-mail qui reçoit les demandes (droits RGPD, corrections, droit de réponse) ;
   - `HEBERGEUR` (facultatif) : coordonnées de l'hébergeur, si celles par défaut dans `site/build.py` (GitHub Pages) changent ou sont inexactes.
2. Répondre aux demandes reçues à cette adresse : un mois pour les droits RGPD, trois jours pour publier un droit de réponse.

## Registre des traitements (RGPD art. 30)

- **Traitement :** publication des participations financières déclarées par les responsables publics.
- **Responsable :** l'éditeur (`EDITEUR_NOM`, `EDITEUR_CONTACT`).
- **Finalité :** information du public, transparence de la vie publique.
- **Base légale :** intérêt légitime (art. 6, 1, f). Les données sont rendues publiques par la loi et librement réutilisables (licence Etalab, open data HATVP).
- **Personnes concernées :** députés, sénateurs, membres du gouvernement, députés européens, élus locaux soumis à déclaration.
- **Données :** identité (nom, prénom), fonction et mandat, participations (société, titres, part du capital, valeur), dates et liens des déclarations. Patrimoine : membres du gouvernement uniquement.
- **Source :** open data HATVP (`declarations.xml`, `liste.csv`), téléchargé chaque lundi.
- **Destinataires :** public. Sous-traitant : GitHub (hébergement GitHub Pages, dépôt public et exécution des mises à jour, États-Unis, cadre UE-États-Unis).
- **Durée :** affichage aligné sur le fichier HATVP de la semaine ; archives hebdomadaires dans le dépôt public pour la traçabilité des corrections.
- **Sécurité :** site statique sans base de données ni formulaire, HTTPS imposé par GitHub Pages, aucun secret dans le dépôt.

## Ce qui reste hors du contrôle automatique

- **Diffamation (étape 4, croisement avec l'activité parlementaire) :** présenter des faits sourcés côte à côte, jamais « conflit d'intérêts ». À ajouter au contrôle quand l'étape 4 sera construite (liste de termes interdits).
- **Alertes par e-mail (étape 3) :** collecter des adresses d'abonnés crée un nouveau traitement (consentement, désinscription, mise à jour de la page de mentions). Le contrôle actuel bloque tout appel réseau et tout formulaire : il faudra l'adapter délibérément.
- **Avis d'un juriste :** ce dispositif couvre les règles connues ; il ne remplace pas une relecture par un avocat avant le lancement public.
