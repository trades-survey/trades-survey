#!/usr/bin/env python3
"""Amendements et scrutins de l'Assemblée nationale qui citent une société cotée du site (open data, licence ouverte).

Sources (XVIIe législature) : amendements, scrutins et dossiers législatifs de data.assemblee-nationale.fr.
Écrit data/raw/assemblee.json, qui n'est pas archivé :
  - amendements : amendements déposés par un député dont le dispositif ou l'exposé sommaire cite une société
    cotée par son nom (liste des noms et exclusions plus bas), avec auteur, cosignataires, sort et texte visé ;
  - scrutins : scrutins publics portant sur ces amendements, ou dont l'intitulé cite une société cotée
    (« proposition de loi visant à la nationalisation d'ArcelorMittal France »), avec la position nominative de chaque député.

Le rapprochement est fait sur le nom exact de la société (mot entier, sans tenir compte des accents ni de la
casse). Les noms qui sont aussi des mots courants ou des noms de lieu (Orange, Carrefour, Safran…) ne sont
cherchés que sous une forme non ambiguë (« groupe Orange »).

  python3 -I scripts/fetch_assemblee.py [data/raw/assemblee.json] [--dossier data/raw]   # --dossier : zips déjà téléchargés
"""
import html, json, os, re, sys, time, urllib.error, urllib.request, zipfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'site'))
from societes import motifs, norm

BASE = 'https://data.assemblee-nationale.fr/static/openData/repository/17/loi/'
FICHIERS = {'amendements': BASE + 'amendements_div_legis/Amendements.json.zip', 'scrutins': BASE + 'scrutins/Scrutins.json.zip',
            'dossiers': BASE + 'dossiers_legislatifs/Dossiers_Legislatifs.json.zip'}
def ouvrir(nom, dossier):
    if dossier:
        return zipfile.ZipFile(os.path.join(dossier, os.path.basename(FICHIERS[nom])))
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'raw', os.path.basename(FICHIERS[nom]))
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    # Le serveur de l'Assemblée répond parfois 503 quelques minutes : on réessaie avant d'abandonner pour la semaine.
    for essai in range(5):
        try:
            with urllib.request.urlopen(FICHIERS[nom], timeout=600) as r, open(tmp, 'wb') as f:
                while b := r.read(1 << 20):
                    f.write(b)
            return zipfile.ZipFile(tmp)
        except (urllib.error.URLError, OSError, zipfile.BadZipFile) as e:
            if essai == 4:
                raise
            print(f'{nom} : {e}, nouvel essai dans {60 * (essai + 1)} s', file=sys.stderr)
            time.sleep(60 * (essai + 1))


def ref(x):
    return x.get('#text') if isinstance(x, dict) else x


def liste(x):
    return x if isinstance(x, list) else ([] if x is None else [x])


def texte_brut(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', s or ''))).strip()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    dossier = args.pop(args.index(sys.argv[sys.argv.index('--dossier') + 1])) if '--dossier' in sys.argv else None
    out = args[0] if args else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'raw', 'assemblee.json')
    rx, noms = motifs()
    titres = {}
    zd = ouvrir('dossiers', dossier)
    for n in zd.namelist():
        if '/document/' in n:
            d = json.loads(zd.read(n))['document']
            titres[d['uid']] = (d.get('titres') or {}).get('titrePrincipal', '')
    amdts = []
    za = ouvrir('amendements', dossier)
    for n in za.namelist():
        a = json.loads(za.read(n))['amendement']
        sig = a['signataires']
        auteur = ref(sig['auteur'].get('acteurRef'))
        if sig['auteur'].get('typeAuteur') != 'Député' or not auteur:
            continue
        c = a['corps'].get('contenuAuteur') or {}
        txt = texte_brut(c.get('dispositif')) + ' ' + texte_brut(c.get('exposeSommaire'))
        trouve = sorted({noms[x] for x in rx.findall(norm(txt))})
        if not trouve:
            continue
        cos = liste((sig.get('cosignataires') or {}).get('acteurRef'))
        cv = a.get('cycleDeVie') or {}
        ident = a['identification']
        div = (a.get('pointeurFragmentTexte') or {}).get('division') or {}
        tx = a['texteLegislatifRef']
        amdts.append({'uid': a['uid'], 'num': ident['numeroLong'], 'organe': ident.get('prefixeOrganeExamen', ''), 'texte': tx,
                      'titre': titres.get(tx, ''), 'article': div.get('articleDesignationCourte', '') or '',
                      'date': cv.get('dateDepot', ''), 'sort': cv['sort'] if isinstance(cv.get('sort'), str) else ((cv.get('etatDesTraitements') or {}).get('etat') or {}).get('libelle', ''),
                      'auteur': auteur, 'cosign': [ref(x) for x in cos if ref(x)], 'societes': trouve,
                      'seance': ref(a.get('seanceDiscussionRef')) or ''})
    # scrutins publics sur ces amendements : même séance et même numéro
    cle = {(x['seance'], x['num']): x['uid'] for x in amdts if x['seance']}
    socs = {x['uid']: x['societes'] for x in amdts}
    scrutins = []
    zs = ouvrir('scrutins', dossier)
    for n in zs.namelist():
        s = json.loads(zs.read(n))['scrutin']
        m = re.match(r"l'amendement n° ?(\d+)", s.get('titre', ''))
        am = cle.get((s.get('seanceRef'), m.group(1))) if m else None
        # seul l'intitulé du texte compte : l'auteur de l'amendement peut porter le nom d'une société (« M. Renault »)
        t = re.search(r'(projet|proposition) de (loi|résolution).*', s.get('titre', ''))
        cites = sorted({noms[x] for x in rx.findall(norm(t.group(0) if t else ''))} | set(socs.get(am, [])))
        if not cites:
            continue
        pos = {}
        for g in liste(((s.get('ventilationVotes') or {}).get('organe') or {}).get('groupes', {}).get('groupe')):
            dn = (g.get('vote') or {}).get('decompteNominatif') or {}
            for k, lib in (('pours', 'pour'), ('contres', 'contre'), ('abstentions', 'abstention'), ('nonVotants', 'non-votant')):
                for v in liste((dn.get(k) or {}).get('votant') if isinstance(dn.get(k), dict) else None):
                    pos[v['acteurRef']] = lib
        scrutins.append({'numero': s['numero'], 'date': s['dateScrutin'], 'titre': s['titre'], 'sort': (s.get('sort') or {}).get('code', ''),
                         'amendement': am or '', 'societes': cites, 'positions': pos})
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump({'amendements': amdts, 'scrutins': scrutins}, open(out, 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'{len(amdts)} amendements de députés citant une société cotée, {len(scrutins)} scrutins publics sur ces amendements')


if __name__ == '__main__':
    main()
