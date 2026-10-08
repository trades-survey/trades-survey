#!/usr/bin/env python3
"""Télécharge le groupe politique des députés et des sénateurs en exercice (licence ouverte).

Sources : open data de l'Assemblée nationale (députés actifs et organes) et du Sénat
(liste générale des sénateurs). Écrit data/raw/groupes.csv, qui n'est pas archivé :
la date de naissance n'y sert qu'au rapprochement avec les déclarations HATVP.

Chaque source est facultative. data.senat.fr ne répond pas depuis les serveurs de GitHub Actions :
à défaut, les groupes du Sénat viennent de data/ref/senateurs_groupes.csv (nom, prénom et groupe,
sans date de naissance), instantané à rafraîchir après un renouvellement en lançant ce script en local.

  python3 -I scripts/fetch_groupes.py [data/raw/groupes.csv] [--instantane]   # --instantane : rafraîchit data/ref
"""
import csv, io, json, os, sys, urllib.request, zipfile

AN = 'https://data.assemblee-nationale.fr/static/openData/repository/17/amo/deputes_actifs_mandats_actifs_organes/AMO10_deputes_actifs_mandats_actifs_organes.json.zip'
SENAT = 'https://data.senat.fr/data/senateurs/ODSEN_GENERAL.csv'
# Libellés des groupes du Sénat, que le fichier ne donne qu'en sigle (les autres sigles restent tels quels)
SENAT_LIB = {'SER': 'Socialiste, Écologiste et Républicain', 'CRCE-K': 'Communiste Républicain Citoyen et Écologiste – Kanaky',
             'RDSE': 'Rassemblement Démocratique et Social Européen', 'RDPI': 'Rassemblement des démocrates, progressistes et indépendants',
             'GEST': 'Écologiste – Solidarité et Territoires', 'NI': 'Non inscrits'}


REF = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'ref', 'senateurs_groupes.csv')


def get(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def deputes():
    z = zipfile.ZipFile(io.BytesIO(get(AN)))
    gp = {}
    for n in z.namelist():
        if '/organe/' in n:
            o = json.loads(z.read(n))['organe']
            if o['codeType'] == 'GP':
                gp[o['uid']] = (o['libelleAbrev'], o['libelle'])
    for n in z.namelist():
        if '/acteur/' not in n:
            continue
        a = json.loads(z.read(n))['acteur']
        ms = a['mandats']['mandat']
        ms = ms if isinstance(ms, list) else [ms]
        g = next((gp[m['organes']['organeRef']] for m in ms if m['typeOrgane'] == 'GP' and not m.get('dateFin') and m['organes']['organeRef'] in gp), None)
        if g:
            i = a['etatCivil']
            yield {'chambre': 'depute', 'prenom': i['ident']['prenom'], 'nom': i['ident']['nom'],
                   'date_naissance': i['infoNaissance']['dateNais'][:10], 'sigle': g[0], 'groupe': g[1]}


def senateurs():
    txt = get(SENAT).decode('latin-1')
    lignes = [l for l in txt.splitlines() if not l.startswith('%')]
    for r in csv.DictReader(lignes):
        if r['État'] == 'ACTIF' and r['Groupe politique']:
            s = r['Groupe politique']
            yield {'chambre': 'senateur', 'prenom': r['Prénom usuel'], 'nom': r['Nom usuel'],
                   'date_naissance': r['Date naissance'][:10], 'sigle': s, 'groupe': SENAT_LIB.get(s, s)}


def senateurs_ref():
    with open(REF, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            yield {'chambre': 'senateur', 'prenom': r['prenom'], 'nom': r['nom'], 'date_naissance': '', 'sigle': r['sigle'], 'groupe': r['groupe']}


def charger(nom, source, secours=None):
    try:
        return list(source())
    except Exception as e:
        print(f'::warning::{nom} : source indisponible ({e})' + (', instantané du dépôt utilisé' if secours else ''))
        return list(secours()) if secours else []


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    out = args[0] if args else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'raw', 'groupes.csv')
    sen = charger('Sénat', senateurs, senateurs_ref)
    if '--instantane' in sys.argv and sen and sen[0]['date_naissance']:
        with open(REF, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['prenom', 'nom', 'sigle', 'groupe'])
            w.writerows([r['prenom'], r['nom'], r['sigle'], r['groupe']] for r in sorted(sen, key=lambda r: (r['nom'], r['prenom'])))
    rows = charger('Assemblée nationale', deputes) + sen
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['chambre', 'prenom', 'nom', 'date_naissance', 'sigle', 'groupe'])
        w.writeheader()
        w.writerows(rows)
    print(f"{sum(r['chambre'] == 'depute' for r in rows)} députés et {sum(r['chambre'] == 'senateur' for r in rows)} sénateurs avec un groupe")


if __name__ == '__main__':
    main()
