"""Pages statiques d'un élu et d'une société, rendues au build (une URL par fiche, lisible sans JavaScript).

Reprend la présentation de site/template.html : même en-tête, même pied de page, même feuille de style.
"""
import html, re

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
    def __init__(self, tpl, db):
        self.tpl, self.db = tpl, db
        self.DEPN, self.TD = js_dict(tpl, 'DEPN'), js_dict(tpl, 'TD')
        self.E = {e['id']: e for e in db['elus']}
        self.S = {s['k']: s for s in db['socs']}
        i = tpl.index('<header class="top">')
        head = tpl[:i]
        # même feuille de style que l'accueil, chargée depuis le dossier parent
        head = re.sub(r'<style>.*?</style>', '<link rel="stylesheet" href="../style.css">', head, flags=re.S)
        self.head = head.replace('href="fonts/', 'href="../fonts/').replace('href="flux.xml"', 'href="../flux.xml"').replace('href="style.css"', 'href="../style.css"')
        hdr = tpl[i:tpl.index('<main')]
        foot = tpl[tpl.index('<footer'):tpl.index('</footer>') + 9]
        rel = lambda s: re.sub(r'href="(#[^"]*|donnees/[^"]*|flux\.xml)"', r'href="../\1"', s)
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

    def page(self, title, desc, nav, body):
        h = self.head.replace('<title>Registre des élus actionnaires</title>',
                              f'<title>{esc(title)} · Registre des élus actionnaires</title>\n<meta name="description" content="{esc(desc)}">', 1)
        hdr = self.header.replace(f'href="../#{nav}"', f'href="../#{nav}" class="on"', 1)
        return ('<!doctype html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                + h + '</head>\n<body>\n' + hdr + '<main class="wrap">' + body + '</main>\n' + self.footer + '\n</body>\n</html>\n')

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
            body += f'<section><h2>Activités, fonctions et mandats déclarés</h2><p class="crumb">{TD.get(ac["t"], ac["t"])} du {date(ac["d"])}. Rémunérations non reprises.</p>'
            for code, titre in RUB.items():
                L = [a for a in ac['l'] if a['r'] == code]
                if not L:
                    continue
                body += (f'<h3 class="kind">{titre}</h3><div class="tbl"><table><thead><tr><th>Intitulé</th><th>Organisme</th><th>Période</th></tr></thead><tbody>'
                         + ''.join(f'<tr><td>{esc(a["i"]) or "—"}</td><td>{esc(a["o"]) or "—"}</td><td class="mono">'
                                   + (f'{mois(a["db"])} – {mois(a["fi"]) if a["fi"] else "en cours"}' if a['db'] else '—') + '</td></tr>' for a in L)
                         + '</tbody></table></div>')
            body += '</section>'
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
            if h['n'] not in socs:
                socs.append(h['n'])
        desc = f"{name}, {e['fn']} ({e['org']}). " + (f"Participations déclarées à la HATVP : {', '.join(socs[:6])}{'…' if len(socs) > 6 else ''}."
                                                       if socs else 'Aucune participation dans sa dernière déclaration à la HATVP.')
        return self.page(f'{name} : participations déclarées', desc, 'elus', body)

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
        desc = f"{s['name']}{' (ISIN ' + s['isin'] + ')' if s['isin'] else ''} : {n} élu{'s' if n > 1 else ''} français la déclare{'nt' if n > 1 else ''} dans sa déclaration à la HATVP."
        return self.page(f"{s['name']} : élus actionnaires", desc, 'societes', body)
