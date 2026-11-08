# Extension Météo (Flamme Rouge: Meteo) — règles officielles vérifiées et implémentation

> ✅ **Implémenté** et **corrigé selon les règles officielles** (vérification en ligne, voir sources en bas).
> Sources : rulebook Meteo (BGG filepage 170569), zatu.com / board-game.co.uk (citent le rulebook),
> passionludique.fr, therewillbe.games, videogamegeek (designer diary), trictrac.net.

## Règles officielles (vérifiées)

**Contenu** : 4 panneaux (standees) + **13 jetons météo** = **9 jetons vierges** (sans effet)
+ **4 jetons événement** (1 vent arrière, 1 vent de face, 1 vent de travers, 1 pluie/Wet).

**Mise en place** : on mélange les 13 jetons et on en pose **un face visible sur chaque
tuile droite du parcours, EN EXCLUANT les tuiles de départ et d'arrivée**. Les jetons
à effet reçoivent leur panneau le long de la tuile, puis **tous les jetons sont retirés** :
la météo est donc **publique dès le début de la course** (pas de jeton face cachée).

**Effets par jeton** :

| Jeton | Effet officiel |
|-------|----------------|
| Vent arrière (jaune) | le coureur sur la tuile **pioche 5 cartes** au lieu de 4 |
| Vent de face (bleu) | il **pioche 3 cartes** au lieu de 4 |
| Vent de travers (vert) | **aucune aspiration donnée ni reçue** sur toute la tuile (comme côte, pavés, arrivée) |
| Pluie / Wet (noir) | si le coureur **termine son mouvement dans une zone humide en ayant perdu des cases à cause d'un blocage** (case d'arrivée pleine), il **chute** : couché sur la case où il s'est arrêté. **Case entièrement accidentée = impassable** (on s'arrête une case avant ; si cette case est humide → nouvelle chute, effet domino). Un coureur couché **ne donne ni ne reçoit l'aspiration**. Pour se relever à son prochain tour : **−2 à sa carte, appliqué APRÈS les modificateurs** (min 5 en descente, plafond 5 en montée) — ex. du rulebook : carte 2 en descente = 5 normalement, **3 après une chute** |

## Implémentation réalisée

1. **Modèle** (`src/game/track.py`) : enum `WeatherType` (`NONE / TAILWIND / HEADWIND / CROSSWIND / RAIN`),
   `WEATHER_TOKENS` = 9 `NONE` + 1 de chaque événement (13 jetons), champs `weather` +
   `weather_revealed` sur `Cell`, `Track.assign_weather()` : un jeton **face visible** par tuile
   droite **hors tuiles de départ/arrivée** (détection via `CellRunType.START/END`),
   `Track.weather_at(x)`.
2. **Moteur** (`src/game/game.py`, `src/game/track.py`) :
   - pioche : `Game._draw_count_for()` — 4 de base, **5 en vent arrière, 3 en vent de face**
     (tuile du coureur au moment de piocher, `start_turn`) ;
   - aspiration : `Track.blocks_slipstream_at()` — vent de travers **et** coureur couché traités
     comme la montée dans `compute_slipstream_steps` (ni donneur ni receveur) ;
   - **chute pluie** dans `Track.move_runner` : case entièrement accidentée **impassable**
     (arrêt une case avant, effet domino) ; si le mouvement se termine **bloqué dans une case
     humide** → `runner.crashed = True` sur la case d'arrêt ; à son prochain mouvement le
     coureur se relève avec **carte − 2 après les modificateurs** (`effective_steps` d'abord,
     puis −2), `crashed = False` ;
   - la météo de la course est loggée dans l'historique dès la mise en place
     (entrée « Météo de la course », tour 0).
3. **UI** (`src/main.py`) : case « Météo » du menu passée à `Game(meteo=...)` ; icônes météo
   visibles sur les tuiles droites (flèches jaune/bleu/vert, goutte noire), croix rouge sur le
   coureur couché, chips météo dans la légende, section « Météo de la course » dans l'historique,
   bandeau « CHUTE sous la pluie ! ».
4. **Tests** (`tests/test_meteo.py`, 19 tests) : composition 9+4, pose face visible hors
   départ/arrivée, pioche 5/3, pas d'aspiration en vent de travers (donneur et receveur),
   coureur couché sans aspiration, chute à la case d'arrêt si bloqué en zone humide, pas de
   chute si non bloqué ou hors zone humide, case tout-accident impassable (domino, avec et
   sans pluie), relevé −2 après modificateurs (descente : carte 2 → 3 ; montée : plafond 5
   puis −2), log de mise en place, câblage UI du menu.

> Note : une variante « course d'un jour » (météo globale tirée aux 2d6) circule sur certains
> forums mais n'a pas été retrouvée dans le rulebook — non retenue.
