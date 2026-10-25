# Journal des versions

Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/). Les numéros suivent [SemVer](https://semver.org/lang/fr/), et la version de `manifest.json` est égale au tag.

## [Non publié]

### Ajouté
- **TRV local Energis** (#200 Base, #201 HC) : Tarif Bleu résidentiel de Saint-Avold, grille du 01/08/2026. Base publiée en 3 et 6 kVA seulement (9-36 kVA en extinction) ; HC dès 3 kVA. Tempo (#202) n'est pas repris.
- **TRV local Barr Energies** (#197 Base, #198 HC) : Tarif Bleu résidentiel de Barr et Villé, fiche descriptive du 01/08/2026 (TURPE 4 postes). Base publiée en 3 et 6 kVA seulement (9-36 kVA en extinction) ; HC dès 3 kVA. Tempo (#199) n'est pas repris.
- **TRV local GEG** (#195 Base, #196 HC) : Tarif Bleu résidentiel du territoire GreenAlp (Grenoble), grille TTC du 01/08/2026 (PART 08.26). HC dès 3 kVA avec le même abonnement que la Base ; Base 9-36 kVA en extinction. EJP (en extinction) n'est pas repris.
- **TRV local Gedia** (#192 Base, #193 HC) : Tarif Bleu résidentiel de la commune de Dreux, grille TTC du 01/08/2026 (page 2 du PDF officiel). HC dès 3 kVA avec le même abonnement que la Base ; Base 9-36 kVA en extinction. Tempo (#194) n'est pas repris.
- **Offres Gaz de Bordeaux NovaFixe Élec et NovaFixe Bonus Élec** (#111, #372, #99, #371), Base de 3 à 15 kVA et HC de 6 à 36 kVA. Grille de Bordeaux du 01/10/2026, vérifiée sur la fiche officielle ; prix fixes 36 mois. La remise Bonus de 100 € après 11 mois n'est pas modélisée.
- **Offre TotalEnergies Verte Fixe** (#95 Base, #133 Heures creuses) : grille officielle du 24/09/2026, vérifiée sur le PDF ; abonnement et kWh HT fixes 12 mois. Pas d'HC en 3 kVA. Les puissances réservées aux compteurs Linky ne sont pas reprises.
- **Offres Octopus Energy Eco Fixe Octobre 2026 et Eco Fixe Plus Octobre 2026** (#30, #139, #29, #138), Base et Heures creuses. Les grilles officielles du 30/09/2026 et du 12/10/2026 ont été vérifiées sur les PDF ; abonnement et kWh HTT fixes 24 mois. Le kWh Base change entre 6 et 7 kVA (cellules fusionnées du PDF). L'option HC est proposée dès 3 kVA. Ces offres sont réservées au territoire Enedis.
- **Offre TotalEnergies Fixe 2 ans** (#25 Base, #126 Heures creuses) : grille officielle du 24/09/2026, vérifiée sur le PDF ; abonnement et kWh HT fixes 24 mois. Pas d'HC en 3 kVA. Les puissances réservées aux compteurs Linky (4, 5, 7 kVA…) ne sont pas reprises.
- **Offre EDF Zen Fixe 2 ans** (#8 Base, #114 Heures creuses) : grille TTC du 01/10/2026 (nouvelles souscriptions), vérifiée sur le PDF EDF ; kWh HT fixe pendant 25 mois. Pas d'HC en 3 kVA. Les majorations (injection, sans Linky, sans index sur 12 mois) et les évolutions possibles de l'abonnement ne sont pas modélisées.
- **TRV local SICAE Oise** (#298 Base, #299 HC) : grille du 01/08/2026, abonnements en €/an, lue sur le rendu du PDF. Base en 3 et 6 kVA seulement, HC dès 3 kVA. Tempo (#300) n'est pas repris.
- **TRV local des ELD** (#189) : `type_prix: reglemente`, sans `duree_fixite_mois` (le prix suit le TRV) et avec le réseau dans `eld:` ; `Offre` porte `type_prix` et `eld`. Premier TRV local : **ÉS Énergies** (#72 Base, #190 HC), grille du 01/08/2026, HC dès 3 kVA ; Base 9-36 kVA en extinction. Tempo (#191) n'est pas repris.
- **Offre GEDIA All Inclusive GES Électricité** (#54, #335), Base et Heures creuses : tableau « Domestique » de la grille TTC du 19-25/10/2026. Elle est réservée au réseau GEDIA (Dreux). Les offres acceptent maintenant **`abonnement_annuel_ttc`**, exclusif de `abonnement_mensuel_ttc`, pour les grilles publiées en €/an (repris sans division par 12).
- **Offres ÉS Énergies** (#73, #74, #329, #332) : Électricité verte à prix fixe 1 an et Prix fixe 1 an Électricité verte 100 % régionale, Base et Heures creuses. Grilles TTC du 01/10/2026 ; le supplément régional de 2,27 € TTC/mois est ajouté à l'abonnement. Les options Week-end (#330, #331, #333, #334) ne sont pas reprises, car le moteur ne gère que Base et HC. Ces offres sont réservées au territoire Strasbourg Électricité Réseaux.
- **Offres Hunélec** (#325, #326, #327, #328) : Offre à prix fixe 1 an, Base et Heures creuses, et sa variante 100 % énergie verte. Grilles TTC du 01/07/2026, lues dans les fiches descriptives page 4. Le supplément « vert » de 2,27 € TTC/mois est ajouté à l'abonnement. Ces offres sont réservées au réseau Hunélec (Haut-Rhin) : le moteur ne filtre pas encore par zone, comme pour GEG.
- **Journalisation SOCLE §8** (#418). Dans l'intégration Home Assistant, chaque module à fonctions a son `_LOGGER = logging.getLogger(__name__)`, avec des messages `%s` et sans f-string ; elle n'importe jamais loguru. Les scripts passent à loguru (groupe `scripts`, jamais dans `manifest.json`), à `WARNING` par défaut et à `DEBUG` avec `SOCLE_DEBUG=1`. Chaque fonction trace son entrée et ses sorties, y compris les `raise` volontaires, et chaque `except` journalise le type et le message de l'exception. Les grandes valeurs (relevés horaires, grilles) sont résumées par leur taille.
- **Tests AST des règles** (`tests/test_journal_regles.py`, d'après `modele-depot`) et **audit** `scripts/audit_debug_sorties.py`. La référence `scripts/audit_debug_sorties.baseline` est à **0**. Le job Qualité échoue si un écart est ajouté.
- `scripts/check_branch_protection.py` est remplacé par la version loguru de `modele-depot`, avec ses tests. Les workflows de release et de protection installent loguru (`uv run --only-group scripts`).
- 4 tests de `offres.py` (`Offre.cles`, erreurs de `charger_offre`) : couverture de 98,0 % à 98,9 %.

## [0.1.0] - 2026-10-22

### Ajouté
- **Offres de marché à prix fixe** (#5, #6) : grilles des fournisseurs en YAML dans `offres/`, comparées comme les tarifs réglementés — abonnement mensuel converti en €/an, puissances non proposées signalées indisponibles, grilles datées appliquées au jour le jour. Lot 1 (#40, #44, #63, #64) : la bellenergie Prudence et Garance, Ohm Sérénité Fixe 1 an, Alterna fixe 1 an. Lot 2 (#38, #43, #56, #57, #61, #62, #65, #68) : Ohm Fixe 2 ans, Alterna Mon électricité du coin, GEG Elec Verte 3 ans, ilek ÉnRFixe+, Primeo Fixe Confort, la bellenergie Constance, Plenitude Pleniweb 1 an, SÉLIA élec vert Fixe.
- **Capteurs par offre** : un capteur de coût sur 12 mois par option de chaque offre, classement mélangé TRV + offres avec libellés.
- **Grilles CRE** (#2) : tarifs réglementés TTC Base et Heures creuses depuis 2012, toutes puissances publiées, copiés depuis l'open data de la CRE (`scripts/maj_tarifs_cre.py`).
- **Moteur de calcul** (#2) : chaque heure consommée est valorisée au prix en vigueur ce jour-là, abonnement compté au jour, heure à cheval sur une limite d'heures creuses répartie au prorata des minutes.
- **Comparaison sur 12 mois** (#2) : lecture des statistiques horaires du capteur d'énergie (recorder), recalcul toutes les 6 h.
- **Capteurs** (#2) : coût de chaque option, option la moins chère (avec classement), économie possible, consommation et part en heures creuses.
- **Configuration depuis l'interface** (#2) : capteur, puissance, option actuelle, plages d'heures creuses (plusieurs plages possibles).

### Modifié
- `cout_option` se règle sur les postes de la grille (`base` ou `hp`/`hc`) au lieu de la clé d'option : prépare les offres de marché sans changer les résultats du TRV.
