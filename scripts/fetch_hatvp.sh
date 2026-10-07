#!/usr/bin/env bash
# Télécharge l'open data HATVP (licence Etalab) dans data/raw/.
set -euo pipefail
cd "$(dirname "$0")/../data/raw"
curl -fSL --retry 3 -o liste.csv https://www.hatvp.fr/livraison/opendata/liste.csv
curl -fSL --retry 3 -o declarations.xml https://www.hatvp.fr/livraison/merge/declarations.xml
ls -la
