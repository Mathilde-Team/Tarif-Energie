# tarifenergie

Intégration Home Assistant : **quel tarif d'électricité aurait coûté le moins cher avec ma consommation réelle des 12 derniers mois ?**

Plutôt qu'une consommation théorique de 4 000 ou 5 000 kWh/an, tarifenergie reprend la consommation **heure par heure** déjà enregistrée par Home Assistant (le capteur du tableau de bord Énergie : Linky, pince ampèremétrique, etc.) et la valorise avec les tarifs officiels.

## Ce que fait la version 0.1

Elle compare, sur les 12 derniers mois de consommation réelle, le coût TTC des options
de tarification des tarifs réglementés (Base, Heures creuses) : abonnement au prorata
du jour, kWh au prix en vigueur à la date de la consommation, heures creuses réparties
au prorata des minutes. La v0.2 y ajoute les offres de marché (voir ci-dessous).

- Compare les **tarifs réglementés** (tarif Bleu) publiés par la [CRE](https://www.data.gouv.fr/datasets/historique-des-tarifs-reglementes-de-vente-delectricite-pour-les-consommateurs-residentiels) : options **Base** et **Heures pleines / Heures creuses**, prix TTC.
- Applique à chaque heure le tarif **en vigueur ce jour-là** : un an de consommation à cheval sur le 1er février et le 1er août est compté avec les bonnes grilles.
- Compte l'abonnement au jour près, pour la puissance souscrite.
- Prend vos plages d'heures creuses (elles dépendent du compteur, pas du fournisseur), même plusieurs plages (« 02:00-07:00, 13:00-16:00 »).

## Capteurs

| Capteur | Valeur | Attributs |
|---|---|---|
| Coût sur 12 mois, option Base (TRV) | € TTC | kWh, part énergie et abonnement, grilles CRE utilisées, période couverte |
| Coût sur 12 mois, option Heures creuses (TRV) | € TTC | kWh HP et HC, idem |
| Coût sur 12 mois, chaque option de chaque offre de marché | € TTC | idem |
| Option la moins chère | `base` / `hphc` ou `<offre>:<option>` (ex. `la_bellenergie_prudence:hphc`) | classement complet avec libellés, options indisponibles et pourquoi |
| Économie possible sur 12 mois | € par rapport à l'option actuelle | classement |
| Consommation sur 12 mois | kWh | période couverte |
| Part en heures creuses | % | |

Avec moins de 12 mois d'historique, les coûts portent sur la période disponible (attribut `jours_couverts`).

## Offres de marché (v0.2)

Les grilles des fournisseurs sont livrées dans `custom_components/tarifenergie/offres/*.yaml`
(inventaire [#6](https://github.com/Mathilde-Team/Tarif-Energie/issues/6), moteur [#5](https://github.com/Mathilde-Team/Tarif-Energie/issues/5)) :
une issue par offre documente la grille, sa date d'effet et ses sources. La v0.2 couvre
les offres **à prix fixe** avec options Base et Heures creuses — 37 offres :

- la bellenergie Prudence 1 an, Constance 2 ans et Garance 3 ans,
- Octopus Energy Eco Fixe Octobre 2026 et Eco Fixe Plus Octobre 2026 (territoire Enedis),
- Ohm Énergie Sérénité Fixe 1 an et Fixe 2 ans,
- Alterna Mon électricité française fixe 1 an et Mon électricité du coin 1 an,
- Engie Elec Référence 3 ans (prix fixe de la part fourniture ; acheminement CU en Base, MUDT en Heures creuses),
- Engie Duo Référence 3 ans, partie électricité (mixte ; Base, même grille qu'Elec Référence 3 ans — option HP/HC en #135, partie gaz documentée hors moteur),
- EDF Zen Estival (prix fixe 12 mois, heures super creuses et heures creuses
  d'été, heures creuses d'hiver — postes et plages saisonniers portés par l'offre),
- TotalEnergies Charge'Heures (heures super creuses 2-6 h et heures creuses
  23-2 h / 6-7 h toute l'année — plages portées par l'offre, sans option Base),
- EDF Zen Fixe 2 ans (kWh HT fixe 2 ans et 1 mois),
- EDF Vert Électrique Week-End (électricité verte, remise week-end et jours fériés, prix révisables 2 fois par an),
- EDF Zen Week-End (remise week-end et jours fériés ; sans jour choisi, contrairement à la Plus) et EDF Zen Week-End Plus (remise week-end, jours fériés et jour choisi — lundi, mercredi ou vendredi ; trois variantes simulées) ; prix révisables 2 fois par an,
- ÉS Énergies Électricité verte à prix fixe 1 an et sa variante 100 % régionale (Strasbourg Électricité Réseaux),
- Gaz de Bordeaux NovaFixe Élec et NovaFixe Bonus Élec (fiche de Bordeaux),
- Gaz de Bordeaux NovaFixe Bonus Duo, partie électricité (mixte électricité + gaz ;
  grille électricité identique à NovaFixe Bonus Élec, fiche de Bordeaux),
- GEDIA All Inclusive GES Électricité (réseau GEDIA, Dreux ; abonnement publié en €/an),
- GEG Mon Offre Elec Verte fixe 3 ans (kWh HC/HP selon la puissance),
- Happ-e by ENGIE Électricité 1 an (prix fixe de la part fourniture ; acheminement CU en Base, MUDT en Heures creuses),
- GEG Mon Offre Elec Verte fixe 3 ans et sa variante Direct Producteur (kWh HC/HP selon la puissance),
- Hunélec Offre à prix fixe 1 an et sa variante 100 % énergie verte (réseau Hunélec, Haut-Rhin),
- ilek ÉnRFixe+ Élec,
- Mint Énergie Classic & Green et Smart & Green,
- Primeo Energie Offre Fixe Confort,
- Primeo Energie Offre Fixe ECO -15 % (Base seule, grille du 01/02/2026, prix HT bloqués jusqu'au 31/07/2027),
- Eni Plenitude Pleniweb 1 an,
- papernest énergie Électricité verte 1 an,
- SÉLIA Mon Contrat élec vert Fixe,
- TotalEnergies Fixe 2 ans,
- elmy Particuliers prix fixe 2 ans (contrats repris par Octopus Energy, plus proposée aux nouveaux clients),
- Wekiwi Offre Duo, électricité Aurore Base et HP/HC (partie électricité seule ; abonnement TRV par défaut, non publié par Wekiwi).

S'y ajoutent les **TRV locaux** des entreprises locales de distribution (`type_prix: reglemente`,
sans durée de fixité, réseau dans `eld:`) : ÉS Énergies (Strasbourg Électricité Réseaux), Barr
Energies (Barr et Villé), GEG (GreenAlp, Grenoble), Gedia (Dreux), SICAE Oise, Energis
(Saint-Avold), Gascogne Énergies Services (Aire-sur-l'Adour), Énergies Services Lannemezan (plateau
de Lannemezan), Oya énergies, Bazas Energies (Bazas), Régie d'Amnéville (Amnéville), SÉOLIS (réseau
Gérédis, Deux-Sèvres), Sorégies (réseau SRD, Vienne), Synelva (pays chartrain), UEM (réseau réséda,
Metz), Vialis (Colmar), Énergies & Services Sarre-Union (Sarre-Union), Régie de Marange-Silvange
(Marange-Silvange), RMMS La Réole (La Réole), Enes Creutzwald (Creutzwald), Enes Hombourg-Haut
(Hombourg-Haut), Enes Schoeneck (Schoeneck), UME (Usine Municipale
d'Erstein), Soréa (Maurienne), SICAE-Précy (Aube), SICAE de la Somme, du Cambraisis, SICAE de la
Vallée du Sausseron, SICAP Pithiviers, SIEL Labergement-Sainte-Marie et Énergies Services Lavaur
(Lavaur, Saint-Paul-Cap-de-Joux).

Les offres **indexées sur le TRV** (`type_prix: indexe_trv`) n'ont pas de durée de fixité et
pas de réseau `eld:`. Leur grille TTC datée est à mettre à jour à chaque mouvement du TRV :
EDF Zen Online (Base de 3 à 15 kVA, HC de 6 à 36 kVA), TotalEnergies Access Électricité
(kWh HT remisé de 10 % pendant 3 ans), TotalEnergies Heures Eco Électricité (prix du TRV),
TotalEnergies Spéciale Électricité et Gaz (duale : partie électricité au prix du TRV,
Base et HP/HC ; remise annoncée de 10 % non modélisée, partie gaz documentée hors moteur),
Gaz de Bordeaux NovaFlex Élec (kWh HT -5 %, fiche de Bordeaux ; Base de 3 à 15 kVA),
Mint Énergie Online & Green (kWh HTT -5 %), Alterna Mon électricité française indexée,
Alpiq Électricité Sérénité (kWh HT -0,5 %), Primeo Offre Essentielle Verte (kWh HT -5 %)
et Jeety Energy Elec-Dom (ex-« élecocité », grille de février 2026, dernière publiée ; HC à partir de 6 kVA).

Chaque offre est comparée sur la consommation réelle comme les tarifs réglementés :
puissances non proposées (ex. Heures creuses en 3 kVA) signalées comme indisponibles,
grilles datées appliquées au jour le jour. Les offres dynamiques ou à coloration de
jours (OctoTempo) viendront ensuite. Pour ajouter une offre : un fichier
YAML sur le modèle des existants, une issue d'inventaire la documentant.

## Installation

1. HACS → Dépôts personnalisés → `https://github.com/Mathilde-Team/Tarif-Energie`, catégorie « Intégration ».
2. Installer tarifenergie, redémarrer Home Assistant.
3. Paramètres → Appareils et services → Ajouter une intégration → tarifenergie.

## Limites connues

- La CRE ne publie l'option Base que jusqu'à 15 kVA : au-delà, elle est signalée indisponible.
- Statistiques horaires : une heure à cheval sur une limite d'heures creuses (ex. 23:30) est répartie au prorata des minutes.
- Pas encore de Tempo (#3), de gaz (#4) ni d'offres de marché des fournisseurs (#5).
- Parties gaz des offres mixtes (TotalEnergies Spéciale #112, Engie Duo Référence #113) : hors comparateur, grilles documentées dans [docs/sources.md](docs/sources.md).

Sources et particularités des données : [docs/sources.md](docs/sources.md).

## Données et licences

Le code de l'intégration est sous licence [MIT](LICENSE) (exception Home Assistant du socle de l'équipe). Les données livrées avec l'intégration ne sont pas couvertes par cette licence :

- **Tarifs réglementés (TRV)** — `custom_components/tarifenergie/tarifs/*.csv` : fichiers open data de la [Commission de régulation de l'énergie (CRE)](https://www.cre.fr/documents/open-data.html) (`Option_Base.csv`, `Option_HPHC.csv`, `Option_Tempo.csv`), copiés **sans modification** par `scripts/maj_tarifs_cre.py`. La CRE les présente comme « réutilisables librement » ; ses [mentions légales](https://www.cre.fr/mentions-legales-et-politique-de-confidentialite.html) demandent de respecter l'intégrité des documents, de citer la source et la date du document (à défaut sa date de mise à jour) et de donner un lien vers la page d'origine. Le jeu de données [data.gouv.fr](https://www.data.gouv.fr/datasets/historique-des-tarifs-reglementes-de-vente-delectricite-pour-les-consommateurs-residentiels) n'indique pas de licence (« License Not Specified »).
  Attribution : « Source : Commission de régulation de l'énergie (CRE), open data Marchés de détail, https://www.cre.fr/documents/open-data.html », avec la date de mise à jour des fichiers.
- **Offres de marché** — `custom_components/tarifenergie/offres/*.yaml` : prix relevés à la main dans les grilles tarifaires publiques des fournisseurs. Chaque fichier cite sa grille dans le champ `source:` et la date d'effet ; l'issue de l'offre documente le relevé. Seuls les prix (des faits) sont repris, pas les documents : ces grilles restent la propriété de leurs fournisseurs et font foi en cas d'écart.
- **Consommation** : lue dans le recorder de votre Home Assistant, elle ne quitte pas votre installation.

## Développement

```sh
uv run --only-group lint ruff check .
uv run -p 3.13 --only-group test pytest --cov
python3 scripts/maj_tarifs_cre.py   # à chaque mouvement tarifaire
```

Branches : PR vers `dev`, puis relais `dev` → `main`. Licence MIT.
