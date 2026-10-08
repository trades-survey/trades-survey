#!/usr/bin/env python3
"""Télécharge la liste officielle des actions cotées sur Euronext (nom et ISIN), pour vérifier les ISIN du site.

Écrit data/raw/euronext.csv (colonnes name, isin). Facultatif : si Euronext ne répond pas ou si le fichier
reçu n'a pas la forme attendue, le script le signale et n'écrit rien ; le build garde alors ses ISIN sans
les marquer vérifiés.

  python3 -I scripts/fetch_euronext.py [data/raw/euronext.csv]
  python3 -I scripts/fetch_euronext.py --fichier export.csv   # lit un export téléchargé à la main
"""
import csv, io, os, re, sys, urllib.parse, urllib.request

URL = 'https://live.euronext.com/fr/pd_es/data/stocks/download?mics=dm_all_stock'
FORM = {'args[fe_type]': 'csv', 'args[fe_layout]': 'ver', 'args[fe_decimal_separator]': '.', 'args[fe_date_format]': 'd/m/Y'}
ISIN_RE = re.compile(r'[A-Z]{2}[A-Z0-9]{9}\d')
MINIMUM = 500  # une liste plus courte est un fichier tronqué ou une page d'erreur


def lire(texte):
    """Extrait (nom, isin) d'un export Euronext : en-tête repéré par sa colonne ISIN, séparateur deviné."""
    lignes = texte.lstrip('﻿').splitlines()
    i = next((k for k, l in enumerate(lignes) if re.search(r'(^|[;,\t"])\s*ISIN\s*("|[;,\t]|$)', l, re.I)), None)
    if i is None:
        return []
    sep = max(';,\t', key=lignes[i].count)
    rd = csv.reader(lignes[i:], delimiter=sep)
    tete = [c.strip().lower() for c in next(rd)]
    ci = tete.index('isin')
    cn = next((k for k, c in enumerate(tete) if c in ('name', 'nom', 'libellé', 'libelle')), 0)
    return [(r[cn].strip(), r[ci].strip()) for r in rd if len(r) > max(ci, cn) and ISIN_RE.fullmatch(r[ci].strip())]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if '--fichier' in sys.argv:
        src = args.pop(0)
        texte = open(src, encoding='utf-8-sig', errors='replace').read()
    else:
        try:
            req = urllib.request.Request(URL, data=urllib.parse.urlencode(FORM).encode(), headers={'User-Agent': 'Mozilla/5.0 (registre des élus actionnaires)'})
            with urllib.request.urlopen(req, timeout=90) as r:
                texte = r.read().decode('utf-8-sig', errors='replace')
        except Exception as e:
            print(f'::warning::Euronext injoignable ({e}) : ISIN non vérifiés cette semaine')
            return
    rows = lire(texte)
    if len(rows) < MINIMUM:
        print(f'::warning::liste Euronext inattendue ({len(rows)} lignes lues) : ISIN non vérifiés cette semaine')
        return
    out = args[0] if args else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'raw', 'euronext.csv')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['name', 'isin'])
        w.writerows(rows)
    print(f'{len(rows)} actions Euronext')


if __name__ == '__main__':
    main()
