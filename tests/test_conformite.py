"""Vérifie que site/check_conformite.py bloque bien les cas non conformes.  python3 -I tests/test_conformite.py"""
import copy, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'site'))
from check_conformite import controler

TPL = open(os.path.join(ROOT, 'site', 'template.html'), encoding='utf-8').read()
DB = {'built': '2026-10-05', 'legal': {'editeur': 'Éditeur Test', 'contact': 'contact@exemple.fr', 'hebergeur': 'Hébergeur'},
      'elus': [{'id': 'jean-dupont', 'p': 'Jean', 'n': 'DUPONT', 'cat': 'depute', 'fn': 'Député', 'dep': '01', 'cats': ['depute'], 'org': 'Ain (01)',
                'mandat': 'Député', 'page': 'https://www.hatvp.fr/pages_nominatives/dupont-jean', 'masked': 0,
                'cj': {'d': '2025-01-01', 't': 'DI', 'l': [{'a': 'Infirmière', 'e': 'Centre hospitalier'}]},
                'h': [{'s': 'AXA', 'n': 'AXA', 'f': 'interets', 'nl': 'participation', 'v': 1000, 'q': '10', 'c': None, 'd': '2025-01-01', 't': 'DI'}],
                'decls': [{'t': 'DI', 'd': '2025-01-01', 'm': False, 'u': 'https://www.hatvp.fr/livraison/dossiers/x.pdf'}]}],
      'socs': [{'k': 'AXA', 'id': 'axa', 'name': 'AXA', 'isin': 'FR0000120628', 'siren': '572093920', 'holders': [{'e': 'jean-dupont', 'v': 1000, 'q': '10', 'd': '2025-01-01', 'f': 'interets'}]}],
      'mv': []}

def accueil(db):
    """Données embarquées dans l'accueil, comme site/build.py les réduit."""
    return {'built': db['built'], 'legal': db['legal'],
            'elus': [{k: e[k] for k in ('id', 'p', 'n', 'cat', 'fn', 'dep', 'org')} | {'g': e.get('g', ''), 'nh': len(e['h']), 'v': 0} for e in db['elus']],
            'socs': [{k: s[k] for k in ('k', 'id', 'name', 'isin', 'siren')} | {'nat': s.get('nat', ''), 'nh': 1, 'nm': 0} for s in db['socs']], 'mv': db['mv']}

def page(db=DB, tpl=TPL, idx=None):
    return tpl.replace('__DATA__', json.dumps(idx or accueil(db), ensure_ascii=False))

FICHE = TPL[:TPL.index('<script id="data"')]
EXPORTS = {'elus.csv': ['id', 'prenom', 'nom', 'groupe'], 'participations.csv': ['elu_id', 'societe', 'isin']}

def cas(nom, attendu, db=DB, tpl=TPL, publication=False, idx=None, pages=None, exports=EXPORTS):
    err = controler(page(db or DB, tpl, idx), publication, None, db, pages or {'elus/jean-dupont.html': FICHE}, exports)
    ok = any(attendu in e for e in err) if attendu else not err
    print(('ok   ' if ok else 'ÉCHEC'), nom, '' if ok else err)
    return ok

def muter(f):
    db = copy.deepcopy(DB); f(db); return db

R = [
    cas('page conforme', None, publication=True),
    cas('Google Fonts', 'ressource externe', tpl=TPL.replace('<style>', '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=X">\n<style>', 1)),
    cas('@import CSS', 'ressource CSS externe', tpl=TPL.replace('<style>', '<style>@import url(https://cdn.example.com/a.css);', 1)),
    cas('script de mesure', 'ressource externe', tpl=TPL.replace('</style>', '</style><script src="https://www.googletagmanager.com/gtag/js"></script>', 1)),
    cas('localStorage', 'localStorage', tpl=TPL.replace('route();\n</script>', 'route();localStorage.x=1;\n</script>')),
    cas('DSP d\'un député', 'patrimoine publiée', db=muter(lambda d: d['elus'][0]['h'][0].update(t='DSP', f='patrimoine'))),
    cas('date de naissance', 'champ non prévu', db=muter(lambda d: d['elus'][0].update(dn='1970-01-01'))),
    cas('année dans l\'identifiant', "année dans l'identifiant", db=muter(lambda d: d['elus'][0].update(id='jean-dupont-1970'))),
    cas('commentaire libre', 'champ non prévu', db=muter(lambda d: d['elus'][0]['h'][0].update(com='x'))),
    cas('nom du conjoint', 'champ non prévu', db=muter(lambda d: d['elus'][0]['cj']['l'][0].update(nom='Martin'))),
    cas('commentaire du conjoint', 'champ non prévu', db=muter(lambda d: d['elus'][0]['cj']['l'][0].update(com='x'))),
    cas('conjoint tiré du patrimoine', "hors déclaration d'intérêts", db=muter(lambda d: d['elus'][0]['cj'].update(t='DSP'))),
    cas('employeur du conjoint occulté', 'occultée', db=muter(lambda d: d['elus'][0]['cj']['l'][0].update(e='[Données non publiées]'))),
    cas('donnée occultée', 'occultée', db=muter(lambda d: d['elus'][0]['h'][0].update(n='[Données non publiées]'))),
    cas('SIREN invalide', 'SIREN invalide', db=muter(lambda d: d['socs'][0].update(siren='https://exemple.com'))),
    cas('lien source hors HATVP', 'hors HATVP', db=muter(lambda d: d['elus'][0].update(page='https://exemple.com/x'))),
    cas('éditeur manquant à la publication', 'éditeur', db=muter(lambda d: d['legal'].update(editeur='')), publication=True),
    cas('éditeur anonyme à la publication', None, db=muter(lambda d: d['legal'].update(editeur='', anonyme=True)), publication=True),
    cas('lien PayPal', None, db=muter(lambda d: d['legal'].update(soutenir='https://www.paypal.com/donate/?hosted_button_id=ABC123')), publication=True),
    cas('lien de soutien hors PayPal', 'lien de soutien', db=muter(lambda d: d['legal'].update(soutenir='https://exemple.com/don'))),
    cas('lien de soutien javascript', 'lien de soutien', db=muter(lambda d: d['legal'].update(soutenir='javascript:alert(1)'))),
    cas('politique de sécurité retirée', 'Content-Security-Policy', tpl=TPL.replace('http-equiv="Content-Security-Policy"', 'name="x"')),
    cas('groupe d\'un élu local', "non parlementaire", db=muter(lambda d: d['elus'][0].update(cat='elu_local', g='LR', gl='Les Républicains'))),
    cas('groupe d\'un député', None, db=muter(lambda d: d['elus'][0].update(g='SOC', gl='Socialistes et apparentés'))),
    cas('variation de valeur', None, db=muter(lambda d: d['mv'].append({'e': 'jean-dupont', 's': 'AXA', 'n': 'AXA', 'f': 'interets', 'm': 'valeur', 'da': '2024-01-01', 'dp': '2025-01-01', 'qa': 10, 'qp': 10, 'va': 900, 'vp': 1000}))),
    cas('mouvement inconnu', 'type de mouvement', db=muter(lambda d: d['mv'].append({'e': 'jean-dupont', 's': 'AXA', 'n': 'AXA', 'f': 'interets', 'm': 'achat', 'da': '', 'dp': '2025-01-01', 'qa': None, 'qp': 10, 'va': None, 'vp': 1000}))),
    cas('date de naissance dans l\'accueil', 'champ non prévu', idx=accueil(DB) | {'elus': [accueil(DB)['elus'][0] | {'dn': '1970-01-01'}]}),
    cas('date de naissance dans un export', "colonne non prévue", exports={'elus.csv': ['id', 'nom', 'date_naissance']}),
    cas('fiche avec script de mesure', 'ressource externe', pages={'elus/x.html': FICHE.replace('</style>', '</style><script src="https://www.googletagmanager.com/gtag/js"></script>', 1)}),
    cas('fiche sans politique de sécurité', 'Content-Security-Policy', pages={'elus/x.html': FICHE.replace('http-equiv="Content-Security-Policy"', 'name="x"')}),
    cas('fiche avec donnée occultée', 'occultée', pages={'elus/x.html': FICHE + '[Données non publiées]'}),
    cas('fiche avec le bouton Soutenir', None, db=muter(lambda d: d['legal'].update(soutenir='https://www.paypal.com/donate/?hosted_button_id=ABC123')),
        pages={'elus/x.html': FICHE.replace('</nav>', '<a href="https://www.paypal.com/donate/?hosted_button_id=ABC123">Soutenir</a></nav>')}),
    cas('fiche avec un autre lien PayPal', 'domaine non prévu', db=muter(lambda d: d['legal'].update(soutenir='https://www.paypal.com/donate/?hosted_button_id=ABC123')),
        pages={'elus/x.html': FICHE.replace('</nav>', '<a href="https://www.paypal.com/autre">x</a></nav>')}),
    cas('données complètes absentes', 'introuvables', db=None),
    cas('page mentions supprimée', 'RGPD', tpl=TPL.replace('Responsable du traitement', 'Responsable')),
]
sys.exit(0 if all(R) else 1)
