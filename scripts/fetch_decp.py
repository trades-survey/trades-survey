#!/usr/bin/env python3
"""Marchés publics attribués aux sociétés cotées du site dont le SIREN est connu (données essentielles de la commande
publique, data.economie.gouv.fr, licence ouverte).

Source : jeu « decp-2022-marches-valides » (marchés notifiés et publiés au format réglementaire de 2022). Pour chaque
société, le titulaire est reconnu par son SIRET, qui commence par le SIREN de la société (titulaire principal ou
cotitulaire). Les filiales qui ont leur propre SIREN ne sont pas comptées.

Écrit data/raw/decp.json, qui n'est pas archivé : {clé de la société: {n, total, d0, d1, acheteurs: [...], dep: {département: [n, total]}}}.
Le nom des principaux acheteurs vient de l'annuaire des entreprises (recherche-entreprises.api.gouv.fr).

  python3 -I scripts/fetch_decp.py [data/raw/decp.json]
"""
import json, os, re, sys, time, urllib.parse, urllib.request
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'site'))
from societes import SIREN

API = 'https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/decp-2022-marches-valides/records'
ANNUAIRE = 'https://recherche-entreprises.api.gouv.fr/search?q={}&page=1&per_page=1'


def get(url, essais=3):
    for i in range(essais):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'registre-des-elus-actionnaires'}), timeout=120) as r:
                return json.load(r)
        except Exception:
            if i == essais - 1:
                raise
            time.sleep(3 * (i + 1))


def requete(**p):
    return get(API + '?' + urllib.parse.urlencode(p))['results']


def departement(code):
    """Code du lieu d'exécution (département ou code postal) → département."""
    c = (code or '').strip().upper()
    if re.fullmatch(r'\d{5}', c):
        return ('2A' if int(c) < 20200 else '2B') if c.startswith('20') else (c[:3] if c.startswith('97') else c[:2])
    if re.fullmatch(r'0?\d{1,2}|2[AB]|97\d', c):
        return c.zfill(2) if c.isdigit() and len(c) < 3 else c
    return ''


def nom_acheteur(siret, cache={}):
    s = (siret or '')[:9]
    if not re.fullmatch(r'\d{9}', s):
        return ''
    if s not in cache:
        try:
            r = get(ANNUAIRE.format(s))['results']
            cache[s] = r[0]['nom_complet'] if r else ''
        except Exception:
            cache[s] = ''
        time.sleep(0.2)
    return cache[s]


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'raw', 'decp.json')
    res = {}
    for k, siren in sorted(SIREN.items()):
        where = ' or '.join(f'startswith(titulaire_id_{i}, "{siren}")' for i in (1, 2, 3))
        try:
            tot = requete(select='count(*) as n, sum(montant) as total, min(datenotification) as d0, max(datenotification) as d1', where=where)[0]
            if not tot['n']:
                continue
            ach = requete(select='acheteur_id, count(*) as n, sum(montant) as total', where=where, group_by='acheteur_id', order_by='total desc', limit=5)
            dep = requete(select='lieuexecution_code, count(*) as n, sum(montant) as total', where=where, group_by='lieuexecution_code', limit=1000)
        except Exception as e:
            print(f'::warning::commande publique indisponible pour {k} ({e})')
            continue
        deps = {}
        for r in dep:
            d = departement(r['lieuexecution_code'])
            if d:
                n, t = deps.get(d, [0, 0])
                deps[d] = [n + r['n'], round(t + (r['total'] or 0))]
        res[k] = {'n': tot['n'], 'total': round(tot['total'] or 0), 'd0': (tot['d0'] or '')[:10], 'd1': (tot['d1'] or '')[:10], 'siren': siren,
                  'acheteurs': [{'nom': nom_acheteur(r['acheteur_id']) or r['acheteur_id'], 'n': r['n'], 'total': round(r['total'] or 0)} for r in ach],
                  'dep': deps}
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(res, open(out, 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'{len(res)} sociétés cotées titulaires de marchés publics')


if __name__ == '__main__':
    main()
