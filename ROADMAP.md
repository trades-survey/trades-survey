# Capitol Trades FR : feuille de route

Validé par Emilien le 2026-10-07 : toutes les fonctions ci-dessous, y compris le croisement
avec l'activité parlementaire.

Rappel juridique (vaut pour toutes les étapes) : participations tirées des déclarations
d'intérêts (DI, DIA, DIM, DIAM) pour tous, et des DSP pour les seuls membres du gouvernement.
Jamais de republication des DSP des parlementaires.

## Étape 1 : extraction des participations (faite, à lancer sur les vraies données)
Voir `README.md`. Bloquée par l'accès réseau à hatvp.fr depuis l'environnement cloud.

## Étape 2 : historique des positions (« mouvements ») : script écrit, testé sur fixture
- Pour chaque couple élu × société, comparer les déclarations successives (tri par date de dépôt).
- Types de mouvement : apparition, disparition, hausse, baisse (nombre de titres ou valeur déclarée).
- Sortie : `data/out/mouvements.csv` (élu, société, ISIN, déclaration avant/après, dates, delta).
- Limite à afficher partout : ce sont des écarts entre deux déclarations, pas des transactions datées
  (pas d'équivalent du STOCK Act en France).

## Étape 3 : site public et alertes
- Recherche par élu, par société, par ISIN ; fiche société listant les élus qui la détiennent.
- Fiche élu : participations actuelles, historique, liens vers les déclarations HATVP sources.
- Alertes : flux RSS et e-mail à chaque nouvelle déclaration qui modifie une position
  (abonnement par élu ou par société).

## Étape 4 : croisement avec l'activité parlementaire et gouvernementale
Objectif : montrer, à côté d'une participation, l'activité de l'élu sur les textes qui touchent
le secteur ou l'entreprise concernée.

Sources (open data officiel) :
- Assemblée nationale (data.assemblee-nationale.fr) : acteurs, organes (commissions),
  amendements, scrutins avec votes nominatifs, dossiers législatifs, rapporteurs.
- Sénat (data.senat.fr) : amendements (Ameli), scrutins, dossiers législatifs, commissions.
- Ministres : textes portés et décrets signés (JORF via Légifrance / DILA), périmètre du portefeuille.

Rattacher une société à un secteur :
- SIREN et code NAF via l'API Recherche d'entreprises (recherche-entreprises.api.gouv.fr).
- Table de secteurs maison (énergie, banque, défense, pharma, agroalimentaire, numérique, etc.)
  construite à partir du NAF, complétée à la main pour les grandes cotées (CAC 40, SBF 120).
- Liste de mots-clés par société (nom, marques, filiales) pour repérer les mentions directes.

Rattacher un texte à des secteurs ou entreprises :
- Commission saisie au fond (première approximation du secteur).
- Mots-clés dans titres, dispositifs et exposés des motifs des amendements.
- Classement assisté (modèle de langage) des dossiers législatifs, relu par un humain avant
  publication.

Liens calculés par élu × participation :
- Amendements déposés ou cosignés sur un texte du secteur ou citant l'entreprise.
- Votes sur ces textes (pour, contre, abstention).
- Rôle de rapporteur, appartenance à la commission compétente.
- Pour un ministre : textes portés ou décrets signés touchant le secteur.

Présentation : « lien à examiner » factuel, jamais « conflit d'intérêts ». Les faits sont
posés côte à côte avec leurs sources, sans qualification, pour limiter le risque de diffamation.
Prévoir un droit de réponse et une procédure de correction.

## Accès réseau (2026-10-07)
Nouvel environnement cloud : hatvp.fr, data.assemblee-nationale.fr, data.senat.fr et data.gouv.fr
répondent. Encore bloqués : legifrance.gouv.fr (403 du proxy) et recherche-entreprises.api.gouv.fr
(connexion coupée), utiles à l'étape 4.
