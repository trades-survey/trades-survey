"""Sources croisées avec les déclarations : cours de bourse, répertoire des représentants d'intérêts, activité à
l'Assemblée nationale, commission permanente, délais de dépôt, commande publique et déports des ministres.

Chaque source est facultative : si son fichier manque (source injoignable cette semaine), la fonction renvoie un
résultat vide et le site se construit sans la rubrique correspondante.
"""
import calendar, csv, datetime as DT, json, os, re
from societes import norm

# Secteurs suivis par chaque commission permanente (rapprochement indicatif, voir la page Méthode)
COMMISSION_SECTEURS = [
    (r'AFFAIRES ECONOMIQUES', {'energie', 'numerique', 'industrie', 'agro', 'conso', 'btp'}),
    (r'FINANCES', {'banque'}),
    (r'DEFENSE|AFFAIRES ETRANGERES.*SENAT', {'defense'}),
    (r'AFFAIRES SOCIALES', {'sante'}),
    (r'DEVELOPPEMENT DURABLE|AMENAGEMENT DU TERRITOIRE', {'transport', 'energie', 'environnement', 'btp'}),
    (r'CULTURE|AFFAIRES CULTURELLES', {'medias'}),
]


def secteurs_commission(chambre, commission):
    c = norm(commission) + (' SENAT' if chambre == 'senateur' else '')
    out = set()
    for motif, s in COMMISSION_SECTEURS:
        if re.search(motif, c):
            out |= s
    return out


def cours(D):
    """Dernier cours de clôture en euros par ISIN (liste Euronext), Euronext Paris de préférence."""
    f = D + 'raw/euronext.csv'
    if not os.path.exists(f):
        return {}
    out = {}
    for r in csv.DictReader(open(f, encoding='utf-8')):
        if r.get('devise') != 'EUR' or not r.get('cours'):
            continue
        try:
            c = float(r['cours'])
        except ValueError:
            continue
        j, m, a = (r.get('date_cours') or '').split(' ')[0].split('/') if '/' in (r.get('date_cours') or '') else ('', '', '')
        paris = 'Paris' in (r.get('marche') or '')
        if r['isin'] not in out or (paris and not out[r['isin']][2]):
            out[r['isin']] = (c, f'{a}-{m}-{j}' if a else '', paris)
    return {k: (v[0], v[1]) for k, v in out.items()}


def lobbying(D):
    f = D + 'raw/lobbying.json'
    return json.load(open(f, encoding='utf-8')) if os.path.exists(f) else {}


def assemblee(D):
    f = D + 'raw/assemblee.json'
    return json.load(open(f, encoding='utf-8')) if os.path.exists(f) else {'amendements': [], 'scrutins': []}


def json_facultatif(D, nom, defaut):
    f = D + nom
    return json.load(open(f, encoding='utf-8')) if os.path.exists(f) else defaut


def plus_deux_mois(d):
    m = d.month + 2
    y, m = d.year + (m > 12), (m - 1) % 12 + 1
    e = DT.date(y, m, min(d.day, calendar.monthrange(y, m)[1]))
    while e.weekday() >= 5:  # échéance un samedi ou un dimanche : premier jour ouvré suivant
        e += DT.timedelta(1)
    return e


# Après les élections générales de 2024, les députés sont entrés en fonction à l'ouverture de la législature (18 juillet 2024)
OUVERTURE_17 = DT.date(2024, 7, 18)


def delai_depot(prise_fonction, depots):
    """Première déclaration d'intérêts déposée pour le mandat en cours (liste HATVP) et délai écoulé depuis l'entrée en fonction."""
    try:
        pf = max(DT.date.fromisoformat(prise_fonction), OUVERTURE_17)
    except ValueError:
        return None
    ds = sorted(d for d in depots if d >= (pf - DT.timedelta(30)).isoformat())
    if not ds:
        return None
    dd = DT.date.fromisoformat(ds[0])
    ech = plus_deux_mois(pf)
    return {'pf': pf.isoformat(), 'dd': dd.isoformat(), 'j': (dd - pf).days, 'ech': ech.isoformat(), 'hors': dd > ech}


# Forme juridique d'après le code de catégorie juridique de l'INSEE
def forme(nj):
    nj = str(nj or '')
    for pre, lib in (('1', 'Entreprise individuelle'), ('5498', 'EURL'), ('54', 'SARL'), ('5710', 'SAS'), ('5720', 'SASU'), ('55', 'SA'), ('56', 'SA'),
                     ('52', 'Société en nom collectif'), ('53', 'Société en commandite'), ('6540', 'SCI'), ('65', 'Société civile'), ('92', 'Association')):
        if nj.startswith(pre):
            return lib
    return 'Autre forme'


FORMES = re.compile(r'\b(SARL|EURL|SASU|SAS|SA|SCI|SCEA|SC|SNC|GAEC|EARL|SELARL|SELAS|STE|SOCIETE|CIVILE|IMMOBILIERE)\b')


def base_nom(n):
    return ' '.join(FORMES.sub(' ', norm(n)).split())


def mandats_sociaux(L, e, built, annees=5):
    """Sociétés du RNE dont l'élu est dirigeant : en activité, ou fermées depuis moins de cinq ans (durée couverte par la
    déclaration d'intérêts). « di » signale une société dont le nom figure aussi dans sa déclaration d'intérêts (activités,
    fonctions ou participations) ; son absence ne signifie rien, les noms étant écrits librement."""
    lim = f'{int(built[:4]) - annees}{built[4:10]}'
    noms = [base_nom(a.get('o', '')) for a in (e.get('ac') or {}).get('l', [])] + [base_nom(a.get('i', '')) for a in (e.get('ac') or {}).get('l', [])]
    noms += [base_nom(h['n']) for h in e['h'] if h['f'] == 'interets']
    noms = [n for n in noms if n]
    out = []
    for s in L:
        if s['et'] != 'A' and not (s['df'] and s['df'] >= lim):
            continue
        b = base_nom(s['nom'])
        # une entreprise individuelle porte le nom de l'élu : son nom ne dit rien de la déclaration
        di = bool(b) and not str(s['nj']).startswith('1') and any(n == b or (len(b) >= 5 and re.search(r'\b' + re.escape(b) + r'\b', n)) or (len(n) >= 5 and re.search(r'\b' + re.escape(n) + r'\b', b)) for n in noms)
        q = ', '.join(x for x in s['q'] if x) or ('Entrepreneur individuel' if str(s['nj']).startswith('1') else '')
        out.append({'si': s['siren'], 'n': s['nom'], 'fj': forme(s['nj']), 'q': q, 'et': s['et'], 'dc': s['dc'], 'df': s['df'], 'di': di})
    return sorted(out, key=lambda x: (x['et'] != 'A', x['n']))
