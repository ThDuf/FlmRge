# Extension Météo (Flamme Rouge: Meteo) — règles et plan d'implémentation

> Recherche faite le soir de la session ; **pas encore implémenté** (voir roadmap README).
> Sources : passionludique.fr, zatu.com, trictrac.net, boardgamegeek (Flamme Rouge: Meteo).

## Règles officielles (résumé)

**Contenu** : 4 panneaux + 13 jetons météo + livret.

**Mise en place** : un jeton météo **face cachée sur chaque tuile droite** (les 7 droites d'une
étape), révélé quand un coureur arrive dessus. Variante « course d'un jour » : météo de départ
tirée aux 2d6 — brouillard 2, pluvieux 3-4, couvert 5-6, venteux 7-8, ensoleillé 9-11, canicule 12.

**Effets par jeton** :

| Jeton | Effet |
|-------|-------|
| Vent arrière (jaune) | à la prochaine phase d'énergie, le coureur sur la tuile **pioche 5 cartes au lieu de 4** |
| Vent de face (bleu) | il **pioche 3 cartes au lieu de 4** |
| Vent de travers (vert) | **aucune aspiration** donnée ni reçue sur toute la tuile (comme côte/pavés) |
| Pluie (noir) | si la case d'arrivée du coureur est **pleine** (mouvement bloqué) → **chute** : coureur couché, ne donne plus d'aspiration ; à son prochain tour il se relève et sa carte vaut **−2** (carte 2 = se relève sans bouger). Pénalité appliquée après les ajustements descente ; ne modifie pas le plafond de 5 en montée |

## Plan d'implémentation proposé

1. **Modèle** : champ `weather` sur `Cell` (`NONE / TAILWIND / HEADWIND / CROSSWIND / RAIN`),
   rempli à la construction de la piste quand l'option est active (`Game(meteo=True)`) :
   mélange des 13 jetons, un par tuile droite, face cachée jusqu'au premier passage d'un coureur.
2. **Moteur** (`src/game/game.py`, `src/game/track.py`) :
   - pioche : 4 cartes de base, **5 en vent arrière, 3 en vent de face** (tuile du coureur au moment de piocher) ;
   - aspiration : coureurs sur tuile **vent de travers** ne donnent ni ne reçoivent (même traitement
     que la montée dans `compute_slipstream_steps`) ;
   - **chute pluie** : dans `move_runner`, si le coureur est sur tuile pluie et que son mouvement
     est bloqué → `runner.crashed = True` ; un tombé ne donne pas d'aspiration ; à son prochain
     tour sa carte vaut **−2** (après ajustements descente, plafond 5 en montée inchangé), puis
     `crashed = False`.
3. **UI** (`src/main.py`) : icônes météo sur les cases (flèches jaune/bleu/vert, goutte noire),
   « ? » tant que non révélé, indicateur de chute (coureur couché / croix rouge), messages dans le
   log, case à cocher « Extension Météo » au menu de sélection d'étape.
4. **Tests** : taille de main 5/3 selon le vent, pas d'aspiration en vent de travers, chute en
   pluie + pénalité −2 au tour suivant.
