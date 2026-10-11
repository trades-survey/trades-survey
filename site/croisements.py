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
