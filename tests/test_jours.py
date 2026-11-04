"""Jours de week-end : samedi, dimanche et jours fériés nationaux (option ÉS #330)."""

from datetime import date

from custom_components.tarifenergie.jours import est_week_end, jours_feries, paques


def test_paques():
    """Dimanche de Pâques (algorithme grégorien anonyme), base des fêtes mobiles."""
    assert paques(2025) == date(2025, 4, 20)
    assert paques(2026) == date(2026, 4, 5)
    assert paques(2027) == date(2027, 3, 28)


def test_onze_jours_feries_nationaux():
    attendus = {
        date(2026, 1, 1),  # Jour de l'An
        date(2026, 4, 6),  # lundi de Pâques
        date(2026, 5, 1),  # Fête du Travail
        date(2026, 5, 8),  # Victoire 1945
        date(2026, 5, 14),  # Ascension
        date(2026, 5, 25),  # lundi de Pentecôte
        date(2026, 7, 14),  # Fête nationale
        date(2026, 8, 15),  # Assomption
        date(2026, 11, 1),  # Toussaint
        date(2026, 11, 11),  # Armistice 1918
        date(2026, 12, 25),  # Noël
    }
    assert jours_feries(2026) == attendus  # les 11 nationaux, ni plus ni moins


def test_est_week_end():
    assert est_week_end(date(2026, 10, 24))  # samedi
    assert est_week_end(date(2026, 10, 25))  # dimanche
    assert not est_week_end(date(2026, 10, 28))  # mercredi
    assert est_week_end(date(2026, 5, 14))  # Ascension, un jeudi férié
    assert not est_week_end(date(2026, 5, 13))  # mercredi ordinaire


def test_jours_rouges_tempo_et_sobriete():
    """#97 : 22 jours rouges par saison connue, en semaine ; un jour absent est un jour Éco."""
    from custom_components.tarifenergie.jours import est_jour_sobriete, jours_rouges_tempo

    rouges = jours_rouges_tempo()
    assert len(rouges) == 4 * 22
    assert all(j.weekday() < 5 and j.month in (11, 12, 1, 2, 3) for j in rouges)
    assert est_jour_sobriete(date(2026, 1, 5))
    assert not est_jour_sobriete(date(2026, 1, 8))
    assert not est_jour_sobriete(date(2026, 7, 14))


def test_jours_eclair():
    """#26 : jours Éclair estimés par les jours rouges Tempo, du 15/10 au 15/04 seulement."""
    from custom_components.tarifenergie.jours import est_jour_eclair, jours_rouges_tempo

    assert est_jour_eclair(date(2026, 1, 5))
    assert not est_jour_eclair(date(2026, 1, 8))
    assert not est_jour_eclair(date(2026, 7, 14))
    rouges = jours_rouges_tempo()
    assert all(est_jour_eclair(j) for j in rouges)  # toujours dans les fenêtres Éclair


def test_jours_blancs_et_couleur_tempo():
    """#108 : 43 jours blancs par saison connue ; un jour absent des calendriers est bleu."""
    from custom_components.tarifenergie.jours import couleur_tempo, jours_blancs_tempo, jours_rouges_tempo

    blancs = jours_blancs_tempo()
    assert len(blancs) == 4 * 43
    assert not blancs & jours_rouges_tempo()  # un jour n'a qu'une couleur
    assert all(j.weekday() != 6 for j in blancs)  # jamais de dimanche blanc
    # Couleurs relevées sur api-couleur-tempo.fr, saison 2025-2026.
    assert couleur_tempo(date(2026, 1, 5)) == "rouge"
    assert couleur_tempo(date(2026, 1, 8)) == "blanc"
    assert couleur_tempo(date(2026, 1, 9)) == "bleu"
    assert couleur_tempo(date(2030, 1, 7)) == "bleu"  # saison non relevée
