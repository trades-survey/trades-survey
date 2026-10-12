#!/usr/bin/env python3
"""Recherche les élus parmi les dirigeants de sociétés inscrits au Registre national des entreprises (RNE, INPI).

Source : API Recherche d'entreprises (https://recherche-entreprises.api.gouv.fr, DINUM, licence ouverte), qui expose
les dirigeants personnes physiques du RNE avec leur nom, leurs prénoms et leur mois et année de naissance, ainsi que
les entrepreneurs individuels dont l'INSEE diffuse l'identité. Écrit data/raw/rne.json, qui n'est pas archivé :
{« PRENOM|NOM|AAAA-MM-JJ »: [sociétés]}.

Une société n'est retenue que si l'un de ses dirigeants a exactement le nom de l'élu, un premier prénom identique et
le même mois et la même année de naissance que dans sa déclaration HATVP. Un dirigeant sans date de naissance au
registre n'est jamais retenu (homonymie invérifiable). Seuls les élus sont recherchés : le nom des conjoints n'est
pas publié par la HATVP et n'est jamais cherché. La date de naissance sert à la requête et au rapprochement ; elle
n'est pas écrite dans le fichier de sortie autrement que dans la clé, et n'est jamais publiée.

  python3 -I scripts/fetch_rne.py [data/raw/rne.json] [--declarations data/out/declarations.csv] [--limite N]
"""
import calendar, csv, json, os, sys, time, urllib.error, urllib.parse, urllib.request
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'site'))
from societes import norm

URL = 'https://recherche-entreprises.api.gouv.fr/search'
SCOPE = {'depute', 'senateur', 'gouvernement', 'depute_europeen', 'elu_local'}
PAUSE = 0.16  # l'API accepte 7 requêtes par seconde
PAGES_MAX = 10


def get(params, essais=5):
    u = URL + '?' + urllib.parse.urlencode(params)
    for i in range(essais):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'registre-des-elus-actionnaires'}), timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or i == essais - 1:
                raise
        except (urllib.error.URLError, TimeoutError):
            if i == essais - 1:
                raise
        time.sleep(2 ** i)


def noms(n):
    """« MAIRE (DUPONT) » : nom de naissance et nom d'usage."""
    n = n or ''
    out = {norm(n.split('(')[0])}
    if '(' in n:
        out.add(norm(n.split('(', 1)[1].rstrip(')')))
    return out - {''}


def meme_personne(d, nom, prenom, mois):
    if d.get('type_dirigeant') != 'personne physique' or d.get('date_de_naissance') != mois:
        return False
    p = norm(d.get('prenoms'))
    return nom in noms(d.get('nom')) and (p == prenom or p.startswith(prenom + ' '))


def chercher(prenom, nom, naissance):
    a, m = int(naissance[:4]), int(naissance[5:7])
    params = {'nom_personne': nom, 'prenoms_personne': prenom, 'type_personne': 'dirigeant', 'per_page': 25,
              'date_naissance_personne_min': f'{a}-{m:02d}-01', 'date_naissance_personne_max': f'{a}-{m:02d}-{calendar.monthrange(a, m)[1]}'}
    N, P, mois = norm(nom), norm(prenom), naissance[:7]
    out, page = [], 1
    while page <= PAGES_MAX:
        r = get({**params, 'page': page})
        time.sleep(PAUSE)
        for s in r.get('results', []):
            if s.get('statut_diffusion') != 'O':
                continue  # identité non diffusible (diffusion partielle) : jamais reprise
            ds = [d for d in s.get('dirigeants', []) if meme_personne(d, N, P, mois)]
            if not ds:
                continue
            out.append({'siren': s['siren'], 'nom': s.get('nom_raison_sociale') or s.get('nom_complet') or '', 'nj': s.get('nature_juridique') or '',
                        'q': sorted({d.get('qualite') or '' for d in ds}), 'et': s.get('etat_administratif') or '',
                        'dc': s.get('date_creation') or '', 'df': s.get('date_fermeture') or ''})
        if page >= (r.get('total_pages') or 1):
            break
        page += 1
    return out


def main():
    args = sys.argv[1:]
    opt = lambda k, d: args[args.index(k) + 1] if k in args else d
    racine = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    src = opt('--declarations', os.path.join(racine, 'out', 'declarations.csv'))
    limite = int(opt('--limite', 0))
    pos = [a for i, a in enumerate(args) if not a.startswith('--') and (i == 0 or not args[i - 1].startswith('--'))]
    out = pos[0] if pos else os.path.join(racine, 'raw', 'rne.json')
    personnes = sorted({(r['prenom'], r['nom'], r['date_naissance']) for r in csv.DictReader(open(src, encoding='utf-8'))
                        if r['categorie'] in SCOPE and len(r['date_naissance']) == 10})
    if limite:
        personnes = personnes[:limite]
    res, erreurs = {}, 0
    for i, (p, n, dn) in enumerate(personnes):
        try:
            L = chercher(p, n, dn)
        except Exception as e:  # une personne injoignable ne bloque pas les autres
            erreurs += 1
            print(f'::warning::RNE : recherche impossible ({type(e).__name__})')
            if erreurs > 50:
                raise
            continue
        if L:
            res[f'{norm(p)}|{norm(n)}|{dn}'] = sorted(L, key=lambda s: s['siren'])
        if i % 250 == 0:
            print(f'{i}/{len(personnes)} élus recherchés')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(res, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print(f'{len(res)} élus sur {len(personnes)} retrouvés parmi les dirigeants du RNE ({sum(map(len, res.values()))} sociétés), {erreurs} erreurs')


if __name__ == '__main__':
    main()
