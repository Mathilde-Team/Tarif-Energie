"""Offres de marché (issues #5 et #6) : lecture des YAML livrés, validation, comparaison."""

from datetime import datetime
from decimal import Decimal

import pytest

from custom_components.tarifenergie.calcul import PlagesHC, comparer, cout_option
from custom_components.tarifenergie.modele import Grilles, TarifIntrouvable
from custom_components.tarifenergie.offres import (
    OffreInvalide,
    grilles_offres,
    lire_offres,
    offre_depuis_dict,
)

UN_JOUR = [(datetime(2026, 10, 19, 14, 0), 1.0)]  # 1 kWh, hors heures creuses
DIX_KWH = [(datetime(2026, 10, 19, 14, 0), 10.0)]  # 10 kWh un jour, hors heures creuses
PLAGES = PlagesHC.lire("22:00-06:00")


@pytest.fixture(scope="module")
def offres():
    return lire_offres()


def test_quatre_offres_livrees(offres):
    assert sorted(offres) == [
        "alpiq_serenite",
        "alterna_du_coin_1an",
        "alterna_fixe_1an",
        "alterna_indexee",
        "amneville_trv_local",
        "barr_trv_local",
        "bazas_trv_local",
        "edf_zen_fixe_2ans",
        "edf_zen_online",
        "edf_zen_week_end_plus",
        "energis_trv_local",
        "enes_creutzwald_trv_local",
        "engie_elec_reference_3ans",
        "es_trv_local",
        "es_verte_fixe_1an",
        "es_verte_regionale_fixe_1an",
        "gascogne_trv_local",
        "gaz_de_bordeaux_novafixe",
        "gaz_de_bordeaux_novafixe_bonus",
        "gaz_de_bordeaux_novaflex",
        "gedia_all_inclusive",
        "gedia_trv_local",
        "geg_direct_producteur_3ans",
        "geg_elec_verte_3ans",
        "geg_trv_local",
        "happe_elec_1an",
        "hunelec_prix_fixe_1an",
        "hunelec_prix_fixe_1an_vert",
        "ilek_enrfixe_plus",
        "la_bellenergie_constance",
        "la_bellenergie_garance",
        "la_bellenergie_prudence",
        "la_reole_trv_local",
        "lannemezan_trv_local",
        "lavaur_trv_local",
        "marange_silvange_trv_local",
        "mint_classic_green",
        "mint_online_green",
        "mint_smart_green",
        "octopus_eco_fixe_oct2026",
        "octopus_eco_fixe_plus_oct2026",
        "ohm_fixe_2ans",
        "ohm_premiohm",
        "ohm_serente_fixe_1an",
        "oya_trv_local",
        "papernest_verte_1an",
        "plenitude_pleniweb_1an",
        "primeo_essentielle_verte",
        "primeo_fixe_confort",
        "primeo_fixe_eco_15",
        "sarre_union_trv_local",
        "selia_elec_vert_fixe",
        "seolis_trv_local",
        "sicae_oise_trv_local",
        "sicae_precy_trv_local",
        "sicae_somme_trv_local",
        "sicae_vs_trv_local",
        "sicap_pithiviers_trv_local",
        "siel_labergement_trv_local",
        "sorea_trv_local",
        "soregies_trv_local",
        "synelva_trv_local",
        "totalenergies_access",
        "totalenergies_fixe_2ans",
        "totalenergies_heures_eco",
        "totalenergies_verte_fixe",
        "uem_trv_local",
        "ume_trv_local",
        "vialis_trv_local",
    ]
    # Chaque offre propose au moins une option sans heures creuses (sa « Base ») :
    # base, week_end ou une variante à jour choisi (#10) — Zen Week-End Plus n'a
    # pas de Base classique, son option Base est « week-end + jour choisi ».
    assert all(
        {"base", "week_end", "week_end_jour_lundi", "week_end_jour_mercredi", "week_end_jour_vendredi"}
        & set(o.grilles)
        for o in offres.values()
    )


def test_hunelec_grilles_du_1er_juillet_2026(offres):
    """Grilles TTC Hunélec du 01/07/2026, page 4 des fiches (#325-#328)."""
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 19).date()
    g = grilles["hunelec_prix_fixe_1an:base"].en_vigueur(3, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 7, 1).date(),
        Decimal("144.84"),  # 12,07 x 12
        {"base": Decimal("0.23506")},
    )
    # kWh Base : 0,23506 € jusqu'à 6 kVA, 0,23346 € au-delà.
    assert grilles["hunelec_prix_fixe_1an:base"].en_vigueur(9, jour).prix == {"base": Decimal("0.23346")}
    g = grilles["hunelec_prix_fixe_1an:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("652.44")  # 54,37 x 12
    assert g.prix == {"hp": Decimal("0.25019"), "hc": Decimal("0.19129")}
    with pytest.raises(TarifIntrouvable, match="3 kVA"):  # pas d'option HC en 3 kVA
        grilles["hunelec_prix_fixe_1an:hphc"].en_vigueur(3, jour)
    # 100 % vert : même grille + 2,27 € TTC/mois de supplément, ajouté à l'abonnement.
    g = grilles["hunelec_prix_fixe_1an_vert:base"].en_vigueur(3, jour)
    assert g.abonnement_an == Decimal("172.08")  # (12,07 + 2,27) x 12
    assert g.prix == {"base": Decimal("0.23506")}
    g = grilles["hunelec_prix_fixe_1an_vert:hphc"].en_vigueur(6, jour)
    assert g.abonnement_an == Decimal("218.76")  # (15,96 + 2,27) x 12
    assert g.prix == {"hp": Decimal("0.25019"), "hc": Decimal("0.19129")}


def test_es_grilles_du_1er_octobre_2026(offres):
    """Grilles TTC ÉS Énergies du 01/10/2026, page 1 des fiches (#73, #74, #329, #332)."""
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 19).date()
    g = grilles["es_verte_fixe_1an:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 10, 1).date(),
        Decimal("191.40"),  # 15,95 x 12
        {"base": Decimal("0.30216")},
    )
    # Cellules fusionnées : 0,30216 € pour 3-6 kVA, 0,29981 € de 9 à 36 kVA.
    assert grilles["es_verte_fixe_1an:base"].en_vigueur(9, jour).prix == {"base": Decimal("0.29981")}
    g = grilles["es_verte_fixe_1an:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("669.12")  # 55,76 x 12
    assert g.prix == {"hp": Decimal("0.32356"), "hc": Decimal("0.24000")}
    with pytest.raises(TarifIntrouvable, match="3 kVA"):  # pas d'option HC en 3 kVA
        grilles["es_verte_fixe_1an:hphc"].en_vigueur(3, jour)
    # 100 % régionale : + 2,27 € TTC/mois, ajouté à l'abonnement.
    assert grilles["es_verte_regionale_fixe_1an:base"].en_vigueur(3, jour).abonnement_an == Decimal("173.40")
    assert grilles["es_verte_regionale_fixe_1an:hphc"].en_vigueur(6, jour).abonnement_an == Decimal("221.40")


def test_gedia_grille_du_19_octobre_2026(offres):
    """GEDIA All Inclusive, tableau « Domestique » du 19-25/10/2026 (#54, #335) : abonnement en €/an."""
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 19).date()
    g = grilles["gedia_all_inclusive:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 10, 19).date(),
        Decimal("190.36"),  # publié en €/an, repris tel quel
        {"base": Decimal("0.26948")},
    )
    assert grilles["gedia_all_inclusive:base"].en_vigueur(9, jour).prix == {"base": Decimal("0.26725")}
    g = grilles["gedia_all_inclusive:hphc"].en_vigueur(15, jour)
    assert g.abonnement_an == Decimal("328.78")
    assert g.prix == {"hp": Decimal("0.28965"), "hc": Decimal("0.21082")}
    with pytest.raises(TarifIntrouvable, match="3 kVA"):
        grilles["gedia_all_inclusive:hphc"].en_vigueur(3, jour)


def test_edf_zen_online_indexee_trv(offres):
    """EDF Zen Online (#21, #122) : indexée sur le TRV, sans durée de fixité ni réseau ELD."""
    offre = offres["edf_zen_online"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("indexe_trv", None, None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 24).date()
    g = grilles["edf_zen_online:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("190.32"),  # 15,86 x 12, comme le TRV
        {"base": Decimal("0.1925")},
    )
    assert grilles["edf_zen_online:base"].en_vigueur(9, jour).prix == {"base": Decimal("0.1909")}
    with pytest.raises(TarifIntrouvable, match="18 kVA"):  # Base 18-36 kVA en extinction
        grilles["edf_zen_online:base"].en_vigueur(18, jour)
    g = grilles["edf_zen_online:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("646.56")  # 53,88 x 12
    assert g.prix == {"hp": Decimal("0.2059"), "hc": Decimal("0.1531")}
    with pytest.raises(TarifIntrouvable, match="3 kVA"):
        grilles["edf_zen_online:hphc"].en_vigueur(3, jour)


def test_totalenergies_access_grille_du_1er_octobre_2026(offres):
    """TotalEnergies Access (#23, #125) : indexée TRV, kWh HT remisé de 10 % pendant 3 ans."""
    offre = offres["totalenergies_access"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("indexe_trv", None, None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 24).date()
    g = grilles["totalenergies_access:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 10, 1).date(),
        Decimal("190.32"),  # 15,86 x 12, abonnement du TRV
        {"base": Decimal("0.1837")},
    )
    assert grilles["totalenergies_access:base"].en_vigueur(36, jour).prix == {"base": Decimal("0.1823")}
    # Abonnements HC du TRV, différents de la Base dès 9 kVA.
    assert grilles["totalenergies_access:hphc"].en_vigueur(9, jour).abonnement_an == Decimal("241.92")
    g = grilles["totalenergies_access:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("646.56")  # 53,88 x 12
    assert g.prix == {"hp": Decimal("0.1965"), "hc": Decimal("0.1467")}
    with pytest.raises(TarifIntrouvable, match="3 kVA"):
        grilles["totalenergies_access:hphc"].en_vigueur(3, jour)


def test_alpiq_serenite_trv_moins_un_demi_pourcent(offres):
    """Alpiq Électricité Sérénité (#42, #150) : grille du 01/08/2026, sans HC en 3 kVA."""
    offre = offres["alpiq_serenite"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("indexe_trv", None, None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 24).date()
    g = grilles["alpiq_serenite:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("190.32"),  # 15,86 x 12
        {"base": Decimal("0.199247")},
    )
    assert grilles["alpiq_serenite:base"].en_vigueur(9, jour).prix == {"base": Decimal("0.197695")}
    g = grilles["alpiq_serenite:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("646.56")  # 53,88 x 12
    assert g.prix == {"hp": Decimal("0.213337"), "hc": Decimal("0.158293")}
    with pytest.raises(TarifIntrouvable, match="3 kVA"):  # pas d'option HC en 3 kVA
        grilles["alpiq_serenite:hphc"].en_vigueur(3, jour)


def test_primeo_essentielle_verte_trv_moins_cinq_pourcent(offres):
    """Primeo Offre Essentielle Verte (#60, #162) : grille du 14/09/2026 (TRV du 01/08/2026 -5 %
    sur le kWh HT), Base de 3 à 36 kVA, sans HC en 3 kVA."""
    offre = offres["primeo_essentielle_verte"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("indexe_trv", None, None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 28).date()
    g = grilles["primeo_essentielle_verte:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 9, 14).date(),
        Decimal("190.32"),  # 15,86 x 12
        {"base": Decimal("0.1919")},
    )
    assert grilles["primeo_essentielle_verte:base"].en_vigueur(36, jour).prix == {"base": Decimal("0.1904")}
    g = grilles["primeo_essentielle_verte:hphc"].en_vigueur(30, jour)
    assert g.abonnement_an == Decimal("557.76")  # 46,48 x 12
    assert g.prix == {"hp": Decimal("0.2054"), "hc": Decimal("0.1528")}
    with pytest.raises(TarifIntrouvable, match="3 kVA"):  # pas d'option HC en 3 kVA
        grilles["primeo_essentielle_verte:hphc"].en_vigueur(3, jour)


def test_gaz_de_bordeaux_novaflex_indexee_trv(offres):
    """NovaFlex Élec (#100, #373) : fiche Bordeaux du 01/10/2026, kWh HT du TRV -5 %."""
    offre = offres["gaz_de_bordeaux_novaflex"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("indexe_trv", None, None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 24).date()
    g = grilles["gaz_de_bordeaux_novaflex:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 10, 1).date(),
        Decimal("190.44"),  # 15,87 x 12
        {"base": Decimal("0.19190")},
    )
    assert grilles["gaz_de_bordeaux_novaflex:base"].en_vigueur(15, jour).prix == {"base": Decimal("0.19042")}
    with pytest.raises(TarifIntrouvable, match="18 kVA"):  # Base de 3 à 15 kVA seulement
        grilles["gaz_de_bordeaux_novaflex:base"].en_vigueur(18, jour)
    g = grilles["gaz_de_bordeaux_novaflex:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("646.56")  # 53,88 x 12
    assert g.prix == {"hp": Decimal("0.20536"), "hc": Decimal("0.15280")}
    with pytest.raises(TarifIntrouvable, match="3 kVA"):  # pas d'option HC en 3 kVA
        grilles["gaz_de_bordeaux_novaflex:hphc"].en_vigueur(3, jour)


def test_totalenergies_heures_eco_reprend_le_trv(offres):
    """TotalEnergies Heures Eco (#94, #132) : grille du 01/10/2026, sans HC en 3 kVA."""
    offre = offres["totalenergies_heures_eco"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("indexe_trv", None, None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 24).date()
    g = grilles["totalenergies_heures_eco:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 10, 1).date(),
        Decimal("190.32"),  # 15,86 x 12
        {"base": Decimal("0.2001")},
    )
    assert grilles["totalenergies_heures_eco:base"].en_vigueur(36, jour).prix == {"base": Decimal("0.1985")}
    g = grilles["totalenergies_heures_eco:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("646.56")  # 53,88 x 12
    assert g.prix == {"hp": Decimal("0.2142"), "hc": Decimal("0.1589")}
    with pytest.raises(TarifIntrouvable, match="3 kVA"):  # pas d'option HC en 3 kVA
        grilles["totalenergies_heures_eco:hphc"].en_vigueur(3, jour)


def test_alterna_indexee_grille_du_1er_septembre_2026(offres):
    """Alterna Mon électricité française indexée (#45, #153) : HC dès 3 kVA."""
    offre = offres["alterna_indexee"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("indexe_trv", None, None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 24).date()
    g = grilles["alterna_indexee:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 9, 1).date(),
        Decimal("211.92"),  # 17,66 x 12
        {"base": Decimal("0.1919")},
    )
    assert grilles["alterna_indexee:base"].en_vigueur(9, jour).prix == {"base": Decimal("0.1904")}
    g = grilles["alterna_indexee:hphc"].en_vigueur(3, jour)
    assert g.abonnement_an == Decimal("167.16")  # 13,93 x 12
    assert g.prix == {"hp": Decimal("0.2054"), "hc": Decimal("0.1528")}
    assert grilles["alterna_indexee:hphc"].en_vigueur(36, jour).abonnement_an == Decimal("688.68")


def test_mint_online_green_grille_du_8_octobre_2026(offres):
    """Mint Online & Green (#35, #143) : indexée TRV, kWh HTT -5 %, coupure Base à 9 kVA."""
    offre = offres["mint_online_green"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("indexe_trv", None, None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 24).date()
    g = grilles["mint_online_green:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 10, 8).date(),
        Decimal("190.32"),  # 15,86 x 12
        {"base": Decimal("0.1919")},
    )
    assert grilles["mint_online_green:base"].en_vigueur(9, jour).prix == {"base": Decimal("0.1904")}
    g = grilles["mint_online_green:hphc"].en_vigueur(6, jour)
    assert g.abonnement_an == Decimal("192.60")  # 16,05 x 12
    assert g.prix == {"hp": Decimal("0.2054"), "hc": Decimal("0.1528")}
    with pytest.raises(TarifIntrouvable, match="3 kVA"):
        grilles["mint_online_green:hphc"].en_vigueur(3, jour)


@pytest.mark.parametrize(
    ("extra", "chemin_fautif"),
    [
        ({"duree_fixite_mois": 12}, "offre.duree_fixite_mois"),  # le prix suit le TRV
        ({"eld": "x"}, "offre.eld"),  # réservé aux TRV locaux
    ],
)
def test_indexee_trv_invalide(extra, chemin_fautif):
    from datetime import date

    donnees = {
        "id": "x",
        "fournisseur": "F",
        "offre": "Indexée",
        "type_prix": "indexe_trv",
        "grille_du": date(2026, 8, 1),
        "source": "https://exemple.fr/grille.pdf",
        "options": {"base": {"abonnement_mensuel_ttc": {6: 15.0}, "kwh_ttc": {"base": 0.2}}},
        **extra,
    }
    with pytest.raises(OffreInvalide, match=chemin_fautif):
        offre_depuis_dict(donnees, "x")


def test_primeo_fixe_eco_15_base_jusqu_a_juillet_2027(offres):
    """Primeo Fixe ECO -15 % (#185) : prix fixe 18 mois, grille du 01/02/2026, Base seule."""
    offre = offres["primeo_fixe_eco_15"]
    assert (offre.type_prix, offre.duree_fixite_mois) == ("fixe", 18)
    grilles = grilles_offres(offres)
    assert "primeo_fixe_eco_15:hphc" not in grilles
    jour = datetime(2026, 10, 24).date()
    g = grilles["primeo_fixe_eco_15:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 2, 1).date(),
        Decimal("196.32"),  # 16,36 x 12
        {"base": Decimal("0.1704")},
    )
    g = grilles["primeo_fixe_eco_15:base"].en_vigueur(36, jour)
    assert (g.abonnement_an, g.prix) == (Decimal("658.32"), {"base": Decimal("0.1693")})


def test_papernest_grille_du_22_septembre_2026(offres):
    """papernest énergie Électricité verte 1 an (#67, #169), grille TTC du 22/09/2026."""
    offre = offres["papernest_verte_1an"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("fixe", None, 12)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 24).date()
    g = grilles["papernest_verte_1an:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 9, 22).date(),
        Decimal("387.72"),  # 32,31 x 12
        {"base": Decimal("0.29841")},
    )
    g = grilles["papernest_verte_1an:hphc"].en_vigueur(6, jour)
    assert g.abonnement_an == Decimal("464.40")  # 38,70 x 12
    assert g.prix == {"hp": Decimal("0.32023"), "hc": Decimal("0.24528")}
    # Dès 15 kVA, l'abonnement HC est celui de la Base.
    assert grilles["papernest_verte_1an:hphc"].en_vigueur(36, jour).abonnement_an == Decimal("1803.36")
    with pytest.raises(TarifIntrouvable, match="3 kVA"):  # pas d'option HC en 3 kVA
        grilles["papernest_verte_1an:hphc"].en_vigueur(3, jour)


def test_happe_elec_1an_grille_du_1er_octobre_2026(offres):
    """Happ-e Électricité 1 an, annexe prix du 01/10/2026 (#71, #128) : fourniture + acheminement.

    Base : CU ; 6 kVA 44,35 + 149,39 €/an, 20,321 + 5,988 c€.
    HC : MUDT ; 6 kVA 44,35 + 170,00 €/an, HP 21,296 + 6,108, HC 18,066 + 4,332 c€ ; pas de 3 kVA.
    """
    offre = offres["happe_elec_1an"]
    assert (offre.type_prix, offre.duree_fixite_mois) == ("fixe", 12)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 19).date()
    g = grilles["happe_elec_1an:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 10, 1).date(),
        Decimal("193.74"),
        {"base": Decimal("0.26309")},
    )
    g = grilles["happe_elec_1an:base"].en_vigueur(3, jour)
    assert g.abonnement_an == Decimal("146.50")
    g = grilles["happe_elec_1an:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("789.81")
    assert g.prix == {"hp": Decimal("0.27404"), "hc": Decimal("0.22398")}
    with pytest.raises(TarifIntrouvable, match="3 kVA"):
        grilles["happe_elec_1an:hphc"].en_vigueur(3, jour)


def test_geg_direct_producteur_grille_du_5_octobre_2026(offres):
    """GEG Direct Producteur fixe 3 ans, grille TTC du 05/10/2026 (#55, #136) : HP selon la puissance."""
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 19).date()
    g = grilles["geg_direct_producteur_3ans:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 10, 5).date(),
        Decimal("207.60"),  # 17,30 x 12
        {"base": Decimal("0.1837")},
    )
    assert grilles["geg_direct_producteur_3ans:base"].en_vigueur(9, jour).prix == {"base": Decimal("0.1823")}
    g = grilles["geg_direct_producteur_3ans:hphc"].en_vigueur(9, jour)
    assert g.prix == {"hp": Decimal("0.1983"), "hc": Decimal("0.1586")}
    g = grilles["geg_direct_producteur_3ans:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("717.12")  # 59,76 x 12
    assert g.prix == {"hp": Decimal("0.2016"), "hc": Decimal("0.1586")}
    with pytest.raises(TarifIntrouvable, match="3 kVA"):
        grilles["geg_direct_producteur_3ans:hphc"].en_vigueur(3, jour)


def test_ohm_premiohm_grille_du_14_octobre_2026(offres):
    """Ohm Premi'Ohm, grille TTC du 14/10/2026 (#39, #147) : kWh unique, fixe 3 ans."""
    offre = offres["ohm_premiohm"]
    assert (offre.type_prix, offre.duree_fixite_mois) == ("fixe", 36)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 19).date()
    g = grilles["ohm_premiohm:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 10, 14).date(),
        Decimal("190.56"),  # 15,88 x 12
        {"base": Decimal("0.2287")},
    )
    assert grilles["ohm_premiohm:base"].en_vigueur(36, jour).prix == {"base": Decimal("0.2287")}
    g = grilles["ohm_premiohm:hphc"].en_vigueur(6, jour)
    assert g.abonnement_an == Decimal("192.84")  # 16,07 x 12
    assert g.prix == {"hp": Decimal("0.2455"), "hc": Decimal("0.1799")}
    with pytest.raises(TarifIntrouvable, match="3 kVA"):
        grilles["ohm_premiohm:hphc"].en_vigueur(3, jour)


def test_mint_classic_green_grille_du_8_octobre_2026(offres):
    """Mint Classic & Green, grille TTC du 08/10/2026 (#34, #142) : coupure Base entre 6 et 9 kVA."""
    offre = offres["mint_classic_green"]
    assert (offre.type_prix, offre.duree_fixite_mois) == ("fixe", 12)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 19).date()
    g = grilles["mint_classic_green:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 10, 8).date(),
        Decimal("188.40"),  # 15,70 x 12
        {"base": Decimal("0.1937")},
    )
    assert grilles["mint_classic_green:base"].en_vigueur(9, jour).prix == {"base": Decimal("0.1924")}
    g = grilles["mint_classic_green:hphc"].en_vigueur(6, jour)
    assert g.abonnement_an == Decimal("190.56")  # 15,88 x 12
    assert g.prix == {"hp": Decimal("0.2062"), "hc": Decimal("0.1576")}
    with pytest.raises(TarifIntrouvable, match="3 kVA"):
        grilles["mint_classic_green:hphc"].en_vigueur(3, jour)


def test_mint_smart_green_grille_du_8_octobre_2026(offres):
    """Mint Smart & Green, grille TTC du 08/10/2026 (#36, #144) : fixe 2 ans."""
    offre = offres["mint_smart_green"]
    assert (offre.type_prix, offre.duree_fixite_mois) == ("fixe", 24)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 19).date()
    g = grilles["mint_smart_green:base"].en_vigueur(6, jour)
    assert (g.abonnement_an, g.prix) == (Decimal("227.28"), {"base": Decimal("0.2015")})  # 18,94 x 12
    assert grilles["mint_smart_green:base"].en_vigueur(9, jour).prix == {"base": Decimal("0.2002")}
    g = grilles["mint_smart_green:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("671.28")  # 55,94 x 12
    assert g.prix == {"hp": Decimal("0.2147"), "hc": Decimal("0.1636")}
    with pytest.raises(TarifIntrouvable, match="3 kVA"):
        grilles["mint_smart_green:hphc"].en_vigueur(3, jour)


def test_engie_elec_reference_grille_d_octobre_2026(offres):
    """Engie Elec Référence 3 ans, grille d'octobre 2026 (#28, #127) : somme des trois parts.

    Base : CU ; 6 kVA 45,79 + 149,39 €/an, 16,379 + 5,988 + 1,838 c€ ; 9 kVA obligations 2,010 c€.
    HC : MUDT ; 6 kVA 45,79 + 170,00 €/an, HP 16,861 + 6,108 + 2,030, HC 14,321 + 4,332 + 2,030 c€.
    """
    offre = offres["engie_elec_reference_3ans"]
    assert (offre.type_prix, offre.duree_fixite_mois) == ("fixe", 36)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 19).date()
    g = grilles["engie_elec_reference_3ans:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 10, 1).date(),
        Decimal("195.18"),
        {"base": Decimal("0.24205")},
    )
    g = grilles["engie_elec_reference_3ans:base"].en_vigueur(36, jour)
    assert (g.abonnement_an, g.prix) == (Decimal("667.55"), {"base": Decimal("0.24377")})
    g = grilles["engie_elec_reference_3ans:hphc"].en_vigueur(6, jour)
    assert g.abonnement_an == Decimal("215.79")
    assert g.prix == {"hp": Decimal("0.24999"), "hc": Decimal("0.20683")}
    with pytest.raises(TarifIntrouvable, match="3 kVA"):
        grilles["engie_elec_reference_3ans:hphc"].en_vigueur(3, jour)


def test_es_trv_local_grille_du_1er_aout_2026(offres):
    """TRV local ÉS (#72, #190) : type « reglemente », sans durée de fixité, HC dès 3 kVA."""
    offre = offres["es_trv_local"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == (
        "reglemente",
        "strasbourg_electricite_reseaux",
        None,
    )
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 19).date()
    g = grilles["es_trv_local:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("191.40"),  # 15,95 x 12
        {"base": Decimal("0.20006")},
    )
    assert grilles["es_trv_local:base"].en_vigueur(9, jour).prix == {"base": Decimal("0.19850")}
    g = grilles["es_trv_local:hphc"].en_vigueur(3, jour)  # HC proposée dès 3 kVA
    assert g.abonnement_an == Decimal("147.48")  # 12,29 x 12
    assert g.prix == {"hp": Decimal("0.21422"), "hc": Decimal("0.15890")}


def test_lavaur_trv_local_grille_du_1er_aout_2026(offres):
    """TRV local Énergies Services Lavaur (#212, #213)."""
    offre = offres["lavaur_trv_local"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == (
        "reglemente",
        "energies_services_lavaur",
        None,
    )
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 24).date()
    g = grilles["lavaur_trv_local:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("190.32"),
        {"base": Decimal("0.2001")},
    )
    # Base 9-36 kVA en extinction, publiée pour les contrats en cours
    g = grilles["lavaur_trv_local:base"].en_vigueur(36, jour)
    assert (g.abonnement_an, g.prix) == (Decimal("646.56"), {"base": Decimal("0.1985")})
    g = grilles["lavaur_trv_local:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("646.56")
    assert g.prix == {"hp": Decimal("0.2142"), "hc": Decimal("0.1589")}


def test_siel_labergement_trv_local_grille_du_1er_aout_2026(offres):
    """TRV local SIEL Labergement (#313, #314) : HC dès 3 kVA, même abonnement qu'en Base."""
    offre = offres["siel_labergement_trv_local"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("reglemente", "siel_labergement", None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 19).date()
    g = grilles["siel_labergement_trv_local:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("190.35"),
        {"base": Decimal("0.2001")},
    )
    assert grilles["siel_labergement_trv_local:base"].en_vigueur(9, jour).prix == {"base": Decimal("0.1985")}
    g = grilles["siel_labergement_trv_local:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("646.51")
    assert g.prix == {"hp": Decimal("0.2142"), "hc": Decimal("0.1589")}
    assert grilles["siel_labergement_trv_local:hphc"].en_vigueur(3, jour).abonnement_an == Decimal("145.56")


def test_sicap_pithiviers_trv_local_grille_du_1er_aout_2026(offres):
    """TRV local SICAP Pithiviers (#310, #311) : abonnement mensuel, kWh Base par puissance."""
    offre = offres["sicap_pithiviers_trv_local"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("reglemente", "sicap_pithiviers", None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 19).date()
    g = grilles["sicap_pithiviers_trv_local:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("190.32"),
        {"base": Decimal("0.2001")},
    )
    assert grilles["sicap_pithiviers_trv_local:base"].en_vigueur(9, jour).prix == {"base": Decimal("0.1985")}
    g = grilles["sicap_pithiviers_trv_local:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("659.88")
    assert g.prix == {"hp": Decimal("0.2142"), "hc": Decimal("0.1589")}
    assert grilles["sicap_pithiviers_trv_local:hphc"].en_vigueur(3, jour).abonnement_an == Decimal("146.64")


def test_sicae_vs_trv_local_grille_du_1er_aout_2026(offres):
    """TRV local SICAE Vallée du Sausseron (#307, #308) : Base en 3 et 6 kVA seulement, HC dès 3 kVA."""
    offre = offres["sicae_vs_trv_local"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("reglemente", "sicae_vs", None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 19).date()
    g = grilles["sicae_vs_trv_local:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("190.35"),
        {"base": Decimal("0.2001")},
    )
    g = grilles["sicae_vs_trv_local:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("659.92")
    assert g.prix == {"hp": Decimal("0.2142"), "hc": Decimal("0.1589")}
    with pytest.raises(TarifIntrouvable, match="9 kVA"):
        grilles["sicae_vs_trv_local:base"].en_vigueur(9, jour)
    assert grilles["sicae_vs_trv_local:hphc"].en_vigueur(3, jour).abonnement_an == Decimal("146.67")


def test_sicae_somme_trv_local_grille_du_1er_aout_2026(offres):
    """TRV local SICAE Somme et Cambraisis (#304, #305) : abonnement en €/an, HC dès 6 kVA."""
    offre = offres["sicae_somme_trv_local"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("reglemente", "sicae_somme", None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 19).date()
    g = grilles["sicae_somme_trv_local:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("190.35"),
        {"base": Decimal("0.2001")},
    )
    g = grilles["sicae_somme_trv_local:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("659.92")
    assert g.prix == {"hp": Decimal("0.2142"), "hc": Decimal("0.1589")}
    with pytest.raises(TarifIntrouvable, match="3 kVA"):
        grilles["sicae_somme_trv_local:hphc"].en_vigueur(3, jour)


def test_sicae_precy_trv_local_grille_du_1er_aout_2026(offres):
    """TRV local SICAE-Précy (#301, #302) : abonnement en €/an, Base 3 à 15 kVA, HC dès 6 kVA."""
    offre = offres["sicae_precy_trv_local"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("reglemente", "sicae_precy", None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 19).date()
    g = grilles["sicae_precy_trv_local:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("190.35"),
        {"base": Decimal("0.2001")},
    )
    assert grilles["sicae_precy_trv_local:base"].en_vigueur(15, jour).abonnement_an == Decimal("328.77")
    with pytest.raises(TarifIntrouvable, match="18 kVA"):
        grilles["sicae_precy_trv_local:base"].en_vigueur(18, jour)
    g = grilles["sicae_precy_trv_local:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("659.92")
    assert g.prix == {"hp": Decimal("0.2142"), "hc": Decimal("0.1589")}
    with pytest.raises(TarifIntrouvable, match="3 kVA"):
        grilles["sicae_precy_trv_local:hphc"].en_vigueur(3, jour)


def test_sorea_trv_local_grille_du_1er_aout_2026(offres):
    """TRV local Soréa (#318, #319) : HC à partir de 6 kVA, même abonnement qu'en Base."""
    offre = offres["sorea_trv_local"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("reglemente", "sorea", None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 19).date()
    g = grilles["sorea_trv_local:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("190.32"),  # 15,86 x 12
        {"base": Decimal("0.2001")},
    )
    abonnement_3kva = grilles["sorea_trv_local:base"].en_vigueur(3, jour).abonnement_an
    assert abonnement_3kva == Decimal("145.56")  # 12,13 x 12
    assert grilles["sorea_trv_local:base"].en_vigueur(9, jour).prix == {"base": Decimal("0.1985")}
    g = grilles["sorea_trv_local:hphc"].en_vigueur(6, jour)
    assert g.abonnement_an == Decimal("190.32")
    assert g.prix == {"hp": Decimal("0.2142"), "hc": Decimal("0.1589")}
    with pytest.raises(TarifIntrouvable, match="3 kVA"):
        grilles["sorea_trv_local:hphc"].en_vigueur(3, jour)


def test_ume_trv_local_grille_du_1er_aout_2026(offres):
    """TRV local UME Erstein (#321, #322) : mêmes montants que le TRV local ÉS, réseau UME."""
    offre = offres["ume_trv_local"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("reglemente", "ume", None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 19).date()
    g = grilles["ume_trv_local:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("191.40"),  # 15,95 x 12
        {"base": Decimal("0.20006")},
    )
    assert grilles["ume_trv_local:base"].en_vigueur(36, jour).prix == {"base": Decimal("0.19850")}
    g = grilles["ume_trv_local:hphc"].en_vigueur(3, jour)  # HC proposée dès 3 kVA
    assert g.abonnement_an == Decimal("147.48")  # 12,29 x 12
    assert g.prix == {"hp": Decimal("0.21422"), "hc": Decimal("0.15890")}
    for option in ("base", "hphc"):
        es, ume = grilles[f"es_trv_local:{option}"], grilles[f"ume_trv_local:{option}"]
        for kva in (3, 6, 9, 36):
            assert ume.en_vigueur(kva, jour).prix == es.en_vigueur(kva, jour).prix
            assert ume.en_vigueur(kva, jour).abonnement_an == es.en_vigueur(kva, jour).abonnement_an


def test_enes_creutzwald_trv_local_grille_du_1er_aout_2026(offres):
    """TRV local Enes Creutzwald (#275, #276)."""
    offre = offres["enes_creutzwald_trv_local"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("reglemente", "enes_creutzwald", None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 24).date()
    g = grilles["enes_creutzwald_trv_local:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("191.42"),
        {"base": Decimal("0.20006")},
    )
    # Base 9-36 kVA en extinction, publiée pour les contrats en cours
    g = grilles["enes_creutzwald_trv_local:base"].en_vigueur(36, jour)
    assert (g.abonnement_an, g.prix) == (Decimal("652.92"), {"base": Decimal("0.19850")})
    g = grilles["enes_creutzwald_trv_local:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("669.06")
    assert g.prix == {"hp": Decimal("0.21422"), "hc": Decimal("0.15890")}


def test_la_reole_trv_local_grille_du_1er_aout_2026(offres):
    """TRV local RMMS La Réole (#272, #273)."""
    offre = offres["la_reole_trv_local"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("reglemente", "rmms_la_reole", None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 24).date()
    g = grilles["la_reole_trv_local:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("190.32"),
        {"base": Decimal("0.2001")},
    )
    # Base 9-36 kVA en extinction, publiée pour les contrats en cours
    g = grilles["la_reole_trv_local:base"].en_vigueur(36, jour)
    assert (g.abonnement_an, g.prix) == (Decimal("646.56"), {"base": Decimal("0.1985")})
    g = grilles["la_reole_trv_local:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("659.88")
    assert g.prix == {"hp": Decimal("0.2142"), "hc": Decimal("0.1589")}


def test_marange_silvange_trv_local_grille_du_1er_aout_2026(offres):
    """TRV local Régie de Marange-Silvange (#265, #266)."""
    offre = offres["marange_silvange_trv_local"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == (
        "reglemente",
        "regie_marange_silvange",
        None,
    )
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 24).date()
    g = grilles["marange_silvange_trv_local:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("190.36"),
        {"base": Decimal("0.2000")},
    )
    # Base 9-36 kVA en extinction, publiée pour les contrats en cours
    g = grilles["marange_silvange_trv_local:base"].en_vigueur(36, jour)
    assert (g.abonnement_an, g.prix) == (Decimal("646.51"), {"base": Decimal("0.1985")})
    g = grilles["marange_silvange_trv_local:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("659.92")
    assert g.prix == {"hp": Decimal("0.2142"), "hc": Decimal("0.1589")}


def test_sarre_union_trv_local_grille_du_1er_aout_2026(offres):
    """TRV local Énergies & Services Sarre-Union (#257, #258)."""
    offre = offres["sarre_union_trv_local"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == (
        "reglemente",
        "energies_services_sarre_union",
        None,
    )
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 24).date()
    g = grilles["sarre_union_trv_local:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("191.40"),
        {"base": Decimal("0.20006")},
    )
    # Base 9-36 kVA en extinction, publiée pour les contrats en cours
    g = grilles["sarre_union_trv_local:base"].en_vigueur(36, jour)
    assert (g.abonnement_an, g.prix) == (Decimal("652.92"), {"base": Decimal("0.19850")})
    g = grilles["sarre_union_trv_local:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("669.12")
    assert g.prix == {"hp": Decimal("0.21422"), "hc": Decimal("0.15890")}


def test_vialis_trv_local_grille_du_1er_aout_2026(offres):
    """TRV local Vialis (#245, #246)."""
    offre = offres["vialis_trv_local"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("reglemente", "vialis", None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 24).date()
    g = grilles["vialis_trv_local:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("191.40"),
        {"base": Decimal("0.2001")},
    )
    with pytest.raises(LookupError):  # Base 18-36 kVA absente de la grille
        grilles["vialis_trv_local:base"].en_vigueur(18, jour)
    g = grilles["vialis_trv_local:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("669.00")
    assert g.prix == {"hp": Decimal("0.2142"), "hc": Decimal("0.1589")}


def test_uem_trv_local_grille_du_1er_aout_2026(offres):
    """TRV local UEM (#242, #243)."""
    offre = offres["uem_trv_local"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("reglemente", "reseda", None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 24).date()
    g = grilles["uem_trv_local:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("190.36"),
        {"base": Decimal("0.2000")},
    )
    # Base 9-36 kVA en extinction, publiée pour les contrats en cours
    g = grilles["uem_trv_local:base"].en_vigueur(36, jour)
    assert (g.abonnement_an, g.prix) == (Decimal("646.51"), {"base": Decimal("0.1985")})
    g = grilles["uem_trv_local:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("659.92")
    assert g.prix == {"hp": Decimal("0.2142"), "hc": Decimal("0.1589")}


def test_synelva_trv_local_grille_du_1er_aout_2026(offres):
    """TRV local Synelva (#239, #240)."""
    offre = offres["synelva_trv_local"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("reglemente", "synelva", None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 24).date()
    g = grilles["synelva_trv_local:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("190.35"),
        {"base": Decimal("0.2003")},
    )
    # Base 9-36 kVA en extinction, publiée pour les contrats en cours
    g = grilles["synelva_trv_local:base"].en_vigueur(36, jour)
    assert (g.abonnement_an, g.prix) == (Decimal("646.51"), {"base": Decimal("0.1988")})
    g = grilles["synelva_trv_local:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("646.51")
    assert g.prix == {"hp": Decimal("0.2145"), "hc": Decimal("0.1592")}


def test_soregies_trv_local_grille_du_1er_aout_2026(offres):
    """TRV local Sorégies (#236, #237)."""
    offre = offres["soregies_trv_local"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("reglemente", "srd", None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 24).date()
    g = grilles["soregies_trv_local:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("190.32"),
        {"base": Decimal("0.2001")},
    )
    # Base 9-36 kVA en extinction, publiée pour les contrats en cours
    g = grilles["soregies_trv_local:base"].en_vigueur(36, jour)
    assert (g.abonnement_an, g.prix) == (Decimal("646.56"), {"base": Decimal("0.1985")})
    g = grilles["soregies_trv_local:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("659.88")
    assert g.prix == {"hp": Decimal("0.2142"), "hc": Decimal("0.1589")}


def test_seolis_trv_local_grille_du_1er_aout_2026(offres):
    """TRV local SÉOLIS (#233, #234)."""
    offre = offres["seolis_trv_local"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("reglemente", "geredis", None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 24).date()
    g = grilles["seolis_trv_local:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("190.35"),
        {"base": Decimal("0.2001")},
    )
    # Base 9-36 kVA en extinction, publiée pour les contrats en cours
    g = grilles["seolis_trv_local:base"].en_vigueur(36, jour)
    assert (g.abonnement_an, g.prix) == (Decimal("646.51"), {"base": Decimal("0.1985")})
    g = grilles["seolis_trv_local:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("659.92")
    assert g.prix == {"hp": Decimal("0.2142"), "hc": Decimal("0.1589")}


def test_amneville_trv_local_grille_du_1er_aout_2026(offres):
    """TRV local Régie d'Amnéville (#221, #222)."""
    offre = offres["amneville_trv_local"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("reglemente", "regie_amneville", None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 24).date()
    g = grilles["amneville_trv_local:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("190.36"),
        {"base": Decimal("0.2000")},
    )
    # Base 9-36 kVA en extinction, publiée pour les contrats en cours
    g = grilles["amneville_trv_local:base"].en_vigueur(36, jour)
    assert (g.abonnement_an, g.prix) == (Decimal("646.51"), {"base": Decimal("0.1985")})
    g = grilles["amneville_trv_local:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("659.92")
    assert g.prix == {"hp": Decimal("0.2142"), "hc": Decimal("0.1589")}


def test_bazas_trv_local_grille_du_1er_aout_2026(offres):
    """TRV local Bazas Energies (#218, #219)."""
    offre = offres["bazas_trv_local"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("reglemente", "bazas_energies", None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 24).date()
    g = grilles["bazas_trv_local:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("190.32"),
        {"base": Decimal("0.2001")},
    )
    with pytest.raises(LookupError):  # Base 9-36 kVA en extinction, absente de la grille
        grilles["bazas_trv_local:base"].en_vigueur(9, jour)
    g = grilles["bazas_trv_local:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("659.88")
    assert g.prix == {"hp": Decimal("0.2142"), "hc": Decimal("0.1589")}


def test_oya_trv_local_grille_du_1er_aout_2026(offres):
    """TRV local Oya énergies (#215, #216)."""
    offre = offres["oya_trv_local"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("reglemente", "oya_energies", None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 24).date()
    g = grilles["oya_trv_local:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("190.32"),
        {"base": Decimal("0.2001")},
    )
    # Base 9-36 kVA en extinction, publiée pour les contrats en cours
    g = grilles["oya_trv_local:base"].en_vigueur(36, jour)
    assert (g.abonnement_an, g.prix) == (Decimal("646.56"), {"base": Decimal("0.1985")})
    g = grilles["oya_trv_local:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("646.56")
    assert g.prix == {"hp": Decimal("0.2142"), "hc": Decimal("0.1589")}


def test_lannemezan_trv_local_grille_du_1er_aout_2026(offres):
    """TRV local Énergies Services Lannemezan (#210, #211)."""
    offre = offres["lannemezan_trv_local"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == (
        "reglemente",
        "energies_services_lannemezan",
        None,
    )
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 24).date()
    g = grilles["lannemezan_trv_local:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("190.32"),
        {"base": Decimal("0.2001")},
    )
    # Base 9-36 kVA en extinction, publiée pour les contrats en cours
    g = grilles["lannemezan_trv_local:base"].en_vigueur(36, jour)
    assert (g.abonnement_an, g.prix) == (Decimal("646.56"), {"base": Decimal("0.1985")})
    g = grilles["lannemezan_trv_local:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("659.88")
    assert g.prix == {"hp": Decimal("0.2142"), "hc": Decimal("0.1589")}


def test_gascogne_trv_local_grille_du_1er_aout_2026(offres):
    """TRV local Gascogne Énergies Services (#205, #206) : abonnements publiés en € TTC/an."""
    offre = offres["gascogne_trv_local"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == (
        "reglemente",
        "gascogne_energies_services",
        None,
    )
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 24).date()
    g = grilles["gascogne_trv_local:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("190.35"),
        {"base": Decimal("0.2001")},
    )
    g = grilles["gascogne_trv_local:base"].en_vigueur(36, jour)  # Base en extinction, contrats en cours
    assert (g.abonnement_an, g.prix) == (Decimal("646.51"), {"base": Decimal("0.1985")})
    g = grilles["gascogne_trv_local:hphc"].en_vigueur(3, jour)
    assert g.abonnement_an == Decimal("146.67")
    assert g.prix == {"hp": Decimal("0.2142"), "hc": Decimal("0.1589")}


def test_energis_trv_local_grille_du_1er_aout_2026(offres):
    """TRV local Energis (#200, #201) : Base en 3 et 6 kVA seulement, prix Base à 5 décimales."""
    offre = offres["energis_trv_local"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("reglemente", "energis", None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 24).date()
    g = grilles["energis_trv_local:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("190.32"),  # 15,86 x 12
        {"base": Decimal("0.19522")},
    )
    with pytest.raises(LookupError):  # Base 9-36 kVA en extinction, absente de la grille
        grilles["energis_trv_local:base"].en_vigueur(9, jour)
    g = grilles["energis_trv_local:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("646.56")  # 53,88 x 12
    assert g.prix == {"hp": Decimal("0.2142"), "hc": Decimal("0.1589")}


def test_barr_trv_local_grille_du_1er_aout_2026(offres):
    """TRV local Barr Energies (#197, #198) : Base publiée en 3 et 6 kVA seulement, HC dès 3 kVA."""
    offre = offres["barr_trv_local"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("reglemente", "barr_energies", None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 24).date()
    g = grilles["barr_trv_local:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("190.32"),  # 15,86 x 12
        {"base": Decimal("0.2001")},
    )
    with pytest.raises(LookupError):  # Base 9-36 kVA en extinction, absente de la grille
        grilles["barr_trv_local:base"].en_vigueur(9, jour)
    g = grilles["barr_trv_local:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("660.00")  # 55,00 x 12
    assert g.prix == {"hp": Decimal("0.2142"), "hc": Decimal("0.1589")}


def test_geg_trv_local_grille_du_1er_aout_2026(offres):
    """TRV local GEG (#195, #196) : réseau GreenAlp, kWh TTC à 4 décimales, HC dès 3 kVA."""
    offre = offres["geg_trv_local"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("reglemente", "greenalp", None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 24).date()
    g = grilles["geg_trv_local:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("190.80"),  # 15,90 x 12
        {"base": Decimal("0.2001")},
    )
    g = grilles["geg_trv_local:base"].en_vigueur(36, jour)
    assert (g.abonnement_an, g.prix) == (Decimal("650.76"), {"base": Decimal("0.1985")})  # 54,23 x 12
    g = grilles["geg_trv_local:hphc"].en_vigueur(3, jour)  # HC proposée dès 3 kVA
    assert g.abonnement_an == Decimal("145.80")  # 12,15 x 12, comme la Base
    assert g.prix == {"hp": Decimal("0.2142"), "hc": Decimal("0.1589")}


def test_gedia_trv_local_grille_du_1er_aout_2026(offres):
    """TRV local Gedia (#192, #193) : réseau de Dreux, Base 9-36 kVA en extinction, HC dès 3 kVA."""
    offre = offres["gedia_trv_local"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("reglemente", "gedia", None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 24).date()
    g = grilles["gedia_trv_local:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("190.32"),  # 15,86 x 12
        {"base": Decimal("0.20006")},
    )
    g = grilles["gedia_trv_local:base"].en_vigueur(36, jour)
    assert (g.abonnement_an, g.prix) == (Decimal("646.56"), {"base": Decimal("0.19850")})  # 53,88 x 12
    g = grilles["gedia_trv_local:hphc"].en_vigueur(3, jour)  # HC proposée dès 3 kVA
    assert g.abonnement_an == Decimal("145.56")  # 12,13 x 12, comme la Base
    assert g.prix == {"hp": Decimal("0.21422"), "hc": Decimal("0.15890")}


def test_sicae_oise_trv_local_grille_du_1er_aout_2026(offres):
    """TRV local SICAE Oise (#298, #299) : Base en 3 et 6 kVA seulement, HC dès 3 kVA."""
    offre = offres["sicae_oise_trv_local"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("reglemente", "sicae_oise", None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 19).date()
    g = grilles["sicae_oise_trv_local:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("190.36"),
        {"base": Decimal("0.2001")},
    )
    g = grilles["sicae_oise_trv_local:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("659.92")
    assert g.prix == {"hp": Decimal("0.2142"), "hc": Decimal("0.1589")}
    with pytest.raises(TarifIntrouvable, match="9 kVA"):
        grilles["sicae_oise_trv_local:base"].en_vigueur(9, jour)
    assert grilles["sicae_oise_trv_local:hphc"].en_vigueur(3, jour).abonnement_an == Decimal("146.68")


@pytest.mark.parametrize(
    ("extra", "chemin_fautif"),
    [
        ({"duree_fixite_mois": 12, "eld": "x"}, "offre.duree_fixite_mois"),  # sans objet pour un TRV
        ({}, "offre.eld"),  # réseau de l'ELD exigé
    ],
)
def test_trv_local_invalide(extra, chemin_fautif):
    from datetime import date

    donnees = {
        "id": "x",
        "fournisseur": "F",
        "offre": "TRV local",
        "type_prix": "reglemente",
        "grille_du": date(2026, 8, 1),
        "source": "https://exemple.fr/trv.pdf",
        "options": {"base": {"abonnement_mensuel_ttc": {6: 15.0}, "kwh_ttc": {"base": 0.2}}},
        **extra,
    }
    with pytest.raises(OffreInvalide, match=chemin_fautif):
        offre_depuis_dict(donnees, "x")


def test_abonnement_annuel_et_mensuel_exclusifs():
    """abonnement_annuel_ttc repris tel quel ; les deux champs ensemble sont refusés."""
    from datetime import date

    base = {
        "id": "x",
        "fournisseur": "F",
        "offre": "O",
        "type_prix": "fixe",
        "grille_du": date(2026, 10, 1),
        "duree_fixite_mois": 12,
        "source": "https://exemple.fr/grille.pdf",
    }
    annuel = {"abonnement_annuel_ttc": {6: 190.36}, "kwh_ttc": {"base": 0.2}}
    offre = offre_depuis_dict({**base, "options": {"base": annuel}}, "x")
    assert offre.grilles["base"].en_vigueur(6, date(2026, 10, 2)).abonnement_an == Decimal("190.36")
    deux = {**annuel, "abonnement_mensuel_ttc": {6: 15.0}}
    with pytest.raises(OffreInvalide, match="exclusifs"):
        offre_depuis_dict({**base, "options": {"base": deux}}, "x")


def test_gaz_de_bordeaux_novafixe_grille_d_octobre_2026(offres):
    """Fiche Bordeaux du 01/10/2026, NovaFixe Élec et Bonus Élec (#99, #111, #371, #372)."""
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 19).date()
    for ident in ("gaz_de_bordeaux_novafixe", "gaz_de_bordeaux_novafixe_bonus"):
        g = grilles[f"{ident}:base"].en_vigueur(6, jour)
        assert (g.debut, g.abonnement_an, g.prix) == (
            datetime(2026, 10, 1).date(),
            Decimal("190.44"),  # 15,87 x 12
            {"base": Decimal("0.18373")},
        )
        assert grilles[f"{ident}:base"].en_vigueur(15, jour).prix == {"base": Decimal("0.18233")}
        with pytest.raises(TarifIntrouvable, match="18 kVA"):  # Base de 3 à 15 kVA seulement
            grilles[f"{ident}:base"].en_vigueur(18, jour)
        g = grilles[f"{ident}:hphc"].en_vigueur(24, jour)
        assert g.abonnement_an == Decimal("469.56")  # 39,13 x 12
        assert g.prix == {"hp": Decimal("0.19648"), "hc": Decimal("0.14669")}
        with pytest.raises(TarifIntrouvable, match="3 kVA"):
            grilles[f"{ident}:hphc"].en_vigueur(3, jour)
        assert offres[ident].duree_fixite_mois == 36


def test_totalenergies_verte_fixe_grille_du_24_septembre_2026(offres):
    """Grille TTC TotalEnergies Verte Fixe du 24/09/2026, PDF officiel (#95 Base, #133 HC)."""
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 19).date()
    g = grilles["totalenergies_verte_fixe:base"].en_vigueur(3, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 9, 24).date(),
        Decimal("145.56"),  # 12,13 x 12
        {"base": Decimal("0.2540")},
    )
    assert grilles["totalenergies_verte_fixe:base"].en_vigueur(36, jour).prix == {"base": Decimal("0.2519")}
    g = grilles["totalenergies_verte_fixe:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("659.88")  # 54,99 x 12
    assert g.prix == {"hp": Decimal("0.2728"), "hc": Decimal("0.1992")}
    with pytest.raises(TarifIntrouvable, match="3 kVA"):  # pas d'option HC en 3 kVA
        grilles["totalenergies_verte_fixe:hphc"].en_vigueur(3, jour)
    assert offres["totalenergies_verte_fixe"].duree_fixite_mois == 12


def test_octopus_eco_fixe_grilles_d_octobre_2026(offres):
    """Grilles TTC Octopus Eco Fixe Plus (12/10/2026) et Eco Fixe (30/09/2026) (#29, #30, #138, #139)."""
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 19).date()
    g = grilles["octopus_eco_fixe_plus_oct2026:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 10, 12).date(),
        Decimal("190.32"),  # 15,86 x 12
        {"base": Decimal("0.1968")},
    )
    # Cellules fusionnées : 1-6 kVA puis 7-36 kVA ; 36 kVA à 54,41 €/mois.
    g = grilles["octopus_eco_fixe_plus_oct2026:base"].en_vigueur(36, jour)
    assert (g.abonnement_an, g.prix) == (Decimal("652.92"), {"base": Decimal("0.1953")})
    # HC proposée dès 3 kVA, même abonnement qu'en Base.
    g = grilles["octopus_eco_fixe_plus_oct2026:hphc"].en_vigueur(3, jour)
    assert g.abonnement_an == Decimal("145.56")  # 12,13 x 12
    assert g.prix == {"hp": Decimal("0.2106"), "hc": Decimal("0.1565")}
    g = grilles["octopus_eco_fixe_oct2026:base"].en_vigueur(9, jour)
    assert (g.debut, g.prix) == (datetime(2026, 9, 30).date(), {"base": Decimal("0.2017")})
    assert grilles["octopus_eco_fixe_oct2026:base"].en_vigueur(3, jour).prix == {"base": Decimal("0.2033")}
    g = grilles["octopus_eco_fixe_oct2026:hphc"].en_vigueur(6, jour)
    assert g.prix == {"hp": Decimal("0.2178"), "hc": Decimal("0.1613")}
    assert offres["octopus_eco_fixe_oct2026"].duree_fixite_mois == 24


def test_totalenergies_fixe_2ans_grille_du_24_septembre_2026(offres):
    """Grille TTC TotalEnergies Fixe 2 ans du 24/09/2026, PDF officiel (#25 Base, #126 HC)."""
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 19).date()
    g = grilles["totalenergies_fixe_2ans:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 9, 24).date(),
        Decimal("190.32"),  # 15,86 x 12
        {"base": Decimal("0.2270")},
    )
    # kWh Base : 0,2270 € en 3 et 6 kVA, 0,2252 € au-delà.
    assert grilles["totalenergies_fixe_2ans:base"].en_vigueur(9, jour).prix == {"base": Decimal("0.2252")}
    g = grilles["totalenergies_fixe_2ans:hphc"].en_vigueur(6, jour)
    assert g.abonnement_an == Decimal("192.60")  # 16,05 x 12
    assert g.prix == {"hp": Decimal("0.2435"), "hc": Decimal("0.1791")}
    with pytest.raises(TarifIntrouvable, match="3 kVA"):  # pas d'option HC en 3 kVA
        grilles["totalenergies_fixe_2ans:hphc"].en_vigueur(3, jour)
    assert offres["totalenergies_fixe_2ans"].duree_fixite_mois == 24


def test_edf_zen_fixe_grille_du_1er_octobre_2026(offres):
    """Grille TTC EDF Zen Fixe 2 ans du 01/10/2026, PDF EDF (#8 Base, #114 HC)."""
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 19).date()
    g = grilles["edf_zen_fixe_2ans:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 10, 1).date(),
        Decimal("190.32"),  # 15,86 x 12
        {"base": Decimal("0.2082")},
    )
    # kWh Base : 0,2082 € en 3 et 6 kVA, 0,2065 € de 9 à 36 kVA.
    assert grilles["edf_zen_fixe_2ans:base"].en_vigueur(9, jour).prix == {"base": Decimal("0.2065")}
    # 36 kVA : 53,88 x 12.
    assert grilles["edf_zen_fixe_2ans:base"].en_vigueur(36, jour).abonnement_an == Decimal("646.56")
    g = grilles["edf_zen_fixe_2ans:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("646.56")  # même abonnement qu'en Base
    assert g.prix == {"hp": Decimal("0.2231"), "hc": Decimal("0.1650")}
    with pytest.raises(TarifIntrouvable, match="3 kVA"):  # pas d'option HC en 3 kVA
        grilles["edf_zen_fixe_2ans:hphc"].en_vigueur(3, jour)
    assert offres["edf_zen_fixe_2ans"].duree_fixite_mois == 25  # 2 ans et 1 mois


def test_prudence_grille_du_1er_aout_2026(offres):
    """Grille TTC du 01/08/2026 (issue #64) : 6 kVA, abonnement 15,36 €/mois, 19,68 c€ Base."""
    grilles = grilles_offres(offres)
    g = grilles["la_bellenergie_prudence:base"].en_vigueur(6, datetime(2026, 10, 19).date())
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("184.32"),  # 15,36 € TTC/mois x 12
        {"base": Decimal("0.1968")},
    )
    g = grilles["la_bellenergie_prudence:hphc"].en_vigueur(6, datetime(2026, 10, 19).date())
    assert g.abonnement_an == Decimal("184.32")
    assert g.prix == {"hp": Decimal("0.2106"), "hc": Decimal("0.1565")}


def test_garance_abonnements_3_ans(offres):
    """Grille du 01/08/2026 (issue #63) : 6 kVA Base 20,36 €/mois, HC 9 kVA 24,66 €/mois."""
    grilles = grilles_offres(offres)
    g = grilles["la_bellenergie_garance:base"].en_vigueur(6, datetime(2026, 10, 19).date())
    assert g.abonnement_an == Decimal("244.32")  # 20,36 x 12
    assert g.prix["base"] == Decimal("0.1968")
    g = grilles["la_bellenergie_garance:hphc"].en_vigueur(9, datetime(2026, 10, 19).date())
    assert g.abonnement_an == Decimal("295.92")  # 24,66 x 12


def test_ohm_grille_du_14_octobre_2026(offres):
    """Grille du 14/10/2026 (issue #40) : 6 kVA Base 14,45 €/mois, 21,83 c€ ; HC 14,64 €/mois."""
    grilles = grilles_offres(offres)
    g = grilles["ohm_serente_fixe_1an:base"].en_vigueur(6, datetime(2026, 10, 19).date())
    assert g.debut == datetime(2026, 10, 14).date()
    assert g.abonnement_an == Decimal("173.40")  # 14,45 x 12
    assert g.prix["base"] == Decimal("0.2183")
    assert grilles["ohm_serente_fixe_1an:base"].en_vigueur(3, datetime(2026, 10, 19).date()).prix == {
        "base": Decimal("0.2001")
    }
    g = grilles["ohm_serente_fixe_1an:hphc"].en_vigueur(6, datetime(2026, 10, 19).date())
    assert g.abonnement_an == Decimal("175.68")  # 14,64 x 12
    assert g.prix == {"hp": Decimal("0.2347"), "hc": Decimal("0.1723")}


def test_alterna_hc_des_3_kva(offres):
    """Grille du 01/09/2026 (issue #44) : HC dès 3 kVA, 6 kVA Base 17,66 €/mois, 19,19 c€."""
    grilles = grilles_offres(offres)
    g = grilles["alterna_fixe_1an:hphc"].en_vigueur(3, datetime(2026, 10, 19).date())
    assert g.abonnement_an == Decimal("167.16")  # 13,93 x 12
    assert g.prix == {"hp": Decimal("0.2054"), "hc": Decimal("0.1528")}
    g = grilles["alterna_fixe_1an:base"].en_vigueur(6, datetime(2026, 10, 19).date())
    assert g.abonnement_an == Decimal("211.92")  # 17,66 x 12
    assert g.prix["base"] == Decimal("0.1919")


# Grille Week-end de l'offre verte (#330), du 01/10/2026 : abonnements € TTC/mois.
GRILLE_WEEK_END_ES = {
    3: 12.13,
    6: 15.86,
    9: 19.88,
    12: 23.76,
    15: 27.40,
    18: 31.14,
    24: 39.14,
    30: 46.47,
    36: 53.88,
}


@pytest.mark.parametrize(("puissance", "mensuel"), sorted(GRILLE_WEEK_END_ES.items()))
def test_es_verte_fixe_1an_option_week_end_toutes_puissances(offres, puissance, mensuel):
    """Option Week-end Base (#330), grille du 01/10/2026 : les neuf abonnements."""
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 19).date()
    g = grilles["es_verte_fixe_1an:week_end"].en_vigueur(puissance, jour)
    assert (g.debut, g.abonnement_an) == (datetime(2026, 10, 1).date(), Decimal(str(mensuel)) * 12)
    assert g.prix == {"semaine": Decimal("0.31108"), "week_end": Decimal("0.22878")}


@pytest.mark.parametrize(("puissance", "mensuel"), sorted(GRILLE_WEEK_END_ES.items()))
def test_es_verte_regionale_fixe_1an_option_week_end_supplement_vert(offres, puissance, mensuel):
    """Option Week-end #333 : la régionale ajoute exactement 2,27 €/mois à chaque puissance."""
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 19).date()
    g = grilles["es_verte_regionale_fixe_1an:week_end"].en_vigueur(puissance, jour)
    assert (g.debut, g.abonnement_an) == (
        datetime(2026, 10, 1).date(),
        (Decimal(str(mensuel)) + Decimal("2.27")) * 12,
    )
    assert g.prix == {"semaine": Decimal("0.31108"), "week_end": Decimal("0.22878")}


def test_es_verte_fixe_1an_option_week_end_un_kwh_samedi(offres):
    """1 kWh un samedi (24/10/2026) : 22,878 c€ + abonnement 6 kVA au prorata."""
    grilles = grilles_offres(offres)
    cout = cout_option(
        "es_verte_fixe_1an:week_end",
        grilles["es_verte_fixe_1an:week_end"],
        6,
        [(datetime(2026, 10, 24, 14), 1.0)],
        PLAGES,
    )
    assert cout.total == (Decimal("190.32") / Decimal("365") + Decimal("0.22878")).quantize(Decimal("0.01"))


# Grille « Week-end et heures creuses » de l'offre verte (#331), du 01/10/2026
# (à partir de 6 kVA) : abonnements € TTC/mois.
GRILLE_WEEK_END_HPHC_ES = {
    6: 16.05,
    9: 20.16,
    12: 24.13,
    15: 27.86,
    18: 31.70,
    24: 39.88,
    30: 47.40,
    36: 54.99,
}


@pytest.mark.parametrize(("puissance", "mensuel"), sorted(GRILLE_WEEK_END_HPHC_ES.items()))
def test_es_verte_fixe_1an_option_week_end_hphc(offres, puissance, mensuel):
    """Option Week-end et heures creuses (#331), grille du 01/10/2026 : les 4 postes croisés."""
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 19).date()
    g = grilles["es_verte_fixe_1an:week_end_hphc"].en_vigueur(puissance, jour)
    assert (g.debut, g.abonnement_an) == (datetime(2026, 10, 1).date(), Decimal(str(mensuel)) * 12)
    assert g.prix == {
        "semaine_hp": Decimal("0.32357"),
        "semaine_hc": Decimal("0.23752"),
        "week_end_hp": Decimal("0.23752"),
        "week_end_hc": Decimal("0.23752"),
    }


@pytest.mark.parametrize(("puissance", "mensuel"), sorted(GRILLE_WEEK_END_HPHC_ES.items()))
def test_es_verte_regionale_fixe_1an_option_week_end_hphc_supplement_vert(offres, puissance, mensuel):
    """Option Week-end et heures creuses #334 : la régionale ajoute 2,27 €/mois à chaque puissance."""
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 19).date()
    g = grilles["es_verte_regionale_fixe_1an:week_end_hphc"].en_vigueur(puissance, jour)
    assert (g.debut, g.abonnement_an) == (
        datetime(2026, 10, 1).date(),
        (Decimal(str(mensuel)) + Decimal("2.27")) * 12,
    )
    assert g.prix == {
        "semaine_hp": Decimal("0.32357"),
        "semaine_hc": Decimal("0.23752"),
        "week_end_hp": Decimal("0.23752"),
        "week_end_hc": Decimal("0.23752"),
    }


def test_lot_2_offres_fixes(offres):
    """Lot 2 (issues #38, #43, #56, #57, #61, #62, #65, #68) : valeurs citées des grilles."""
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 19).date()

    # Ohm Fixe 2 ans, grille du 16/10/2026 (#38) : 6 kVA 15,88 €/mois, 22,49 c€.
    g = grilles["ohm_fixe_2ans:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix["base"]) == (
        datetime(2026, 10, 16).date(),
        Decimal("190.56"),  # 15,88 x 12
        Decimal("0.2249"),
    )
    g = grilles["ohm_fixe_2ans:hphc"].en_vigueur(6, jour)
    assert g.prix == {"hp": Decimal("0.2421"), "hc": Decimal("0.1771")}

    # Alterna du coin 1 an, grille du 01/09/2026 (#43) : 6 kVA 17,66 €/mois, 19,68 c€.
    g = grilles["alterna_du_coin_1an:base"].en_vigueur(6, jour)
    assert g.abonnement_an == Decimal("211.92")  # 17,66 x 12
    assert g.prix["base"] == Decimal("0.1968")
    g = grilles["alterna_du_coin_1an:hphc"].en_vigueur(3, jour)  # HC dès 3 kVA
    assert g.abonnement_an == Decimal("167.16")  # 13,93 x 12
    assert g.prix == {"hp": Decimal("0.2107"), "hc": Decimal("0.1565")}

    # GEG fixe 3 ans, grille du 05/10/2026 (#56) : kWh HC/HP selon la puissance.
    g = grilles["geg_elec_verte_3ans:hphc"].en_vigueur(6, jour)
    assert g.prix == {"hp": Decimal("0.1983"), "hc": Decimal("0.1584")}
    g = grilles["geg_elec_verte_3ans:hphc"].en_vigueur(12, jour)
    assert g.prix == {"hp": Decimal("0.2014"), "hc": Decimal("0.1584")}
    g = grilles["geg_elec_verte_3ans:hphc"].en_vigueur(18, jour)
    assert g.prix == {"hp": Decimal("0.2014"), "hc": Decimal("0.1656")}
    g = grilles["geg_elec_verte_3ans:base"].en_vigueur(3, jour)
    assert g.prix["base"] == Decimal("0.1837")

    # ilek ÉnRFixe+, grille d'octobre 2026 (#57) : 6 kVA 25,10 €/mois, 24,00 c€.
    g = grilles["ilek_enrfixe_plus:base"].en_vigueur(6, jour)
    assert g.abonnement_an == Decimal("301.20")  # 25,10 x 12
    assert g.prix["base"] == Decimal("0.2400")

    # Primeo Fixe Confort, grille du 01/08/2026 (#61) : 6 kVA 20,16 €/mois, 16,74 c€.
    g = grilles["primeo_fixe_confort:base"].en_vigueur(6, jour)
    assert g.abonnement_an == Decimal("241.92")  # 20,16 x 12
    assert g.prix["base"] == Decimal("0.1674")
    g = grilles["primeo_fixe_confort:hphc"].en_vigueur(6, jour)
    assert g.prix == {"hp": Decimal("0.1787"), "hc": Decimal("0.1344")}

    # la bellenergie Constance, grille du 01/08/2026 (#62) : 6 kVA 17,87 €/mois.
    g = grilles["la_bellenergie_constance:base"].en_vigueur(6, jour)
    assert g.abonnement_an == Decimal("214.44")  # 17,87 x 12
    assert g.prix["base"] == Decimal("0.1968")
    g = grilles["la_bellenergie_constance:hphc"].en_vigueur(9, jour)
    assert g.abonnement_an == Decimal("266.04")  # 22,17 x 12

    # Plenitude Pleniweb 1 an, grille du 01/10/2026 (#65) : 6 kVA 18,26 €/mois, 18,37 c€.
    g = grilles["plenitude_pleniweb_1an:base"].en_vigueur(6, jour)
    assert g.abonnement_an == Decimal("219.12")  # 18,26 x 12
    assert g.prix["base"] == Decimal("0.1837")
    g = grilles["plenitude_pleniweb_1an:hphc"].en_vigueur(3, jour)  # HC dès 3 kVA
    assert g.prix == {"hp": Decimal("0.1965"), "hc": Decimal("0.1467")}

    # Sélia élec vert Fixe, grille du 21/09/2026 (#68) : abonnements TRV, 27,36 c€ Base.
    g = grilles["selia_elec_vert_fixe:base"].en_vigueur(6, jour)
    assert g.abonnement_an == Decimal("190.32")  # 15,86 x 12
    assert g.prix["base"] == Decimal("0.2736")
    g = grilles["selia_elec_vert_fixe:hphc"].en_vigueur(6, jour)
    assert g.prix == {"hp": Decimal("0.2941"), "hc": Decimal("0.2139")}


def test_cles_de_comparaison_composites(offres):
    cles = grilles_offres(offres)
    assert "la_bellenergie_prudence:base" in cles
    assert "la_bellenergie_prudence:hphc" in cles
    assert all(isinstance(g, Grilles) for g in cles.values())


def test_cout_option_prudence_sur_un_kwh(offres):
    """1 kWh un jour : abonnement au prorata (184,32 €/an ÷ 365) + 19,68 c€."""
    grilles = grilles_offres(offres)
    cout = cout_option(
        "la_bellenergie_prudence:base", grilles["la_bellenergie_prudence:base"], 6, UN_JOUR, PLAGES
    )
    assert cout.total == (Decimal("184.32") / Decimal("365") + Decimal("0.1968")).quantize(Decimal("0.01"))


def test_comparaison_trv_contre_offres(offres):
    """Le classement mélange TRV et offres.

    Avec 10 kWh un lundi (19/10/2026) : EDF Zen Week-End Plus jour choisi lundi
    (#10, 16,91 c€, 190,32 €/an : 2,21 €) bat Primeo Fixe ECO -15 % Base (17,04 c€,
    196,32 €/an : 2,24 €), elle-même devant Primeo Fixe Confort Base (16,74 c€,
    241,92 €/an : 2,34 €), le TRV Base (20,01 c€, 190,81 €/an) et GEG (18,37 c€ mais
    grille du 05/10).
    """
    from custom_components.tarifenergie.const import OPTIONS
    from custom_components.tarifenergie.modele import Grilles as GrillesTRV

    grilles = {option: GrillesTRV.charger(option) for option in OPTIONS}
    grilles.update(grilles_offres(offres))
    comp = comparer(grilles, 6, DIX_KWH, PLAGES, "base")
    assert comp.moins_chere.option == "edf_zen_week_end_plus:week_end_jour_lundi"
    assert comp.couts["primeo_fixe_eco_15:base"].total < comp.couts["primeo_fixe_confort:base"].total
    trv = comp.couts["base"]
    moins_chere = comp.couts[comp.moins_chere.option]
    assert comp.economie == (trv.total - moins_chere.total).quantize(Decimal("0.01"))
    # Puissance non proposée par l'offre : indisponible, avec la raison.
    comp3 = comparer(grilles, 3, DIX_KWH, PLAGES, "base")
    assert "la_bellenergie_prudence:hphc" in comp3.indisponibles


@pytest.mark.parametrize(
    ("donnees", "chemin_fautif"),
    [
        ({"id": "autre", "type_prix": "fixe"}, "offre.id"),
        ({"id": "x", "type_prix": "indexe"}, "offre.type_prix"),
        (
            {
                "id": "x",
                "type_prix": "fixe",
                "grille_du": "2026-08-01",
                "duree_fixite_mois": 12,
                "source": "https://exemple.fr",
                "fournisseur": "F",
                "offre": "O",
                "options": {"base": {"abonnement_mensuel_ttc": {42: 11.0}, "kwh_ttc": {"base": 0.2}}},
            },
            "abonnement_mensuel_ttc",
        ),
        (
            {
                "id": "x",
                "type_prix": "fixe",
                "grille_du": "2026-10-01",
                "duree_fixite_mois": 12,
                "source": "https://exemple.fr",
                "fournisseur": "F",
                "offre": "O",
                "options": {
                    "base": {"abonnement_mensuel_ttc": {6: 15.0}, "kwh_ttc": {"base": 0.2}},
                    "week_end_hphc": {
                        "abonnement_mensuel_ttc": {6: 15.0},
                        "kwh_ttc": {"semaine_hp": 0.3, "semaine_hc": 0.2},
                    },
                },
            },
            "offre.options.week_end_hphc",
        ),
        (
            {
                "id": "x",
                "type_prix": "fixe",
                "grille_du": "2026-10-01",
                "duree_fixite_mois": 12,
                "source": "https://exemple.fr",
                "fournisseur": "F",
                "offre": "O",
                "options": {
                    "base": {"abonnement_mensuel_ttc": {6: 15.0}, "kwh_ttc": {"base": 0.2}},
                    "week_end": {"abonnement_mensuel_ttc": {6: 15.0}, "kwh_ttc": {"semaine": 0.3}},
                },
            },
            "offre.options.week_end",
        ),
        (
            {
                "id": "x",
                "type_prix": "fixe",
                "grille_du": "2026-10-01",
                "duree_fixite_mois": 12,
                "source": "https://exemple.fr",
                "fournisseur": "F",
                "offre": "O",
                "options": {
                    "base": {"abonnement_mensuel_ttc": {6: 15.0}, "kwh_ttc": {"base": 0.2}},
                    "week_end": {"abonnement_mensuel_ttc": {6: 15.0}, "kwh_ttc": {"base": 0.3}},
                },
            },
            "offre.options.week_end",
        ),
        (
            {
                "id": "x",
                "type_prix": "fixe",
                "grille_du": "2026-10-01",
                "duree_fixite_mois": 12,
                "source": "https://exemple.fr",
                "fournisseur": "F",
                "offre": "O",
                "options": {
                    "base": {"abonnement_mensuel_ttc": {6: 15.0}, "kwh_ttc": {"base": 0.2}},
                    "week_end": {
                        "abonnement_mensuel_ttc": {6: 15.0},
                        "kwh_ttc": {"hp": 0.3, "hc": 0.2},
                    },
                },
            },
            "offre.options.week_end",
        ),
        (
            {
                "id": "x",
                "type_prix": "fixe",
                "grille_du": "2026-08-01",
                "duree_fixite_mois": 12,
                "source": "https://exemple.fr",
                "fournisseur": "F",
                "offre": "O",
                "options": {"hphc": {"abonnement_mensuel_ttc": {6: 15.0}, "kwh_ttc": {"hp": 0.2}}},
            },
            "offre.options",
        ),
    ],
)
def test_offres_invalides(donnees, chemin_fautif):
    if isinstance(donnees.get("grille_du"), str):
        from datetime import date

        donnees["grille_du"] = date.fromisoformat(donnees["grille_du"])
    with pytest.raises(OffreInvalide, match=chemin_fautif):
        offre_depuis_dict(donnees, "x")


def test_cles_par_option(offres):
    """``Offre.cles()`` : une clé ``<id>:<option>`` par option proposée, triée."""
    for offre in offres.values():
        assert offre.cles() == [f"{offre.id}:{option}" for option in sorted(offre.grilles)]


def test_charger_offre_yaml_invalide(tmp_path):
    """YAML illisible : OffreInvalide qui nomme le fichier (issue #418 : cause journalisée)."""
    from custom_components.tarifenergie.offres import charger_offre

    chemin = tmp_path / "casse.yaml"
    chemin.write_text("id: [non fermé\n", encoding="utf-8")
    with pytest.raises(OffreInvalide, match=r"casse\.yaml : YAML invalide"):
        charger_offre(chemin)


def test_charger_offre_fichier_illisible(tmp_path):
    """Octets non UTF-8 : OffreInvalide « fichier illisible »."""
    from custom_components.tarifenergie.offres import charger_offre

    chemin = tmp_path / "binaire.yaml"
    chemin.write_bytes(b"\xff\xfe\x00offre")
    with pytest.raises(OffreInvalide, match=r"binaire\.yaml : fichier illisible"):
        charger_offre(chemin)


def test_charger_offre_contenu_invalide(tmp_path):
    """YAML valide mais offre incomplète : le nom du fichier préfixe l'erreur de validation."""
    from custom_components.tarifenergie.offres import charger_offre

    chemin = tmp_path / "incomplete.yaml"
    chemin.write_text("id: x\n", encoding="utf-8")
    with pytest.raises(OffreInvalide, match=r"^incomplete\.yaml : "):
        charger_offre(chemin)


# Grille EDF Zen Week-End Plus (#10 Base, #116 HC), du 15/09/2026 : abonnements
# € TTC/mois (pas de 3 kVA), identiques pour toutes les options de l'offre.
GRILLE_ZEN_WEEK_END_PLUS = {
    6: 15.86,
    9: 19.88,
    12: 23.76,
    15: 27.40,
    18: 31.14,
    24: 39.14,
    30: 46.47,
    36: 53.88,
}


@pytest.mark.parametrize(("puissance", "mensuel"), sorted(GRILLE_ZEN_WEEK_END_PLUS.items()))
def test_zen_week_end_plus_grilles_et_jour_choisi(offres, puissance, mensuel):
    """EDF Zen Week-End Plus (#10, #116), grille du 15/09/2026 : huit abonnements, le
    jour choisi (lundi/mercredi/vendredi) porté par chaque variante, sans 3 kVA."""
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 19).date()
    for option, numero in (("lundi", 0), ("mercredi", 2), ("vendredi", 4)):
        g = grilles[f"edf_zen_week_end_plus:week_end_jour_{option}"].en_vigueur(puissance, jour)
        assert (g.debut, g.abonnement_an, g.jour_choisi) == (
            datetime(2026, 9, 15).date(),
            Decimal(str(mensuel)) * 12,
            numero,
        )
        assert g.prix == {
            "semaine": Decimal("0.2259"),
            "week_end": Decimal("0.1691"),
            "jour_choisi": Decimal("0.1691"),
        }
        g = grilles[f"edf_zen_week_end_plus:week_end_hphc_jour_{option}"].en_vigueur(puissance, jour)
        assert (g.abonnement_an, g.jour_choisi) == (Decimal(str(mensuel)) * 12, numero)
        assert g.prix == {
            "semaine_hp": Decimal("0.2314"),
            "semaine_hc": Decimal("0.1731"),
            "week_end_hp": Decimal("0.1731"),
            "week_end_hc": Decimal("0.1731"),
            "jour_choisi_hp": Decimal("0.1731"),
            "jour_choisi_hc": Decimal("0.1731"),
        }
    with pytest.raises(TarifIntrouvable, match="3 kVA"):  # pas de 3 kVA
        grilles["edf_zen_week_end_plus:week_end_jour_lundi"].en_vigueur(3, jour)


def test_zen_week_end_plus_un_kwh_selon_le_jour(offres):
    """1 kWh selon le jour : semaine 22,59 c€, samedi et jour choisi 16,91 c€ (#10)."""
    grilles = grilles_offres(offres)
    # Lundi 19/10 avec jour choisi lundi : poste jour_choisi.
    cout = cout_option(
        "edf_zen_week_end_plus:week_end_jour_lundi",
        grilles["edf_zen_week_end_plus:week_end_jour_lundi"],
        6,
        [(datetime(2026, 10, 19, 14), 1.0)],
        PLAGES,
    )
    assert cout.kwh == {"jour_choisi": Decimal("1.0")}
    # Mercredi 21/10 avec jour choisi lundi : poste semaine.
    cout = cout_option(
        "edf_zen_week_end_plus:week_end_jour_lundi",
        grilles["edf_zen_week_end_plus:week_end_jour_lundi"],
        6,
        [(datetime(2026, 10, 21, 14), 1.0)],
        PLAGES,
    )
    assert cout.kwh == {"semaine": Decimal("1.0")}
    # Samedi 24/10 : poste week_end.
    cout = cout_option(
        "edf_zen_week_end_plus:week_end_jour_lundi",
        grilles["edf_zen_week_end_plus:week_end_jour_lundi"],
        6,
        [(datetime(2026, 10, 24, 14), 1.0)],
        PLAGES,
    )
    assert cout.kwh == {"week_end": Decimal("1.0")}


def test_zen_week_end_plus_jour_choisi_hphc_repartition(offres):
    """Option HC (#116) : samedi tout en week_end_hc, vendredi choisi coupé HP/HC."""
    grilles = grilles_offres(offres)
    # Samedi 24/10, 2 kWh de 0 h à 1 h (heures creuses) : week_end_hc.
    cout = cout_option(
        "edf_zen_week_end_plus:week_end_hphc_jour_lundi",
        grilles["edf_zen_week_end_plus:week_end_hphc_jour_lundi"],
        6,
        [(datetime(2026, 10, 24, 0), 2.0), (datetime(2026, 10, 24, 14), 2.0)],
        PLAGES,
    )
    assert cout.kwh == {"week_end_hc": Decimal("2.0"), "week_end_hp": Decimal("2.0")}
    # Vendredi 23/10 avec jour choisi vendredi : jour_choisi_hp/hc.
    cout = cout_option(
        "edf_zen_week_end_plus:week_end_hphc_jour_vendredi",
        grilles["edf_zen_week_end_plus:week_end_hphc_jour_vendredi"],
        6,
        [(datetime(2026, 10, 23, 0), 2.0), (datetime(2026, 10, 23, 14), 2.0)],
        PLAGES,
    )
    assert cout.kwh == {"jour_choisi_hc": Decimal("2.0"), "jour_choisi_hp": Decimal("2.0")}
    # Mardi 20/10 avec jour choisi vendredi : semaine_hp/hc.
    cout = cout_option(
        "edf_zen_week_end_plus:week_end_hphc_jour_vendredi",
        grilles["edf_zen_week_end_plus:week_end_hphc_jour_vendredi"],
        6,
        [(datetime(2026, 10, 20, 0), 2.0), (datetime(2026, 10, 20, 14), 2.0)],
        PLAGES,
    )
    assert cout.kwh == {"semaine_hc": Decimal("2.0"), "semaine_hp": Decimal("2.0")}


def test_offre_a_jour_choisi_schema_invalide():
    """Une option à jour choisi exige ses postes exacts ; une offre sans option
    sans heures creuses (Base, week_end ou jour choisi) est refusée."""
    from datetime import date

    donnees = {
        "id": "x",
        "fournisseur": "F",
        "offre": "Jour choisi",
        "type_prix": "fixe",
        "duree_fixite_mois": 6,
        "grille_du": date(2026, 9, 15),
        "source": "https://exemple.fr/grille.pdf",
        "options": {
            "week_end_jour_lundi": {
                "abonnement_mensuel_ttc": {6: 15.86},
                "kwh_ttc": {"semaine": 0.2259, "week_end": 0.1691},  # jour_choisi manquant
            }
        },
    }
    with pytest.raises(OffreInvalide, match="attendus"):
        offre_depuis_dict(donnees, "x")
    # Seule une option à heures creuses : pas d'option Base pour comparer.
    donnees["options"] = {
        "week_end_hphc_jour_lundi": {
            "abonnement_mensuel_ttc": {6: 15.86},
            "kwh_ttc": {
                "semaine_hp": 0.2314,
                "semaine_hc": 0.1731,
                "week_end_hp": 0.1731,
                "week_end_hc": 0.1731,
                "jour_choisi_hp": 0.1731,
                "jour_choisi_hc": 0.1731,
            },
        }
    }
    with pytest.raises(OffreInvalide, match="option Base attendue"):
        offre_depuis_dict(donnees, "x")
