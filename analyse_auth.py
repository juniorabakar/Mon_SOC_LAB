#!/usr/bin/env python3

"""Compte le nombre d'échecs d'authentification par IP dans un journal"""

import re
import sys
from collections import Counter

MOTIF = re.compile(r"Failed password for .* from (\d+\.\d+\.\d+\.\d+)")

def analyser(chemin,seuil=5):
    compteur = Counter()
    with open(chemin) as f:
        for ligne in f:
            trouve = MOTIF.search(ligne)
            if trouve:
                compteur[trouve.group(1)] +=1

    return {ip: n for ip, n in compteur.items() if n >=seuil}

if __name__ == "__main__":
    for ip, n in sorted(analyser(sys.argv[1]).items(), key=lambda x : -x[1]):
        print(f"{ip:16} {n} echecs")
