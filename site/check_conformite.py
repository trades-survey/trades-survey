"""Contrôle de conformité du site construit (RGPD, loi sur la transparence, LCEN, licence Etalab).

Lancé après site/build.py, en CI et chaque lundi. Toute anomalie fait échouer le workflow,
donc rien de non conforme n'est publié. Voir docs/CONFORMITE.md pour la justification de chaque règle.

  python3 -I site/check_conformite.py                 # contrôle du build
  python3 -I site/check_conformite.py --publication   # exige aussi des mentions légales complètes
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, 'public')

# Domaines vers lesquels le site peut faire des liens (navigation seulement, jamais de chargement).
LIENS_AUTORISES = {'www.hatvp.fr', 'www.etalab.gouv.fr', 'www.cnil.fr', 'www.pappers.fr'}
# Mouchards, stockage côté navigateur et appels réseau : interdits (pas de bandeau cookies, pas de consentement à recueillir).
TRACEURS = [r'document\.cookie', r'localStorage', r'sessionStorage', r'indexedDB', r'sendBeacon', r'\bfetch\(',
            r'XMLHttpRequest', r'WebSocket', r'<iframe', r'<img[^>]+src=["\']https?:', r'googletagmanager', r'google-analytics',
            r'gtag\(', r'matomo', r'_paq', r'facebook\.net', r'hotjar', r'plausible', r'doubleclick']
# Seuls champs que le site a le droit d'embarquer, par objet (minimisation des données).
CHAMPS = {
    # groupe politique (g, gl) : parlementaires en exercice seulement, d'après l'open data de leur assemblée (RGPD art. 9, 2, e)
    'elu': {'id', 'p', 'n', 'cat', 'fn', 'dep', 'cats', 'org', 'mandat', 'page', 'masked', 'h', 'decls', 'cj', 'g', 'gl'},
    # activité du conjoint : activité et employeur seulement (jamais le nom ni le commentaire)
    'conjoint': {'d', 't', 'l'},
    'conjoint_ligne': {'a', 'e'},
    'holding': {'s', 'n', 'f', 'nl', 'v', 'q', 'c', 'd', 't'},
    'decl': {'t', 'd', 'm', 'u'},
    'soc': {'k', 'id', 'name', 'isin', 'iv', 'siren', 'nat', 'holders'},
    'holder': {'e', 'v', 'q', 'd', 'f'},
    'mv': {'e', 's', 'n', 'f', 'm', 'da', 'dp', 'qa', 'qp', 'va', 'vp'},
}
# Données embarquées dans l'accueil (listes, filtres, recherche) : un sous-ensemble des précédentes
CHAMPS_ACCUEIL = {
    'elu': {'id', 'p', 'n', 'cat', 'fn', 'dep', 'org', 'g', 'nh', 'v'},
    'soc': {'k', 'id', 'name', 'isin', 'siren', 'nat', 'nh', 'nm'},
    'mv': CHAMPS['mv'],
}
MOUVEMENTS = {'apparition', 'disparition', 'hausse', 'baisse', 'valeur'}
# Colonnes autorisées dans les exports téléchargeables (jamais de date de naissance, de commentaire ni de donnée du conjoint)
EXPORTS = {
    'elus.csv': {'id', 'prenom', 'nom', 'fonction', 'circonscription_ou_ministere', 'departement', 'groupe', 'groupe_libelle', 'lignes_declarees', 'valeur_declaree_eur', 'fiche_hatvp', 'url'},
    'participations.csv': {'elu_id', 'prenom', 'nom', 'fonction', 'societe', 'libelle_declare', 'isin', 'nature', 'famille', 'nombre_titres', 'capital_pct', 'valeur_declaree_eur', 'type_declaration', 'date_declaration'},
    'mouvements.csv': {'elu_id', 'prenom', 'nom', 'societe', 'libelle_declare', 'isin', 'ecart', 'date_declaration_avant', 'date_declaration_apres', 'titres_avant', 'titres_apres', 'valeur_avant_eur', 'valeur_apres_eur'},
}
TYPES_INTERETS = {'DI', 'DIA', 'DIM', 'DIAM'}
TYPES_PATRIMOINE = {'DSP', 'DSPM', 'DSPFM'}
TODO = '[à compléter]'


def scanner(page, nom, err):
    """Règles valables pour toute page HTML publiée : ressources, liens, traceurs, politique de sécurité."""
    # 1. Aucune ressource tierce chargée par le navigateur (l'IP du visiteur ne part chez personne).
    for tag in re.findall(r'<(?:link|script|img|iframe|source|video|audio|embed|object)\b[^>]*>', page, re.I):
        if re.search(r'(?:src|href)\s*=\s*["\']?(?:https?:)?//', tag, re.I):
            err.append(f'ressource externe chargée ({nom}) : {tag[:120]}')
    for u in re.findall(r'@import[^;]*|url\(\s*["\']?(?:https?:)?//[^)]*\)', page):
        err.append(f'ressource CSS externe ({nom}) : {u[:120]}')
    for d in sorted({h.lower() for h in re.findall(r'https?://([^/"\'\s<>`)]+)', page)}):
        if d not in LIENS_AUTORISES:
            err.append(f'lien vers un domaine non prévu ({nom}) : {d}')
    for t in TRACEURS:
        if re.search(t, page, re.I):
            err.append(f'traceur ou stockage navigateur interdit ({nom}) : {t}')
    # Politique de sécurité dans la page : aucune connexion sortante ni ressource tierce possible.
    csp = re.search(r'<meta http-equiv="Content-Security-Policy" content="([^"]+)"', page)
    if not csp or "default-src 'self'" not in csp.group(1) or "connect-src 'none'" not in csp.group(1):
        err.append(f'politique de sécurité (Content-Security-Policy) absente ou trop large ({nom})')
    if 'Données non publiées' in page:
        err.append(f'donnée occultée par la HATVP reprise sur le site ({nom})')


def controler(html, publication=False, css=None, db=None, pages=None, exports=None):
    """Renvoie la liste des manquements trouvés dans le site construit.

    html : l'accueil (index.html) ; db : les données complètes (donnees/registre.json) ;
    pages : {nom: html} des fiches statiques ; exports : {nom du CSV: liste des colonnes}.
    """
    err = []
    m = re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.S)
    if not m:
        return ['données embarquées introuvables']
    idx = json.loads(m.group(1).replace('<\\/', '</'))
    page = html[:m.start()] + html[m.end():]
    scanner(page, 'accueil', err)
    for u in re.findall(r'@import[^;]*|url\(\s*["\']?(?:https?:)?//[^)]*\)', ''.join((css or {}).values())):
        err.append(f'ressource CSS externe : {u[:120]}')
    for nom, p in (pages or {}).items():
        scanner(p, nom, err)
    for nom, cols in (exports or {}).items():
        extra = set(cols) - EXPORTS.get(nom, set())
        if extra:
            err.append(f'colonne non prévue dans l\'export {nom} : {sorted(extra)}')
    if db is None:
        return err + ['données complètes (donnees/registre.json) introuvables']

    # 2. Données embarquées : seulement les champs prévus, liens seulement vers la HATVP.
    def champs(obj, quoi, ref=CHAMPS):
        extra = set(obj) - ref[quoi]
        if extra:
            err.append(f'champ non prévu dans {quoi} : {sorted(extra)}')
    for e in idx['elus']:
        champs(e, 'elu', CHAMPS_ACCUEIL)
    for s in idx['socs']:
        champs(s, 'soc', CHAMPS_ACCUEIL)
    for mv in idx['mv']:
        champs(mv, 'mv', CHAMPS_ACCUEIL)
    if json.dumps(idx, ensure_ascii=False).count('Données non publiées'):
        err.append('donnée occultée par la HATVP reprise sur le site')
    for e in db['elus']:
        champs(e, 'elu')
        for h in e['h']:
            champs(h, 'holding')
            # Garde-fou loi 2013-907 / art. LO 135-2 : aucune déclaration de patrimoine hors gouvernement.
            if h['t'] in TYPES_PATRIMOINE and e['cat'] != 'gouvernement':
                err.append(f"déclaration de patrimoine publiée pour un élu non ministre : {e['id']}")
            if h['t'] not in TYPES_INTERETS | TYPES_PATRIMOINE:
                err.append(f"type de déclaration inconnu {h['t']} : {e['id']}")
            if h['f'] == 'patrimoine' and h['t'] not in TYPES_PATRIMOINE:
                err.append(f"famille patrimoine sur une déclaration d'intérêts : {e['id']}")
        if e.get('cj'):
            champs(e['cj'], 'conjoint')
            if e['cj']['t'] not in TYPES_INTERETS:
                err.append(f"activité du conjoint hors déclaration d'intérêts : {e['id']}")
            for c in e['cj']['l']:
                champs(c, 'conjoint_ligne')
        for d in e['decls']:
            champs(d, 'decl')
            if d['t'] in TYPES_PATRIMOINE and e['cat'] != 'gouvernement' and 'gouvernement' not in e['cats']:
                err.append(f"lien vers une déclaration de patrimoine d'un élu non ministre : {e['id']}")
        for u in [e['page']] + [d['u'] for d in e['decls']]:
            if u and not u.startswith('https://www.hatvp.fr/'):
                err.append(f"lien source hors HATVP : {u}")
        if e.get('g') and e['cat'] not in ('depute', 'senateur'):
            err.append(f"groupe politique publié pour un élu non parlementaire : {e['id']}")
        # Pas de date ni d'année de naissance dans les identifiants publics.
        if re.search(r'(?:19|20)\d\d', e['id']):
            err.append(f"année dans l'identifiant public : {e['id']}")
    for s in db['socs']:
        champs(s, 'soc')
        if s.get('siren') and not re.fullmatch(r'\d{9}', s['siren']):
            err.append(f"SIREN invalide pour {s['k']} : {s['siren']}")
        for h in s['holders']:
            champs(h, 'holder')
    for mv in db['mv']:
        champs(mv, 'mv')
        if mv['m'] not in MOUVEMENTS:
            err.append(f"type de mouvement inconnu : {mv['m']}")
    brut = json.dumps(db, ensure_ascii=False)
    if re.search(r'\d{4}-\d\d-\d\d', json.dumps([[e['id'], e['p'], e['n'], e['org'], e['mandat']] for e in db['elus']], ensure_ascii=False)):
        err.append('date complète dans les données d\'identité des élus (date de naissance ?)')
    if 'Données non publiées' in brut:
        err.append('donnée occultée par la HATVP reprise sur le site')


    # 3. Mentions obligatoires présentes dans la page.
    for texte, raison in [('licence ouverte Etalab', 'attribution Etalab (licence ouverte)'),
                          ('#mentions', 'lien vers les mentions légales'),
                          ('function mentions()', 'page des mentions légales'),
                          ('Responsable du traitement', 'information RGPD (art. 13-14)'),
                          ('droit de réponse', 'procédure de droit de réponse (LCEN art. 6 IV)'),
                          ('CNIL', 'droit de réclamation auprès de la CNIL')]:
        if texte not in page:
            err.append(f'mention manquante : {raison}')
    if not re.fullmatch(r'\d{4}-\d\d-\d\d', idx.get('built', '')):
        err.append('date de mise à jour des données absente (attribution Etalab)')
    legal = idx.get('legal') or {}
    if publication:
        for k, nom in [('editeur', 'nom de l\'éditeur (variable EDITEUR_NOM, ou EDITEUR_ANONYME)'), ('contact', 'adresse de contact (variable EDITEUR_CONTACT)'),
                       ('hebergeur', 'hébergeur')]:
            if not legal.get(k) and not (k == 'editeur' and legal.get('anonyme')):
                err.append(f'mentions légales incomplètes : {nom}')
        if legal.get('contact') and not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', legal['contact']):
            err.append('adresse de contact invalide')
    return err


def main():
    publication = '--publication' in sys.argv
    lire = lambda *p: open(os.path.join(PUB, *p), encoding='utf-8').read()
    html = lire('index.html')
    css, pages = {}, {}
    for base, _, fs in os.walk(PUB):
        for f in fs:
            rel = os.path.relpath(os.path.join(base, f), PUB)
            if f.endswith('.css'):
                css[rel] = lire(rel)
            elif f.endswith('.html') and rel != 'index.html':
                pages[rel] = lire(rel)
    reg = os.path.join(PUB, 'donnees', 'registre.json')
    db = json.loads(lire('donnees', 'registre.json')) if os.path.exists(reg) else None
    exports = {}
    for f in os.listdir(os.path.join(PUB, 'donnees')) if os.path.isdir(os.path.join(PUB, 'donnees')) else []:
        if f.endswith('.csv'):
            exports[f] = lire('donnees', f).lstrip('\ufeff').split('\n', 1)[0].strip().split(',')
    err = controler(html, publication, css, db, pages, exports)
    if err:
        print('Site non conforme, publication bloquée :')
        for e in err:
            print(' -', e)
        sys.exit(1)
    print('Contrôle de conformité OK' + (' (publication)' if publication else ''))


if __name__ == '__main__':
    main()
