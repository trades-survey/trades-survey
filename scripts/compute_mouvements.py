#!/usr/bin/env python3
"""Étape 2 : déduit les mouvements de positions entre déclarations successives.

Entrées :
  - participations.csv (ou participations_isin.csv) produit par l'étape 1
  - declarations.csv produit par extract_participations.py --declarations-out
    (indispensable : une déclaration sans participation fait « disparaître » les
    positions précédentes)

Pour chaque élu, on trie ses déclarations par date de dépôt, séparément pour les
déclarations d'intérêts et pour les DSP (ministres), qui ne listent pas les mêmes
choses. Chaque société est comparée d'une déclaration à la suivante.

Attention : ce sont des écarts entre deux déclarations, pas des transactions datées.

Usage :
  python3 -I compute_mouvements.py participations.csv declarations.csv -o mouvements.csv
"""
import argparse
import csv
import re
import sys
import unicodedata
from collections import defaultdict

INTEREST_TYPES = {"DI", "DIA", "DIM", "DIAM"}

FIELDS = [
    "prenom", "nom", "famille", "societe", "isin", "mouvement",
    "declaration_avant", "date_avant", "declaration_apres", "date_apres",
    "nb_parts_avant", "nb_parts_apres", "valeur_avant", "valeur_apres",
    "delta_parts", "delta_valeur",
]

LEGAL_FORMS = re.compile(r"\b(SA|SAS|SASU|SE|SCA|NV|PLC|AG|INC|GROUPE|GROUP)\b")


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().upper()
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = LEGAL_FORMS.sub(" ", s)
    return " ".join(s.split())


def famille(typ):
    return "interets" if typ.upper() in INTEREST_TYPES else "patrimoine"


def person_key(r):
    return (norm(r["nom"]), norm(r["prenom"]))


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def fmt(v):
    if v is None:
        return ""
    return int(v) if float(v).is_integer() else round(v, 2)


def holdings(rows):
    """Société -> position cumulée (plusieurs lignes d'une même société s'additionnent)."""
    out = {}
    for r in rows:
        key = r.get("isin") or norm(r["societe"])
        h = out.setdefault(key, {"societe": r["societe"], "isin": r.get("isin", ""),
                                 "parts": None, "valeur": None})
        for f, col in (("parts", "nb_parts"), ("valeur", "valeur_eur")):
            v = num(r.get(col))
            if v is not None:
                h[f] = (h[f] or 0) + v
    return out


def classify(a, b):
    if a is None:
        return "apparition"
    if b is None:
        return "disparition"
    for f in ("parts", "valeur"):  # le nombre de titres prime sur la valeur
        if a[f] is not None and b[f] is not None and a[f] != b[f]:
            return "hausse" if b[f] > a[f] else "baisse"
    return "inchange"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("participations")
    ap.add_argument("declarations")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--avec-inchanges", action="store_true", help="écrire aussi les positions inchangées")
    args = ap.parse_args(argv)

    with open(args.participations, newline="", encoding="utf-8") as fh:
        by_decl = defaultdict(list)
        masquees = 0
        for r in csv.DictReader(fh):
            # Nom occulté par la HATVP (« SCI [Données non publiées] ») : impossible de
            # suivre la même société d'une déclaration à l'autre, on l'écarte.
            if r.get("societe_masquee") == "oui":
                masquees += 1
                continue
            by_decl[r["declaration_id"]].append(r)

    timelines = defaultdict(list)  # (personne, famille) -> déclarations
    with open(args.declarations, newline="", encoding="utf-8") as fh:
        for d in csv.DictReader(fh):
            # Une déclaration modificative sans la section ne dit rien des participations :
            # on ne la compare pas, sinon tout apparaîtrait comme vendu.
            if d.get("section_presente", "oui") == "non":
                continue
            timelines[(person_key(d), famille(d["type_declaration"]))].append(d)

    counts = defaultdict(int)
    with open(args.output, "w", newline="", encoding="utf-8") as out:
        w = csv.DictWriter(out, fieldnames=FIELDS)
        w.writeheader()
        for (_, fam), decls in timelines.items():
            decls.sort(key=lambda d: (d["date_depot"], d["declaration_id"]))
            prev, prev_h = None, {}
            for d in decls:
                cur_h = holdings(by_decl.get(d["declaration_id"], []))
                for key in sorted(set(prev_h) | set(cur_h)):
                    a, b = prev_h.get(key), cur_h.get(key)
                    if prev is None:  # première déclaration : position initiale, pas un mouvement
                        mv = "position_initiale"
                    else:
                        mv = classify(a, b)
                    counts[mv] += 1
                    if mv == "inchange" and not args.avec_inchanges:
                        continue
                    ref = b or a
                    pa, pb = (a or {}).get("parts"), (b or {}).get("parts")
                    va, vb = (a or {}).get("valeur"), (b or {}).get("valeur")
                    w.writerow({
                        "prenom": d["prenom"], "nom": d["nom"], "famille": fam,
                        "societe": ref["societe"], "isin": ref["isin"], "mouvement": mv,
                        "declaration_avant": prev["declaration_id"] if prev else "",
                        "date_avant": prev["date_depot"] if prev else "",
                        "declaration_apres": d["declaration_id"], "date_apres": d["date_depot"],
                        "nb_parts_avant": fmt(pa), "nb_parts_apres": fmt(pb),
                        "valeur_avant": fmt(va), "valeur_apres": fmt(vb),
                        "delta_parts": fmt((pb or 0) - (pa or 0)) if prev and (pa is not None or pb is not None) else "",
                        "delta_valeur": fmt((vb or 0) - (va or 0)) if prev and (va is not None or vb is not None) else "",
                    })
                prev, prev_h = d, cur_h
    print(f"{masquees} lignes à nom occulté écartées", file=sys.stderr)
    print(f"{len(timelines)} historiques, mouvements : {dict(sorted(counts.items()))}", file=sys.stderr)


if __name__ == "__main__":
    main()
