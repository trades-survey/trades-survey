#!/usr/bin/env python3
"""Télécharge le groupe politique des députés et des sénateurs en exercice (licence ouverte).

Sources : open data de l'Assemblée nationale (députés actifs et organes) et du Sénat
(liste générale des sénateurs). Écrit data/raw/groupes.csv, qui n'est pas archivé :
la date de naissance n'y sert qu'au rapprochement avec les déclarations HATVP.

  python3 -I scripts/fetch_groupes.py [data/raw/groupes.csv]
"""
import csv, io, json, os, sys, urllib.request, zipfile

AN = 'https://data.assemblee-nationale.fr/static/openData/repository/17/amo/deputes_actifs_mandats_actifs_organes/AMO10_deputes_actifs_mandats_actifs_organes.json.zip'
SENAT = 'https://data.senat.fr/data/senateurs/ODSEN_GENERAL.csv'
# Libellés des groupes du Sénat, que le fichier ne donne qu'en sigle (les autres sigles restent tels quels)
SENAT_LIB = {'SER': 'Socialiste, Écologiste et Républicain', 'CRCE-K': 'Communiste Républicain Citoyen et Écologiste – Kanaky',
             'RDSE': 'Rassemblement Démocratique et Social Européen', 'RDPI': 'Rassemblement des démocrates, progressistes et indépendants',
             'GEST': 'Écologiste – Solidarité et Territoires', 'NI': 'Non inscrits'}


def get(url):
    with urllib.request.urlopen(url, timeout=120) as r:
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


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'raw', 'groupes.csv')
    rows = list(deputes()) + list(senateurs())
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['chambre', 'prenom', 'nom', 'date_naissance', 'sigle', 'groupe'])
        w.writeheader()
        w.writerows(rows)
    print(f"{sum(r['chambre'] == 'depute' for r in rows)} députés et {sum(r['chambre'] == 'senateur' for r in rows)} sénateurs avec un groupe")


if __name__ == '__main__':
    main()
