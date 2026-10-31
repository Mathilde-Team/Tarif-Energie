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
        "bitche_trv_local",
        "cesml_trv_local",
        "dyneff_contrat_plus",
        "dyneff_contrat_plus_verte",
        "edf_vert_electrique",
        "edf_vert_electrique_regional",
        "edf_vert_electrique_week_end",
        "edf_zen_estival",
        "edf_zen_fixe_2ans",
        "edf_zen_online",
        "edf_zen_week_end",
        "edf_zen_week_end_plus",
        "elmy_prix_fixe_2ans",
        "enercoop",
        "energis_trv_local",
        "enes_creutzwald_trv_local",
        "enes_hagondange_trv_local",
        "enes_hombourg_haut_trv_local",
        "enes_schoeneck_trv_local",
        "engie_duo_reference_3ans",
        "engie_elec_reference_3ans",
        "es_trv_local",
        "es_verte_fixe_1an",
        "es_verte_regionale_fixe_1an",
        "gascogne_trv_local",
        "gaz_de_bordeaux_novafixe",
        "gaz_de_bordeaux_novafixe_bonus",
        "gaz_de_bordeaux_novafixe_bonus_duo",
        "gaz_de_bordeaux_novaflex",
        "gazelec_peronne_trv_local",
        "gedia_all_inclusive",
        "gedia_trv_local",
        "geg_direct_producteur_3ans",
        "geg_elec_verte_3ans",
        "geg_trv_local",
        "happe_elec_1an",
        "hunelec_prix_fixe_1an",
        "hunelec_prix_fixe_1an_vert",
        "ilek_enrfixe_plus",
        "ilek_voiture_electrique",
        "jeety_elec_dom",
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
        "montois_trv_local",
        "octopus_eco_fixe_oct2026",
        "octopus_eco_fixe_plus_oct2026",
        "ohm_extra_eco",
        "ohm_fixe_2ans",
        "ohm_premiohm",
        "ohm_serente_fixe_1an",
        "oya_trv_local",
        "papernest_verte_1an",
        "pierrevillers_trv_local",
        "plenitude_pleniweb_1an",
        "primeo_essentielle_verte",
        "primeo_fixe_confort",
        "primeo_fixe_eco_15",
        "rombas_trv_local",
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
        "totalenergies_charge_heures",
        "totalenergies_fixe_2ans",
        "totalenergies_heures_eco",
        "totalenergies_speciale",
        "totalenergies_verte_fixe",
        "uem_trv_local",
        "ume_trv_local",
        "urban_solar_smb",
        "vialis_trv_local",
        "wekiwi_duo_aurore",
    ]
    # Chaque offre propose au moins une option sans heures creuses (sa « Base ») :
    # base, week_end, une variante à jour choisi (#10) ou des postes saisonniers
    # (#20 : Zen Estival porte ses plages, un client sans HC y est simulable).
    # Zen Week-End Plus n'a pas de Base classique : « week-end + jour choisi ».
    assert all(
        {
            "base",
            "week_end",
            "week_end_jour_lundi",
            "week_end_jour_mercredi",
            "week_end_jour_vendredi",
            "hphc_saisonnieres",
        }
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


def test_jeety_elec_dom_grille_du_1er_fevrier_2026(offres):
    """Jeety Energy Elec-Dom (#59 Base, #161 HC) : indexée TRV, grille de février 2026
    jamais revue au mouvement du TRV du 01/08/2026 (dernière publiée, page tarifs)."""
    offre = offres["jeety_elec_dom"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("indexe_trv", None, None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 28).date()
    # Base : 0,1940 € jusqu'à 6 kVA, 0,1927 € au-delà.
    g = grilles["jeety_elec_dom:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 2, 1).date(),
        Decimal("188.40"),  # 15,70 x 12
        {"base": Decimal("0.1940")},
    )
    assert grilles["jeety_elec_dom:base"].en_vigueur(3, jour).abonnement_an == Decimal("144.36")  # 12,03 x 12
    g = grilles["jeety_elec_dom:base"].en_vigueur(36, jour)
    assert (g.abonnement_an, g.prix) == (Decimal("630.48"), {"base": Decimal("0.1927")})  # 52,54 x 12
    # HP/HC : publiée dès 6 kVA seulement (3 kVA « non indiqué » sur la page).
    g = grilles["jeety_elec_dom:hphc"].en_vigueur(6, jour)
    assert (g.abonnement_an, g.prix) == (
        Decimal("195.12"),  # 16,26 x 12
        {"hp": Decimal("0.2065"), "hc": Decimal("0.1579")},
    )
    # 55,15 x 12
    assert grilles["jeety_elec_dom:hphc"].en_vigueur(36, jour).abonnement_an == Decimal("661.80")
    with pytest.raises(TarifIntrouvable, match="3 kVA"):
        grilles["jeety_elec_dom:hphc"].en_vigueur(3, jour)


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


def test_totalenergies_speciale_reprend_le_trv(offres):
    """TotalEnergies Spéciale Électricité et Gaz, partie élec (#96, #134) : copie de la grille d'Heures Eco.

    Décision du 28/10/2026 (commentaire de #96) : un fichier par offre, avec une
    copie de la grille de la partie électricité (duale : seule l'électricité
    entre dans le comparateur). Base et HP/HC (#96, #134), la partie
    gaz est documentée hors moteur (#112). La remise annoncée de 10 % n'est pas
    modélisée (grille PDF hors remise).
    """
    offre = offres["totalenergies_speciale"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("indexe_trv", None, None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 24).date()
    g = grilles["totalenergies_speciale:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 10, 1).date(),
        Decimal("190.32"),  # 15,86 x 12
        {"base": Decimal("0.2001")},
    )
    assert grilles["totalenergies_speciale:base"].en_vigueur(36, jour).prix == {"base": Decimal("0.1985")}
    g = grilles["totalenergies_speciale:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("646.56")  # 53,88 x 12
    assert g.prix == {"hp": Decimal("0.2142"), "hc": Decimal("0.1589")}
    with pytest.raises(TarifIntrouvable, match="3 kVA"):  # pas d'option HC en 3 kVA
        grilles["totalenergies_speciale:hphc"].en_vigueur(3, jour)


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


def test_edf_vert_electrique_regional_revisable(offres):
    """EDF Vert Électrique Régional (#18, #119) : « Autre offre » CRE révisable, grille du 15/09/2026."""
    offre = offres["edf_vert_electrique_regional"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("revisable", None, None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 24).date()
    g = grilles["edf_vert_electrique_regional:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 9, 15).date(),
        Decimal("190.32"),  # 15,86 x 12
        {"base": Decimal("0.2037")},  # moins cher qu'à 9 kVA, à l'inverse des autres offres EDF
    )
    g = grilles["edf_vert_electrique_regional:base"].en_vigueur(9, jour)
    assert g.prix == {"base": Decimal("0.2065")}
    g = grilles["edf_vert_electrique_regional:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("646.56")  # 53,88 x 12
    assert g.prix == {"hp": Decimal("0.2237"), "hc": Decimal("0.1560")}
    for option in ("base", "hphc"):  # pas d'option en 3 kVA
        with pytest.raises(TarifIntrouvable, match="3 kVA"):
            grilles[f"edf_vert_electrique_regional:{option}"].en_vigueur(3, jour)


def test_edf_vert_electrique_revisable(offres):
    """EDF Vert Électrique Base (#9) : « Autre offre » CRE révisable, grille du 15/09/2026."""
    offre = offres["edf_vert_electrique"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("revisable", None, None)
    grilles = grilles_offres(offres)
    assert "edf_vert_electrique:hphc" not in grilles  # #115 : pas de grille HC publiée
    jour = datetime(2026, 10, 24).date()
    g = grilles["edf_vert_electrique:base"].en_vigueur(3, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 9, 15).date(),
        Decimal("145.56"),  # 12,13 x 12
        {"base": Decimal("0.2022")},
    )
    g = grilles["edf_vert_electrique:base"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("646.56")  # 53,88 x 12
    assert g.prix == {"base": Decimal("0.2007")}


def test_ohm_extra_eco_revisable(offres):
    """Ohm Énergie Extra Éco (#37 Base, #145 HC) : révisable 2 fois par an, grille du 01/09/2026."""
    offre = offres["ohm_extra_eco"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("revisable", None, None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 24).date()
    g = grilles["ohm_extra_eco:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 9, 1).date(),
        Decimal("183.36"),  # 15,28 x 12
        {"base": Decimal("0.1940")},
    )
    assert grilles["ohm_extra_eco:base"].en_vigueur(36, jour).abonnement_an == Decimal("622.92")  # 51,91 x 12
    with pytest.raises(TarifIntrouvable):  # avant la grille du 01/09/2026
        grilles["ohm_extra_eco:base"].en_vigueur(6, datetime(2026, 8, 31).date())
    g = grilles["ohm_extra_eco:hphc"].en_vigueur(6, jour)
    assert g.abonnement_an == Decimal("180.72")  # 15,06 x 12
    assert g.prix == {"hp": Decimal("0.2065"), "hc": Decimal("0.1579")}
    with pytest.raises(TarifIntrouvable, match="3 kVA"):  # HC à partir de 4 kVA
        grilles["ohm_extra_eco:hphc"].en_vigueur(3, jour)


@pytest.mark.parametrize("type_prix", ["indexe_trv", "revisable"])
@pytest.mark.parametrize(
    ("extra", "chemin_fautif"),
    [
        ({"duree_fixite_mois": 12}, "offre.duree_fixite_mois"),  # prix sans durée de fixité
        ({"eld": "x"}, "offre.eld"),  # réservé aux TRV locaux
    ],
)
def test_indexee_trv_invalide(extra, chemin_fautif, type_prix):
    from datetime import date

    donnees = {
        "id": "x",
        "fournisseur": "F",
        "offre": "Indexée",
        "type_prix": type_prix,
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


def test_ilek_voiture_electrique_base_indexee_trv(offres):
    """ilek Offre Voiture électrique (#58) : kWh HT du TRV, abonnement ilek, Base seule."""
    offre = offres["ilek_voiture_electrique"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("indexe_trv", None, None)
    grilles = grilles_offres(offres)
    assert "ilek_voiture_electrique:hphc" not in grilles  # plages propres à ilek (#159, #160)
    jour = datetime(2026, 10, 24).date()
    g = grilles["ilek_voiture_electrique:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("301.20"),  # 25,10 x 12, bien au-dessus du TRV
        {"base": Decimal("0.2001")},  # kWh TTC du TRV
    )
    g = grilles["ilek_voiture_electrique:base"].en_vigueur(36, jour)
    assert (g.abonnement_an, g.prix) == (Decimal("1064.88"), {"base": Decimal("0.1985")})


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


def test_engie_duo_reference_grille_d_octobre_2026(offres):
    """Engie Duo Référence 3 ans, partie électricité — Base (#98) : copie de la grille d'Elec Référence.

    Décision du 28/10/2026 (commentaire de #98) : un fichier par offre, avec une
    copie de la grille de la partie électricité. Base seule ici (CU) ; le HP/HC
    est en #135, la partie gaz est documentée hors moteur (#113).
    """
    offre = offres["engie_duo_reference_3ans"]
    assert (offre.type_prix, offre.duree_fixite_mois) == ("fixe", 36)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 19).date()
    g = grilles["engie_duo_reference_3ans:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 10, 1).date(),
        Decimal("195.18"),
        {"base": Decimal("0.24205")},
    )
    g = grilles["engie_duo_reference_3ans:base"].en_vigueur(36, jour)
    assert (g.abonnement_an, g.prix) == (Decimal("667.55"), {"base": Decimal("0.24377")})
    assert "engie_duo_reference_3ans:hphc" not in grilles  # option HP/HC en #135


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


def test_enes_hombourg_haut_trv_local_grille_du_1er_aout_2026(offres):
    """TRV local Enes Hombourg-Haut (#277, #278) : grille unique Enes, images du dossier
    « creutzwald » (décision du propriétaire du 28/10/2026)."""
    offre = offres["enes_hombourg_haut_trv_local"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == (
        "reglemente",
        "enes_hombourg_haut",
        None,
    )
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 24).date()
    g = grilles["enes_hombourg_haut_trv_local:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("191.42"),
        {"base": Decimal("0.20006")},
    )
    # Base 9-36 kVA en extinction, publiée pour les contrats en cours
    g = grilles["enes_hombourg_haut_trv_local:base"].en_vigueur(36, jour)
    assert (g.abonnement_an, g.prix) == (Decimal("652.92"), {"base": Decimal("0.19850")})
    g = grilles["enes_hombourg_haut_trv_local:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("669.06")
    assert g.prix == {"hp": Decimal("0.21422"), "hc": Decimal("0.15890")}


def test_enes_schoeneck_trv_local_grille_du_1er_aout_2026(offres):
    """TRV local Enes Schoeneck (#279, #280) : grille unique Enes, images du dossier
    « creutzwald » (décision du propriétaire du 28/10/2026)."""
    offre = offres["enes_schoeneck_trv_local"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == (
        "reglemente",
        "enes_schoeneck",
        None,
    )
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 24).date()
    g = grilles["enes_schoeneck_trv_local:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("191.42"),
        {"base": Decimal("0.20006")},
    )
    # Base 9-36 kVA en extinction, publiée pour les contrats en cours
    g = grilles["enes_schoeneck_trv_local:base"].en_vigueur(36, jour)
    assert (g.abonnement_an, g.prix) == (Decimal("652.92"), {"base": Decimal("0.19850")})
    g = grilles["enes_schoeneck_trv_local:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("669.06")
    assert g.prix == {"hp": Decimal("0.21422"), "hc": Decimal("0.15890")}


def test_bitche_trv_local_grille_du_1er_aout_2026(offres):
    """TRV local Régie de Bitche (#283, #284) : abonnements annuels identiques
    Base et HC, Base 9-36 kVA en extinction."""
    offre = offres["bitche_trv_local"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("reglemente", "bitche", None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 24).date()
    g = grilles["bitche_trv_local:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("171.94"),
        {"base": Decimal("0.2001")},
    )
    # Base 9-36 kVA en extinction, publiée pour les contrats en cours
    g = grilles["bitche_trv_local:base"].en_vigueur(36, jour)
    assert (g.abonnement_an, g.prix) == (Decimal("571.82"), {"base": Decimal("0.1985")})
    # HC dès 3 kVA, mêmes abonnements qu'en Base
    g = grilles["bitche_trv_local:hphc"].en_vigueur(3, jour)
    assert g.abonnement_an == Decimal("132.77")
    assert g.prix == {"hp": Decimal("0.2142"), "hc": Decimal("0.1589")}
    g = grilles["bitche_trv_local:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("571.82")
    assert g.prix == {"hp": Decimal("0.2142"), "hc": Decimal("0.1589")}


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


def test_cesml_trv_local_grille_du_1er_aout_2026(offres):
    """TRV local de CESML (#248 Base, #249 HC) : grille résidentielle du 01/08/2026."""
    offre = offres["cesml_trv_local"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("reglemente", "cesml", None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 11, 1).date()
    g = grilles["cesml_trv_local:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("190.32"),
        {"base": Decimal("0.2001")},
    )
    # Base 9-36 kVA en extinction, publiée pour les contrats en cours
    g = grilles["cesml_trv_local:base"].en_vigueur(36, jour)
    assert (g.abonnement_an, g.prix) == (Decimal("646.56"), {"base": Decimal("0.1985")})
    # HC dès 3 kVA, même abonnement mensuel que la Base (12,13 €/mois)
    g = grilles["cesml_trv_local:hphc"].en_vigueur(3, jour)
    assert g.abonnement_an == Decimal("145.56")
    assert g.prix == {"hp": Decimal("0.2142"), "hc": Decimal("0.1589")}


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


def test_gazelec_peronne_trv_local_grille_du_1er_aout_2026(offres):
    """TRV local de Gazélec Péronne (#208 Base, #209 HC) : annexe tarifaire du 01/08/2026."""
    offre = offres["gazelec_peronne_trv_local"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("reglemente", "gazelec_peronne", None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 31).date()
    g = grilles["gazelec_peronne_trv_local:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("190.35"),
        {"base": Decimal("0.2001")},
    )
    # Base 9-36 kVA en extinction, publiée pour les contrats en cours
    g = grilles["gazelec_peronne_trv_local:base"].en_vigueur(12, jour)
    assert (g.abonnement_an, g.prix) == (Decimal("285.13"), {"base": Decimal("0.1985")})
    # HC publiée dès 3 kVA, au même abonnement que la Base
    g = grilles["gazelec_peronne_trv_local:hphc"].en_vigueur(3, jour)
    assert g.abonnement_an == Decimal("145.56")
    assert g.prix == {"hp": Decimal("0.2142"), "hc": Decimal("0.1589")}


def test_enes_hagondange_trv_local_grille_du_1er_aout_2026(offres):
    """TRV local d'Enes Hagondange (#203 Base, #204 HC) : grille HTML du 01/08/2026."""
    offre = offres["enes_hagondange_trv_local"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("reglemente", "enes_hagondange", None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 31).date()
    g = grilles["enes_hagondange_trv_local:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("190.36"),
        {"base": Decimal("0.2000")},
    )
    # Base 9-36 kVA en extinction, publiée pour les contrats en cours
    g = grilles["enes_hagondange_trv_local:base"].en_vigueur(36, jour)
    assert (g.abonnement_an, g.prix) == (Decimal("646.51"), {"base": Decimal("0.1985")})
    # HC publiée dès 3 kVA (146,68 €/an)
    g = grilles["enes_hagondange_trv_local:hphc"].en_vigueur(3, jour)
    assert g.abonnement_an == Decimal("146.68")
    assert g.prix == {"hp": Decimal("0.2142"), "hc": Decimal("0.1589")}
    g = grilles["enes_hagondange_trv_local:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("659.92")


@pytest.mark.parametrize(
    ("cle", "eld"),
    [
        ("montois_trv_local", "regie_montois_la_montagne"),
        ("pierrevillers_trv_local", "regie_pierrevillers"),
        ("rombas_trv_local", "seml_omega_rombas"),
    ],
)
def test_omega_trv_local_grille_commune_du_1er_aout_2026(offres, cle, eld):
    """TRV locaux OMEGA : Montois (#224, #225), Pierrevillers (#227, #228), Rombas (#230, #231).

    Grille commune OMEGA du 01/08/2026, un fichier par régie (décision du 28/10/2026, #224) :
    mêmes prix qu'Amnéville, réseau propre dans ``eld``.
    """
    offre = offres[cle]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("reglemente", eld, None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 31).date()
    g = grilles[f"{cle}:base"].en_vigueur(3, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("145.56"),
        {"base": Decimal("0.2000")},
    )
    # Base 9-36 kVA en extinction, publiée pour les contrats en cours
    g = grilles[f"{cle}:base"].en_vigueur(9, jour)
    assert (g.abonnement_an, g.prix) == (Decimal("238.61"), {"base": Decimal("0.1985")})
    g = grilles[f"{cle}:hphc"].en_vigueur(6, jour)
    assert g.abonnement_an == Decimal("192.59")
    assert g.prix == {"hp": Decimal("0.2142"), "hc": Decimal("0.1589")}
    with pytest.raises(TarifIntrouvable, match="3 kVA"):  # pas d'option HC en 3 kVA
        grilles[f"{cle}:hphc"].en_vigueur(3, jour)
    # Mêmes grilles qu'Amnéville, au centime près
    for option, puissance in (("base", 36), ("hphc", 36)):
        ref = grilles[f"amneville_trv_local:{option}"].en_vigueur(puissance, jour)
        g = grilles[f"{cle}:{option}"].en_vigueur(puissance, jour)
        assert (g.abonnement_an, g.prix) == (ref.abonnement_an, ref.prix)


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


def test_gaz_de_bordeaux_novafixe_bonus_duo_grille_d_octobre_2026(offres):
    """Partie électricité du Duo, fiche Bordeaux du 01/10/2026 (#181, #336).

    Même grille que NovaFixe Bonus Élec (#99, #371) : la partie électricité
    de l'offre duale est le contrat NovaFixe Bonus Élec (règlement de l'offre).
    """
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 19).date()
    g = grilles["gaz_de_bordeaux_novafixe_bonus_duo:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 10, 1).date(),
        Decimal("190.44"),  # 15,87 x 12
        {"base": Decimal("0.18373")},
    )
    g = grilles["gaz_de_bordeaux_novafixe_bonus_duo:hphc"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 10, 1).date(),
        Decimal("190.44"),  # 15,87 x 12
        {"hp": Decimal("0.19648"), "hc": Decimal("0.14669")},
    )
    assert grilles["gaz_de_bordeaux_novafixe_bonus_duo:hphc"].en_vigueur(36, jour).abonnement_an == (
        Decimal("646.56")  # 53,88 x 12
    )
    with pytest.raises(TarifIntrouvable, match="3 kVA"):  # HP/HC dès 6 kVA seulement
        grilles["gaz_de_bordeaux_novafixe_bonus_duo:hphc"].en_vigueur(3, jour)
    with pytest.raises(TarifIntrouvable, match="18 kVA"):  # Base de 3 à 15 kVA seulement
        grilles["gaz_de_bordeaux_novafixe_bonus_duo:base"].en_vigueur(18, jour)
    assert offres["gaz_de_bordeaux_novafixe_bonus_duo"].duree_fixite_mois == 36


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


def test_elmy_prix_fixe_2ans_grille_du_1er_aout_2026(offres):
    """Grille elmy Particuliers prix fixe 2 ans du 01/08/2026, PDF elmy (#104 Base, #176 HC)."""
    offre = offres["elmy_prix_fixe_2ans"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("fixe", None, 24)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 25).date()
    g = grilles["elmy_prix_fixe_2ans:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("190.32"),  # 15,86 x 12
        {"base": Decimal("0.2323")},
    )
    # kWh Base : 0,2323 € en 3 et 6 kVA, 0,2307 € de 9 à 36 kVA.
    assert grilles["elmy_prix_fixe_2ans:base"].en_vigueur(9, jour).prix == {"base": Decimal("0.2307")}
    # 36 kVA : 54,90 x 12.
    assert grilles["elmy_prix_fixe_2ans:base"].en_vigueur(36, jour).abonnement_an == Decimal("658.80")
    g = grilles["elmy_prix_fixe_2ans:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("569.88")  # 47,49 x 12
    assert g.prix == {"hp": Decimal("0.2489"), "hc": Decimal("0.1848")}
    with pytest.raises(TarifIntrouvable, match="3 kVA"):  # pas d'option HC en 3 kVA
        grilles["elmy_prix_fixe_2ans:hphc"].en_vigueur(3, jour)


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


# Grille EDF Zen Week-End (#12 Base, #117 HC), du 15/09/2026 : abonnements
# € TTC/mois, identiques aux deux options (la Base existe dès 3 kVA).
GRILLE_ZEN_WEEK_END = {
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


@pytest.mark.parametrize(("puissance", "mensuel"), sorted(GRILLE_ZEN_WEEK_END.items()))
def test_zen_week_end_grilles(offres, puissance, mensuel):
    """EDF Zen Week-End (#12, #117), grille du 15/09/2026 : neuf abonnements en Base
    (week_end), huit en heures creuses (week_end_hphc, pas de 3 kVA)."""
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 19).date()
    g = grilles["edf_zen_week_end:week_end"].en_vigueur(puissance, jour)
    assert (g.debut, g.abonnement_an, g.jour_choisi) == (
        datetime(2026, 9, 15).date(),
        Decimal(str(mensuel)) * 12,
        None,
    )
    assert g.prix == {"semaine": Decimal("0.2285"), "week_end": Decimal("0.1710")}
    if puissance == 3:
        with pytest.raises(TarifIntrouvable, match="3 kVA"):  # pas d'option HC en 3 kVA
            grilles["edf_zen_week_end:week_end_hphc"].en_vigueur(3, jour)
    else:
        g = grilles["edf_zen_week_end:week_end_hphc"].en_vigueur(puissance, jour)
        assert (g.abonnement_an, g.jour_choisi) == (Decimal(str(mensuel)) * 12, None)
        assert g.prix == {
            "semaine_hp": Decimal("0.2359"),
            "semaine_hc": Decimal("0.1762"),
            "week_end_hp": Decimal("0.1762"),
            "week_end_hc": Decimal("0.1762"),
        }


def test_zen_week_end_un_kwh_samedi(offres):
    """1 kWh un samedi (24/10/2026) : 17,10 c€ + abonnement 6 kVA au prorata (#12)."""
    grilles = grilles_offres(offres)
    cout = cout_option(
        "edf_zen_week_end:week_end",
        grilles["edf_zen_week_end:week_end"],
        6,
        [(datetime(2026, 10, 24, 14), 1.0)],
        PLAGES,
    )
    assert cout.kwh == {"week_end": Decimal("1.0")}
    assert cout.total == (Decimal("190.32") / Decimal("365") + Decimal("0.1710")).quantize(Decimal("0.01"))


# Grille EDF Vert Électrique Week-End (#19 Base, #120 HC), du 15/09/2026 : abonnements
# € TTC/mois (pas de 3 kVA) ; l'option HC publie 39,88 et 47,40 € en 24 et 30 kVA.
GRILLE_VERT_WEEK_END = {
    6: (15.86, 15.86),
    9: (19.88, 19.88),
    12: (23.76, 23.76),
    15: (27.40, 27.40),
    18: (31.14, 31.14),
    24: (39.14, 39.88),
    30: (46.47, 47.40),
    36: (53.88, 53.88),
}


@pytest.mark.parametrize(("puissance", "mensuels"), sorted(GRILLE_VERT_WEEK_END.items()))
def test_vert_electrique_week_end_grilles(offres, puissance, mensuels):
    """EDF Vert Électrique Week-End (#19, #120), grille du 15/09/2026 : huit abonnements
    par option, ceux de 24 et 30 kVA propres à l'option HC, sans 3 kVA."""
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 19).date()
    base, hc = mensuels
    g = grilles["edf_vert_electrique_week_end:week_end"].en_vigueur(puissance, jour)
    assert (g.debut, g.abonnement_an) == (datetime(2026, 9, 15).date(), Decimal(str(base)) * 12)
    assert g.prix == {"semaine": Decimal("0.2171"), "week_end": Decimal("0.1630")}
    g = grilles["edf_vert_electrique_week_end:week_end_hphc"].en_vigueur(puissance, jour)
    assert g.abonnement_an == Decimal(str(hc)) * 12
    assert g.prix == {
        "semaine_hp": Decimal("0.2259"),
        "semaine_hc": Decimal("0.1691"),
        "week_end_hp": Decimal("0.1691"),
        "week_end_hc": Decimal("0.1691"),
    }


def test_vert_electrique_week_end_sans_3_kva(offres):
    """Ni l'option Week-End ni l'option HC ne sont proposées en 3 kVA (#19, #120)."""
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 19).date()
    for option in ("week_end", "week_end_hphc"):
        with pytest.raises(TarifIntrouvable, match="3 kVA"):
            grilles[f"edf_vert_electrique_week_end:{option}"].en_vigueur(3, jour)


def test_vert_electrique_week_end_jour_ferie(offres):
    """1 kWh le mercredi 11/11/2026 (férié national) : tarif week-end 16,30 c€ (#19)."""
    grilles = grilles_offres(offres)
    cout = cout_option(
        "edf_vert_electrique_week_end:week_end",
        grilles["edf_vert_electrique_week_end:week_end"],
        6,
        [(datetime(2026, 11, 11, 14), 1.0)],
        PLAGES,
    )
    assert cout.kwh == {"week_end": Decimal("1.0")}
    assert cout.energie == Decimal("0.1630")


def test_zen_estival_grille_et_saisons(offres):
    """Zen Estival HP/HC (#20) : grille du 15/09/2026, postes saisonniers été/hiver."""
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 19).date()
    g = grilles["edf_zen_estival:hphc_saisonnieres"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.option) == (
        datetime(2026, 9, 15).date(),
        Decimal("151.20"),  # 12,60 x 12
        "edf_zen_estival:hphc_saisonnieres",
    )
    assert g.prix == {
        "ete_hsc": Decimal("0.1252"),
        "ete_hc": Decimal("0.1607"),
        "ete_hp": Decimal("0.2707"),
        "hiver_hc": Decimal("0.1738"),
        "hiver_hp": Decimal("0.2802"),
    }
    assert [(s.nom, s.debut, s.fin) for s in g.saisons] == [
        ("ete", (4, 15), (9, 30)),
        ("hiver", (10, 1), (4, 14)),
    ]
    assert [s.hsc for s in g.saisons] == [((120, 360), (1320, 1440)), ()]
    assert [s.hc for s in g.saisons] == [((360, 450), (780, 960)), ((1350, 390), (750, 870))]


def test_zen_estival_cout_saisonnier(offres):
    """Été : HSC 02-06/22-24, HC 06-07:30/13-16 ; hiver : HC 22:30-06:30/12:30-14:30."""
    grilles = grilles_offres(offres)
    grilles_option = grilles["edf_zen_estival:hphc_saisonnieres"]
    # Été (20/09/2026) : 3 h en HSC, 6 h en HC (06:00-07:30), 8 h et 20 h en HP.
    conso_ete = [(datetime(2026, 9, 20, h, 0), 1.0) for h in (3, 6, 8, 20)]
    cout = cout_option("hphc_saisonnieres", grilles_option, 6, conso_ete)
    assert cout.kwh == {"ete_hsc": Decimal(1), "ete_hc": Decimal(1), "ete_hp": Decimal(2)}
    assert cout.energie == Decimal("0.1252") + Decimal("0.1607") + 2 * Decimal("0.2707")
    # Hiver (19/10/2026) : 3 h en HC (22:30-06:30), 13 h en HC (12:30-14:30), 20 h en HP.
    conso_hiver = [(datetime(2026, 10, 19, h, 0), 1.0) for h in (3, 13, 20)]
    cout = cout_option("hphc_saisonnieres", grilles_option, 6, conso_hiver)
    assert cout.kwh == {"hiver_hc": Decimal(2), "hiver_hp": Decimal(1)}
    assert cout.energie == 2 * Decimal("0.1738") + Decimal("0.2802")
    # Charnières : le 14/04 est hiver, le 15/04 été (plages d'été dès le 15/04).
    conso_charniere = [(datetime(2027, 4, 14, 3, 0), 1.0), (datetime(2027, 4, 15, 3, 0), 1.0)]
    cout = cout_option("hphc_saisonnieres", grilles_option, 6, conso_charniere)
    assert cout.kwh == {
        "hiver_hc": Decimal(1),
        "hiver_hp": Decimal(0),
        "ete_hsc": Decimal(1),
        "ete_hc": Decimal(0),
        "ete_hp": Decimal(0),
    }


def test_zen_estival_comparable_sans_heures_creuses(offres):
    """Les plages sont portées par l'offre : aucun client n'est exclu (issue #20)."""
    grilles = grilles_offres(offres)
    conso = [(datetime(2026, 9, 20, 20, 0), 2.0)]  # 20 h : heures pleines d'été
    comparaison = comparer(
        {k: v for k, v in grilles.items() if k.startswith("edf_zen_estival")},
        6,
        conso,
        PlagesHC.lire("23:30-06:30"),  # plages du compteur : sans effet ici
        "base",
    )
    assert "edf_zen_estival:hphc_saisonnieres" in comparaison.couts
    assert comparaison.couts["edf_zen_estival:hphc_saisonnieres"].kwh == {
        "ete_hsc": Decimal(0),
        "ete_hc": Decimal(0),
        "ete_hp": Decimal(2),
    }


def _zen_estival_dict(**remplacements):
    donnees = {
        "id": "x",
        "fournisseur": "F",
        "offre": "Saisonnière",
        "type_prix": "fixe",
        "grille_du": datetime(2026, 9, 15).date(),
        "duree_fixite_mois": 12,
        "source": "https://exemple.fr/grille.pdf",
        "options": {
            "hphc_saisonnieres": {
                "abonnement_mensuel_ttc": {6: 12.6},
                "saisons": {
                    "ete": {
                        "du": "04-15",
                        "au": "09-30",
                        "plages": {"hsc": "02:00-06:00", "hc": "13:00-16:00"},
                        "kwh_ttc": {"hsc": 0.1252, "hc": 0.1607, "hp": 0.2707},
                    },
                    "hiver": {
                        "du": "10-01",
                        "au": "04-14",
                        "plages": {"hc": "22:30-06:30"},
                        "kwh_ttc": {"hc": 0.1738, "hp": 0.2802},
                    },
                },
            }
        },
    }
    for cle, valeur in remplacements.items():
        if valeur is None:
            donnees["options"]["hphc_saisonnieres"]["saisons"].pop(cle)
        else:
            donnees["options"]["hphc_saisonnieres"]["saisons"][cle] = valeur
    return donnees


@pytest.mark.parametrize(
    ("remplacement", "message"),
    [
        # L'été ne commence que le 01/05 : l'année n'est plus partitionnée.
        (
            {
                "ete": {
                    "du": "05-01",
                    "au": "09-30",
                    "plages": {"hsc": "02:00-06:00", "hc": "13:00-16:00"},
                    "kwh_ttc": {"hsc": 0.1252, "hc": 0.1607, "hp": 0.2707},
                }
            },
            "partitionner",
        ),
        # HSC à l'intérieur des HC : chevauchement interdit.
        (
            {
                "ete": {
                    "du": "04-15",
                    "au": "09-30",
                    "plages": {"hsc": "13:30-14:00", "hc": "13:00-16:00"},
                    "kwh_ttc": {"hsc": 0.1252, "hc": 0.1607, "hp": 0.2707},
                }
            },
            "chevaucher",
        ),
        # Postes incomplets pour l'été (HP manquant).
        (
            {
                "ete": {
                    "du": "04-15",
                    "au": "09-30",
                    "plages": {"hsc": "02:00-06:00", "hc": "13:00-16:00"},
                    "kwh_ttc": {"hsc": 0.1252, "hc": 0.1607},
                }
            },
            "postes attendus : hc et hp",
        ),
        # Borne illisible.
        (
            {
                "ete": {
                    "du": "15/04",
                    "au": "09-30",
                    "plages": {"hsc": "02:00-06:00", "hc": "13:00-16:00"},
                    "kwh_ttc": {"hsc": 0.1252, "hc": 0.1607, "hp": 0.2707},
                }
            },
            "MM-JJ",
        ),
        # Hiver sans ses plages HC.
        (
            {"hiver": {"du": "10-01", "au": "04-14", "kwh_ttc": {"hc": 0.1738, "hp": 0.2802}}},
            "plages hc attendues",
        ),
    ],
)
def test_zen_estival_saisons_invalides(remplacement, message):
    with pytest.raises(OffreInvalide, match=message):
        offre_depuis_dict(_zen_estival_dict(**remplacement), "x")


def test_zen_estival_hiver_seul_refuse():
    """Une offre saisonnière sans l'été : postes et partitionnement impossibles."""
    donnees = _zen_estival_dict(ete=None)
    with pytest.raises(OffreInvalide, match="ete\\+hiver attendues, ou annee seule"):
        offre_depuis_dict(donnees, "x")


def test_charge_heures_grille_et_plages(offres):
    """Charge'Heures (#24) : grille du 01/10/2026, saison unique aux plages constantes."""
    grilles = grilles_offres(offres)
    g = grilles["totalenergies_charge_heures:hphc_saisonnieres"].en_vigueur(6, datetime(2026, 10, 19).date())
    assert (g.debut, g.abonnement_an) == (datetime(2026, 10, 1).date(), Decimal("188.28"))  # 15,69 x 12
    assert g.prix == {
        "annee_hsc": Decimal("0.1335"),
        "annee_hc": Decimal("0.1576"),
        "annee_hp": Decimal("0.2302"),
    }
    assert [(s.nom, s.debut, s.fin, s.hsc, s.hc) for s in g.saisons] == [
        ("annee", (1, 1), (12, 31), ((120, 360),), ((1380, 120), (360, 420)))
    ]


def test_charge_heures_cout(offres):
    """HSC 02-06, HC 23-02 et 06-07, HP le reste — plages constantes toute l'année."""
    grilles = grilles_offres(offres)
    conso = [(datetime(2026, 10, 19, h, 0), 1.0) for h in (0, 3, 6, 12)]
    grilles_option = grilles["totalenergies_charge_heures:hphc_saisonnieres"]
    cout = cout_option("hphc_saisonnieres", grilles_option, 6, conso)
    assert cout.kwh == {"annee_hc": Decimal(2), "annee_hsc": Decimal(1), "annee_hp": Decimal(1)}
    assert cout.energie == 2 * Decimal("0.1576") + Decimal("0.1335") + Decimal("0.2302")


def test_saison_annee_incomplete_refusee():
    """Une saison unique « annee » doit couvrir toute l'année."""
    donnees = _zen_estival_dict()
    del donnees["options"]["hphc_saisonnieres"]["saisons"]["ete"]
    del donnees["options"]["hphc_saisonnieres"]["saisons"]["hiver"]
    donnees["options"]["hphc_saisonnieres"]["saisons"]["annee"] = {
        "du": "02-01",  # le 1er janvier n'est dans aucune saison
        "au": "12-31",
        "plages": {"hsc": "02:00-06:00", "hc": "23:00-02:00, 06:00-07:00"},
        "kwh_ttc": {"hsc": 0.1335, "hc": 0.1576, "hp": 0.2302},
    }
    with pytest.raises(OffreInvalide, match="partitionner"):
        offre_depuis_dict(donnees, "x")


def test_wekiwi_duo_aurore_grille_du_19_octobre_2026(offres):
    """Offre Duo Wekiwi, électricité Aurore Base et HP/HC (#183, #337) : partie
    électricité seule, abonnement TRV par décision du propriétaire du 28/10/2026
    (non publié par Wekiwi)."""
    offre = offres["wekiwi_duo_aurore"]
    assert (offre.type_prix, offre.duree_fixite_mois) == ("fixe", 12)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 19).date()
    # Base : kWh 0,2182 € (3-6 kVA) / 0,2270 € (9-36 kVA), 18-36 kVA en extinction
    g = grilles["wekiwi_duo_aurore:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an) == (datetime(2026, 10, 19).date(), Decimal("190.81"))
    assert g.prix == {"base": Decimal("0.2182")}
    g = grilles["wekiwi_duo_aurore:base"].en_vigueur(15, jour)
    assert (g.abonnement_an, g.prix) == (Decimal("330.57"), {"base": Decimal("0.2270")})
    # HP/HC : kWh Aurore standard toutes puissances, remise d'entrée non modélisée
    g = grilles["wekiwi_duo_aurore:hphc"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an) == (datetime(2026, 10, 19).date(), Decimal("190.8131821"))
    assert g.prix == {"hp": Decimal("0.2325"), "hc": Decimal("0.1901")}
    g = grilles["wekiwi_duo_aurore:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("650.6862576")
    assert g.prix == {"hp": Decimal("0.2325"), "hc": Decimal("0.1901")}
    # HC dès 3 kVA (abonnement TRV HPHC 3 kVA)
    assert grilles["wekiwi_duo_aurore:hphc"].en_vigueur(3, jour).abonnement_an == Decimal("145.7629941")


@pytest.mark.parametrize(
    ("ident", "base", "hp", "hc"),
    [
        ("dyneff_contrat_plus", "0.19069", "0.19649", "0.16034"),  # #47, #155
        ("dyneff_contrat_plus_verte", "0.19369", "0.19949", "0.16334"),  # #46, #154
    ],
)
def test_dyneff_contrat_plus_revisable(offres, ident, base, hp, hc):
    """Dyneff Contrat+ (#46, #47, #154, #155) : révisable, grilles du 01/08/2026, abonnement par tranche."""
    offre = offres[ident]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("revisable", None, None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 24).date()
    g = grilles[f"{ident}:base"].en_vigueur(3, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("144.36"),  # 12,03 x 12
        {"base": Decimal(base)},
    )
    assert grilles[f"{ident}:base"].en_vigueur(36, jour).prix == {"base": Decimal(base)}  # prix unique
    g = grilles[f"{ident}:hphc"].en_vigueur(6, jour)
    assert g.abonnement_an == Decimal("187.80")  # 15,65 x 12, comme en Base
    assert g.prix == {"hp": Decimal(hp), "hc": Decimal(hc)}
    with pytest.raises(TarifIntrouvable, match="3 kVA"):
        grilles[f"{ident}:hphc"].en_vigueur(3, jour)


def test_enercoop_basic_flexi_watt(offres):
    """Enercoop Basic Watt (#48) et Flexi Watt HC (#49) : révisable, grille du 01/08/2026."""
    offre = offres["enercoop"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("revisable", None, None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 24).date()
    g = grilles["enercoop:base"].en_vigueur(6, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("181.92"),  # 15,16 x 12
        {"base": Decimal("0.25406")},
    )
    assert grilles["enercoop:base"].en_vigueur(9, jour).prix == {"base": Decimal("0.25714")}
    g = grilles["enercoop:hphc"].en_vigueur(3, jour)
    assert g.abonnement_an == Decimal("132.72")  # 11,06 x 12
    assert g.prix == {"hp": Decimal("0.27764"), "hc": Decimal("0.18983")}
    assert grilles["enercoop:hphc"].en_vigueur(36, jour).abonnement_an == Decimal("921.24")  # 76,77 x 12


def test_urban_solar_smb_revisable(offres):
    """Urban Solar Essentielle SMB (#69 Base, #171 HC) : révisable 2 fois par an, grille du 01/08/2026."""
    offre = offres["urban_solar_smb"]
    assert (offre.type_prix, offre.eld, offre.duree_fixite_mois) == ("revisable", None, None)
    grilles = grilles_offres(offres)
    jour = datetime(2026, 10, 24).date()
    g = grilles["urban_solar_smb:base"].en_vigueur(3, jour)
    assert (g.debut, g.abonnement_an, g.prix) == (
        datetime(2026, 8, 1).date(),
        Decimal("146.04"),  # 12,17 x 12
        {"base": Decimal("0.2180")},
    )
    g = grilles["urban_solar_smb:hphc"].en_vigueur(36, jour)
    assert g.abonnement_an == Decimal("759.84")  # 63,32 x 12
    assert g.prix == {"hp": Decimal("0.2377"), "hc": Decimal("0.1750")}
    with pytest.raises(TarifIntrouvable, match="3 kVA"):
        grilles["urban_solar_smb:hphc"].en_vigueur(3, jour)
