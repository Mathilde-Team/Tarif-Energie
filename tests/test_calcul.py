"""Moteur : heures creuses, prix du jour, abonnement au jour, classement."""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from custom_components.tarifenergie.calcul import (
    PlagesHC,
    PlagesInvalides,
    comparer,
    cout_option,
    heures_locales,
)
from custom_components.tarifenergie.modele import Grille, Grilles


def _grilles(option: str, prix: dict[str, str], abonnement: str = "365") -> Grilles:
    """Deux grilles fictives : prix doublés à partir du 01/08/2026."""
    p1 = {k: Decimal(v) for k, v in prix.items()}
    p2 = {k: v * 2 for k, v in p1.items()}
    return Grilles(
        [
            Grille(option, 6, date(2026, 1, 1), date(2026, 7, 31), Decimal(abonnement), p1),
            Grille(option, 6, date(2026, 8, 1), None, Decimal(abonnement) * 2, p2),
        ]
    )


class TestPlages:
    def test_lecture_et_minuit(self):
        p = PlagesHC.lire("22:00-06:00")
        assert p.minutes_par_jour() == 8 * 60
        assert [p.fraction_hc(h) for h in (21, 22, 23, 0, 5, 6)] == [0, 1, 1, 1, 1, 0]
        assert p.texte() == "22:00-06:00"

    def test_demi_heures_et_plusieurs_plages(self):
        p = PlagesHC.lire("23h30-07h30 ; 13:00-14:00")
        assert p.fraction_hc(23) == Decimal("0.5")
        assert p.fraction_hc(7) == Decimal("0.5")
        assert p.fraction_hc(13) == 1
        assert p.minutes_par_jour() == 9 * 60
        assert p.texte() == "23:30-07:30, 13:00-14:00"

    def test_jusqu_a_minuit(self):
        p = PlagesHC.lire("20:00-24:00, 00:00-04:00")
        assert p.minutes_par_jour() == 8 * 60
        assert p.fraction_hc(23) == 1

    @pytest.mark.parametrize(
        "texte",
        [
            "",
            " , ",
            "22-06",
            "25:00-06:00",
            "22:00-24:30",
            "22:61-06:00",
            "06:00-06:00",
            "00:00-24:00",
            "22:00-06:00, 23:00-01:00",
            "01:00-03:00, 02:00-04:00",
        ],
    )
    def test_refus(self, texte):
        with pytest.raises(PlagesInvalides):
            PlagesHC.lire(texte)


def test_base_prix_du_jour_et_abonnement():
    grilles = _grilles("base", {"base": "0.10"})
    conso = [(datetime(2026, 7, 31, 12), 10.0), (datetime(2026, 8, 1, 12), 10.0)]
    cout = cout_option("base", grilles, 6, conso)
    # 10 kWh à 0,10 puis 10 kWh à 0,20 ; abonnement 365 €/an puis 730 €/an : 1 € + 2 €.
    assert cout.energie == Decimal("3.00")
    assert cout.abonnement == Decimal(3)
    assert cout.total == Decimal("6.00")
    assert cout.kwh == {"base": Decimal(20)}
    assert cout.arrondi()["grilles"] == ["2026-01-01", "2026-08-01"]


def test_hphc_repartition_au_prorata():
    grilles = _grilles("hphc", {"hp": "0.20", "hc": "0.10"})
    plages = PlagesHC.lire("23:30-07:30")
    conso = [(datetime(2026, 3, 1, 23), 2.0), (datetime(2026, 3, 1, 12), 1.0), (datetime(2026, 3, 1, 3), 0.0)]
    cout = cout_option("hphc", grilles, 6, conso, plages)
    assert cout.kwh == {"hc": Decimal(1), "hp": Decimal(2)}
    assert cout.energie == Decimal("0.50")
    assert cout.abonnement == Decimal(1)  # un seul jour


def test_week_end_repartition():
    """Option Week-end : kWh au tarif week-end le samedi/dimanche/jour férié, sinon semaine."""
    grilles = Grilles(
        [
            Grille(
                "es_verte_fixe_1an:week_end",
                6,
                date(2026, 1, 1),
                None,
                Decimal(0),
                {"semaine": Decimal("0.31108"), "week_end": Decimal("0.22878")},
            )
        ]
    )
    conso = [
        (datetime(2026, 10, 24, 12), 1.0),  # samedi
        (datetime(2026, 10, 28, 12), 1.0),  # mercredi
        (datetime(2026, 5, 14, 12), 1.0),  # Ascension, jeudi férié
    ]
    cout = cout_option("es_verte_fixe_1an:week_end", grilles, 6, conso)
    assert cout.kwh == {"semaine": Decimal(1), "week_end": Decimal(2)}
    assert cout.energie == Decimal("0.31108") + 2 * Decimal("0.22878")


def test_week_end_hphc_repartition():
    """Week-end ET heures creuses (#331) : postes croisés, HC du point de livraison aussi le week-end."""
    grilles = Grilles(
        [
            Grille(
                "es_verte_fixe_1an:week_end_hphc",
                6,
                date(2026, 1, 1),
                None,
                Decimal(0),
                {
                    "semaine_hp": Decimal("0.32357"),
                    "semaine_hc": Decimal("0.23752"),
                    "week_end_hp": Decimal("0.23752"),
                    "week_end_hc": Decimal("0.23752"),
                },
            )
        ]
    )
    conso = [
        (datetime(2026, 10, 23, 23), 1.0),  # vendredi 23 h : heures creuses, semaine
        (datetime(2026, 10, 28, 12), 1.0),  # mercredi midi : heures pleines, semaine
        (datetime(2026, 10, 24, 12), 1.0),  # samedi midi : heures pleines, week-end
        (datetime(2026, 10, 25, 2), 1.0),  # dimanche 2 h : heures creuses, week-end
    ]
    cout = cout_option("es_verte_fixe_1an:week_end_hphc", grilles, 6, conso, PlagesHC.lire("23:00-07:00"))
    assert cout.kwh == {
        "semaine_hp": Decimal(1),
        "semaine_hc": Decimal(1),
        "week_end_hp": Decimal(1),
        "week_end_hc": Decimal(1),
    }
    assert cout.energie == Decimal("0.32357") + 3 * Decimal("0.23752")


def test_week_end_hphc_sans_plages():
    """L'option croisée week-end x heures creuses exige les plages d'heures creuses."""
    grilles = Grilles(
        [
            Grille(
                "x:week_end_hphc",
                6,
                date(2026, 1, 1),
                None,
                Decimal(0),
                {
                    "semaine_hp": Decimal("0.32"),
                    "semaine_hc": Decimal("0.24"),
                    "week_end_hp": Decimal("0.24"),
                    "week_end_hc": Decimal("0.24"),
                },
            )
        ]
    )
    with pytest.raises(ValueError, match="demande des plages"):
        cout_option("x:week_end_hphc", grilles, 6, [(datetime(2026, 10, 24, 12), 1.0)])


def test_annee_bissextile():
    grilles = Grilles([Grille("base", 6, date(2028, 1, 1), None, Decimal(366), {"base": Decimal(0)})])
    assert cout_option("base", grilles, 6, [(datetime(2028, 2, 29), 1.0)]).abonnement == 1


def test_hphc_sans_plages():
    with pytest.raises(ValueError, match="plages"):
        cout_option("hphc", _grilles("hphc", {"hp": "1", "hc": "1"}), 6, [])


def test_comparer_classement_et_economie():
    grilles = {
        "base": _grilles("base", {"base": "0.15"}),
        "hphc": _grilles("hphc", {"hp": "0.20", "hc": "0.10"}),
    }
    plages = PlagesHC.lire("22:00-06:00")
    # Toute la consommation la nuit : Heures creuses gagne.
    conso = [(h, 1.0) for h in heures_locales(datetime(2026, 3, 1), datetime(2026, 3, 3)) if h.hour < 6]
    comp = comparer(grilles, 6, conso, plages, "base")
    assert comp.jours == 2
    assert comp.moins_chere.option == "hphc"
    assert [c.option for c in comp.classement] == ["hphc", "base"]
    assert comp.economie == comp.couts["base"].total - comp.couts["hphc"].total == Decimal("0.60")
    assert comparer(grilles, 6, conso, plages, "hphc").economie == 0


def test_comparer_option_indisponible():
    grilles = {"base": Grilles([]), "hphc": _grilles("hphc", {"hp": "0.2", "hc": "0.1"})}
    comp = comparer(grilles, 6, [(datetime(2026, 3, 1, 1), 1.0)], PlagesHC.lire("22:00-06:00"), "base")
    assert set(comp.couts) == {"hphc"}
    assert "6 kVA" in comp.indisponibles["base"]
    assert comp.economie is None
    vide = comparer(grilles, 6, [], PlagesHC.lire("22:00-06:00"), "hphc")
    assert vide.jours == 0 and vide.couts["hphc"].total == 0


def test_cas_reel_une_annee_constante():
    """1 kWh par heure pendant un an, 6 kVA, grilles réelles : ordre de grandeur vérifié à la main."""
    grilles = {"base": Grilles.charger("base"), "hphc": Grilles.charger("hphc")}
    debut = datetime(2025, 10, 18)
    conso = [(h, 1.0) for h in heures_locales(debut, debut + timedelta(days=365))]
    comp = comparer(grilles, 6, conso, PlagesHC.lire("22:00-06:00"), "base")
    base = comp.couts["base"]
    assert base.kwh["base"] == 8760
    # Prix du kWh entre 0,1940 et 0,2001 € TTC, abonnement entre 185,94 et 190,81 €/an.
    assert Decimal(8760) * Decimal("0.1940") + Decimal("185.94") < base.total
    assert base.total < Decimal(8760) * Decimal("0.2001") + Decimal("190.81")
    assert comp.couts["hphc"].kwh["hc"] == 8760 / 3


def test_week_end_jour_choisi_repartition():
    """Zen Week-End Plus option Base (#10) : poste jour_choisi pour le jour choisi,
    week_end pour samedi/dimanche/férié, semaine sinon."""
    grilles = Grilles(
        [
            Grille(
                "edf_zen_week_end_plus:week_end_jour_lundi",
                6,
                date(2026, 1, 1),
                None,
                Decimal(0),
                {
                    "semaine": Decimal("0.2259"),
                    "week_end": Decimal("0.1691"),
                    "jour_choisi": Decimal("0.1691"),
                },
                jour_choisi=0,
            )
        ]
    )
    conso = [
        (datetime(2026, 10, 19, 12), 1.0),  # lundi : jour choisi
        (datetime(2026, 10, 21, 12), 1.0),  # mercredi : semaine
        (datetime(2026, 10, 24, 12), 1.0),  # samedi : week-end
        (datetime(2026, 10, 25, 12), 1.0),  # dimanche : week-end
        (datetime(2026, 11, 11, 12), 1.0),  # mercredi 11/11 : férié national
    ]
    cout = cout_option("edf_zen_week_end_plus:week_end_jour_lundi", grilles, 6, conso)
    assert cout.kwh == {
        "jour_choisi": Decimal(1),
        "semaine": Decimal(1),
        "week_end": Decimal(3),
    }
    assert cout.energie == Decimal("0.2259") + 4 * Decimal("0.1691")


def test_week_end_hphc_jour_choisi_repartition():
    """Zen Week-End Plus option heures creuses (#116) : six postes croisés, le jour
    choisi s'ajoute au week-end, les heures creuses s'y appliquent aussi."""
    grilles = Grilles(
        [
            Grille(
                "edf_zen_week_end_plus:week_end_hphc_jour_vendredi",
                6,
                date(2026, 1, 1),
                None,
                Decimal(0),
                {
                    "semaine_hp": Decimal("0.2314"),
                    "semaine_hc": Decimal("0.1731"),
                    "week_end_hp": Decimal("0.1731"),
                    "week_end_hc": Decimal("0.1731"),
                    "jour_choisi_hp": Decimal("0.1731"),
                    "jour_choisi_hc": Decimal("0.1731"),
                },
                jour_choisi=4,
            )
        ]
    )
    conso = [
        (datetime(2026, 10, 20, 12), 1.0),  # mardi midi : heures pleines, semaine
        (datetime(2026, 10, 21, 2), 1.0),  # mercredi 2 h : heures creuses, semaine
        (datetime(2026, 10, 23, 12), 1.0),  # vendredi midi : heures pleines, jour choisi
        (datetime(2026, 10, 23, 2), 1.0),  # vendredi 2 h : heures creuses, jour choisi
        (datetime(2026, 10, 24, 12), 1.0),  # samedi midi : heures pleines, week-end
        (datetime(2026, 10, 25, 2), 1.0),  # dimanche 2 h : heures creuses, week-end
    ]
    cout = cout_option(
        "edf_zen_week_end_plus:week_end_hphc_jour_vendredi", grilles, 6, conso, PlagesHC.lire("22:00-06:00")
    )
    assert cout.kwh == {
        "semaine_hp": Decimal(1),
        "semaine_hc": Decimal(1),
        "jour_choisi_hp": Decimal(1),
        "jour_choisi_hc": Decimal(1),
        "week_end_hp": Decimal(1),
        "week_end_hc": Decimal(1),
    }
    assert cout.energie == Decimal("0.2314") + 5 * Decimal("0.1731")
