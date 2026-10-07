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
LIENS_AUTORISES = {'www.hatvp.fr', 'www.etalab.gouv.fr', 'www.cnil.fr'}
# Mouchards, stockage côté navigateur et appels réseau : interdits (pas de bandeau cookies, pas de consentement à recueillir).
TRACEURS = [r'document\.cookie', r'localStorage', r'sessionStorage', r'indexedDB', r'sendBeacon', r'\bfetch\(',
            r'XMLHttpRequest', r'WebSocket', r'<iframe', r'<img[^>]+src=["\']https?:', r'googletagmanager', r'google-analytics',
            r'gtag\(', r'matomo', r'_paq', r'facebook\.net', r'hotjar', r'plausible', r'doubleclick']
# Seuls champs que le site a le droit d'embarquer, par objet (minimisation des données).
CHAMPS = {
    'elu': {'id', 'p', 'n', 'cat', 'fn', 'cats', 'org', 'mandat', 'page', 'masked', 'h', 'decls'},
    'holding': {'s', 'n', 'f', 'nl', 'v', 'q', 'c', 'd', 't'},
    'decl': {'t', 'd', 'm', 'u'},
    'soc': {'k', 'id', 'name', 'isin', 'holders'},
    'holder': {'e', 'v', 'q', 'd', 'f'},
    'mv': {'e', 's', 'n', 'f', 'm', 'da', 'dp', 'qa', 'qp', 'va', 'vp'},
}
TYPES_INTERETS = {'DI', 'DIA', 'DIM', 'DIAM'}
TYPES_PATRIMOINE = {'DSP', 'DSPM', 'DSPFM'}
TODO = '[à compléter]'


def controler(html, publication=False, css=None):
    """Renvoie la liste des manquements trouvés dans la page construite."""
    err = []
    m = re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.S)
    if not m:
        return ['données embarquées introuvables']
    db = json.loads(m.group(1).replace('<\\/', '</'))
    page = html[:m.start()] + html[m.end():]

    # 1. Aucune ressource tierce chargée par le navigateur (l'IP du visiteur ne part chez personne).
    for tag in re.findall(r'<(?:link|script|img|iframe|source|video|audio|embed|object)\b[^>]*>', page, re.I):
        if re.search(r'(?:src|href)\s*=\s*["\']?(?:https?:)?//', tag, re.I):
            err.append(f'ressource externe chargée : {tag[:120]}')
    for u in re.findall(r'@import[^;]*|url\(\s*["\']?(?:https?:)?//[^)]*\)', page + ''.join((css or {}).values())):
        err.append(f'ressource CSS externe : {u[:120]}')
    for d in sorted({h.lower() for h in re.findall(r'https?://([^/"\'\s<>`)]+)', page)}):
        if d not in LIENS_AUTORISES:
            err.append(f'lien vers un domaine non prévu : {d}')
    for t in TRACEURS:
        if re.search(t, page, re.I):
            err.append(f'traceur ou stockage navigateur interdit : {t}')

    # 2. Données embarquées : seulement les champs prévus, liens seulement vers la HATVP.
    def champs(obj, quoi):
        extra = set(obj) - CHAMPS[quoi]
        if extra:
            err.append(f'champ non prévu dans {quoi} : {sorted(extra)}')
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
        for d in e['decls']:
            champs(d, 'decl')
            if d['t'] in TYPES_PATRIMOINE and e['cat'] != 'gouvernement' and 'gouvernement' not in e['cats']:
                err.append(f"lien vers une déclaration de patrimoine d'un élu non ministre : {e['id']}")
        for u in [e['page']] + [d['u'] for d in e['decls']]:
            if u and not u.startswith('https://www.hatvp.fr/'):
                err.append(f"lien source hors HATVP : {u}")
        # Pas de date ni d'année de naissance dans les identifiants publics.
        if re.search(r'(?:19|20)\d\d', e['id']):
            err.append(f"année dans l'identifiant public : {e['id']}")
    for s in db['socs']:
        champs(s, 'soc')
        for h in s['holders']:
            champs(h, 'holder')
    for mv in db['mv']:
        champs(mv, 'mv')
    brut = m.group(1)
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
    if not re.fullmatch(r'\d{4}-\d\d-\d\d', db.get('built', '')):
        err.append('date de mise à jour des données absente (attribution Etalab)')
    legal = db.get('legal') or {}
    if publication:
        for k, nom in [('editeur', 'nom de l\'éditeur (variable EDITEUR_NOM)'), ('contact', 'adresse de contact (variable EDITEUR_CONTACT)'),
                       ('hebergeur', 'hébergeur')]:
            if not legal.get(k):
                err.append(f'mentions légales incomplètes : {nom}')
        if legal.get('contact') and not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', legal['contact']):
            err.append('adresse de contact invalide')
    return err


def main():
    publication = '--publication' in sys.argv
    html = open(os.path.join(PUB, 'index.html'), encoding='utf-8').read()
    css = {}
    for base, _, fs in os.walk(PUB):
        for f in fs:
            if f.endswith('.css'):
                css[f] = open(os.path.join(base, f), encoding='utf-8').read()
    err = controler(html, publication, css)
    if not os.path.exists(os.path.join(PUB, '.htaccess')):
        err.append('public/.htaccess absent (HTTPS obligatoire)')
    if err:
        print('Site non conforme, publication bloquée :')
        for e in err:
            print(' -', e)
        sys.exit(1)
    print('Contrôle de conformité OK' + (' (publication)' if publication else ''))


if __name__ == '__main__':
    main()
