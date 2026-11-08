# Extension Peloton (Flamme Rouge: Peloton) — recherche des règles officielles

> Recherche faite sur le rulebook officiel (PDF anglais, 1jour-1jeu / ultraboardgames.com),
> complété par dicetower, zatu, strongholdgames, lelabodesjeux, islaythedragon, opinionatedgamers.
> **Pas encore implémenté** (branche `extension-peloton`, item roadmap).

## Contenu

- **2 plateaux joueurs** (équipes rose et blanche) → jusqu'à **6 joueurs** (2 équipes de plus).
- **106 cartes** : 60 Énergie (2 decks Sprinteur + 2 decks Rouleur, un par couleur — même
  composition que la base : Sprinteur 15 cartes `2,2,3,3,4,4,5,5,6,6,6,7,7,7,8`,
  Rouleur 15 cartes `2,2,2,3,3,3,4,4,4,5,5,5,6,6,7`) + 30 Fatigue (2 decks de 15 cartes valeur 2)
  + 6 cartes Étape **double face** (face 5-6 joueurs / face 2-4 joueurs) + 2 cartes référence
  + 6 cartes **Muscle Team** + 2 cartes **Peloton Attack!**.
- **4 figurines** cyclistes (2 par couleur : un Rouleur + un Sprinteur).
- **9 tuiles piste double face** : pavés, zones d'approvisionnement, tuile Échappée (tile #2),
  tuile Bonus / arrivée large 3 files (tile #9, pour 5-6 joueurs), tuile départ 3 files (5-6 joueurs), etc.

## Règles nouvelles (confirmées rulebook)

### Largeur des cases
- Les cases ne font plus seulement 2 files : **1 à 3 files** selon la tuile.
- Un coureur peut traverser les autres, mais ne peut pas terminer son mouvement sur une case
  pleine : il s'arrête derrière, sur la première case avec une file libre.

### Pavés (Cobblestones)
- Tuiles créant des sections **étroites à 1 file** (parfois 2).
- **Aucune aspiration donnée ni reçue** par un coureur sur des pavés (comme une montée).

### Zones d'approvisionnement (Supply Zones)
- Tuiles créant des sections **larges à 3 files**.
- Si on **commence son tour** dans une zone d'approvisionnement : **vitesse minimale = 4**.
  L'aspiration s'applique normalement.
- Note : 3 coureurs côte à côte dans une zone 3 files qui aspirent vers une section plus
  étroite → déplacer d'abord les 2 files de droite ; le 3e reste sur sa case mais passe en
  file de droite. Un coureur derrière eux reste sur place (case devant encore occupée).

### Variante Échappée (Breakaway)
- La **2e tuile de l'étape** (juste après le départ) doit être la **tuile Échappée** (tile #2,
  face `e2` en 5-6 joueurs, face `2` en 1-4 joueurs). Placement normal dans la zone jaune.
- **Phase d'enchères** avant le 1er tour, 2 manches simultanées : choisir 1 coureur, piocher
  4 cartes de son deck Énergie, en jouer **1 face cachée** (l'offre), recycler le reste, révéler.
  Répéter pour la 2e manche.
- **5-6 joueurs** : les **2** plus hautes offres (total des 2 cartes) partent dans l'échappée,
  la plus haute en file de droite ; **2-4 joueurs** : seule la plus haute offre part.
  Égalité → le coureur le plus en arrière (le plus à gauche) gagne.
- L'échappé est placé sur la **case échappée** de la tuile (4 cases après la ligne de départ).
- Les cartes jouées des échappés sont **retirées du jeu** ; ils prennent **2 cartes Fatigue**
  qu'ils recyclent ; les perdants recyclent leurs cartes d'enchère ; tout le monde remélange
  dans son deck.

### Conception d'étapes (conseils du rulebook)
- 2-3 sections montée/pavés max par étape ; **pas de zone d'approvisionnement juste avant
  l'arrivée** ; une étape = 9 tuiles droites + tous les virages ; chaque tuile d'extension
  remplace une droite de base ; en 5-6 joueurs, ajouter la tuile Bonus (#9) + les 2 zones
  d'approvisionnement.

### Équipes factices (dummy teams, IA)
- **Équipe Peloton** (une seule) : les 2 coureurs d'une couleur + **seulement le deck Rouleur**
  de cette couleur + **2 cartes Attack!** mélangées. Placée dans la zone de départ **avant** les
  humains, l'un devant l'autre, le plus en avant possible. Ne fait pas d'enchères. Phase
  Mouvement : après les humains, piocher 1 carte pour l'équipe, déplacer les 2 coureurs
  (ordre normal) selon la carte ; si c'est une carte **Attack!** → le coureur le plus en avant
  avance de **2**, le plus en arrière de **9**. **Ne prend jamais de carte Fatigue.**
- **Équipe Muscle** (plusieurs possibles) : les 2 coureurs d'une couleur + leurs 2 decks +
  **1 carte Muscle** dans le deck du Sprinteur. Placée avant les humains, Sprinteur devant
  Rouleur, le plus en avant possible. Ne fait pas d'enchères, ne prend jamais de Fatigue.
  Piocher la carte du dessus de chaque deck, déplacer normalement.
- Les deux ensemble : placer l'Équipe Peloton d'abord.
- **Solo** : 1 Peloton + 1 Muscle ; le joueur démarre avec 3 cartes Fatigue réparties à sa
  guise (record du designer : 6). **2 joueurs avec factices** : ajouter d'abord le Peloton.

### Plus de 6 joueurs (jusqu'à 12)
- Chacun pour soi : 1 coureur par joueur, pas de plateau joueur ; le plus jeune place en
  premier, puis sens horaire ; variante Échappée recommandée (face `e2` de la tuile).

## Plan d'implémentation proposé

1. **Modèle** (`src/game/track.py`) : largeur de case déjà paramétrée (`Tile.width`,
   `Cell.runners` liste) — généraliser : pavés = `CellGeographyType.COBBLE` (1 file, pas
   d'aspiration, même traitement que montée dans `compute_slipstream_steps`) ; zone
   d'appro = 3 files + `CellGeographyType.SUPPLY` (min 4 si le coureur y commence son tour,
   dans `effective_steps`) ; nouvelles tuiles Peloton dans `TILE_DEFS`-like (pavés, supply,
   échappée, arrivée large).
2. **Moteur** (`src/game/game.py`) : variantes — `Game(peloton=True)` ; enchères
   d'échappée (2 manches, 2 cartes Fatigue pour le(s) gagnant(s), cartes retirées du jeu) ;
   équipes factices Peloton/Muscle (IA : piocher et jouer automatiquement, Attack! = 2/9,
   jamais de Fatigue).
3. **UI** (`src/main.py`) : case « Peloton » au menu déjà prête ; tuiles pavés / zones d'appro ;
   5-6 joueurs (couleurs rose/blanc) ; placement échappée.
4. **Tests** : pas d'aspiration sur pavés, min 4 en zone d'appro, largeur 1/3 files,
   enchères échappée (2 manches, égalité, +2 fatigue), IA Peloton (Attack! 2/9) et Muscle.
