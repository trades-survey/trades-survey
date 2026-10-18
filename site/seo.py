"""Référencement : métadonnées des pages, données structurées schema.org, dates de modification, sitemap et llms.txt.

Les moteurs de recherche et les assistants conversationnels lisent le HTML sans exécuter le JavaScript : chaque page
indexable porte donc son contenu, une adresse canonique, une description et des données structurées (JSON-LD).
"""
import hashlib, html, json, os, re

NOM = 'Registre des élus actionnaires'
LICENCE = 'https://www.etalab.gouv.fr/licence-ouverte-open-licence/'
HATVP_OPEN = 'https://www.hatvp.fr/open-data/'
# Marqueur remplacé, une fois la page rendue, par la date de sa dernière modification réelle (voir Dates)
MODIFIE = '__MODIFIE__'


def site_url():
    return (os.environ.get('SITE_URL', '').strip() or 'https://trades-survey.github.io/trades-survey/').rstrip('/') + '/'


def esc(s):
    return html.escape('' if s is None else str(s), quote=True)


def texte(h):
    """HTML → texte brut, pour les descriptions et les données structurées."""
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', h))).strip()


def coupe(s, n=158):
    s = texte(s)
    return s if len(s) <= n else s[:n - 1].rsplit(' ', 1)[0].rstrip(' ,;:') + '…'


def ld(obj):
    return ('<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
            + '</script>\n')


def meta(url, titre, desc, graphe, image, og_type='website', extra=''):
    """Balises de tête d'une page : description, adresse canonique, aperçu de partage (Open Graph) et JSON-LD."""
    t, d = esc(titre), esc(coupe(desc))
    return (f'<meta name="description" content="{d}">\n<link rel="canonical" href="{esc(url)}">\n'
            f'<meta property="og:type" content="{og_type}">\n<meta property="og:site_name" content="{NOM}">\n<meta property="og:locale" content="fr_FR">\n'
            f'<meta property="og:title" content="{t}">\n<meta property="og:description" content="{d}">\n<meta property="og:url" content="{esc(url)}">\n'
            f'<meta property="og:image" content="{esc(image)}">\n<meta property="og:image:width" content="1200">\n<meta property="og:image:height" content="630">\n'
            f'<meta property="og:image:alt" content="{NOM}">\n<meta name="twitter:card" content="summary_large_image">\n'
            + extra + ld({'@context': 'https://schema.org', '@graph': graphe}))


def site_ids(site):
    return {'site': site + '#site', 'editeur': site + '#editeur', 'donnees': site + '#donnees'}


def website(site):
    i = site_ids(site)
    return [{'@type': 'WebSite', '@id': i['site'], 'url': site, 'name': NOM, 'inLanguage': 'fr-FR', 'publisher': {'@id': i['editeur']},
             'description': "Participations dans des sociétés déclarées à la HATVP par les députés, les sénateurs, les membres du gouvernement, "
                            "les députés européens et les principaux élus locaux, et leur évolution d'une déclaration à l'autre."},
            {'@type': 'Organization', '@id': i['editeur'], 'name': NOM, 'url': site, 'logo': site + 'icon-180.png'}]


def page_web(site, url, titre, desc, miette, principal=None, kind='WebPage'):
    """Page : WebPage (ou ProfilePage, CollectionPage…), fil d'Ariane et entité décrite."""
    p = {'@type': kind, '@id': url, 'url': url, 'name': titre, 'description': coupe(desc, 300), 'inLanguage': 'fr-FR',
         'isPartOf': {'@id': site_ids(site)['site']}, 'dateModified': MODIFIE,
         'breadcrumb': {'@type': 'BreadcrumbList', 'itemListElement': [
             {'@type': 'ListItem', 'position': i + 1, 'name': n, 'item': u} for i, (n, u) in enumerate([('Accueil', site)] + miette)]}}
    if principal:
        p['mainEntity'] = principal
    return p


def dataset(site, built, n_elus, n_socs):
    return {'@type': 'Dataset', '@id': site_ids(site)['donnees'], 'name': 'Participations financières déclarées par les élus français à la HATVP',
            'description': (f"Participations dans des sociétés (actions, parts sociales, comptes-titres) déclarées à la Haute Autorité pour la transparence de la vie publique "
                            f"par {n_elus} députés, sénateurs, membres du gouvernement, députés européens et élus locaux, rattachées à {n_socs} sociétés, "
                            "avec les écarts entre deux déclarations successives. Déclarations de patrimoine reprises pour les seuls membres du gouvernement. "
                            "Données extraites chaque semaine de l'open data de la HATVP."),
            'url': site, 'inLanguage': 'fr-FR', 'license': LICENCE, 'isAccessibleForFree': True, 'dateModified': built,
            'creator': {'@id': site_ids(site)['editeur']}, 'isBasedOn': HATVP_OPEN, 'spatialCoverage': {'@type': 'Place', 'name': 'France'},
            'temporalCoverage': '2023-07/..', 'keywords': ['HATVP', 'déclaration d\'intérêts', 'députés', 'sénateurs', 'ministres', 'actions', 'participations financières', 'transparence de la vie publique'],
            'distribution': [{'@type': 'DataDownload', 'encodingFormat': f, 'contentUrl': site + 'donnees/' + n, 'name': t} for n, f, t in [
                ('elus.csv', 'text/csv', 'Élus'), ('participations.csv', 'text/csv', 'Participations déclarées'),
                ('mouvements.csv', 'text/csv', 'Écarts entre deux déclarations'), ('registre.json', 'application/json', 'Ensemble des données')]]}


def faq_ld(qr):
    return {'@type': 'FAQPage', 'mainEntity': [{'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': texte(r)}} for q, r in qr]}


def verification():
    """Balises de vérification de la Search Console de Google et de Bing Webmaster Tools (variables du dépôt, facultatives)."""
    h = ''
    for var, nom in (('GOOGLE_SITE_VERIFICATION', 'google-site-verification'), ('BING_SITE_VERIFICATION', 'msvalidate.01')):
        v = os.environ.get(var, '').strip()
        if v:
            if not re.fullmatch(r'[\w-]{8,100}', v):
                raise SystemExit(f'{var} invalide')
            h += f'<meta name="{nom}" content="{v}">\n'
    return h


def indexnow_key():
    k = os.environ.get('INDEXNOW_KEY', '').strip()
    if k and not re.fullmatch(r'[a-zA-Z0-9-]{8,128}', k):
        raise SystemExit('INDEXNOW_KEY invalide (8 à 128 lettres, chiffres ou tirets)')
    return k


class Dates:
    """Date de dernière modification réelle de chaque page, gardée d'une semaine à l'autre (data/ref/pages.json).

    Une page dont le contenu n'a pas changé garde sa date : le sitemap n'annonce aux moteurs que les pages modifiées.
    """
    def __init__(self, path, built):
        self.path, self.built = path, built
        try:
            self.old = json.load(open(path, encoding='utf-8'))
        except (OSError, ValueError):
            self.old = {}
        self.new = {}

    def date(self, rel, page):
        corps = page.split('<body>', 1)[-1]
        h = hashlib.sha1(corps.encode('utf-8')).hexdigest()[:12]
        o = self.old.get(rel)
        d = o[1] if o and o[0] == h else self.built
        self.new[rel] = [h, d]
        return d

    def save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(dict(sorted(self.new.items())), f, ensure_ascii=False, separators=(',', ':'))
            f.write('\n')


def sitemap(site, dates):
    from xml.sax.saxutils import escape as xe
    urls = ''.join(f'<url><loc>{xe(site + ("" if rel == "index.html" else rel.removesuffix("index.html")))}</loc><lastmod>{d}</lastmod></url>\n'
                   for rel, (_, d) in sorted(dates.items(), key=lambda kv: (kv[0] != 'index.html', kv[0].count('/'), kv[0])) if rel != '404.html')
    return '<?xml version="1.0" encoding="utf-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + '</urlset>\n'


def robots(site):
    return ('# Tous les robots sont les bienvenus, moteurs de recherche et assistants conversationnels compris.\n'
            f'User-agent: *\nAllow: /\n\nSitemap: {site}sitemap.xml\n')


def llms(site, built, n, top, faq):
    """llms.txt (https://llmstxt.org) : présentation du site en Markdown pour les assistants conversationnels."""
    L = [f'# {NOM}', '',
         f"> Participations dans des sociétés (actions, parts sociales, comptes-titres) que les députés, les sénateurs, les membres du gouvernement, "
         f"les députés européens élus en France et les principaux élus locaux ont déclarées à la Haute Autorité pour la transparence de la vie publique (HATVP), "
         f"et leur évolution d'une déclaration à l'autre. Données mises à jour chaque semaine ; dernière extraction le {built}.", '',
         f"Chiffres de la dernière mise à jour : {n['elus']} élus avec une déclaration publiée, dont {n['holders']} déclarent au moins une participation ; "
         f"{n['socs']} sociétés citées ; {n['mv']} écarts entre deux déclarations successives (hors simples variations de cours).", '',
         'À savoir avant de citer ce site :',
         "- Un « mouvement » est un écart entre deux déclarations successives d'un même élu, pas une transaction datée : les élus français ne déclarent pas leurs achats et ventes de titres au fil de l'eau.",
         "- Les montants sont ceux déclarés par les élus, à la date de chaque déclaration.",
         "- Pour les parlementaires et les élus locaux, seules les déclarations d'intérêts sont utilisées ; les déclarations de patrimoine des parlementaires ne peuvent pas être republiées. "
         "Pour les membres du gouvernement, les valeurs mobilières de la déclaration de patrimoine publiée sont reprises.",
         "- Le site juxtapose des faits déclarés, avec leur source. Il ne présume d'aucun conflit d'intérêts : détenir des actions est légal et leur déclaration est ce que la loi demande.",
         "- Source : open data de la HATVP, licence ouverte Etalab 2.0. Citer « HATVP, retraité par le Registre des élus actionnaires » avec la date d'extraction.", '',
         '## Pages principales', '',
         f'- [Accueil]({site}): chiffres clés, derniers mouvements, sociétés cotées les plus détenues',
         f'- [Index des élus]({site}elus/): une fiche par élu, avec ses participations, ses déclarations sources et leur évolution',
         f'- [Index des sociétés]({site}societes/): une fiche par société, avec les élus qui la déclarent',
         f'- [Méthode et limites]({site}methode.html): sources, traitements, ce que le site ne dit pas, corrections et droit de réponse', '',
         '## Données ouvertes', '',
         f'- [Élus (CSV)]({site}donnees/elus.csv)', f'- [Participations (CSV)]({site}donnees/participations.csv)',
         f'- [Mouvements entre deux déclarations (CSV)]({site}donnees/mouvements.csv)', f'- [Ensemble des données (JSON)]({site}donnees/registre.json)',
         f'- [Flux RSS des derniers mouvements]({site}flux.xml)', '',
         '## Sociétés cotées les plus détenues', '']
    L += [f'- [{s["name"]}]({site}societes/{s["id"]}.html): {s["nh"]} élu{"s" if s["nh"] > 1 else ""}' + (f' (ISIN {s["isin"]})' if s['isin'] else '') for s in top]
    L += ['', '## Questions fréquentes', '']
    for q, r in faq:
        L += [f'### {q}', '', texte(r), '']
    return '\n'.join(L).rstrip() + '\n'
