#!/usr/bin/env python3
"""Rapproche les sociétés cotées du site du répertoire des représentants d'intérêts (open data HATVP, licence ouverte).

Source : https://www.hatvp.fr/agora/opendata/agora_repertoire_opendata.json (une entrée par organisation inscrite,
avec ses activités de lobbying déclarées chaque année). Écrit data/raw/lobbying.json, qui n'est pas archivé :
{clé de la société: [organisations rattachées]}.

Une organisation est rattachée à une société cotée quand son SIREN est celui de la société, quand son nom est
celui de la société (formes juridiques retirées), ou quand son nom commence par celui de la société suivi d'un
autre mot (« VINCI AUTOROUTES ») : filiale probable. Ces deux derniers rapprochements ne valent que pour les
organisations inscrites comme entreprises ou sociétés : filiale probable, signalée comme telle et vérifiable par son nom et sa fiche.
Les dirigeants et collaborateurs inscrits au répertoire ne sont pas lus.

  python3 -I scripts/fetch_lobbying.py [data/raw/lobbying.json] [--fichier agora.json]
"""
import json, os, sys, urllib.request
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'site'))
from societes import ISIN, SIREN, ALIAS, SUFFIX, norm

URL = 'https://www.hatvp.fr/agora/opendata/agora_repertoire_opendata.json'
# préfixes trop courts ou trop communs pour désigner à coup sûr une filiale
PREFIXE_MIN = 5
ANNEES = 3  # activités comptées sur les trois derniers exercices publiés


def cible(resp):
    t = ' '.join(resp).lower()
    return ('parlement' if 'député' in t or 'sénateur' in t else None), ('gouvernement' if 'gouvernement' in t or 'cabinet ministériel' in t else None)


def resume(o):
    ex = [e['publicationCourante'] for e in o.get('exercices', []) if e.get('publicationCourante', {}).get('publicationDate')]
    ex.sort(key=lambda e: e['dateDebut'][-4:] + e['dateDebut'][3:5], reverse=True)
    n = np = ng = 0
    objets = []
    for e in ex[:ANNEES]:
        for a in e.get('activites', []):
            a = a.get('publicationCourante', {})
            n += 1
            par = gou = False
            for act in a.get('actionsRepresentationInteret', []):
                p, g = cible(act.get('reponsablesPublics', []))
                par, gou = par or bool(p), gou or bool(g)
            np += par
            ng += gou
            if par or gou:
                objets.append({'o': a.get('objet', '').strip(), 'd': (a.get('publicationDate') or '')[:10], 'dom': a.get('domainesIntervention', []),
                               'c': [x for x, y in (('Parlement', par), ('Gouvernement', gou)) if y]})
    dern = ex[0] if ex else {}
    return {'nom': o['denomination'], 'siren': o.get('identifiantNational', '') if o.get('typeIdentifiantNational') == 'SIREN' else '',
            'id': o.get('identifiantNational', ''), 'depense': dern.get('montantDepense', ''),
            'exercice': (dern.get('dateDebut', '')[-4:] if dern else ''), 'n': n, 'np': np, 'ng': ng,
            'objets': sorted(objets, key=lambda x: x['d'][6:10] + x['d'][3:5] + x['d'][:2], reverse=True)[:6]}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if '--fichier' in sys.argv:
        data = json.load(open(args.pop(0), encoding='utf-8'))
    else:
        with urllib.request.urlopen(urllib.request.Request(URL, headers={'User-Agent': 'registre-des-elus-actionnaires'}), timeout=300) as r:
            data = json.load(r)
    out = args[0] if args else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'raw', 'lobbying.json')
    par_siren = {v: k for k, v in SIREN.items()}
    noms = {}
    for k in ISIN:
        for n in [k] + [a for a, v in ALIAS.items() if v == k]:
            noms.setdefault(n, k)
    res = {}
    for o in data['publications']:
        d = norm(o.get('denomination', ''))
        base = SUFFIX.sub('', d)
        k, lien = None, ''
        if o.get('typeIdentifiantNational') == 'SIREN' and o.get('identifiantNational') in par_siren:
            k, lien = par_siren[o['identifiantNational']], 'siren'
        elif (o.get('categorieOrganisation') or {}).get('categorie') not in ('ENTREPRISE', 'SOCIETE'):
            continue  # rapprochement par le nom réservé aux entreprises (une association « Carrefour national… » n'est pas Carrefour)
        elif base in noms:
            k, lien = noms[base], 'nom'
        else:
            for n, kk in noms.items():
                if len(n) >= PREFIXE_MIN and d.startswith(n + ' '):
                    k, lien = kk, 'filiale'
                    break
        if k:
            res.setdefault(k, []).append({**resume(o), 'lien': lien})
    for L in res.values():
        L.sort(key=lambda x: (x['lien'] == 'filiale', -x['n']))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(res, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print(f"{len(res)} sociétés cotées rattachées à {sum(map(len, res.values()))} inscrits du répertoire des représentants d'intérêts")


if __name__ == '__main__':
    main()
