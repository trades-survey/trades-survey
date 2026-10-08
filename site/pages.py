"""Pages statiques d'un élu et d'une société, rendues au build (une URL par fiche, lisible sans JavaScript).

Reprend la présentation de site/template.html : même en-tête, même pied de page, même feuille de style.
"""
import html, re

CAT = {'depute': 'Député', 'senateur': 'Sénateur', 'gouvernement': 'Gouvernement', 'depute_europeen': 'Député européen', 'elu_local': 'Élu local'}
MV = {'apparition': 'Apparition', 'disparition': 'Disparition', 'hausse': 'Hausse', 'baisse': 'Baisse', 'valeur': 'Variation de valeur'}
NAT = {'cotee': 'Cotée en bourse', 'mutualiste': 'Parts sociales (banque mutualiste ou coopérative)', 'fonds': 'Compte-titres, PEA ou fonds',
       'non_cotee': 'Société non cotée', '': 'Nature non déterminée'}
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
                t = '<div class="tbl"><table><thead><tr><th>Société ou support</th><th class="n">Titres</th><th class="n">Capital</th><th class="n">Valeur déclarée</th></tr></thead><tbody>' + ''.join(
                    f'<tr><td>{self.s_link(h["s"]) if h["nl"] == "participation" or h["f"] == "patrimoine" else esc(h["n"])}'
                    + (' <span class="cat">(compte-titres, lignes non détaillées)</span>' if h['nl'] == 'portefeuille_titres' else '')
                    + f'</td><td class="n">{num(h["q"])}</td><td class="n">{esc(h["c"]) + " %" if h["c"] else "—"}</td><td class="n">{eur(h["v"])}</td></tr>' for h in L) + '</tbody></table></div>'
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
        body += "<p class=\"note\">Cette page juxtapose des informations publiées par la HATVP. Elle ne porte aucune appréciation sur la situation de l'élu.</p>"
        socs = []
        for h in I + P:
            if h['n'] not in socs:
                socs.append(h['n'])
        desc = f"{name}, {e['fn']} ({e['org']}). " + (f"Participations déclarées à la HATVP : {', '.join(socs[:6])}{'…' if len(socs) > 6 else ''}."
                                                       if socs else 'Aucune participation dans sa dernière déclaration à la HATVP.')
        return self.page(f'{name} : participations déclarées', desc, 'elus', body)

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
        meta.append(f'<span class="mono">ISIN {s["isin"]}</span><span>Rattachement manuel</span>' if s['isin'] else '<span>Pas encore rattachée à un code ISIN</span>')
        if s['siren']:
            meta.append(f'<span class="mono">SIREN {s["siren"]}</span>')
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
        if len(names) > 1:
            body += f'<p class="note">Libellés regroupés sous ce nom : {" · ".join(esc(n) for n in names)}</p>'
        n = len(H)
        desc = f"{s['name']}{' (ISIN ' + s['isin'] + ')' if s['isin'] else ''} : {n} élu{'s' if n > 1 else ''} français la déclare{'nt' if n > 1 else ''} dans sa déclaration à la HATVP."
        return self.page(f"{s['name']} : élus actionnaires", desc, 'societes', body)
