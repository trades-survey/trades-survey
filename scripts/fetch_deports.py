#!/usr/bin/env python3
"""Décrets de déport des membres du Gouvernement, tirés du Journal officiel (open data de la DILA, licence ouverte).

Un ministre qui a un intérêt dans une entreprise ou un organisme s'abstient d'en connaître : un décret « pris en
application de l'article 2-1 [ou 2-2] du décret n° 59-178 du 22 janvier 1959 relatif aux attributions des ministres »
confie les actes correspondants à un autre membre du Gouvernement. Ce script lit les livraisons quotidiennes du JO
(https://echanges.dila.gouv.fr/OPENDATA/JORF/), retient ces décrets et en garde le titre, le ministère, la date et le
ministère et la date, ainsi que les sociétés cotées du site qu'ils citent (le texte des articles, qui peut nommer
des tiers, n'est pas conservé).

État conservé dans data/ref/deports.json (archivé) : {"dernier": nom de la dernière livraison lue, "decrets": [...]}.
Chaque exécution ne lit que les livraisons plus récentes ; les livraisons quotidiennes remontent à juillet 2025.

  python3 -I scripts/fetch_deports.py [data/ref/deports.json] [--max N]   # N : nombre maximal de livraisons lues
"""
import html, json, os, re, sys, tarfile, tempfile, urllib.request
import xml.etree.ElementTree as ET
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'site'))
from societes import motifs, norm

BASE = 'https://echanges.dila.gouv.fr/OPENDATA/JORF/'
TITRE = re.compile(r"pris en application de l'article 2(-[12])? du décret n° ?59-178", re.I)


def texte(el):
    return ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', ET.tostring(el, encoding='unicode'))).split()) if el is not None else ''


def lire_livraison(chemin, decrets, articles):
    with tarfile.open(chemin, 'r:gz') as tar:
        for m in tar:
            if not m.isfile() or not m.name.endswith('.xml'):
                continue
            if '/texte/version/' not in m.name and '/article/' not in m.name:
                continue
            brut = tar.extractfile(m).read()
            if b'59-178' not in brut:
                continue
            x = ET.fromstring(brut)
            if '/texte/version/' in m.name:
                t = x.findtext('.//TITREFULL') or ''
                if TITRE.search(t):
                    i = x.findtext('.//META_COMMUN/ID')
                    decrets[i] = {**decrets.get(i, {}), 'id': i, 'titre': ' '.join(t.split()), 'date': x.findtext('.//DATE_TEXTE') or '',
                                  'publication': x.findtext('.//DATE_PUBLI') or '', 'ministere': x.findtext('.//MINISTERE') or ''}
            else:
                tt = x.find('.//CONTEXTE/TEXTE/TITRE_TXT')
                if tt is not None and TITRE.search(tt.text or ''):
                    tx = x.find('.//CONTEXTE/TEXTE')
                    cid = tx.get('cid')
                    # l'article peut arriver sans la version du texte : le décret est créé d'après son contexte
                    decrets.setdefault(cid, {'id': cid, 'titre': ' '.join((tt.text or '').split()), 'date': tx.get('date_signature', ''),
                                             'publication': tx.get('date_publi', ''), 'ministere': ''})
                    articles.setdefault(cid, {})[x.findtext('.//META_ARTICLE/NUM') or ''] = texte(x.find('.//BLOC_TEXTUEL/CONTENU'))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    mx = int(sys.argv[sys.argv.index('--max') + 1]) if '--max' in sys.argv else 10 ** 6
    if '--max' in sys.argv:
        args.remove(str(mx))
    out = args[0] if args else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'ref', 'deports.json')
    etat = json.load(open(out, encoding='utf-8')) if os.path.exists(out) else {'dernier': '', 'decrets': []}
    with urllib.request.urlopen(BASE, timeout=120) as r:
        index = r.read().decode('utf-8', 'replace')
    livraisons = sorted(set(re.findall(r'JORF_\d{8}-\d{6}\.tar\.gz', index)))
    a_lire = [f for f in livraisons if f > etat['dernier']][:mx]
    decrets = {d['id']: d for d in etat['decrets']}
    articles = {}
    for f in a_lire:
        with tempfile.NamedTemporaryFile(suffix='.tar.gz') as tmp:
            try:
                with urllib.request.urlopen(BASE + f, timeout=600) as r:
                    while b := r.read(1 << 20):
                        tmp.write(b)
                tmp.flush()
                lire_livraison(tmp.name, decrets, articles)
            except Exception as e:  # livraison illisible : on s'arrête là et on reprendra à la prochaine exécution
                print(f'::warning::livraison {f} illisible ({e})')
                break
        etat['dernier'] = f
    rx, noms = motifs()
    for i, d in decrets.items():
        # Le texte des articles n'est pas conservé : il peut nommer des tiers (conjoint, associés). Seules les sociétés
        # du site qu'il cite sont gardées ; un décret déjà lu garde celles trouvées à sa lecture.
        a = articles.get(i) or d.pop('articles', None)
        if a:
            d['societes'] = sorted({noms[x] for x in rx.findall(norm(' '.join(a.values())))})
        d.pop('articles', None)
        d.setdefault('societes', [])
    etat['decrets'] = sorted(decrets.values(), key=lambda d: d['date'], reverse=True)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(etat, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"{len(a_lire)} livraisons lues, {len(etat['decrets'])} décrets de déport connus (dernière livraison : {etat['dernier']})")


if __name__ == '__main__':
    main()
