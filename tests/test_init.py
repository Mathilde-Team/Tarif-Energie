"""Capteurs créés à partir d'une consommation horaire, et lecture réelle des statistiques.

Identifiants d'entité en anglais : langue par défaut de Home Assistant en test.
"""

from datetime import datetime, timedelta
from unittest.mock import patch

from homeassistant.components.recorder.models import StatisticMeanType
from homeassistant.components.recorder.statistics import async_import_statistics
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.recorder.common import async_wait_recording_done

from custom_components.tarifenergie.const import DOMAIN
from custom_components.tarifenergie.coordinateur import async_conso_horaire

CAPTEUR = "sensor.linky"
DONNEES = {
    "entite_energie": CAPTEUR,
    "puissance": 6,
    "option_actuelle": "base",
    "heures_creuses": "22:00-06:00",
}


def _nuit(jours: int = 3) -> list[tuple[datetime, float]]:
    """2 kWh par heure de 0 h à 6 h : tout en heures creuses."""
    debut = datetime(2026, 10, 1, tzinfo=dt_util.get_default_time_zone())
    return [(debut + timedelta(days=j, hours=h), 2.0) for j in range(jours) for h in range(6)]


async def _installer(hass: HomeAssistant, conso, donnees=DONNEES) -> MockConfigEntry:
    entree = MockConfigEntry(domain=DOMAIN, title="Maison", unique_id=CAPTEUR, data=donnees)
    entree.add_to_hass(hass)
    with patch("custom_components.tarifenergie.coordinateur.async_conso_horaire", return_value=conso):
        assert await hass.config_entries.async_setup(entree.entry_id)
        await hass.async_block_till_done()
    return entree


async def test_capteurs(hass: HomeAssistant):
    entree = await _installer(hass, _nuit())
    assert entree.state is ConfigEntryState.LOADED
    base = hass.states.get("sensor.maison_12_month_cost_base_option")
    hphc = hass.states.get("sensor.maison_12_month_cost_off_peak_option")
    # 36 kWh à 0,2001 + 3 jours de 190,81 €/an ; 36 kWh à 0,1589 + 3 jours de 190,8131821 €/an.
    assert base.state == "8.77"
    assert hphc.state == "7.29"
    assert base.attributes["unit_of_measurement"] == "EUR"
    assert base.attributes["kwh"] == {"base": 36.0}
    assert base.attributes["jours_couverts"] == 3
    assert base.attributes["grilles"] == ["2026-08-01"]
    # Offres de marché (issues #40, #44, #63, #64 et lot 2) : à cette consommation
    # nocturne, Charge'Heures (#24) est la moins chère (24 kWh en HSC à 13,35 c€,
    # 12 kWh en HC à 15,76 c€) ; les grilles
    # postérieures au 3 octobre (GEG 05/10, Mint 08/10, Ohm 14/10 et 16/10, GEDIA 19/10)
    # sont indisponibles.
    # postérieures au 3 octobre (GEG 05/10, Ohm 14/10 et 16/10, Octopus Eco Fixe Plus 12/10,
    # GEDIA 19/10) sont indisponibles.
    prudence = hass.states.get("sensor.maison_12_month_cost_la_bellenergie_prudence_off_peak")
    assert prudence is not None
    assert prudence.state == "7.15"
    assert prudence.attributes["kwh"] == {"hp": 0.0, "hc": 36.0}
    moins_chere = hass.states.get("sensor.maison_cheapest_option").state
    assert moins_chere == "totalenergies_charge_heures:hphc_saisonnieres"
    economie = hass.states.get("sensor.maison_possible_12_month_saving")
    assert economie.state == "2.13"
    assert [e["option"] for e in economie.attributes["classement"]] == [
        # Charge'Heures (#24) : 24 x 0,1335 + 12 x 0,1576 + 3/365 x 188,28 = 6,64 €.
        "totalenergies_charge_heures:hphc_saisonnieres",
        "primeo_fixe_confort:hphc",
        # Gaz de Bordeaux NovaFixe HC (#372, #371) : 36 x 0,14669 + 3/365 x 190,44 = 6,85 €
        # (remise de 100 € du Bonus non modélisée : même total).
        "gaz_de_bordeaux_novafixe:hphc",
        "gaz_de_bordeaux_novafixe_bonus:hphc",
        # Duo (#336) : partie électricité identique à NovaFixe Bonus Élec
        # (même grille) ; la remise de 100 € du Bonus n'est pas modélisée.
        "gaz_de_bordeaux_novafixe_bonus_duo:hphc",
        # TotalEnergies Access HC (#125, indexée TRV, kWh HT -10 %) : 36 x 0,1467
        # + 3/365 x 190,32 = 6,85 €.
        "totalenergies_access:hphc",
        # Gaz de Bordeaux NovaFlex HC (#373, indexée TRV, kWh HT -5 %) : 36 x 0,1528
        # + 3/365 x 190,44 = 7,07 €.
        "gaz_de_bordeaux_novaflex:hphc",
        # Primeo Essentielle Verte HC (#162, indexée TRV, kWh HT -5 %) : 36 x 0,1528
        # + 3/365 x 190,32 = 7,07 €, ex æquo au centime départagé par la clé.
        "primeo_essentielle_verte:hphc",
        # EDF Zen Online HC (#122, indexée TRV) : 36 x 0,1531 + 3/365 x 190,32 = 7,076 €,
        # devant Plenitude HC (7,082 €) bien qu'à égalité au centime.
        "edf_zen_online:hphc",
        "plenitude_pleniweb_1an:hphc",
        # TRV local Bitche HC (#284) : 36 x 0,1589 + 3/365 x 171,94 = 7,13 €,
        # le TRV local le moins cher en HC (abonnement ELD sous le TRV national).
        "bitche_trv_local:hphc",
        "la_bellenergie_prudence:hphc",
        # Ohm Extra Éco HC (#145, révisable) : 36 x 0,1579 + 3/365 x 180,72 = 7,17 €.
        "ohm_extra_eco:hphc",
        # EDF Vert Électrique Régional HC (#119, révisable) : 36 x 0,1560 + 3/365 x 190,32 = 7,18 €.
        "edf_vert_electrique_regional:hphc",
        "alterna_fixe_1an:hphc",
        # Alterna indexée HC (#153) : 36 x 0,1528 + 3/365 x 211,92 = 7,24 €, juste
        # derrière Alterna fixe HC, à égalité au centime.
        "alterna_indexee:hphc",
        # Alpiq Sérénité HC (#150) : kWh HT du TRV -0,5 %, abonnement du TRV = 7,26 €.
        "alpiq_serenite:hphc",
        # TRV local CESML HC (#249) : 36 x 0,1589 + 3/365 x 190,32 = 7,28 €.
        "cesml_trv_local:hphc",
        # TRV local Energis HC (#201) : 7,28 €, juste devant le TRV national HC
        # (abonnement 6 kVA un peu moins cher).
        "energis_trv_local:hphc",
        # TRV local Gazélec Péronne HC (#209) : 36 x 0,1589 + 3/365 x 190,35 = 7,28 €.
        "gazelec_peronne_trv_local:hphc",
        # TRV local Gedia HC (#193) : 36 x 0,15890 + 3/365 x 190,32 = 7,28 €, juste
        # devant le TRV national HC (7,29 €, abonnement un peu plus cher).
        "gedia_trv_local:hphc",
        # TRV local Lavaur HC (#213) : 7,28 €.
        "lavaur_trv_local:hphc",
        # TRV local Oya HC (#216) : 7,28 €.
        "oya_trv_local:hphc",
        # TRV local SIEL Labergement (#314) HC : 36 x 0,1589 + 3/365 x 190,35 €, sous le TRV national.
        "siel_labergement_trv_local:hphc",
        # TRV local Soréa HC (#319) : 36 x 0,1589 + 3/365 x 190,32 = 7,285 €, juste sous le TRV national.
        "sorea_trv_local:hphc",
        # TotalEnergies Heures Eco HC (#132) : mêmes prix HT que le TRV ; les prix TTC
        # arrondis du PDF la placent un centime sous le TRV national (7,28 € contre 7,29 €).
        "totalenergies_heures_eco:hphc",
        # TotalEnergies Spéciale partie élec, HC (#134) : même grille qu'Heures Eco
        # (décision du 28/10/2026 : un fichier par offre), donc 7,28 € aussi ;
        # départage par le nom de l'option.
        "totalenergies_speciale:hphc",
        # TRV local GEG HC (#196) : 36 x 0,1589 + 3/365 x 190,80 = 7,29 €, à égalité au
        # centime avec le TRV national HC ; départage par le nom de l'option.
        "geg_trv_local:hphc",
        "hphc",
        # Jeety Elec-Dom HC (#161, indexée TRV) : 36 x 0,1579 + 3/365 x 195,12 = 7,29 €,
        # à égalité au centime avec le TRV national HC (grille de février 2026 non
        # revue au mouvement du TRV du 01/08/2026) ; départage par le nom de l'option.
        "jeety_elec_dom:hphc",
        # TRV local Amnéville HC (#222) : 7,30 €.
        "amneville_trv_local:hphc",
        # TRV local Barr HC (#198) : 36 x 0,1589 + 3/365 x 192,48 = 7,30 €, juste
        # derrière le TRV national HC (abonnement un peu plus cher).
        "barr_trv_local:hphc",
        # TRV local Bazas HC (#219) : 7,30 €.
        "bazas_trv_local:hphc",
        # TRV local Enes Hagondange HC (#204) : grille OMEGA, 7,30 €.
        "enes_hagondange_trv_local:hphc",
        # TRV local Gascogne HC (#206) : abonnement annuel 192,59 €, total 7,30 €.
        "gascogne_trv_local:hphc",
        # TRV local La Réole HC (#273) : 7,30 €.
        "la_reole_trv_local:hphc",
        # TRV local Lannemezan HC (#211) : 7,30 €.
        "lannemezan_trv_local:hphc",
        # TRV local Marange-Silvange HC (#266) : 7,30 €.
        "marange_silvange_trv_local:hphc",
        # TRV locaux OMEGA HC (#225 Montois, #228 Pierrevillers, #231 Rombas) : grille commune
        # d'Amnéville, 36 x 0,1589 + 3/365 x 192,59 = 7,30 €.
        "montois_trv_local:hphc",
        "pierrevillers_trv_local:hphc",
        "rombas_trv_local:hphc",
        # TRV local SÉOLIS HC (#234) : 7,30 €.
        "seolis_trv_local:hphc",
        # TRV local SICAE Oise (#298, #299) HC : 36 x 0,1589 + 3/365 x 192,59 €.
        "sicae_oise_trv_local:hphc",
        # TRV local SICAE-Précy HC (#302) : 36 x 0,1589 + 3/365 x 192,59 = 7,303 €.
        "sicae_precy_trv_local:hphc",
        # TRV local SICAE Somme (#304, #305) HC : 36 x 0,1589 + 3/365 x 192,59 €.
        "sicae_somme_trv_local:hphc",
        # TRV local SICAE Vallée du Sausseron (#307, #308) HC : 36 x 0,1589 + 3/365 x 192,59 €.
        "sicae_vs_trv_local:hphc",
        # TRV local SICAP Pithiviers (#310, #311) HC : 36 x 0,1589 + 3/365 x 192,60 €.
        "sicap_pithiviers_trv_local:hphc",
        # TRV local Sorégies HC (#237) : 7,30 €.
        "soregies_trv_local:hphc",
        # TRV local Synelva HC (#240) : 7,30 €.
        "synelva_trv_local:hphc",
        # TRV local UEM HC (#243) : 7,30 €.
        "uem_trv_local:hphc",
        # TRV local Enes Creutzwald HC (#276) : 7,32 €, à égalité au centime avec
        # es_trv_local:hphc ; départage par le nom de l'option.
        "enes_creutzwald_trv_local:hphc",
        # TRV local Enes Hombourg-Haut HC (#278) : même grille unique Enes que
        # Creutzwald (décision du propriétaire du 28/10/2026) ; même total,
        # départage par le nom de l'option.
        "enes_hombourg_haut_trv_local:hphc",
        # TRV local Enes Schoeneck HC (#280) : même grille unique Enes que
        # Creutzwald (décision du propriétaire du 28/10/2026) ; même total,
        # départage par le nom de l'option.
        "enes_schoeneck_trv_local:hphc",
        # TRV local ÉS HC (#190) : 36 x 0,15890 + 3/365 x 194,16 = 7,316 €, juste
        # après le TRV national HC (abonnement un peu plus cher).
        "es_trv_local:hphc",
        # TRV local Sarre-Union HC (#258) : 7,32 €, à égalité au centime avec
        # es_trv_local:hphc ; départage par le nom de l'option.
        "sarre_union_trv_local:hphc",
        # TRV local UME HC (#322) : mêmes montants que l'ÉS, ex æquo départagé par la clé.
        "ume_trv_local:hphc",
        # TRV local Vialis HC (#246) : 7,32 €, à égalité au centime avec
        # es_trv_local:hphc ; départage par le nom de l'option.
        "vialis_trv_local:hphc",
        # Octopus Eco Fixe HC (#139) : 36 x 0,1613 + 3/365 x 190,32 = 7,37 €.
        "octopus_eco_fixe_oct2026:hphc",
        "alterna_du_coin_1an:hphc",
        "la_bellenergie_constance:hphc",
        # EDF Zen Estival hiver (#20) : 36 x 0,1738 + 3/365 x 151,20 = 7,50 €.
        "edf_zen_estival:hphc_saisonnieres",
        # EDF Zen Fixe HC (#114) : 36 x 0,1650 + 3/365 x 190,32 = 7,50 €.
        "edf_zen_fixe_2ans:hphc",
        "la_bellenergie_garance:hphc",
        # EDF Vert Électrique Week-End HC (#120) : tout à 16,91 c€ (nuit HC + samedi
        # 03/10) + 3/365 x 190,32 = 7,65 €.
        "edf_vert_electrique_week_end:week_end_hphc",
        # Primeo Fixe ECO -15 % Base (#185) : 36 x 0,1704 + 3/365 x 196,32 = 7,75 €,
        # juste devant Primeo Fixe Confort Base.
        "primeo_fixe_eco_15:base",
        # EDF Zen Week-End Plus HC (#116) : tout à 17,31 c€ (nuit HC + samedi 03/10,
        # vendredi choisi ou non) + 3/365 x 190,32 = 7,80 €, les trois variantes
        # ex æquo départagées par la clé.
        "edf_zen_week_end_plus:week_end_hphc_jour_lundi",
        "edf_zen_week_end_plus:week_end_hphc_jour_mercredi",
        "edf_zen_week_end_plus:week_end_hphc_jour_vendredi",
        # EDF Zen Week-End HC (#117) : tout à 17,62 c€ (nuit HC + samedi 03/10)
        # + 3/365 x 190,32 = 7,91 €.
        "edf_zen_week_end:week_end_hphc",
        "primeo_fixe_confort:base",
        # TotalEnergies Fixe 2 ans HC (#126) : 36 x 0,1791 + 3/365 x 192,60 = 8,03 €.
        "totalenergies_fixe_2ans:hphc",
        # elmy prix fixe 2 ans HC (#176) : 36 x 0,1848 + 3/365 x 180,12 = 8,13 €.
        "elmy_prix_fixe_2ans:hphc",
        # Gaz de Bordeaux NovaFixe Base (#111, #99) : 36 x 0,18373 + 3/365 x 190,44 = 8,18 €.
        "gaz_de_bordeaux_novafixe:base",
        "gaz_de_bordeaux_novafixe_bonus:base",
        # Duo (#181) : Base de la même grille que NovaFixe Bonus Élec.
        "gaz_de_bordeaux_novafixe_bonus_duo:base",
        # TotalEnergies Access Base (#23) : 36 x 0,1837 + 3/365 x 190,32 = 8,18 €.
        "totalenergies_access:base",
        # EDF Zen Week-End Plus Base, jour choisi vendredi (#10) : 24 x 0,2259
        # + 12 x 0,1691 (vendredi choisi) + 3/365 x 190,32 = 8,33 €.
        "edf_zen_week_end_plus:week_end_jour_vendredi",
        "plenitude_pleniweb_1an:base",
        # Hunélec HC (#326) : 36 x 0,19129 + 3/365 x 191,52 = 8,46 € ;
        # 100 % vert (#328) : + 2,27 €/mois = 8,68 € ; TRV Base : 8,77 €.
        "hunelec_prix_fixe_1an:hphc",
        # Gaz de Bordeaux NovaFlex Base (#100) : 36 x 0,1919 + 3/365 x 190,44 = 8,47 €.
        "gaz_de_bordeaux_novaflex:base",
        # Primeo Essentielle Verte Base (#60) : 36 x 0,1919 + 3/365 x 190,32 = 8,47 €.
        "primeo_essentielle_verte:base",
        # EDF Zen Online Base (#21) : 36 x 0,1925 + 3/365 x 190,32 = 8,49 €.
        "edf_zen_online:base",
        # Ohm Extra Éco Base (#37, révisable) : 36 x 0,1940 + 3/365 x 183,36 = 8,49 €, à égalité
        # avec EDF Zen Online Base, départagée par le nom.
        "ohm_extra_eco:base",
        # Jeety Elec-Dom Base (#59, indexée TRV) : 36 x 0,1940 + 3/365 x 188,40 = 8,53 €.
        "jeety_elec_dom:base",
        # TRV local Energis Base (#200) : 36 x 0,19522 + 3/365 x 190,32 = 8,59 €.
        "energis_trv_local:base",
        "la_bellenergie_prudence:base",
        # TRV local Bitche Base (#283) : 36 x 0,2001 + 3/365 x 171,94 = 8,62 €.
        "bitche_trv_local:base",
        # Enercoop Flexi Watt HC (#49, révisable) : 36 x 0,18983 + 3/365 x 217,32 = 8,62 €.
        "enercoop:hphc",
        "alterna_fixe_1an:base",
        # Alterna indexée Base (#45) : 36 x 0,1919 + 3/365 x 211,92 = 8,65 €.
        "alterna_indexee:base",
        "hunelec_prix_fixe_1an_vert:hphc",
        # EDF Vert Électrique Week-End Base (#19) : 24 x 0,2171 + 12 x 0,163 (samedi
        # 03/10) + 3/365 x 190,32 = 8,73 €.
        "edf_vert_electrique_week_end:week_end",
        # Alpiq Sérénité Base (#42) : 36 x 0,199247 + 3/365 x 190,32 = 8,74 €.
        "alpiq_serenite:base",
        # TotalEnergies Verte Fixe HC (#133) : 36 x 0,1992 + 3/365 x 192,60 = 8,75 €.
        "totalenergies_verte_fixe:hphc",
        # TRV local Amnéville Base (#221) : 8,76 €.
        "amneville_trv_local:base",
        # TRV local Enes Hagondange Base (#203) : 8,76 €.
        "enes_hagondange_trv_local:base",
        # TRV local Marange-Silvange Base (#265) : 8,76 €.
        "marange_silvange_trv_local:base",
        # TRV locaux OMEGA Base (#224 Montois, #227 Pierrevillers, #230 Rombas) : 8,76 €,
        # comme Amnéville (grille commune).
        "montois_trv_local:base",
        "pierrevillers_trv_local:base",
        "rombas_trv_local:base",
        # TRV local UEM Base (#242) : 8,76 €.
        "uem_trv_local:base",
        # TRV local Barr Base (#197) : 36 x 0,2001 + 3/365 x 190,32 = 8,77 €, à égalité au
        # centime avec le TRV national Base ; départage par le nom de l'option.
        "barr_trv_local:base",
        "base",
        # TRV local Bazas Base (#218) : 8,77 €, à égalité au centime avec
        # TRV national Base ; départage par le nom de l'option.
        "bazas_trv_local:base",
        # TRV local CESML Base (#248) : 8,77 €.
        "cesml_trv_local:base",
        # TRV local Gascogne Base (#205) : 36 x 0,2001 + 3/365 x 190,35 = 8,77 €, à égalité
        # au centime avec le TRV national Base ; départage par le nom de l'option.
        "gascogne_trv_local:base",
        # TRV local Gazélec Péronne Base (#208) : 8,77 €.
        "gazelec_peronne_trv_local:base",
        # TRV local Gedia Base (#192) : 36 x 0,20006 + 3/365 x 190,32 = 8,77 €, à égalité au
        # centime avec le TRV national Base ; départage par le nom de l'option.
        "gedia_trv_local:base",
        # TRV local GEG Base (#195) : 36 x 0,2001 + 3/365 x 190,80 = 8,77 €, à égalité au
        # centime avec le TRV national Base ; départage par le nom de l'option.
        "geg_trv_local:base",
        # TRV local La Réole Base (#272) : 8,77 €, à égalité au centime avec
        # TRV national Base ; départage par le nom de l'option.
        "la_reole_trv_local:base",
        # TRV local Lannemezan Base (#210) : 8,77 €, à égalité au centime avec le TRV
        # national Base ; départage par le nom de l'option.
        "lannemezan_trv_local:base",
        # TRV local Lavaur Base (#212) : 8,77 €, à égalité au centime avec
        # TRV national Base ; départage par le nom de l'option.
        "lavaur_trv_local:base",
        # TRV local Oya Base (#215) : 8,77 €, à égalité au centime avec
        # TRV national Base ; départage par le nom de l'option.
        "oya_trv_local:base",
        # TRV local SÉOLIS Base (#233) : 8,77 €, à égalité au centime avec
        # TRV national Base ; départage par le nom de l'option.
        "seolis_trv_local:base",
        # TRV local SICAE Oise (#298, #299) Base : 36 x 0,2001 + 3/365 x 190,36 €.
        "sicae_oise_trv_local:base",
        # TRV local SICAE-Précy Base (#301) : 36 x 0,2001 + 3/365 x 190,35 = 8,768 €.
        "sicae_precy_trv_local:base",
        # TRV local SICAE Somme (#304, #305) Base : 36 x 0,2001 + 3/365 x 190,35 €.
        "sicae_somme_trv_local:base",
        # TRV local SICAE Vallée du Sausseron (#307, #308) Base : 36 x 0,2001 + 3/365 x 190,35 €.
        "sicae_vs_trv_local:base",
        # TRV local SICAP Pithiviers (#310, #311) Base : 36 x 0,2001 + 3/365 x 190,32 €.
        "sicap_pithiviers_trv_local:base",
        # TRV local SIEL Labergement (#313, #314) Base : 36 x 0,2001 + 3/365 x 190,35 €.
        "siel_labergement_trv_local:base",
        # TRV local Soréa Base (#318) : 36 x 0,2001 + 3/365 x 190,32 = 8,77 €.
        "sorea_trv_local:base",
        # TRV local Sorégies Base (#236) : 8,77 €, à égalité au centime avec
        # TRV national Base ; départage par le nom de l'option.
        "soregies_trv_local:base",
        # TotalEnergies Heures Eco Base (#94) : 36 x 0,2001 + 3/365 x 190,32 = 8,77 €,
        # à égalité au centime avec le TRV national.
        "totalenergies_heures_eco:base",
        # TotalEnergies Spéciale Électricité et Gaz, partie élec, Base (#96) :
        # même grille qu'Heures Eco (décision du 28/10/2026 : un fichier par
        # offre), donc 8,77 € aussi ; départage par le nom de l'option.
        "totalenergies_speciale:base",
        # TRV local Enes Creutzwald Base (#275) : 8,78 €, à égalité au centime avec
        # es_trv_local:base ; départage par le nom de l'option.
        "enes_creutzwald_trv_local:base",
        # TRV local Enes Hombourg-Haut Base (#277) : même grille unique Enes que
        # Creutzwald (décision du propriétaire du 28/10/2026) ; même total,
        # départage par le nom de l'option.
        "enes_hombourg_haut_trv_local:base",
        # TRV local Enes Schoeneck Base (#279) : même grille unique Enes que
        # Creutzwald (décision du propriétaire du 28/10/2026) ; même total,
        # départage par le nom de l'option.
        "enes_schoeneck_trv_local:base",
        # TRV local ÉS Base (#72) : 36 x 0,20006 + 3/365 x 191,40 = 8,775 € (TRV national : 8,772 €).
        "es_trv_local:base",
        # TRV local Sarre-Union Base (#257) : 8,78 €, à égalité au centime avec
        # es_trv_local:base ; départage par le nom de l'option.
        "sarre_union_trv_local:base",
        # TRV local Synelva Base (#239) : 8,78 €, à égalité au centime avec
        # es_trv_local:base ; départage par le nom de l'option.
        "synelva_trv_local:base",
        "ume_trv_local:base",  # TRV local UME Base (#321), ex æquo avec l'ÉS
        # TRV local Vialis Base (#245) : 8,78 €, à égalité au centime avec
        # es_trv_local:base ; départage par le nom de l'option.
        "vialis_trv_local:base",
        "alterna_du_coin_1an:base",
        # EDF Vert Électrique Base (#9, révisable) : 36 x 0,2022 + 3/365 x 190,32 = 8,84 €.
        "edf_vert_electrique:base",
        "la_bellenergie_constance:base",
        # Octopus Eco Fixe Base (#30) : 36 x 0,2033 + 3/365 x 190,32 = 8,88 €.
        "octopus_eco_fixe_oct2026:base",
        # EDF Vert Électrique Régional Base (#18) : 36 x 0,2037 + 3/365 x 190,32 = 8,90 €.
        "edf_vert_electrique_regional:base",
        # EDF Zen Week-End Plus Base, jour choisi lundi ou mercredi (#10) : 24 x 0,2259
        # + 12 x 0,1691 (samedi) + 3/365 x 190,32 = 9,02 € (le vendredi choisi
        # donnerait 8,33 €, consommation du test sans vendredi).
        "edf_zen_week_end_plus:week_end_jour_lundi",
        "edf_zen_week_end_plus:week_end_jour_mercredi",
        # EDF Zen Fixe Base (#8) : 36 x 0,2082 + 3/365 x 190,32 = 9,06 €.
        "edf_zen_fixe_2ans:base",
        "la_bellenergie_garance:base",
        # EDF Zen Week-End Base (#12) : 24 x 0,2285 + 12 x 0,171 (samedi 03/10)
        # + 3/365 x 190,32 = 9,10 €.
        "edf_zen_week_end:week_end",
        # Engie Elec Référence 3 ans HC (#127) : 36 x 0,20683 + 3/365 x 215,79 = 9,22 €.
        "engie_elec_reference_3ans:hphc",
        "selia_elec_vert_fixe:hphc",
        # ilek Voiture électrique Base (#58) : 36 x 0,2001 + 3/365 x 301,20 = 9,68 €.
        "ilek_voiture_electrique:base",
        # TotalEnergies Fixe 2 ans Base (#25) : 36 x 0,2270 + 3/365 x 190,32 = 9,74 €.
        "totalenergies_fixe_2ans:base",
        # Happ-e Électricité 1 an HC (#128) : 36 x 0,22398 + 3/365 x 214,35 = 9,83 €.
        "happe_elec_1an:hphc",
        # elmy prix fixe 2 ans Base (#104) : 36 x 0,2323 + 3/365 x 190,32 = 9,93 €.
        "elmy_prix_fixe_2ans:base",
        "ilek_enrfixe_plus:hphc",
        # Hunélec Base (#325, #327) : 36 x 0,23506 + 3/365 x 188,88 = 10,01 € (vert : 10,24 €).
        "hunelec_prix_fixe_1an:base",
        # ÉS Week-end et heures creuses (#331) : tout à 23,752 c€ (nuit HC + samedi
        # 03/10) + 3/365 x 192,60 = 10,13 €.
        "es_verte_fixe_1an:week_end_hphc",
        # ÉS HC (#329) : 36 x 0,24 + 3/365 x 194,16 = 10,2358 €, juste devant
        # Hunélec vert Base (10,2385 €) ; ÉS 100 % régionale HC (#332) : 10,46 €.
        "es_verte_fixe_1an:hphc",
        "hunelec_prix_fixe_1an_vert:base",
        # Engie Duo Référence 3 ans, partie élec, Base (#98) : même grille qu'Elec
        # Référence 3 ans (décision du 28/10/2026 : un fichier par offre), donc
        # 10,32 € aussi ; départage par le nom de l'option.
        "engie_duo_reference_3ans:base",
        # Engie Elec Référence 3 ans Base (#28) : 36 x 0,24205 + 3/365 x 195,18 = 10,32 €.
        "engie_elec_reference_3ans:base",
        # ÉS 100 % régionale Week-end et heures creuses (#334) : 10,13 € + 2,27 x 12 x
        # 3/365 = 10,36 € (même kWh que #331, supplément vert sur l'abonnement).
        "es_verte_regionale_fixe_1an:week_end_hphc",
        "es_verte_regionale_fixe_1an:hphc",
        # Enercoop Basic Watt Base (#48, révisable) : 36 x 0,25406 + 3/365 x 181,92 = 10,64 €.
        "enercoop:base",
        # TotalEnergies Verte Fixe Base (#95) : 36 x 0,2540 + 3/365 x 145,56 = 10,71 €.
        "totalenergies_verte_fixe:base",
        # Happ-e Électricité 1 an Base (#71) : 36 x 0,26309 + 3/365 x 193,74 = 11,06 €.
        "happe_elec_1an:base",
        "ilek_enrfixe_plus:base",
        "selia_elec_vert_fixe:base",
        # ÉS Week-end Base (#330) : 24 x 0,31108 + 12 x 0,22878 (samedi 03/10)
        # + 3/365 x 190,32 = 11,78 €.
        "es_verte_fixe_1an:week_end",
        # ÉS 100 % régionale Week-end Base (#333) : 11,78 € + 2,27 x 12 x 3/365
        # = 12,00 € (même kWh, supplément vert sur l'abonnement).
        "es_verte_regionale_fixe_1an:week_end",
        # ÉS Base (#73) : 36 x 0,30216 + 3/365 x 191,40 = 12,45 € ; régionale (#74) : 12,67 €.
        "es_verte_fixe_1an:base",
        # papernest HC (#169) : 36 x 0,24528 + 3/365 x 464,40 = 12,65 €, juste devant
        # ÉS 100 % régionale Base (12,67 €) ; papernest Base (#67) : 13,93 €, dernière.
        "papernest_verte_1an:hphc",
        "es_verte_regionale_fixe_1an:base",
        "papernest_verte_1an:base",
    ]
    assert "2026-10-01" in economie.attributes["indisponibles"]["geg_elec_verte_3ans:base"]
    assert "2026-10-01" in economie.attributes["indisponibles"]["geg_direct_producteur_3ans:hphc"]
    assert "2026-10-01" in economie.attributes["indisponibles"]["ohm_serente_fixe_1an:base"]
    assert "2026-10-01" in economie.attributes["indisponibles"]["ohm_premiohm:hphc"]
    assert "2026-10-01" in economie.attributes["indisponibles"]["gedia_all_inclusive:hphc"]
    # Mint Online & Green (#35, #143) : grille applicable au 08/10/2026 seulement.
    assert "2026-10-01" in economie.attributes["indisponibles"]["mint_online_green:hphc"]
    assert "2026-10-01" in economie.attributes["indisponibles"]["mint_classic_green:base"]
    assert "2026-10-01" in economie.attributes["indisponibles"]["mint_smart_green:hphc"]
    # Octopus Eco Fixe Plus (#29, #138) : grille du 12/10/2026, postérieure à la période.
    assert "2026-10-01" in economie.attributes["indisponibles"]["octopus_eco_fixe_plus_oct2026:base"]
    # Wekiwi Offre Duo Aurore (#183, #337) : prix relevés le 19/10/2026, postérieurs à la période.
    assert "2026-10-01" in economie.attributes["indisponibles"]["wekiwi_duo_aurore:base"]
    assert "2026-10-01" in economie.attributes["indisponibles"]["wekiwi_duo_aurore:hphc"]
    assert hass.states.get("sensor.maison_12_month_consumption").state == "36.0"
    assert hass.states.get("sensor.maison_off_peak_share").state == "100.0"
    assert await hass.config_entries.async_unload(entree.entry_id)


async def test_option_indisponible_au_dela_de_15_kva(hass: HomeAssistant):
    await _installer(hass, _nuit(), {**DONNEES, "puissance": 36, "option_actuelle": "hphc"})
    base = hass.states.get("sensor.maison_12_month_cost_base_option")
    assert base.state == "unknown"
    assert "36 kVA" in base.attributes["indisponible"]
    # À 36 kVA, Charge'Heures (#24, 632,64 €/an, HSC 13,35 c€) : 10,29 €, devant
    # Gaz de Bordeaux NovaFixe HC (646,56 €/an, 14,669 c€, #372) : 10,60 €, juste
    # devant TotalEnergies Access HC (même abonnement, 14,67 c€), EDF Zen Online HC (15,31 c€ :
    # 10,83 €), Plenitude HC (681,72 €/an, 14,67 c€ : 10,88 €), Prudence HC et le TRV HC.
    moins_chere = hass.states.get("sensor.maison_cheapest_option").state
    assert moins_chere == "totalenergies_charge_heures:hphc_saisonnieres"
    assert hass.states.get("sensor.maison_possible_12_month_saving").state == "0.78"


async def test_sans_donnees(hass: HomeAssistant):
    await _installer(hass, [])
    # Sans consommation, toutes les options coûtent 0,00 € : le classement départage
    # les ex æquo par ordre alphabétique de la clé de comparaison.
    assert hass.states.get("sensor.maison_cheapest_option").state == "alpiq_serenite:base"
    assert hass.states.get("sensor.maison_off_peak_share").state == "unknown"
    await _installer_vide_hphc(hass)


async def _installer_vide_hphc(hass: HomeAssistant):
    """Sans aucune option calculable : capteurs inconnus, pas d'erreur."""
    coord = hass.config_entries.async_entries(DOMAIN)[0].runtime_data
    coord.grilles = {}
    with patch("custom_components.tarifenergie.coordinateur.async_conso_horaire", return_value=[]):
        await coord.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("sensor.maison_cheapest_option").state == "unknown"
    assert hass.states.get("sensor.maison_12_month_consumption").state == "unknown"
    assert hass.states.get("sensor.maison_possible_12_month_saving").state == "unknown"


async def test_lecture_des_statistiques_en_kwh(hass: HomeAssistant):
    """Statistiques réelles en Wh : converties en kWh, variations négatives écartées, heure locale."""
    debut = dt_util.utcnow().replace(minute=0, second=0, microsecond=0) - timedelta(hours=3)
    metadata = {
        "source": "recorder",
        "statistic_id": CAPTEUR,
        "unit_of_measurement": "Wh",
        "unit_class": "energy",
        "has_sum": True,
        "mean_type": StatisticMeanType.NONE,
        "name": None,
    }
    sommes = [0, 1500, 1000, 3000]  # 0, +1,5 kWh, -0,5 (écartée), +2 kWh
    async_import_statistics(
        hass,
        metadata,
        [{"start": debut + timedelta(hours=i), "sum": s, "state": s} for i, s in enumerate(sommes)],
    )
    await async_wait_recording_done(hass)
    conso = await async_conso_horaire(hass, CAPTEUR, debut - timedelta(hours=1), debut + timedelta(hours=4))
    assert [round(k, 3) for _, k in conso] == [0.0, 1.5, 2.0]
    assert all(h.tzinfo == dt_util.get_default_time_zone() for h, _ in conso)
