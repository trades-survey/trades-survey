"""Pages statiques d'un élu et d'une société, rendues au build (une URL par fiche, lisible sans JavaScript).

Reprend la présentation de site/template.html : même en-tête, même pied de page, même feuille de style.
"""
import html, re
import seo

CAT = {'depute': 'Député', 'senateur': 'Sénateur', 'gouvernement': 'Gouvernement', 'depute_europeen': 'Député européen', 'elu_local': 'Élu local'}
MV = {'apparition': 'Apparition', 'disparition': 'Disparition', 'hausse': 'Hausse', 'baisse': 'Baisse', 'valeur': 'Variation de valeur'}
NAT = {'cotee': 'Cotée en bourse', 'mutualiste': 'Parts sociales (banque mutualiste ou coopérative)', 'fonds': 'Compte-titres, PEA ou fonds',
       'non_cotee': 'Société non cotée', '': 'Nature non déterminée'}
RUB = {'activite_pro': 'Activités professionnelles des cinq dernières années', 'conseil': 'Activités de conseil',
       'dirigeant': "Fonctions dans l'organe dirigeant d'un organisme", 'benevole': 'Fonctions bénévoles', 'mandat': 'Mandats électifs'}
SECTEURS = {'energie': 'Énergie', 'banque': "Banque, assurance, gestion d'actifs", 'defense': 'Défense, aéronautique, spatial', 'sante': 'Santé, pharmacie',
            'numerique': 'Numérique, télécoms, électronique', 'btp': 'BTP, immobilier, concessions', 'transport': 'Automobile, transport',
            'conso': 'Luxe, consommation, distribution', 'agro': 'Agroalimentaire, boissons', 'industrie': 'Industrie, chimie, matériaux',
            'medias': 'Médias, publicité, jeux', 'environnement': "Eau, déchets, services à l'environnement", 'services': 'Services aux entreprises'}
# Fonction en toutes lettres, dans les titres et les descriptions des fiches
FONCTION = {'Gouvernement': 'membre du gouvernement', 'Maire ou adjoint': 'maire ou adjoint au maire'}
VOTE = {'pour': 'Pour', 'contre': 'Contre', 'abstention': 'Abstention', 'non-votant': 'Non-votant'}
MOIS = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.']


def js_dict(tpl, name):
    """Lit un objet littéral JavaScript simple (const NAME={...}) du gabarit, pour ne pas dupliquer les tables."""
    m = re.search(r'const ' + name + r'=\{(.*?)\};', tpl)
    return {k1 or k2: v1 or v2 for k1, k2, v1, v2 in
            re.findall(r"(?:'([^']+)'|(\w+)):(?:'([^']*)'|\"([^\"]*)\")", m.group(1))}


def esc(s):
    return html.escape('' if s is None else str(s), quote=True)


def num(v):
    if v is None or v == '':
        return '—'
    try:
        n = float(v)
    except ValueError:
        return esc(v)
    s = f'{n:,.0f}' if n == int(n) else f'{n:,.2f}'.rstrip('0')
    return s.replace(',', ' ').replace('.', ',')


def eur(v):
    return '—' if v is None else num(v) + ' €'


def an_url(a):
    """Page d'un amendement sur le site de l'Assemblée nationale : numéro du texte sur quatre chiffres, suivi de A ou C
    pour la première ou la seconde partie d'une loi de finances, organe d'examen, numéro sans le préfixe I- ou II-."""
    m = re.search(r'B(?:TC)?(\d+)(?:P(\d))?', a['u'])
    if not m:
        return ''
    partie = {'1': 'A', '2': 'C'}.get(m.group(2), '')
    return f"https://www.assemblee-nationale.fr/dyn/17/amendements/{m.group(1).zfill(4)}{partie}/{a['o']}/{re.sub(r'^I+-', '', a['n'])}"


# Plafond des indemnités cumulées d'un élu (une fois et demie l'indemnité parlementaire de base) : un montant annuel
# déclaré pour un mandat au-delà de ce seuil relève presque toujours d'une erreur de saisie dans la déclaration.
PLAFOND_MANDAT = 150000


def remuneration(a):
    if not a.get('rm'):
        return '—'
    bn = f' {a["bn"].lower()}' if a.get('bn') else ''
    h = '<br>'.join(f'{y} : {num(v)} €{bn}' for y, v in a['rm'])
    if a['r'] == 'mandat' and any(v > PLAFOND_MANDAT for _, v in a['rm']):
        h += '<br><span class="cat">Montant supérieur au plafond légal des indemnités d\'élu : probable erreur de saisie dans la déclaration.</span>'
    return h


def scrutin_url(n):
    return f'https://www.assemblee-nationale.fr/dyn/17/scrutins/{n}'


def mois(d):
    """« 05/2022 » → « mai 2022 »."""
    m = re.fullmatch(r'(\d\d)/(\d{4})', d or '')
    return f'{MOIS[int(m.group(1)) - 1]} {m.group(2)}' if m and 1 <= int(m.group(1)) <= 12 else esc(d)


def date(d):
    if not d:
        return '—'
    y, m, j = d[:10].split('-')
    return f'{int(j)} {MOIS[int(m) - 1]} {y}'


class Site:
    def __init__(self, tpl, db, site=None):
        self.tpl, self.db = tpl, db
        self.site = site or seo.site_url()
        self.DEPN, self.TD = js_dict(tpl, 'DEPN'), js_dict(tpl, 'TD')
        self.E = {e['id']: e for e in db['elus']}
        self.S = {s['k']: s for s in db['socs']}
        i = tpl.index('<header class="top">')
        head = tpl[:i]
        # même feuille de style que l'accueil, chargée depuis le dossier parent
        head = re.sub(r'<style>.*?</style>', '<link rel="stylesheet" href="../style.css">', head, flags=re.S)
        self.head = re.sub(r'href="(?![a-z]+:|#|/|\.\./)', 'href="../', head)
        hdr = tpl[i:tpl.index('<main')]
        foot = tpl[tpl.index('<footer'):tpl.index('</footer>') + 9]
        rel = lambda s: re.sub(r'href="(#[^"]*|donnees/[^"]*|flux\.xml|methode\.html[^"]*|elus/|societes/)"', r'href="../\1"', s)
        self.header, self.footer = rel(hdr), rel(foot)

    def dep_name(self, c):
        return f"{self.DEPN.get(c, c)}{'' if c == '099' else f' ({c})'}" if c else ''

    def e_link(self, eid):
        e = self.E.get(eid)
        return f'<a href="../elus/{e["id"]}.html">{esc(e["p"] + " " + e["n"])}</a>' if e else ''

    def s_link(self, k):
        s = self.S.get(k)
        return f'<a href="../societes/{s["id"]}.html">{esc(s["name"])}</a>' if s else esc(k)

    def pappers(self, s, label=None):
        if s.get('siren'):
            u = f"https://www.pappers.fr/entreprise/{s['siren']}"
        elif s.get('isin') and not s['isin'].startswith('FR'):
            return ''
        else:
            from urllib.parse import quote
            u = f"https://www.pappers.fr/recherche?q={quote(s['name'])}"
        return f'<a href="{esc(u)}" target="_blank" rel="noopener noreferrer nofollow">{label or ("Fiche Pappers" if s.get("siren") else "Rechercher sur Pappers")}</a>'

    def lobbying(self, s):
        L = s.get('lob')
        if not L:
            return ''
        rows = ''
        for o in L:
            u = f'https://www.hatvp.fr/fiche-organisation/?organisation={o["id"]}' if o.get('id') else ''
            nom = (f'<a href="{esc(u)}" target="_blank" rel="noopener">{esc(o["nom"])}</a>' if u else esc(o['nom']))
            lien = {'siren': 'même SIREN', 'nom': 'même nom', 'filiale': 'filiale probable (nom)'}.get(o['lien'], '')
            rows += (f'<tr><td>{nom} <span class="cat">({lien})</span></td><td class="n">{o["n"]}</td><td class="n">{o["np"]}</td><td class="n">{o["ng"]}</td>'
                     f'<td>{esc(o["depense"]) or "—"}{" (" + esc(o["exercice"]) + ")" if o.get("exercice") else ""}</td></tr>')
        objets = [x for o in L for x in o.get('objets', [])][:8]
        h = ('<section><h2>Représentation d\'intérêts</h2><p class="crumb">Organisations du groupe inscrites au répertoire des représentants d\'intérêts tenu par la HATVP. '
             'Activités déclarées sur les trois derniers exercices publiés, dont celles visant des parlementaires ou le Gouvernement.</p>'
             '<div class="tbl"><table><thead><tr><th>Organisation inscrite</th><th class="n">Activités</th><th class="n">Vers le Parlement</th><th class="n">Vers le Gouvernement</th>'
             '<th>Dépenses déclarées (dernier exercice)</th></tr></thead><tbody>' + rows + '</tbody></table></div>')
        if objets:
            h += ('<h3 class="kind">Derniers objets déclarés</h3><ul>' + ''.join(f'<li>{esc(x["o"][:300])} <span class="cat">({", ".join(x["c"])}, {esc(x["d"])})</span></li>' for x in objets) + '</ul>')
        return h + '</section>'

    def an_societe(self, s, H):
        n = s.get('an')
        if not n:
            return ''
        holders = {h['e'] for h in H}
        L = [(eid, x) for eid in holders for x in (self.E[eid].get('an') or []) if s['k'] in x['s']]
        L.sort(key=lambda t: t[1]['d'], reverse=True)
        h = (f'<section><h2>À l\'Assemblée nationale</h2><p>Depuis juillet 2024, {n["a"]} amendement{"s" if n["a"] > 1 else ""} de député{"s" if n["a"] > 1 else ""} '
             f'cite{"nt" if n["a"] > 1 else ""} {esc(s["name"])}, et {n["v"]} scrutin{"s" if n["v"] > 1 else ""} public{"s" if n["v"] > 1 else ""} porte{"nt" if n["v"] > 1 else ""} sur ces amendements ou sur un texte dont l\'intitulé la cite.</p>')
        if L:
            h += '<h3 class="kind">Actes de députés qui déclarent détenir la société (liens à examiner)</h3>'
            rows = ''
            for eid, x in L:
                rows += self.an_rows([x], elu=eid).split('<tbody>')[1].split('</tbody>')[0]
            h += ('<div class="tbl"><table><thead><tr><th>Date</th><th>Député</th><th>Acte</th><th>Texte</th><th>Société citée</th><th>Issue</th></tr></thead><tbody>'
                  + rows + '</tbody></table></div>')
        return h + '</section>'

    def decp(self, s):
        m = s.get('decp')
        if not m or not m.get('n'):
            return ''
        u = 'https://data.economie.gouv.fr/explore/dataset/decp-2022-marches-valides/table/?q=' + esc(m.get('siren', ''))
        h = (f'<section><h2>Marchés publics</h2><p>{m["n"]} marché{"s" if m["n"] > 1 else ""} public{"s" if m["n"] > 1 else ""} notifié{"s" if m["n"] > 1 else ""} '
             f'à la société (titulaire ou cotitulaire, SIREN {esc(m.get("siren", ""))}) entre le {date(m["d0"])} et le {date(m["d1"])}, '
             f'pour un montant total déclaré de {eur(m["total"])}. Les filiales qui ont leur propre SIREN ne sont pas comptées. Pour un accord-cadre, le montant déclaré est souvent le maximum prévu, pas la somme payée. '
             f'<a href="{u}" target="_blank" rel="noopener">Voir les marchés</a></p>')
        if m.get('acheteurs'):
            h += ('<h3 class="kind">Principaux acheteurs</h3><div class="tbl"><table><thead><tr><th>Acheteur</th><th class="n">Marchés</th><th class="n">Montant</th></tr></thead><tbody>'
                  + ''.join(f'<tr><td>{esc(a["nom"])}</td><td class="n">{a["n"]}</td><td class="n">{eur(a["total"])}</td></tr>' for a in m['acheteurs'])
                  + '</tbody></table></div>')
        return h + '</section>'

    def deports(self, s):
        L = s.get('dep')
        if not L:
            return ''
        h = ('<section><h2>Déports de membres du Gouvernement</h2><p class="crumb">Décrets publiés au Journal officiel par lesquels un ministre '
             's\'abstient de connaître des actes relatifs aux entités qu\'ils citent, dont cette société ; ces actes sont alors confiés à un autre membre du Gouvernement.</p><ul>')
        for d in L:
            h += (f'<li><a href="https://www.legifrance.gouv.fr/jorf/id/{esc(d["u"])}" target="_blank" rel="noopener">{esc(d["t"])}</a>'
                  f' <span class="cat">({date(d["d"])}{", " + esc(d["m"]) if d.get("m") else ""})</span>'
                  + '</li>')
        return h + '</ul></section>'

    def mv_rows(self, L, elu=True, soc=True):
        if not L:
            return '<p class="empty">Aucun mouvement entre deux déclarations successives.</p>'
        rows = ''.join(
            f'<tr><td><span class="pill m-{m["m"]}">{MV[m["m"]]}</span></td>'
            + (f'<td>{self.e_link(m["e"])}</td>' if elu else '') + (f'<td>{self.s_link(m["s"])}</td>' if soc else '')
            + f'<td class="mono">{date(m["da"]) if m["da"] else "—"}</td><td class="mono">{date(m["dp"])}</td>'
            f'<td class="n">{num(m["qa"])} → {num(m["qp"])}</td><td class="n">{eur(m["va"])} → {eur(m["vp"])}</td></tr>' for m in L)
        return ('<div class="tbl"><table><thead><tr><th>Écart constaté</th>' + ('<th>Élu</th>' if elu else '') + ('<th>Société</th>' if soc else '')
                + '<th>Entre le</th><th>et le</th><th class="n">Titres</th><th class="n">Valeur déclarée</th></tr></thead><tbody>' + rows + '</tbody></table></div>')

    def page(self, title, desc, nav, body, rel, graphe, og_type='website', prefix='../', extra=''):
        """Page complète. rel : chemin de la page dans le site ; prefix : chemin de la racine vu de la page."""
        url = self.site + rel.removesuffix('index.html')
        h = self.head.replace('<title>Registre des élus actionnaires</title>',
                              f'<title>{esc(title)} · {seo.NOM}</title>\n' + seo.meta(url, title, desc, seo.website(self.site) + graphe,
                                                                                 self.site + 'og.png', og_type, extra), 1)
        hdr = re.sub(f'href="\\.\\./(#{nav}|{nav}\\.html)"', r'href="../\1" class="on"', self.header, count=1) if nav else self.header
        out = ('<!doctype html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
               + h + '</head>\n<body>\n' + hdr + '<main class="wrap">' + body + '</main>\n' + self.footer + '\n</body>\n</html>\n')
        return out if prefix == '../' else out.replace('="../', '="' + prefix)

    def elu(self, e):
        TD = self.TD
        I = [h for h in e['h'] if h['f'] == 'interets']
        P = [h for h in e['h'] if h['f'] == 'patrimoine']
        mv = [m for m in self.db['mv'] if m['e'] == e['id']]

        def hold(L, title, src):
            if not L:
                t = '<p class="empty">Aucune participation déclarée dans cette déclaration.</p>'
            else:
                vc = any('vc' in h for h in L)
                t = ('<div class="tbl"><table><thead><tr><th>Société ou support</th><th class="n">Titres</th><th class="n">Capital</th><th class="n">Valeur déclarée</th>'
                     + ('<th class="n">Au dernier cours</th>' if vc else '') + '</tr></thead><tbody>' + ''.join(
                    f'<tr><td>{self.s_link(h["s"]) if h["nl"] == "participation" or h["f"] == "patrimoine" else esc(h["n"])}'
                    + (' <span class="cat">(compte-titres, lignes non détaillées)</span>' if h['nl'] == 'portefeuille_titres' else '')
                    + f'</td><td class="n">{num(h["q"])}</td><td class="n">{esc(h["c"]) + " %" if h["c"] else "—"}</td><td class="n">{eur(h["v"])}</td>'
                    + (f'<td class="n">{eur(h.get("vc"))}</td>' if vc else '') + '</tr>' for h in L) + '</tbody></table></div>'
                     + ('<p class="crumb">« Au dernier cours » : nombre de titres déclaré multiplié par le dernier cours de clôture sur Euronext. '
                        "Estimation qui suppose que l'élu détient toujours les mêmes titres ; ce n'est pas une donnée déclarée.</p>" if vc else ''))
            return f'<section><h2>{title}</h2><p class="crumb">{src}</p>{t}</section>'

        srcI = f"{TD.get(I[0]['t'], I[0]['t'])} du {date(I[0]['d'])}" if I else "Dernière déclaration d'intérêts"
        name = e['p'] + ' ' + e['n']
        meta = [f'<span>{esc(e["fn"])}</span>', f'<span>{esc(e["org"])}</span>']
        if e['dep'] and self.DEPN.get(e['dep'], '\0') not in e['org']:
            meta.append(f'<span>{esc(self.dep_name(e["dep"]))}</span>')
        if e.get('g'):
            meta.append(f'<span>Groupe {esc(e["gl"])}' + (f' ({esc(e["g"])})' if e['g'] != e['gl'] else '') + '</span>')
        if len(e['cats']) > 1:
            meta.append('<span>Aussi : ' + ', '.join(CAT[c] for c in e['cats'] if c != e['cat']) + '</span>')
        if e['page']:
            meta.append(f'<a href="{esc(e["page"])}" rel="noopener" target="_blank">Fiche HATVP</a>')
        body = f'<p class="crumb"><a href="../#elus">Élus</a></p>\n<section><h1>{esc(name)}</h1><div class="meta">{"".join(meta)}</div></section>\n'
        body += hold(I, 'Participations déclarées', srcI)
        if e['cat'] == 'gouvernement' or P:
            body += hold(P, 'Valeurs mobilières (patrimoine)', f"{TD.get(P[0]['t'], P[0]['t'])} du {date(P[0]['d'])}. Publiée pour les membres du gouvernement uniquement."
                         if P else 'Aucune déclaration de patrimoine publiée au format ouvert.')
        body += self.commission(e) + self.activite_an(e)
        ac = e.get('ac')
        if ac:
            body += (f'<section><h2>Activités, fonctions et mandats déclarés</h2><p class="crumb">{TD.get(ac["t"], ac["t"])} du {date(ac["d"])}. '
                     'Rémunérations telles que déclarées, par année, brutes ou nettes selon la déclaration ; elles peuvent porter sur une activité antérieure au mandat.</p>')
            for code, titre in RUB.items():
                L = [a for a in ac['l'] if a['r'] == code]
                if not L:
                    continue
                rem = code != 'benevole'
                body += (f'<h3 class="kind">{titre}</h3><div class="tbl"><table><thead><tr><th>Intitulé</th><th>Organisme</th><th>Période</th>'
                         + ('<th>Rémunération déclarée</th>' if rem else '') + '</tr></thead><tbody>'
                         + ''.join(f'<tr><td>{esc(a["i"]) or "—"}</td><td>{esc(a["o"]) or "—"}</td><td class="mono">'
                                   + (f'{mois(a["db"])} – {mois(a["fi"]) if a["fi"] else "en cours"}' if a['db'] else '—') + '</td>'
                                   + (f'<td>{remuneration(a)}</td>' if rem else '') + '</tr>' for a in L)
                         + '</tbody></table></div>')
            body += '</section>'
        body += self.rne(e)
        cj = e.get('cj')
        if cj:
            t = ('<div class="tbl"><table><thead><tr><th>Activité</th><th>Employeur</th></tr></thead><tbody>'
                 + ''.join(f'<tr><td>{esc(c["a"]) if c["a"] else "—"}</td><td>{esc(c["e"]) if c["e"] else "—"}</td></tr>' for c in cj['l'])
                 + '</tbody></table></div>') if cj['l'] else '<p class="empty">Aucune activité déclarée.</p>'
            body += (f'<section><h2>Activité professionnelle du conjoint</h2><p class="crumb">{TD.get(cj["t"], cj["t"])} du {date(cj["d"])}. '
                     "Conjoint, partenaire de PACS ou concubin, tel que déclaré à la HATVP ; son nom n'est pas publié.</p>" + t + '</section>')
        if e['masked']:
            k = e['masked']
            body += (f'<p class="note">{k} ligne{"s" if k > 1 else ""} dont le nom a été occulté par la HATVP (le plus souvent une société civile familiale) '
                     f'n\'{"apparaissent" if k > 1 else "apparaît"} pas ici.</p>')
        body += f"<section><h2>Évolution d'une déclaration à l'autre</h2>{self.mv_rows(mv, elu=False)}</section>"
        body += ('<section><h2>Déclarations sources</h2><div class="tbl"><table><thead><tr><th>Déclaration</th><th>Déposée le</th><th>Document</th></tr></thead><tbody>'
                 + ''.join(f'<tr><td>{esc(TD.get(d["t"], d["t"]))}{" <span class=\"cat\">(modificative)</span>" if d["m"] else ""}</td><td class="mono">{date(d["d"])}</td><td>'
                           + (f'<a href="{esc(d["u"])}" target="_blank" rel="noopener">PDF HATVP</a>' if d['u'] else
                              (f'<a href="{esc(e["page"])}" target="_blank" rel="noopener">Fiche HATVP</a>' if e['page'] else '—')) + '</td></tr>'
                           for d in reversed(e['decls'])) + '</tbody></table></div></section>')
        dl = e.get('dl')
        if dl:
            quand = f'{dl["j"]} jour{"s" if dl["j"] > 1 else ""} après' if dl['dd'] > dl['pf'] else ('le jour même' if dl['dd'] == dl['pf'] else 'avant cette date')
            body += (f'<p class="note">Entrée en fonction de député : {date(dl["pf"])}. Déclaration d\'intérêts de début de mandat déposée le {date(dl["dd"])}, '
                     f'{quand} (liste publiée par la HATVP). La loi demande un dépôt dans les deux mois qui suivent l\'entrée en fonction, soit au plus tard le {date(dl["ech"])} '
                     + ('<strong>; le dépôt est postérieur à cette date.</strong>' if dl['hors'] else '.') + '</p>')
        body += "<p class=\"note\">Cette page juxtapose des informations publiées par la HATVP. Elle ne porte aucune appréciation sur la situation de l'élu.</p>"
        socs = []
        for h in I + P:
            n = self.S[h['s']]['name'] if h['s'] in self.S and h['nl'] == 'participation' else h['n']
            if n not in socs:
                socs.append(n)
        fonction = FONCTION.get(e['fn'], e['fn'].lower())
        name = e['p'] + ' ' + e['n'].title()  # « Jean Dupont » dans les titres et les données structurées, comme on le cherche
        lieu = self.dep_name(e['dep']).split(' (')[0] if e['dep'] and e['dep'] != '099' else ''
        n = len(socs)
        desc = (f"{name}, {fonction}{' (' + lieu + ')' if lieu else ''}. "
                + (f"{n} participation{'s' if n > 1 else ''} déclarée{'s' if n > 1 else ''} à la HATVP : {', '.join(socs[:5])}{'…' if n > 5 else ''}. "
                   if socs else 'Aucune participation dans sa dernière déclaration à la HATVP. ')
                + "Déclarations sources et écarts d'une déclaration à l'autre.")
        rel = f"elus/{e['id']}.html"
        url = self.site + rel
        titre = f'{name}, {fonction} : actions et participations déclarées'
        personne = {'@type': 'Person', 'name': name, 'givenName': e['p'], 'familyName': e['n'].title(), 'jobTitle': e['fn'],
                    **({'workLocation': {'@type': 'Place', 'name': e['org']}} if e['org'] else {}), **({'sameAs': [e['page']]} if e['page'] else {})}
        graphe = [seo.page_web(self.site, url, titre, desc, [('Élus', self.site + 'elus/'), (name, url)], personne, 'ProfilePage')]
        return self.page(titre, desc, 'elus', body, rel, graphe, 'profile')

    def rne(self, e):
        L = e.get('rne')
        if not L:
            return ''
        rows = ''.join(
            f'<tr><td><a href="https://annuaire-entreprises.data.gouv.fr/entreprise/{esc(x["si"])}" target="_blank" rel="noopener">{esc(x["n"]) or "—"}</a>'
            + (' <span class="cat">(aussi dans sa déclaration d\'intérêts)</span>' if x['di'] else '')
            + f'</td><td class="mono">{esc(x["si"])}</td><td>{esc(x["fj"])}</td><td>{esc(x["q"]) or "—"}</td><td class="mono">{date(x["dc"]) if x["dc"] else "—"}</td>'
            f'<td>{"En activité" if x["et"] == "A" else "Fermée le " + date(x["df"]) if x["df"] else "Fermée"}</td></tr>' for x in L)
        return ('<section><h2>Sociétés au Registre national des entreprises</h2>'
                '<p class="crumb">Sociétés en activité, ou fermées depuis moins de cinq ans, dont un dirigeant inscrit au Registre national des entreprises (INPI) '
                'porte le même nom, le même premier prénom et le même mois de naissance que l\'élu dans sa déclaration à la HATVP '
                '(rapprochement établi par ce site, via l\'annuaire des entreprises de l\'État). Un homonyme né le même mois reste possible. '
                'Le registre ne donne pas les dates du mandat : la fonction indiquée est la dernière inscrite. Lien à examiner, '
                'qui ne dit rien de l\'activité réelle de la société ni du rôle de l\'élu.</p>'
                '<div class="tbl"><table><thead><tr><th>Société</th><th>SIREN</th><th>Forme</th><th>Fonction au registre</th><th>Créée le</th><th>État</th></tr></thead><tbody>'
                + rows + '</tbody></table></div></section>')

    def commission(self, e):
        if not e.get('com'):
            return ''
        f = f" ({esc(e['comf'])})" if e.get('comf') else ''
        h = f'<section><h2>Commission permanente</h2><p>Membre de la {esc(e["com"][0].lower() + e["com"][1:])}{f}, d\'après l\'open data de son assemblée.</p>'
        if e.get('lk'):
            h += ('<p>Sociétés déclarées dont le secteur relève de cette commission (lien à examiner) :</p><ul>'
                  + ''.join(f'<li>{self.s_link(x["s"])} <span class="cat">({esc(SECTEURS.get(x["sec"], x["sec"]))})</span></li>' for x in e['lk']) + '</ul>'
                  '<p class="crumb">Rapprochement indicatif entre le secteur de la société et les domaines de la commission, établi par ce site. '
                  "Il ne signifie pas que l'élu a pris part à une décision concernant la société.</p>")
        return h + '</section>'

    def an_rows(self, L, elu=None):
        rows = ''
        for x in L:
            if x['k'] == 'amendement':
                u = an_url(x)
                quoi = (f'<a href="{esc(u)}" target="_blank" rel="noopener">Amendement n° {esc(x["n"])}</a>' if u else f'Amendement n° {esc(x["n"])}') + f' <span class="cat">({esc(x["r"])})</span>'
                issue = esc(x['so']) or '—'
            else:
                quoi = f'<a href="{scrutin_url(x["n"])}" target="_blank" rel="noopener">Scrutin n° {esc(x["n"])}</a>'
                issue = f'Vote : {VOTE.get(x["p"], esc(x["p"]))} <span class="cat">({esc(x["so"])})</span>'
            texte = esc(x['ti']) + (f' <span class="cat">({esc(x["ar"])})</span>' if x.get('ar') else '')
            rows += (f'<tr><td class="mono">{date(x["d"])}</td>' + (f'<td>{self.e_link(elu)}</td>' if elu else '') + f'<td>{quoi}</td><td>{texte}</td>'
                     f'<td>{", ".join(self.s_link(k) for k in x["s"])}</td><td>{issue}</td></tr>')
        return ('<div class="tbl"><table><thead><tr><th>Date</th>' + ('<th>Député</th>' if elu else '') +
                '<th>Acte</th><th>Texte</th><th>Société citée</th><th>Issue</th></tr></thead><tbody>' + rows + '</tbody></table></div>')

    def activite_an(self, e):
        if not e.get('an'):
            return ''
        return ('<section><h2>Amendements et votes citant une société déclarée</h2>'
                '<p class="crumb">Amendements déposés ou cosignés par le député dont le texte cite une société qu\'il déclare détenir, et scrutins publics '
                'sur ces amendements ou sur un texte dont l\'intitulé la cite (open data de l\'Assemblée nationale, XVIIe législature). Liens à examiner : '
                'citer une société n\'est pas agir en sa faveur.</p>' + self.an_rows(e['an']) + '</section>')

    def societe(self, s, labels=()):
        seen, H = set(), []
        for h in s['holders']:
            if h['e'] not in seen:
                seen.add(h['e'])
                H.append(h)
        H.sort(key=lambda h: -(h['v'] or 0))
        mv = [m for m in self.db['mv'] if m['s'] == s['k']]
        names = list(dict.fromkeys([n for n in labels if n] + [m['n'] for m in mv if m['n']]))
        meta = [f'<span>{NAT[s.get("nat", "")]}</span>']
        meta.append(f'<span class="mono">ISIN {s["isin"]}</span><span>' + ('Vérifié dans la liste Euronext' if s.get('iv') else 'Rattachement manuel') + '</span>' if s['isin'] else '<span>Pas encore rattachée à un code ISIN</span>')
        if s['siren']:
            meta.append(f'<span class="mono">SIREN {s["siren"]}</span>')
        if s.get('sec'):
            meta.append(f'<span>Secteur : {esc(SECTEURS.get(s["sec"], s["sec"]))}</span>')
        if s.get('cours'):
            meta.append(f'<span>Dernier cours : {num(s["cours"]["c"])} € ({date(s["cours"]["d"])})</span>')
        meta.append(self.pappers(s))
        body = f'<p class="crumb"><a href="../#societes">Sociétés</a></p>\n<section><h1>{esc(s["name"])}</h1><div class="meta">{"".join(meta)}</div></section>\n'
        if H:
            body += ('<section><h2>Élus qui déclarent la détenir</h2><div class="tbl"><table><thead><tr><th>Élu</th><th>Fonction</th><th class="n">Titres</th><th class="n">Valeur déclarée</th><th>Déclaration du</th></tr></thead><tbody>'
                     + ''.join(f'<tr><td>{self.e_link(h["e"])}{" <span class=\"cat\">(patrimoine)</span>" if h["f"] == "patrimoine" else ""}</td>'
                               f'<td class="cat">{esc(self.E[h["e"]]["fn"])}</td><td class="n">{num(h["q"])}</td><td class="n">{eur(h["v"])}</td><td class="mono">{date(h["d"])}</td></tr>' for h in H)
                     + '</tbody></table></div></section>')
        else:
            body += '<section><h2>Élus qui déclarent la détenir</h2><p class="empty">Aucun élu ne la déclare dans sa dernière déclaration.</p></section>'
        body += f'<section><h2>Mouvements</h2>{self.mv_rows(mv, soc=False)}</section>'
        body += self.lobbying(s) + self.an_societe(s, H) + self.decp(s) + self.deports(s)
        if len(names) > 1:
            body += f'<p class="note">Libellés regroupés sous ce nom : {" · ".join(esc(n) for n in names)}</p>'
        n = len(H)
        qui = [v for k, v in (('depute', 'députés'), ('senateur', 'sénateurs'), ('gouvernement', 'membres du gouvernement'))
               if any(self.E[h['e']]['cat'] == k for h in H)]
        desc = (f"{s['name']}{' (ISIN ' + s['isin'] + ')' if s['isin'] else ''} : "
                + (f"{n} élu{'s' if n > 1 else ''} français la déclare{'nt' if n > 1 else ''} dans sa déclaration à la HATVP" if n else "aucun élu ne la déclare dans sa dernière déclaration à la HATVP")
                + (f" ({', '.join(qui)})" if qui else '')
                + ". Nombre de titres, valeur déclarée et écarts entre deux déclarations.")
        rel = f"societes/{s['id']}.html"
        url = self.site + rel
        titre = f"{s['name']} : {n} élu{'s' if n > 1 else ''} actionnaire{'s' if n > 1 else ''}" if n else f"{s['name']} : élus actionnaires"
        ids = [{'@type': 'PropertyValue', 'propertyID': k.upper(), 'value': s[k]} for k in ('isin', 'siren') if s.get(k)]
        org = {'@type': 'Organization', 'name': s['name'], **({'identifier': ids} if ids else {}),
               **({'sameAs': [f"https://annuaire-entreprises.data.gouv.fr/entreprise/{s['siren']}"]} if s.get('siren') else {})}
        graphe = [seo.page_web(self.site, url, titre, desc, [('Sociétés', self.site + 'societes/'), (s['name'], url)], org)]
        return self.page(titre, desc, 'societes', body, rel, graphe)

    # Pages sans fiche : accueil (contenu lisible sans JavaScript), index, méthode, page introuvable

    def accueil(self, idx):
        """Contenu de l'accueil, rendu au build dans <main id="app"> : visible sans JavaScript, et repris tel quel par la route #accueil."""
        holders = sum(1 for e in idx['elus'] if e['nh'])
        socs = [s for s in idx['socs'] if s['nh']]
        mvt = [m for m in idx['mv'] if m['m'] != 'valeur']
        top = sorted((s for s in socs if s['nat'] == 'cotee'), key=lambda s: -s['nh'])[:12]
        last = self.mv_rows(mvt[:8]).replace('<th>Entre le</th>', '<th>Avant</th>').replace('<th>et le</th>', '<th>Après</th>')
        h = ('''<section><h1>Actions et participations des élus, d'après leurs propres déclarations</h1>
  <p class="lede">Les participations dans des sociétés déclarées par les députés, les sénateurs, les membres du gouvernement, les députés européens élus en France et les principaux élus locaux à la Haute Autorité pour la transparence de la vie publique, et leur évolution d'une déclaration à l'autre.</p></section>
  <section><label for="q" class="kind">Rechercher un élu, une société, un code ISIN ou un code postal</label>
    <div class="search" style="margin-top:6px"><input id="q" type="search" placeholder="Ex. Air Liquide, FR0000120271, Dupont, 69003" autocomplete="off"></div>
    <div class="results" id="qr" hidden></div></section>
  <section class="figs" aria-label="Chiffres clés">'''
             f'<div><b>{num(len(idx["elus"]))}</b><span>élus avec une déclaration publiée</span></div>'
             f'<div><b>{num(holders)}</b><span>déclarent au moins une participation</span></div>'
             f'<div><b>{num(len(socs))}</b><span>sociétés citées</span></div>'
             f'<div><b>{num(len(mvt))}</b><span>écarts entre deux déclarations (hors variations de cours)</span></div></section>'
             '''
  <p class="note"><strong>À lire avant tout.</strong> En France, les élus ne déclarent pas leurs achats et ventes de titres au fil de l'eau. Ils déposent des déclarations à des dates données. Un « mouvement » ici est donc un écart entre deux déclarations successives, pas une transaction datée.</p>
  <div class="cols">
    <section><h2>Derniers mouvements déclarés</h2><div id="lastmv">''' + last + '''</div><p><a href="#mouvements">Tous les mouvements</a></p></section>
    <section><h2>Sociétés cotées les plus citées</h2><div class="tbl"><table><thead><tr><th>Société</th><th class="n">Élus</th></tr></thead><tbody>'''
             + ''.join(f'<tr><td>{self.s_link(s["k"])}' + (f'<div class="mono cat">{s["isin"]}</div>' if s['isin'] else '') + f'</td><td class="n">{s["nh"]}</td></tr>' for s in top)
             + '''</tbody></table></div><p><a href="#societes?nat=cotee">Toutes les sociétés cotées</a></p></section>
  </div>
  <section><h2>Parcourir</h2><ul>
    <li><a href="elus/">Index des élus</a> : une fiche par député, sénateur, membre du gouvernement, député européen et élu local</li>
    <li><a href="societes/">Index des sociétés</a> : une fiche par société citée, avec les élus qui la déclarent</li>
    <li><a href="methode.html">Méthode et limites</a> : sources, traitements, corrections et droit de réponse</li>
    <li>Données ouvertes : <a href="donnees/participations.csv">participations</a>, <a href="donnees/mouvements.csv">mouvements</a>, <a href="donnees/elus.csv">élus</a> (CSV), <a href="donnees/registre.json">ensemble des données</a> (JSON), <a href="flux.xml">flux RSS</a></li>
  </ul></section>
  <section class="prose"><h2>Questions fréquentes</h2>'''
             + ''.join(f'<h3>{esc(q)}</h3><p>{r}</p>' for q, r in self.faq(idx)) + '</section>')
        return h.replace('href="../', 'href="')

    def faq(self, idx):
        """Questions et réponses de l'accueil (aussi en données structurées et dans llms.txt). Réponses en HTML, liens depuis la racine."""
        top = sorted((s for s in idx['socs'] if s['nh'] and s['nat'] == 'cotee'), key=lambda s: -s['nh'])[:5]
        return [
            ("Les députés et les sénateurs doivent-ils déclarer leurs actions ?",
             "Oui. Les députés, les sénateurs, les membres du gouvernement et les principaux élus locaux déclarent à la Haute Autorité pour la transparence de la vie publique (HATVP) "
             "leurs participations financières directes dans le capital de sociétés, dans leur déclaration d'intérêts, au début de leur mandat puis à chaque modification substantielle. "
             "La HATVP publie ces déclarations ; ce site en reprend les participations, élu par élu et société par société."),
            ("Peut-on connaître les achats et ventes d'actions d'un élu ?",
             "Pas au jour le jour : la loi française n'impose pas aux élus de déclarer chaque transaction. Le site compare les déclarations successives d'un même élu "
             "et signale les écarts (une société qui apparaît ou disparaît, un nombre de titres qui augmente ou baisse), sans date de transaction. "
             '<a href="#mouvements">Voir les derniers mouvements</a>.'),
            ("Quelles sociétés cotées les élus détiennent-ils le plus ?",
             "D'après la dernière déclaration de chaque élu : " + ', '.join(f'{self.s_link(s["k"])} ({s["nh"]} élus)' for s in top) + '. '
             f"Données extraites le {date(idx['built'])}."),
            ("Pourquoi le patrimoine des parlementaires n'apparaît-il pas ?",
             "Les déclarations de patrimoine des députés et des sénateurs sont seulement consultables en préfecture et la loi interdit de les publier. "
             "Le site n'utilise donc que leurs déclarations d'intérêts. Les déclarations de patrimoine des membres du gouvernement sont publiques : le site en reprend les valeurs mobilières."),
            ("Détenir des actions est-il interdit pour un élu ?",
             "Non. Détenir des actions est légal, et les déclarer est précisément ce que la loi demande. Le site présente des faits déclarés, avec leur source ; "
             "il ne qualifie aucune situation et ne présume d'aucun conflit d'intérêts."),
            ("D'où viennent les données et peut-on les réutiliser ?",
             "De l'open data de la HATVP, téléchargé chaque lundi, sous licence ouverte Etalab 2.0. Les données retraitées sont téléchargeables sous la même licence : "
             '<a href="donnees/participations.csv">participations</a>, <a href="donnees/mouvements.csv">mouvements</a> et <a href="donnees/elus.csv">élus</a> au format CSV. '
             '<a href="methode.html">Méthode et limites</a>.'),
        ]

    def index_elus(self):
        ordre = ['depute', 'senateur', 'gouvernement', 'depute_europeen', 'elu_local']
        titres = {'depute': 'Députés', 'senateur': 'Sénateurs', 'gouvernement': 'Membres du gouvernement', 'depute_europeen': 'Députés européens', 'elu_local': 'Élus locaux'}

        def li(e):
            k = len(e['h'])
            return (f'<li><a href="{e["id"]}.html">{esc(e["p"] + " " + e["n"])}</a> <span class="cat">{esc(e["org"] or e["fn"])}'
                    f'{" · " + esc(e["fn"]) if e["cat"] == "elu_local" else ""} · {k if k else "aucune"} participation{"s" if k > 1 else ""}</span></li>')
        body = ('<p class="crumb"><a href="../#elus">Liste filtrable des élus</a></p><section><h1>Index des élus</h1>'
                '<p class="lede">Tous les élus dont une déclaration est publiée par la HATVP, avec le nombre de participations figurant dans leur dernière déclaration.</p>'
                '<p>' + ' · '.join(f'<a href="#{c}">{titres[c]}</a>' for c in ordre) + '</p></section>')
        for c in ordre:
            L = sorted((e for e in self.db['elus'] if e['cat'] == c), key=lambda e: (e['n'], e['p']))
            body += f'<section><h2 id="{c}">{titres[c]} ({num(len(L))})</h2>'
            if c == 'elu_local':
                deps = {}
                for e in L:
                    deps.setdefault(e['dep'], []).append(e)
                for d in sorted(deps, key=lambda d: (d == '', d == '099', d)):
                    body += f'<h3 class="kind">{esc(self.dep_name(d)) if d else "Région, collectivité ou département non déterminé"}</h3><ul>' + ''.join(li(e) for e in deps[d]) + '</ul>'
            else:
                body += '<ul>' + ''.join(li(e) for e in L) + '</ul>'
            body += '</section>'
        titre = 'Index des élus : députés, sénateurs, ministres et élus locaux'
        desc = (f"Les {num(len(self.db['elus']))} élus dont une déclaration est publiée par la HATVP : députés, sénateurs, membres du gouvernement, "
                "députés européens et élus locaux, avec leurs participations déclarées dans des sociétés.")
        url = self.site + 'elus/'
        return self.page(titre, desc, 'elus', body.replace('href="../elus/', 'href="'), 'elus/index.html',
                         [seo.page_web(self.site, url, titre, desc, [('Élus', url)], kind='CollectionPage')])

    def index_societes(self):
        ordre = ['cotee', 'mutualiste', 'fonds', 'non_cotee', '']
        n_el = {s['k']: len({h['e'] for h in s['holders']}) for s in self.db['socs']}
        body = ('<p class="crumb"><a href="../#societes">Liste filtrable des sociétés</a></p><section><h1>Index des sociétés</h1>'
                '<p class="lede">Toutes les sociétés citées dans au moins une déclaration, avec le nombre d\'élus qui la détiennent d\'après leur dernière déclaration.</p></section>')
        for c in ordre:
            L = sorted((s for s in self.db['socs'] if s.get('nat', '') == c), key=lambda s: s['name'].lower())
            if not L:
                continue
            body += (f'<section><h2>{NAT[c]} ({num(len(L))})</h2><ul>'
                     + ''.join(f'<li><a href="{s["id"]}.html">{esc(s["name"])}</a> <span class="cat">{(s["isin"] + " · ") if s["isin"] else ""}'
                               f'{n_el[s["k"]] or "aucun"} élu{"s" if n_el[s["k"]] > 1 else ""}</span></li>' for s in L) + '</ul></section>')
        titre = 'Index des sociétés détenues par des élus'
        desc = (f"Les {num(len(self.db['socs']))} sociétés citées dans les déclarations des élus à la HATVP : sociétés cotées, parts sociales, "
                "comptes-titres et sociétés non cotées, avec le nombre d'élus qui les déclarent.")
        url = self.site + 'societes/'
        return self.page(titre, desc, 'societes', body, 'societes/index.html',
                         [seo.page_web(self.site, url, titre, desc, [('Sociétés', url)], kind='CollectionPage')])

    def methode(self, built):
        """Page « Méthode et limites », rendue au build depuis la route #methode du gabarit (une seule source pour le texte)."""
        m = re.search(r"function methode\(\)\{\n  app.innerHTML=`(.*?)`;\n\}", self.tpl, re.S)
        c = self.db['legal'].get('contact')
        body = m.group(1).replace('${contact()}', f'<a href="mailto:{esc(c)}">{esc(c)}</a>' if c else '<mark>[à compléter]</mark>').replace('${date(DB.built)}', date(built))
        assert '${' not in body, 'expression non prise en charge dans la route #methode'
        titre = 'Méthode et limites'
        desc = ("Comment le Registre des élus actionnaires extrait les participations des déclarations publiées par la HATVP : sources, regroupement des sociétés, "
                "codes ISIN, calcul des écarts entre deux déclarations, limites, corrections et droit de réponse.")
        url = self.site + 'methode.html'
        return self.page(titre, desc, 'methode', body, 'methode.html', [seo.page_web(self.site, url, titre, desc, [(titre, url)])], prefix='./')

    def introuvable(self):
        """404.html, servie par GitHub Pages à n'importe quelle profondeur : liens depuis le chemin du site."""
        from urllib.parse import urlparse
        body = '<section><h1>Page introuvable</h1><p>Cette adresse ne correspond à aucune page. <a href="../">Retour à l\'accueil</a> · <a href="../elus/">Index des élus</a> · <a href="../societes/">Index des sociétés</a></p></section>'
        return self.page('Page introuvable', 'Cette adresse ne correspond à aucune page du site.', '', body, '404.html', [],
                         prefix=urlparse(self.site).path, extra='<meta name="robots" content="noindex">\n')
