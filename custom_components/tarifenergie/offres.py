"""Offres de marché : grilles tarifaires des fournisseurs en YAML (issues #5 et #6).

Chaque fichier ``offres/<id>.yaml`` décrit une offre d'électricité pour particuliers,
telle que publiée dans les grilles des fournisseurs (inventaire #6, une issue par
offre). Le moteur lit les offres **à prix fixe** et **indexées sur le TRV** (typologie
CRE), ainsi que les TRV locaux des ELD et les offres à option Week-end (postes
semaine / week-end : tarif week-end les samedis, dimanches et jours fériés
nationaux), ainsi que l'option Flex de Zen Week-End (jours Éco / Sobriété, #97 :
jours Sobriété estimés par les jours rouges Tempo de ``calendriers/tempo_rouge.yaml``) ;
les offres dynamiques (OctoTempo…) viendront plus tard avec leurs structures propres.

Format YAML (exemple complet : ``offres/la_bellenergie_prudence.yaml``) ::

    id: la_bellenergie_prudence          # doit être le nom du fichier, sans extension
    fournisseur: la bellenergie
    offre: Prudence
    type_prix: fixe                      # ou reglemente (TRV local d'une ELD : eld:, sans durée de fixité)
                                         # ou indexe_trv (suit le TRV : sans durée de fixité ni eld:)
                                         # ou revisable (« Autre offre » CRE : prix révisés par le
                                         # fournisseur, sans durée de fixité ni eld:)
    grille_du: 2026-08-01                 # date d'effet de la grille tarifaire
    duree_fixite_mois: 12
    source: https://…/grille.pdf         # fiche de référence (registre #27)
    options:
      base:
        abonnement_mensuel_ttc: {3: 11.63, 6: 15.36, …}     # € TTC/mois par puissance
        kwh_ttc_par_puissance: {3: {base: 0.1968}, …}         # c'→€ TTC/kWh par poste
      hphc:                              # option facultative (jamais en 3 kVA au TRV)
        abonnement_mensuel_ttc: {6: 15.36, …}
        kwh_ttc: {hp: 0.2106, hc: 0.1565}                     # prix uniforme
        # ou abonnement_annuel_ttc: {6: 190.36, …} pour une grille publiée en €/an
      week_end:                          # option « Week-end » (ex. ÉS Énergies, #330)
        abonnement_mensuel_ttc: {3: 12.13, …}
        kwh_ttc: {semaine: 0.31108, week_end: 0.22878}         # les deux postes exigés
      flex:                              # option Flex de Zen Week-End (#97) : jours Éco / Sobriété
        abonnement_mensuel_ttc: {6: 15.86, …}
        plages_hc: "13:00-18:00, 20:00-08:00"                  # heures creuses imposées par l'offre
        kwh_ttc: {eco_hp: 0.2142, eco_hc: 0.1595, sobriete_hp: 0.7467, sobriete_hc: 0.2142}

Les prix sont TTC, en €/kWh (les grilles des fournisseurs sont en c€ TTC/kWh).
L'abonnement mensuel est converti en €/an (multiplié par 12, en ``Decimal`` exact) ;
``abonnement_annuel_ttc`` (grilles publiées en €/an) est repris tel quel. Les
puissances non listées par une offre la rendent « indisponible » pour l'utilisateur
concerné, avec la raison, comme pour les options du TRV.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from .calcul import PlagesHC
from .const import PUISSANCES
from .modele import Grille, Grilles, Saison

_LOGGER = logging.getLogger(__name__)

DOSSIER_OFFRES = Path(__file__).parent / "offres"
# « reglemente » : TRV local d'une entreprise locale de distribution (ELD) —
# barème national, abonnement propre au réseau ; pas de durée de fixité (le
# prix suit les mouvements du TRV), identifiant de réseau ``eld`` exigé.
# « indexe_trv » : offre de marché indexée sur le TRV (typologie CRE) — prix HT
# alignés sur le TRV ou à remise constante ; comme un TRV local, pas de durée de
# fixité et une grille TTC datée à mettre à jour à chaque mouvement du TRV, mais
# sans réseau ``eld``.
# « revisable » : « Autre offre » de la typologie CRE (#18) — prix de marché que le
# fournisseur révise à date fixe (EDF Vert Électrique Régional : 2 fois par an) sans
# suivre le TRV ; pas de durée de fixité ni de réseau ``eld``, grille TTC datée à
# mettre à jour à chaque révision.
TYPE_PRIX: tuple[str, ...] = ("fixe", "reglemente", "indexe_trv", "revisable")
SANS_FIXITE: tuple[str, ...] = ("reglemente", "indexe_trv", "revisable")
POSTES = (
    "base",
    "hp",
    "hc",
    "semaine",
    "week_end",
    "jour_choisi",
    "semaine_hp",
    "semaine_hc",
    "week_end_hp",
    "week_end_hc",
    "jour_choisi_hp",
    "jour_choisi_hc",
    # Postes saisonniers des offres été/hiver (Zen Estival, #20) ou à plages
    # constantes toute l'année (Charge'Heures, #24) : le préfixe est la saison,
    # portée par la grille avec ses plages (cf. ``_saisons``).
    "ete_hsc",
    "ete_hc",
    "ete_hp",
    "hiver_hc",
    "hiver_hp",
    "annee_hsc",
    "annee_hc",
    "annee_hp",
    # Option Flex de Zen Week-End (#97) : jours Éco et jours Sobriété, chacun en HP/HC.
    "eco_hp",
    "eco_hc",
    "sobriete_hp",
    "sobriete_hc",
)
MOIS_PAR_AN = Decimal("12")

# Options à postes imposés : l'option exige exactement cet ensemble de postes
# (« week_end » : #330 ; « week_end_hphc » : week-end ET heures creuses, #331).
POSTES_PAR_OPTION: dict[str, tuple[frozenset[str], str]] = {
    "week_end": (frozenset({"semaine", "week_end"}), "semaine+week_end attendus (option week_end)"),
    "week_end_hphc": (
        frozenset({"semaine_hp", "semaine_hc", "week_end_hp", "week_end_hc"}),
        "semaine_hp+semaine_hc+week_end_hp+week_end_hc attendus (option week_end_hphc)",
    ),
    # Option Flex (#97) : 345 jours Éco, 20 jours Sobriété (estimés par les jours rouges Tempo).
    "flex": (
        frozenset({"eco_hp", "eco_hc", "sobriete_hp", "sobriete_hc"}),
        "eco_hp+eco_hc+sobriete_hp+sobriete_hc attendus (option flex)",
    ),
}

# Jour de semaine du « jour choisi » des offres Zen Week-End Plus (#10, #116) :
# le client choisit lundi, mercredi ou vendredi, et le moteur simule les trois
# variantes (une clé de comparaison par jour choisi).
JOUR_CHOISI: dict[str, int] = {
    "week_end_jour_lundi": 0,
    "week_end_jour_mercredi": 2,
    "week_end_jour_vendredi": 4,
    "week_end_hphc_jour_lundi": 0,
    "week_end_hphc_jour_mercredi": 2,
    "week_end_hphc_jour_vendredi": 4,
}
POSTES_PAR_OPTION.update(
    (option, (frozenset({"semaine", "week_end", "jour_choisi"}), "semaine+week_end+jour_choisi attendus"))
    for option in ("week_end_jour_lundi", "week_end_jour_mercredi", "week_end_jour_vendredi")
)
POSTES_PAR_OPTION.update(
    (
        option,
        (
            frozenset(
                {"semaine_hp", "semaine_hc", "week_end_hp", "week_end_hc", "jour_choisi_hp", "jour_choisi_hc"}
            ),
            "semaine_hp+semaine_hc+week_end_hp+week_end_hc+jour_choisi_hp+jour_choisi_hc attendus",
        ),
    )
    for option in ("week_end_hphc_jour_lundi", "week_end_hphc_jour_mercredi", "week_end_hphc_jour_vendredi")
)


class OffreInvalide(ValueError):
    """L'offre ne respecte pas le schéma. Le message donne le chemin de la valeur fautive."""


def _exiger(condition: bool, chemin: str, message: str) -> None:
    _LOGGER.debug("_exiger: entrée")
    if not condition:
        _LOGGER.debug("_exiger: lève une exception")
        raise OffreInvalide(f"{chemin} : {message}")
    _LOGGER.debug("_exiger: fin")


def _texte(d: dict[str, Any], cle: str, chemin: str) -> str:
    _LOGGER.debug("_texte: entrée")
    _exiger(isinstance(d.get(cle), str) and d[cle].strip() != "", chemin + f".{cle}", "texte attendu")
    _LOGGER.debug("_texte: sortie")
    return d[cle]


def _decimal(valeur: Any, chemin: str) -> Decimal:
    _LOGGER.debug("_decimal: entrée")
    _exiger(
        isinstance(valeur, (int, float)) and not isinstance(valeur, bool) and valeur > 0,
        chemin,
        "nombre positif attendu (€ TTC, c€ TTC/kWh convertis en €)",
    )
    _LOGGER.debug("_decimal: sortie")
    return Decimal(str(valeur))


def _puissances(d: dict[str, Any], chemin: str) -> dict[int, Decimal]:
    """Mapping puissance (kVA) → abonnement (€ TTC/an).

    ``abonnement_mensuel_ttc`` (multiplié par 12) ou ``abonnement_annuel_ttc``
    (tel quel, pour les grilles publiées en €/an : diviser par 12 ne tombe pas
    juste, ex. GEDIA 190,36 €/an), exclusifs.
    """
    _LOGGER.debug("_puissances: entrée")
    _exiger(
        not ("abonnement_mensuel_ttc" in d and "abonnement_annuel_ttc" in d),
        chemin,
        "abonnement_mensuel_ttc et abonnement_annuel_ttc sont exclusifs",
    )
    champ, facteur = (
        ("abonnement_annuel_ttc", Decimal(1))
        if "abonnement_annuel_ttc" in d
        else ("abonnement_mensuel_ttc", MOIS_PAR_AN)
    )
    brutes = d.get(champ)
    _exiger(isinstance(brutes, dict) and brutes != {}, f"{chemin}.{champ}", "mapping attendu")
    puissances: dict[int, Decimal] = {}
    for puissance, montant in brutes.items():
        _exiger(
            isinstance(puissance, int) and not isinstance(puissance, bool) and puissance in PUISSANCES,
            f"{chemin}.{champ}",
            f"puissance inconnue : {puissance} (attendues : {', '.join(map(str, PUISSANCES))} kVA)",
        )
        puissances[puissance] = _decimal(montant, f"{chemin}.{champ}[{puissance}]") * facteur
    _LOGGER.debug("_puissances: %s", puissances)
    return puissances


def _postes(d: dict[str, Any], chemin: str) -> dict[str, Decimal]:
    """Mapping poste (base / hp / hc / semaine / week_end) → prix € TTC/kWh."""
    _LOGGER.debug("_postes: entrée")
    brutes = d.get("kwh_ttc")
    _exiger(isinstance(brutes, dict) and brutes != {}, chemin + ".kwh_ttc", "mapping attendu")
    postes: dict[str, Decimal] = {}
    for poste, prix in brutes.items():
        _exiger(poste in POSTES, f"{chemin}.kwh_ttc", f"poste inconnu : {poste}")
        postes[poste] = _decimal(prix, f"{chemin}.kwh_ttc[{poste}]")
    _LOGGER.debug("_postes: %s", postes)
    return postes


def _exiger_postes(prix: dict[str, Decimal], option: str, chemin: str) -> None:
    """Postes d'une option : ensemble imposé pour week_end/week_end_hphc, sinon base ou hp+hc."""
    _LOGGER.debug("_exiger_postes: entrée")
    if option in POSTES_PAR_OPTION:
        attendus, message = POSTES_PAR_OPTION[option]
        _exiger(set(prix) == attendus, chemin, message)
    else:
        _exiger(
            set(prix) <= {"base"} or set(prix) == {"hp", "hc"},
            chemin,
            "base OU hp+hc attendus",
        )
    _LOGGER.debug("_exiger_postes: fin")


def _jour_annee(texte: str, chemin: str) -> tuple[int, int]:
    """« 04-15 » → (4, 15) : borne de saison en mois/jour (issue #20)."""
    _LOGGER.debug("_jour_annee: entrée")
    _exiger(isinstance(texte, str) and re.match(r"^\d{2}-\d{2}$", texte), chemin, "attendu : MM-JJ")
    mois, jour = (int(x) for x in texte.split("-"))
    _exiger(1 <= mois <= 12 and 1 <= jour <= 31, chemin, "mois ou jour impossible")
    _LOGGER.debug("_jour_annee: %s-%s", mois, jour)
    return mois, jour


def _plages_saison(
    donnees: dict[str, Any], cle: str, chemin: str, exigees: bool
) -> tuple[tuple[int, int], ...]:
    """Plages HSC/HC d'une saison : texte ``PlagesHC`` validé, en minutes."""
    _LOGGER.debug("_plages_saison: entrée")
    texte = donnees.get(cle)
    if texte is None:
        _exiger(not exigees, chemin, f"plages {cle} attendues")
        _LOGGER.debug("_plages_saison: vide")
        return ()
    _exiger(isinstance(texte, str) and texte.strip() != "", chemin, "texte de plages attendu")
    plages = PlagesHC.lire(texte).plages
    _LOGGER.debug("_plages_saison: %s plage(s)", len(plages))
    return plages


def _saisons(donnees: dict[str, Any], chemin: str) -> tuple[tuple[Saison, ...], dict[str, Decimal]]:
    """Saisons d'une offre à postes et plages portées par l'offre (#20, #24).

    Deux formes : été+hiver (postes saisonniers, ex. Zen Estival) ou une saison
    unique ``annee`` pour des plages constantes toute l'année (ex. Charge'Heures).
    Chaque saison exige hc et hp, plus hsc facultatif ; les HSC et HC d'une
    saison ne se chevauchent pas. Les saisons doivent partitionner l'année
    (aucun jour hors saison, aucun doublon).
    """
    _LOGGER.debug("_saisons: entrée")
    saisons_brutes = donnees.get("saisons")
    _exiger(
        isinstance(saisons_brutes, dict)
        and (set(saisons_brutes) == {"ete", "hiver"} or set(saisons_brutes) == {"annee"}),
        f"{chemin}.saisons",
        "saisons ete+hiver attendues, ou annee seule (plages constantes)",
    )
    saisons: list[Saison] = []
    prix: dict[str, Decimal] = {}
    for nom in saisons_brutes:
        saison = saisons_brutes[nom]
        chemin_saison = f"{chemin}.saisons.{nom}"
        _exiger(isinstance(saison, dict), chemin_saison, "mapping attendu")
        debut = _jour_annee(saison.get("du"), f"{chemin_saison}.du")
        fin = _jour_annee(saison.get("au"), f"{chemin_saison}.au")
        _exiger(debut != fin, chemin_saison, "saison vide (du == au)")
        brutes = saison.get("kwh_ttc")
        _exiger(
            isinstance(brutes, dict) and {"hc", "hp"} <= set(brutes) <= {"hsc", "hc", "hp"},
            f"{chemin_saison}.kwh_ttc",
            "postes attendus : hc et hp, plus hsc facultatif",
        )
        hsc = _plages_saison(saison.get("plages", {}), "hsc", f"{chemin_saison}.plages", "hsc" in brutes)
        hc = _plages_saison(saison.get("plages", {}), "hc", f"{chemin_saison}.plages", True)
        intervalles_hsc = sorted(PlagesHC(plages=hsc)._intervalles())
        intervalles_hc = sorted(PlagesHC(plages=hc)._intervalles())
        _exiger(
            not any(
                hsc_d < hc_f and hc_d < hsc_f
                for hsc_d, hsc_f in intervalles_hsc
                for hc_d, hc_f in intervalles_hc
            ),
            f"{chemin_saison}.plages",
            "les plages HSC et HC ne doivent pas se chevaucher",
        )
        saisons.append(Saison(nom, debut, fin, hsc, hc))
        for poste in brutes:
            prix[f"{nom}_{poste}"] = _decimal(brutes[poste], f"{chemin_saison}.kwh_ttc[{poste}]")
    _exiger(
        _saisons_couvre_annee(tuple(saisons)),
        f"{chemin}.saisons",
        "les saisons doivent partitionner l'année (chaque jour dans exactement une saison)",
    )
    _LOGGER.debug("_saisons: %s saison(s)", len(saisons))
    return tuple(saisons), prix


def _saisons_couvre_annee(saisons: tuple[Saison, ...]) -> bool:
    """Chaque jour d'une année bissextile tombe dans exactement une saison."""
    _LOGGER.debug("_saisons_couvre_annee: entrée")
    vues: set[tuple[int, int]] = set()
    for jour in (date(2024, 1, 1) + timedelta(days=n) for n in range(366)):
        couvertes = [s for s in saisons if s.couvre(jour)]
        if len(couvertes) != 1:
            _LOGGER.debug("_saisons_couvre_annee: %s couvert(s) le %s", len(couvertes), jour)
            return False
        vues.add((jour.month, jour.day))
    _LOGGER.debug("_saisons_couvre_annee: %s", len(vues) == 366)
    return len(vues) == 366


def _plages_offre(donnees: dict[str, Any], chemin: str, option: str) -> tuple[tuple[int, int], ...] | None:
    """Heures creuses imposées par l'offre (``plages_hc``) : exigées par l'option Flex, refusées ailleurs."""
    _LOGGER.debug("_plages_offre: entrée")
    if option != "flex":
        _exiger("plages_hc" not in donnees, f"{chemin}.plages_hc", "réservé à l'option flex")
        _LOGGER.debug("_plages_offre: sans objet")
        return None
    plages = _plages_saison(donnees, "plages_hc", chemin, True)
    _LOGGER.debug("_plages_offre: %s plage(s)", len(plages))
    return plages


def _grilles_option(
    donnees: dict[str, Any],
    chemin: str,
    cles: tuple[str, ...],
    debut: date,
    option: str = "",
    jour_choisi: int | None = None,
) -> dict[int, Grille]:
    """Grilles d'une option de l'offre : abonnements mensuels x12, prix par poste.

    Les options « week_end » et « week_end_hphc » exigent leurs postes exacts
    (cf. ``POSTES_PAR_OPTION``) ; les autres (« base », « hphc ») : base seul
    ou hp + hc. ``jour_choisi`` (lundi/mercredi/vendredi des offres à jour
    choisi, #10/#116) est porté par la grille pour le moteur de calcul.
    """
    _LOGGER.debug("_grilles_option: entrée")
    abonnements = _puissances(donnees, chemin)
    plages_hc = _plages_offre(donnees, chemin, option)
    grilles: dict[int, Grille] = {}
    if "kwh_ttc_par_puissance" in donnees:
        _exiger("kwh_ttc" not in donnees, chemin, "kwh_ttc et kwh_ttc_par_puissance sont exclusifs")
        par_puissance = donnees["kwh_ttc_par_puissance"]
        _exiger(isinstance(par_puissance, dict) and par_puissance != {}, chemin, "mapping attendu")
        for puissance, postes in par_puissance.items():
            _exiger(
                puissance in abonnements,
                f"{chemin}[{puissance}]",
                "prix donné sans abonnement à cette puissance",
            )
            _exiger(isinstance(postes, dict) and postes != {}, f"{chemin}[{puissance}]", "postes attendus")
            prix: dict[str, Decimal] = {}
            for poste, montant in postes.items():
                _exiger(poste in POSTES, f"{chemin}[{puissance}]", f"poste inconnu : {poste}")
                prix[poste] = _decimal(montant, f"{chemin}[{puissance}].{poste}")
            _exiger_postes(prix, option, f"{chemin}[{puissance}]")
            grilles[puissance] = Grille(
                cles, puissance, debut, None, abonnements[puissance], prix, jour_choisi, plages_hc=plages_hc
            )
    else:
        prix_uniforme = _postes(donnees, chemin)
        _exiger_postes(prix_uniforme, option, chemin)
        for puissance, abonnement in abonnements.items():
            grilles[puissance] = Grille(
                cles, puissance, debut, None, abonnement, prix_uniforme, jour_choisi, plages_hc=plages_hc
            )
    _LOGGER.debug("_grilles_option: %s grille(s)", len(grilles))
    return grilles


def _grilles_saisonniere(
    donnees: dict[str, Any], chemin: str, cles: tuple[str, ...], debut: date
) -> dict[int, Grille]:
    """Grilles d'une option à postes saisonniers (#20) : abonnement unique, prix par saison."""
    _LOGGER.debug("_grilles_saisonniere: entrée")
    abonnements = _puissances(donnees, chemin)
    saisons, prix = _saisons(donnees, chemin)
    grilles = {
        puissance: Grille(cles, puissance, debut, None, abonnement, dict(prix), None, saisons)
        for puissance, abonnement in abonnements.items()
    }
    _LOGGER.debug("_grilles_saisonniere: %s grille(s)", len(grilles))
    return grilles


@dataclass(frozen=True)
class Offre:
    """Une offre (prix fixe, indexée sur le TRV ou TRV local d'une ELD), convertie en grilles par option."""

    id: str
    fournisseur: str
    offre: str
    grille_du: date
    duree_fixite_mois: int | None  # None si le prix suit le TRV (« reglemente », « indexe_trv »)
    grilles: dict[str, Grilles]  # option du TRV ("base", "hphc") → Grilles
    type_prix: str = "fixe"
    eld: str | None = None  # réseau de l'ELD, pour un TRV local

    def cles(self) -> list[str]:
        """Clés de comparaison : ``<id>:<option>`` (ex. ``la_bellenergie_prudence:hphc``)."""
        _LOGGER.debug("Offre.cles: entrée")
        _LOGGER.debug("Offre.cles: sortie")
        return [f"{self.id}:{option}" for option in sorted(self.grilles)]


def offre_depuis_dict(donnees: Any, ident: str) -> Offre:
    """Valide le contenu d'un fichier d'offre et le convertit en grilles."""
    _LOGGER.debug("offre_depuis_dict: entrée")
    _exiger(isinstance(donnees, dict), "offre", "mapping attendu")
    _exiger(donnees.get("id") == ident, "offre.id", f"doit valoir « {ident} » (nom du fichier)")
    _exiger(
        ":" not in ident,
        "offre.id",
        "le caractère « : » est réservé aux clés de comparaison « <id>:<option> »",
    )
    _exiger(donnees.get("type_prix") in TYPE_PRIX, "offre.type_prix", f"attendu : {', '.join(TYPE_PRIX)}")
    type_prix = donnees["type_prix"]
    duree = donnees.get("duree_fixite_mois")
    eld = None
    if type_prix in SANS_FIXITE:
        _exiger(
            duree is None,
            "offre.duree_fixite_mois",
            "sans objet quand le prix suit le TRV ou est révisable",
        )
        if type_prix == "reglemente":
            eld = _texte(donnees, "eld", "offre")
        else:
            _exiger("eld" not in donnees, "offre.eld", "réservé aux TRV locaux (type_prix « reglemente »)")
    else:
        _exiger(
            isinstance(duree, int) and not isinstance(duree, bool) and duree > 0,
            "offre.duree_fixite_mois",
            "entier positif attendu",
        )
    _exiger(
        donnees.get("grille_du") is not None and hasattr(donnees["grille_du"], "isoformat"),
        "offre.grille_du",
        "date attendue (YYYY-MM-DD)",
    )
    _texte(donnees, "source", "offre.source")
    options = donnees.get("options")
    # Au moins une option sans heures creuses (la « Base » de l'offre) : base,
    # week_end, une variante à jour choisi (#10) ou des postes saisonniers
    # (#20 : les plages HSC/HC sont portées par l'offre, pas par le compteur —
    # un client sans heures creuses y est simulable aussi) ; hphc/week_end_hphc
    # seules ne permettraient aucun comparatif pour un client sans heures creuses.
    _exiger(
        isinstance(options, dict)
        and set(options)
        <= {"base", "hphc", "week_end", "week_end_hphc", "hphc_saisonnieres", "flex", *JOUR_CHOISI}
        and set(options)
        & {
            "base",
            "week_end",
            "week_end_jour_lundi",
            "week_end_jour_mercredi",
            "week_end_jour_vendredi",
            "hphc_saisonnieres",
        },
        "offre.options",
        "option Base attendue (base, week_end, week_end_jour_* ou hphc_saisonnieres) ;"
        " les autres sont facultatives",
    )
    grilles: dict[str, Grilles] = {}
    for option in ("base", "hphc", "week_end", "week_end_hphc", "hphc_saisonnieres", "flex", *JOUR_CHOISI):
        if option not in options:
            continue
        if option == "hphc_saisonnieres":
            grilles_saison = _grilles_saisonniere(
                options[option], f"offre.options.{option}", f"{ident}:{option}", donnees["grille_du"]
            )
            _exiger(grilles_saison != {}, f"offre.options.{option}", "aucune puissance définie")
            grilles[option] = Grilles(tuple(grilles_saison[p] for p in sorted(grilles_saison)))
            continue
        grilles_option = _grilles_option(
            options[option],
            f"offre.options.{option}",
            f"{ident}:{option}",
            donnees["grille_du"],
            option,
            JOUR_CHOISI.get(option),
        )
        _exiger(grilles_option != {}, f"offre.options.{option}", "aucune puissance définie")
        grilles[option] = Grilles(tuple(grilles_option[p] for p in sorted(grilles_option)))
    _LOGGER.debug("offre_depuis_dict: sortie")
    return Offre(
        _texte(donnees, "id", "offre"),
        _texte(donnees, "fournisseur", "offre"),
        _texte(donnees, "offre", "offre"),
        donnees["grille_du"],
        duree,
        grilles,
        type_prix,
        eld,
    )


def charger_offre(chemin: Path) -> Offre:
    """Lit et valide un fichier YAML du dossier ``offres/``."""
    _LOGGER.debug("charger_offre: entrée")
    try:
        donnees = yaml.safe_load(chemin.read_text(encoding="utf-8"))
    except yaml.YAMLError as err:
        _LOGGER.debug("charger_offre: %s : %s", type(err).__name__, err)
        _LOGGER.debug("charger_offre: lève une exception")
        raise OffreInvalide(f"{chemin.name} : YAML invalide ({err})") from None
    except (OSError, UnicodeDecodeError) as err:
        _LOGGER.debug("charger_offre: %s : %s", type(err).__name__, err)
        _LOGGER.debug("charger_offre: lève une exception")
        raise OffreInvalide(f"{chemin.name} : fichier illisible ({err})") from None
    try:
        _LOGGER.debug("charger_offre: sortie")
        return offre_depuis_dict(donnees, chemin.stem)
    except OffreInvalide as err:
        _LOGGER.debug("charger_offre: %s : %s", type(err).__name__, err)
        _LOGGER.debug("charger_offre: lève une exception")
        raise OffreInvalide(f"{chemin.name} : {err}") from None


def lire_offres(dossier: Path = DOSSIER_OFFRES) -> dict[str, Offre]:
    """Toutes les offres livrées avec l'intégration, indexées par identifiant."""
    _LOGGER.debug("lire_offres: entrée")
    offres: dict[str, Offre] = {}
    for chemin in sorted(dossier.glob("*.yaml")):
        offre = charger_offre(chemin)
        offres[offre.id] = offre
    _LOGGER.debug("lire_offres: %s offre(s) %s", len(offres), sorted(offres))
    return offres


def grilles_offres(offres: dict[str, Offre]) -> dict[str, Grilles]:
    """Grilles de toutes les offres, indexées par clé de comparaison ``<id>:<option>``."""
    _LOGGER.debug("grilles_offres: entrée")
    resultats: dict[str, Grilles] = {}
    for offre in offres.values():
        for option, grilles in offre.grilles.items():
            resultats[f"{offre.id}:{option}"] = grilles
    _LOGGER.debug("grilles_offres: %s grille(s) %s", len(resultats), sorted(resultats))
    return resultats
