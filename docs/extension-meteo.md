# Extension Météo (Flamme Rouge: Meteo) — règles et implémentation

> ✅ **Implémenté** (voir roadmap README) : `Game(meteo=True)`, case « Météo » au menu,
> `tests/test_meteo.py`.
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

## Implémentation réalisée

1. **Modèle** (`src/game/track.py`) : enum `WeatherType` (`NONE / TAILWIND / HEADWIND / CROSSWIND / RAIN`),
   champs `weather` + `weather_revealed` sur `Cell`, `WEATHER_TOKENS` (les 13 jetons : 3/3/3/4),
   `Track.assign_weather()` (un jeton face cachée par tuile droite, mélange du sac),
   `Track.weather_at(x)` / `Track.reveal_weather_at(x)` (révèle toute la tuile au 1er passage).
2. **Moteur** (`src/game/game.py`, `src/game/track.py`) :
   - pioche : `Game._draw_count_for()` — 4 de base, **5 en vent arrière, 3 en vent de face**
     (tuile du coureur au moment de piocher, `start_turn`) ;
   - aspiration : `Track.blocks_slipstream_at()` — vent de travers et coureur couché traités
     comme la montée dans `compute_slipstream_steps` (ni donneur ni receveur) ;
   - **chute pluie** : dans `Track.move_runner`, coureur sur tuile pluie dont la case d'arrivée
     est pleine → `runner.crashed = True` (reste sur place) ; à son prochain mouvement il se
     relève, sa carte vaut **−2** (après ajustements descente, plafond 5 en montée inchangé),
     `crashed = False` ; `Game._reveal_weather()` révèle les jetons au passage et les logue
     dans l'historique (`entry["weather"]`).
3. **UI** (`src/main.py`) : case « Météo » du menu passée à `Game(meteo=...)` ; icônes météo sur
   les cases du parcours (flèches jaune/bleu/vert, goutte noire, « ? » tant que caché), croix rouge
   sur le coureur couché, chips météo dans la légende, section « Météo » dans l'historique,
   bandeau « CHUTE sous la pluie ! ».
4. **Tests** (`tests/test_meteo.py`, 18 tests) : pose des jetons (droites seules, face cachée),
   révélation, pioche 5/3, pas d'aspiration en vent de travers (donneur et receveur), coureur
   couché sans aspiration, chute en pluie + relevé −2 (carte 5 → 3 cases, carte 2 → sans bouger),
   plafond montagne inchangé, câblage UI du menu.
