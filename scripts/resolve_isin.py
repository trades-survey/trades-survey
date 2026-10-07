#!/usr/bin/env python3
"""Ajoute l'ISIN aux participations quand la société est cotée.

Rapproche le nom déclaré d'un référentiel (nom;isin), par exemple l'export des
valeurs cotées d'Euronext (https://live.euronext.com/fr/products/equities/list).
Le rapprochement se fait sur un nom normalisé (forme juridique, accents et
ponctuation retirés). Les noms ambigus ou non cotés (SCI, SARL...) restent vides.

Usage :
  python3 -I resolve_isin.py participations.csv referentiel.csv -o participations_isin.csv
"""
import argparse
import csv
import re
import unicodedata

LEGAL = r"\b(s\.?a\.?s?\.?u?|se|sca|nv|plc|ag|group(e)?|holding|ord|actions?|titres?|sa)\b"


def norm(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(LEGAL, " ", s)
    return " ".join(s.split())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("participations")
    ap.add_argument("referentiel", help="CSV avec colonnes name/nom et isin (séparateur auto)")
    ap.add_argument("-o", "--output", required=True)
    a = ap.parse_args()
    with open(a.referentiel, newline="", encoding="utf-8-sig") as fh:
        sample = fh.read(4096)
        fh.seek(0)
        rd = csv.DictReader(fh, dialect=csv.Sniffer().sniff(sample, ";,\t"))
        ref = {}
        for r in rd:
            r = {k.lower().strip(): (v or "").strip() for k, v in r.items() if k}
            name, isin = r.get("name") or r.get("nom", ""), r.get("isin", "")
            if name and re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}\d", isin):
                ref.setdefault(norm(name), set()).add(isin)
    hit = total = 0
    with open(a.participations, newline="", encoding="utf-8") as fi, \
            open(a.output, "w", newline="", encoding="utf-8") as fo:
        rd = csv.DictReader(fi)
        w = csv.DictWriter(fo, fieldnames=rd.fieldnames)
        w.writeheader()
        for r in rd:
            total += 1
            isins = ref.get(norm(r["societe"]), set())
            if len(isins) == 1:
                r["isin"] = next(iter(isins))
                hit += 1
            w.writerow(r)
    print(f"ISIN trouvé pour {hit}/{total} lignes")


if __name__ == "__main__":
    main()
