#!/usr/bin/env python3
"""Extrait les participations financières des déclarations HATVP.

Entrées (open data HATVP, licence Etalab) :
  - declarations.xml  https://www.hatvp.fr/livraison/merge/declarations.xml
  - liste.csv         https://www.hatvp.fr/livraison/opendata/liste.csv (facultatif)

Sortie : un CSV avec une ligne par participation déclarée.

Contrainte juridique : les déclarations de situation patrimoniale (DSP) des
parlementaires ne doivent pas être republiées. On ne lit donc que les
déclarations d'intérêts (DI, DIA, DIM, DIAM) pour tout le monde, et les DSP
uniquement pour les membres du gouvernement (option --ministres-patrimoine).

Le parseur ne dépend pas d'un schéma figé : il cherche la section dont le nom
contient « participationFinanciere » et lit chaque item qui porte un nomSociete.

Usage :
  python3 -I extract_participations.py declarations.xml -o participations.csv \
      [--liste liste.csv] [--ministres-patrimoine] [--declarations-out declarations.csv]
"""
import argparse
import csv
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime

INTEREST_TYPES = {"DI", "DIA", "DIM", "DIAM"}
PATRIMOINE_TYPES = {"DSP", "DSPM", "DSPFM"}
# Sections de DSP qui décrivent des titres détenus (ministres seulement) :
# valeursEnBourseDto (comptes-titres, PEA : établissement + valeur, sans détail
# des lignes) et valeursNonEnBourseDto (sociétés non cotées : dénomination, % détenu).
PATRIMOINE_SECTION_RE = re.compile(r"^valeurs(Non)?EnBourse", re.I)
GOUV_RE = re.compile(r"membre du gouvernement", re.I)
NON_PUBLIE_RE = re.compile(r"\[\s*Données non publiées\s*\]", re.I)
DEPT_RE = re.compile(r"\(\s*(\d[\dAB]?\d?)\s*\)")

FIELDS = [
    "declaration_id", "type_declaration", "modificative", "date_depot", "categorie",
    "civilite", "prenom", "nom", "date_naissance",
    "type_mandat", "mandat", "organe", "departement",
    "section", "nature_ligne", "societe", "societe_masquee", "nb_parts", "valeur_eur", "capital_detenu_pct",
    "remuneration", "conseil_activite", "commentaire", "isin",
    "valeur_brute", "nb_parts_brut",
]

DECL_FIELDS = ["declaration_id", "type_declaration", "modificative", "date_depot", "categorie",
               "prenom", "nom", "date_naissance", "type_mandat", "mandat", "organe", "section_presente"]


def local(tag):
    return tag.rsplit("}", 1)[-1]


def text(el):
    if el is None:
        return ""
    return " ".join(NON_PUBLIE_RE.sub(" ", el.text or "").split())


def find_first(root, *names):
    """Premier descendant (profondeur d'abord) dont le nom local est dans names."""
    wanted = {n.lower() for n in names}
    for el in root.iter():
        if local(el.tag).lower() in wanted and text(el):
            return text(el)
    return ""


def parse_date(s):
    s = s.strip()
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:19], fmt).date().isoformat()
        except ValueError:
            pass
    return s


NUM_RE = re.compile(r"-?\d[\d\s  .,]*")


def parse_number(s):
    """'1 250,50 €' -> 1250.5 ; renvoie '' si rien d'exploitable."""
    if not s:
        return ""
    m = NUM_RE.search(s)
    if not m:
        return ""
    n = re.sub(r"[\s  ]", "", m.group(0)).rstrip(".,")
    if "," in n and "." in n:
        # le dernier séparateur est la décimale
        if n.rfind(",") > n.rfind("."):
            n = n.replace(".", "").replace(",", ".")
        else:
            n = n.replace(",", "")
    elif "," in n:
        n = n.replace(",", ".")
    elif n.count(".") > 1:
        n = n.replace(".", "")
    elif "." in n and len(n.split(".")[1]) == 3:
        n = n.replace(".", "")  # séparateur de milliers « 1.000 »
    try:
        v = float(n)
    except ValueError:
        return ""
    return int(v) if v.is_integer() else v


def item_fields(item):
    """Feuilles directes d'un item, nom local en minuscules -> texte."""
    out = {}
    for child in item:
        if len(child) == 0:
            name = local(child.tag).lower()
            out[name] = text(child)
            if NON_PUBLIE_RE.search(child.text or ""):
                out.setdefault("_masques", set()).add(name)
    return out


def items_in(section):
    """Items d'une section : éléments dont une feuille directe nomme la société."""
    names = {"nomsociete", "nomentreprise", "denomination", "libelle", "nature", "etablissement"}
    for el in section.iter():
        if any(len(c) == 0 and local(c.tag).lower() in names for c in el):
            yield el


def general_info(decl):
    gen = next((e for e in decl if local(e.tag).lower() == "general"), decl)
    declarant = next((e for e in gen.iter() if local(e.tag).lower() == "declarant"), gen)
    sub = lambda path: text(gen.find(path))
    typ = sub("typeDeclaration/id")
    categorie_mandat = sub("mandat/label")  # « Député ou sénateur », « Membre du Gouvernement »…
    type_mandat = sub("qualiteMandat/labelTypeMandat")
    organe = sub("organe/labelOrgane")
    m = DEPT_RE.search(organe)
    info = {
        "declaration_id": text(decl.find("uuid")),
        "type_declaration": typ.upper(),
        "modificative": "oui" if sub("declarationModificative").lower() == "true" else "non",
        "date_depot": parse_date(text(decl.find("dateDepot"))),
        "civilite": find_first(declarant, "civilite"),
        "prenom": find_first(declarant, "prenom"),
        "nom": find_first(declarant, "nom"),
        "date_naissance": parse_date(find_first(declarant, "dateNaissance")),
        "type_mandat": type_mandat or categorie_mandat,
        "mandat": sub("qualiteDeclarant") or categorie_mandat,
        "organe": organe,
        "departement": m.group(1) if m else "",
    }
    info["categorie"] = categorie(categorie_mandat, type_mandat)
    return info


def categorie(categorie_mandat, type_mandat):
    c, t = categorie_mandat.lower(), type_mandat.lower()
    if GOUV_RE.search(c):
        return "gouvernement"
    if t.startswith("député") or t.startswith("depute"):
        return "depute"
    if t.startswith("sénateur") or t.startswith("senateur"):
        return "senateur"
    if "député européen" in c:
        return "depute_europeen"
    if c.startswith("elu local"):
        return "elu_local"
    return "autre"


def is_government(info):
    return info["categorie"] == "gouvernement"


def rows_for(decl, ministres_patrimoine, stats, seen=None):
    info = general_info(decl)
    typ = info["type_declaration"]
    stats["declarations"] += 1
    stats["types"][typ] = stats["types"].get(typ, 0) + 1
    if seen is not None and (typ in INTEREST_TYPES or (
            typ in PATRIMOINE_TYPES and ministres_patrimoine and is_government(info))):
        # Déclaration retenue, même sans participation : l'étape 2 en a besoin
        # pour détecter les disparitions.
        sec_re = re.compile("participationfinanciere", re.I) if typ in INTEREST_TYPES else PATRIMOINE_SECTION_RE
        present = any(sec_re.search(local(c.tag)) for c in decl)
        seen.append({**{k: info[k] for k in DECL_FIELDS if k in info},
                     "section_presente": "oui" if present else "non"})
    if typ in INTEREST_TYPES:
        section_match = lambda tag: "participationfinanciere" in tag.lower()
    elif typ in PATRIMOINE_TYPES and ministres_patrimoine and is_government(info):
        section_match = lambda tag: bool(PATRIMOINE_SECTION_RE.search(tag))
    else:
        if typ in PATRIMOINE_TYPES:
            stats["dsp_ignorees"] += 1
        return
    for section in decl:
        tag = local(section.tag)
        if not section_match(tag):
            continue
        neant = find_first(section, "neant").lower() == "true"
        if neant:
            stats["sections_neant"] += 1
        for item in items_in(section):
            f = item_fields(item)
            societe = f.get("nomsociete") or f.get("nomentreprise") or f.get("denomination") \
                or f.get("libelle") or f.get("nature", "")
            nature_ligne = "participation" if "participationfinanciere" in tag.lower() else "titres_non_cotes"
            if not societe and f.get("etablissement"):
                # Compte-titres ou PEA d'un ministre : la DSP ne détaille pas les lignes.
                nature_ligne = "portefeuille_titres"
                societe = f"{f.get('natureplacement') or 'Valeurs mobilières'} ({f['etablissement']})"
            if not societe:
                continue
            valeur_brute = f.get("evaluation") or f.get("valeur") or f.get("valeuractuelle") \
                or f.get("montant", "")
            parts_brut = f.get("nombreparts") or f.get("nombretitres") or f.get("nombre", "")
            yield {
                **info,
                "section": tag,
                "nature_ligne": nature_ligne,
                "societe": " ".join(societe.split()),
                # La HATVP occulte souvent la fin du nom (SCI, GFA familiaux…) : nom non comparable.
                "societe_masquee": "oui" if f.get("_masques", set()) & {"nomsociete", "denomination"} else "non",
                "nb_parts": parse_number(parts_brut),
                "valeur_eur": parse_number(valeur_brute),
                "capital_detenu_pct": parse_number(f.get("capitaldetenu") or f.get("participation", "")),
                "remuneration": f.get("remuneration", ""),
                "conseil_activite": f.get("acticonseil", ""),
                "commentaire": " ".join(f.get("commentaire", "").split()),
                "isin": "",
                "valeur_brute": valeur_brute,
                "nb_parts_brut": parts_brut,
            }


def load_liste(path):
    """Index des métadonnées de liste.csv par (nom, prenom) pour compléter mandat/département."""
    idx = {}
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh, delimiter=";"):
            key = (r.get("nom", "").strip().upper(), r.get("prenom", "").strip().upper())
            idx.setdefault(key, r)
    return idx


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("xml")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--liste", help="liste.csv HATVP pour compléter type_mandat / département")
    ap.add_argument("--ministres-patrimoine", action="store_true",
                    help="inclure les titres des DSP des membres du gouvernement")
    ap.add_argument("--declarations-out",
                    help="CSV listant toutes les déclarations retenues, y compris sans participation")
    args = ap.parse_args(argv)

    liste = load_liste(args.liste) if args.liste else {}
    stats = {"declarations": 0, "types": {}, "dsp_ignorees": 0, "sections_neant": 0, "rows": 0}
    seen = [] if args.declarations_out else None
    with open(args.output, "w", newline="", encoding="utf-8") as out:
        w = csv.DictWriter(out, fieldnames=FIELDS)
        w.writeheader()
        depth = 0
        for event, el in ET.iterparse(args.xml, events=("start", "end")):
            if event == "start":
                depth += 1
                continue
            depth -= 1
            if local(el.tag).lower() != "declaration" or depth != 1:
                continue
            for row in rows_for(el, args.ministres_patrimoine, stats, seen):
                meta = liste.get((row["nom"].upper(), row["prenom"].upper()))
                if meta:
                    row["type_mandat"] = row["type_mandat"] or meta.get("type_mandat", "")
                    row["departement"] = row["departement"] or meta.get("departement", "")
                w.writerow(row)
                stats["rows"] += 1
            el.clear()
    if seen is not None:
        with open(args.declarations_out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=DECL_FIELDS)
            w.writeheader()
            w.writerows(seen)
    print(f"{stats['declarations']} déclarations lues, {stats['rows']} participations écrites "
          f"dans {args.output}", file=sys.stderr)
    print(f"types: {dict(sorted(stats['types'].items()))}", file=sys.stderr)
    print(f"DSP ignorées (non-ministres): {stats['dsp_ignorees']}, "
          f"sections « néant »: {stats['sections_neant']}", file=sys.stderr)


if __name__ == "__main__":
    main()
