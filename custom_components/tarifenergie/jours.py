"""Jours de week-end des offres « Week-end » : samedi, dimanche et jours fériés nationaux.

Définition retenue par les grilles des fournisseurs (ex. ÉS Énergies, issue
#330) : le tarif week-end s'applique les samedis, dimanches et jours fériés
nationaux français — les 11 jours fériés légaux, fêtes mobiles calculées par
l'algorithme grégorien anonyme (les deux jours supplémentaires d'Alsace-
Moselle ne sont pas nationaux).

Python pur : aucun import Home Assistant (testable seul).
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

_LOGGER = logging.getLogger(__name__)


def paques(annee: int) -> date:
    """Dimanche de Pâques (algorithme grégorien anonyme), base des fêtes mobiles."""
    _LOGGER.debug("paques: entrée")
    a = annee % 19
    b, c = divmod(annee, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    ll = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ll) // 451
    mois, jour = divmod(h + ll - 7 * m + 114, 31)
    _LOGGER.debug("paques: sortie")
    return date(annee, mois, jour + 1)


def jours_feries(annee: int) -> frozenset[date]:
    """Les 11 jours fériés nationaux français de ``annee`` (fixes et mobiles)."""
    _LOGGER.debug("jours_feries: entrée")
    dimanche_paques = paques(annee)
    fixes = (
        date(annee, 1, 1),  # Jour de l'An
        date(annee, 5, 1),  # Fête du Travail
        date(annee, 5, 8),  # Victoire 1945
        date(annee, 7, 14),  # Fête nationale
        date(annee, 8, 15),  # Assomption
        date(annee, 11, 1),  # Toussaint
        date(annee, 11, 11),  # Armistice 1918
        date(annee, 12, 25),  # Noël
    )
    mobiles = (
        dimanche_paques + timedelta(days=1),  # lundi de Pâques
        dimanche_paques + timedelta(days=39),  # Ascension
        dimanche_paques + timedelta(days=50),  # lundi de Pentecôte
    )
    resultat = frozenset((*fixes, *mobiles))
    _LOGGER.debug("jours_feries: %s jour(s) férié(s) en %s", len(resultat), annee)
    return resultat


def est_week_end(jour: date) -> bool:
    """Samedi, dimanche ou jour férié national (définition des offres « Week-end »)."""
    _LOGGER.debug("est_week_end: entrée")
    resultat = jour.weekday() >= 5 or jour in jours_feries(jour.year)
    _LOGGER.debug("est_week_end: sortie")
    return resultat
