# Sources de données

Vérifiées le 18/10/2026. Découpage du projet : #1.

## Utilisées

| Donnée | Source | Format | Usage |
|---|---|---|---|
| Tarifs réglementés d'électricité (TRVE) Base, Heures creuses, Tempo, depuis 2012, HT et TTC, par puissance | CRE, [jeu de données sur data.gouv.fr](https://www.data.gouv.fr/datasets/historique-des-tarifs-reglementes-de-vente-delectricite-pour-les-consommateurs-residentiels) (fichiers [Option_Base.csv](https://www.cre.fr/fileadmin/Documents/Open_data/Marches_de_detail/Option_Base.csv), [Option_HPHC.csv](https://www.cre.fr/fileadmin/Documents/Open_data/Marches_de_detail/Option_HPHC.csv), [Option_Tempo.csv](https://www.cre.fr/fileadmin/Documents/Open_data/Marches_de_detail/Option_Tempo.csv), [Notice.txt](https://www.cre.fr/fileadmin/Documents/Open_data/Marches_de_detail/Notice.txt)) | CSV `;`, virgule décimale, dates JJ/MM/AAAA | `tarifs/*.csv`, copiés tels quels ; `scripts/maj_tarifs_cre.py` les remet à jour |
| Consommation réelle | Statistiques horaires du recorder Home Assistant (capteur d'énergie cumulée) | `change` par heure, converti en kWh | `coordinateur.py` |

Particularités constatées dans les fichiers CRE :
- l'option **Base** n'est publiée que de 3 à 15 kVA : au-delà, l'option est signalée indisponible ;
- l'option **Heures creuses** existe en 3 kVA depuis la grille du 01/08/2026 ;
- les prix TTC incluent CTA, accise (ex-CSPE), TCFE et TVA, selon la notice ;
- les abonnements TTC de l'option Heures creuses ont 7 décimales (ex. 239,8378787 €/an) : ils sont gardés tels quels, l'arrondi au centime se fait sur le total.

Le jeu de données data.gouv.fr indique une licence « non spécifiée » ; la CRE le publie comme données ouvertes sur son site. À confirmer avant toute redistribution hors de ce dépôt.

## Documentées hors moteur

Les parties **gaz** des offres mixtes ne sont pas comparées par l'intégration (moteur
électricité uniquement, #4) ; leurs grilles relevées restent documentées dans les issues :

| Offre | Partie gaz | Issues | Relevé |
|---|---|---|---|
| TotalEnergies Spéciale Électricité et Gaz | indexée sur le prix repère de vente de gaz (PRVG) de la CRE, 6 zones tarifaires ; option T1 < 4 MWh/an, option T2 | #112 (T1), #387 (T2) | 19/10/2026, grille « Offre - Spéciale - 1 oct. 2026 » |
| Engie Duo Référence 3 ans | prix fixe de la fourniture 3 ans, acheminement révisé 1 fois/an ; 5 % biométhane | #113 | 19/10/2026, fiche « Grille tarifaire - octobre 2026 » |

La partie électricité de ces offres mixtes est modélisée dans les issues correspondantes
(TotalEnergies Spéciale : #96/#134 ; Engie Duo : #98/#135).

## Calendriers Tempo

| Donnée | Source | Format | Dans le dépôt |
|---|---|---|---|
| Jours blancs et rouges Tempo, saisons 2022-2023 à 2025-2026 (option Tempo #108, option Flex #97) | [api-couleur-tempo.fr](https://www.api-couleur-tempo.fr/api/joursTempo?periode=2025-2026) (données RTE/EDF), relevé le 04/11/2026 | YAML, une liste de dates par saison (1er septembre au 31 août) | `calendriers/tempo_blanc.yaml`, `calendriers/tempo_rouge.yaml` ; un jour absent est bleu ; mise à jour par PR en fin de saison |

## Prévues

| Donnée | Source | Issue |
|---|---|---|
| Prix repère du gaz | CRE | #4 |
| Offres de marché des fournisseurs | Comparateur Énergie-Info du Médiateur national de l'énergie (sans API publique documentée : conditions de réutilisation à vérifier d'abord) | #5 |
| Distributeur par commune | Agence ORE | #5 |
