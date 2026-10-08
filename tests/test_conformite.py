"""Vérifie que site/check_conformite.py bloque bien les cas non conformes.  python3 -I tests/test_conformite.py"""
import copy, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'site'))
from check_conformite import controler

TPL = open(os.path.join(ROOT, 'site', 'template.html'), encoding='utf-8').read()
DB = {'built': '2026-10-05', 'legal': {'editeur': 'Éditeur Test', 'contact': 'contact@exemple.fr', 'hebergeur': 'Hébergeur'},
      'elus': [{'id': 'jean-dupont', 'p': 'Jean', 'n': 'DUPONT', 'cat': 'depute', 'fn': 'Député', 'dep': '01', 'cats': ['depute'], 'org': 'Ain (01)',
                'mandat': 'Député', 'page': 'https://www.hatvp.fr/pages_nominatives/dupont-jean', 'masked': 0,
                'h': [{'s': 'AXA', 'n': 'AXA', 'f': 'interets', 'nl': 'participation', 'v': 1000, 'q': '10', 'c': None, 'd': '2025-01-01', 't': 'DI'}],
                'decls': [{'t': 'DI', 'd': '2025-01-01', 'm': False, 'u': 'https://www.hatvp.fr/livraison/dossiers/x.pdf'}]}],
      'socs': [{'k': 'AXA', 'id': 'axa', 'name': 'AXA', 'isin': 'FR0000120628', 'siren': '572093920', 'holders': [{'e': 'jean-dupont', 'v': 1000, 'q': '10', 'd': '2025-01-01', 'f': 'interets'}]}],
      'mv': []}

def page(db=DB, tpl=TPL):
    return tpl.replace('__DATA__', json.dumps(db, ensure_ascii=False))

def cas(nom, html, attendu, publication=False):
    err = controler(html, publication)
    ok = any(attendu in e for e in err) if attendu else not err
    print(('ok   ' if ok else 'ÉCHEC'), nom, '' if ok else err)
    return ok

def muter(f):
    db = copy.deepcopy(DB); f(db); return page(db)

R = [
    cas('page conforme', page(), None, publication=True),
    cas('Google Fonts', page(tpl=TPL.replace('<style>', '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=X">\n<style>', 1)), 'ressource externe'),
    cas('@import CSS', page(tpl=TPL.replace('<style>', '<style>@import url(https://cdn.example.com/a.css);', 1)), 'ressource CSS externe'),
    cas('script de mesure', page(tpl=TPL.replace('</style>', '</style><script src="https://www.googletagmanager.com/gtag/js"></script>', 1)), 'ressource externe'),
    cas('localStorage', page(tpl=TPL.replace('route();\n</script>', 'route();localStorage.x=1;\n</script>')), 'localStorage'),
    cas('DSP d\'un député', muter(lambda d: d['elus'][0]['h'][0].update(t='DSP', f='patrimoine')), 'patrimoine publiée'),
    cas('date de naissance', muter(lambda d: d['elus'][0].update(dn='1970-01-01')), 'champ non prévu'),
    cas('année dans l\'identifiant', muter(lambda d: d['elus'][0].update(id='jean-dupont-1970')), "année dans l'identifiant"),
    cas('commentaire libre', muter(lambda d: d['elus'][0]['h'][0].update(com='x')), 'champ non prévu'),
    cas('donnée occultée', muter(lambda d: d['elus'][0]['h'][0].update(n='[Données non publiées]')), 'occultée'),
    cas('SIREN invalide', muter(lambda d: d['socs'][0].update(siren='https://exemple.com')), 'SIREN invalide'),
    cas('lien source hors HATVP', muter(lambda d: d['elus'][0].update(page='https://exemple.com/x')), 'hors HATVP'),
    cas('éditeur manquant à la publication', muter(lambda d: d['legal'].update(editeur='')), 'éditeur', publication=True),
    cas('éditeur anonyme à la publication', muter(lambda d: d['legal'].update(editeur='', anonyme=True)), None, publication=True),
    cas('lien PayPal', muter(lambda d: d['legal'].update(soutenir='https://www.paypal.com/donate/?hosted_button_id=ABC123')), None, publication=True),
    cas('lien de soutien hors PayPal', muter(lambda d: d['legal'].update(soutenir='https://exemple.com/don')), 'lien de soutien'),
    cas('lien de soutien javascript', muter(lambda d: d['legal'].update(soutenir='javascript:alert(1)')), 'lien de soutien'),
    cas('politique de sécurité retirée', page(tpl=TPL.replace('http-equiv="Content-Security-Policy"', 'name="x"')), 'Content-Security-Policy'),
    cas('page mentions supprimée', page(tpl=TPL.replace('Responsable du traitement', 'Responsable')), 'RGPD'),
]
sys.exit(0 if all(R) else 1)
