# Flamme Rouge - Jeu de Société Numérique

Recréation numérique du jeu de société **Flamme Rouge** en Python avec Pygame.

![Flamme Rouge Logo](https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Flamme_Rouge_logo.svg/1200px-Flamme_Rouge_logo.svg.png)

## 📌 À propos du jeu

**Flamme Rouge** est un jeu de course cycliste tactique où chaque joueur contrôle une équipe de deux coureurs : un **rouleur** et un **sprinteur**. Le but est d'être le premier à franchir la ligne d'arrivée avec l'un de ses coureurs.

### Règles principales
- Avant le 1ᵉʳ tour, **phase de placement** : les coureurs sont placés derrière la ligne de départ, au plus proche de la ligne (manuellement ou aléatoirement).
- Chaque tour se divise en **4 phases** : Énergie, Mouvement, Aspiration, Terminale.
- **Phase d'Énergie** : Les joueurs piochent 4 cartes et en jouent une face cachée pour chaque coureur.
- **Phase de Mouvement** : Les cartes sont révélées et les coureurs avancent (pas à pas, un clic par mouvement).
- **Phase d'Aspiration** : Application de l'**aspiration** (pack par pack).
- **Phase Terminale** : Application de la **fatigue**.

### Mécaniques spéciales
- **Aspiration** : Si exactement une case vide (2 files) sépare deux packs, le pack arrière avance d'une case et fusionne ; le pack fusionné est revérifié immédiatement (aspirations en cascade possibles). Les coureurs gardent leur file.
- **Fatigue** : Chaque coureur dont la CASE devant lui est vide (2 files) reçoit une carte Fatigue (valeur 2). Une simple file libre ne suffit pas.
- **Mouvement** : Un coureur traverse les autres coureurs ; il ne peut pas finir son mouvement sur une case pleine (il s'arrête derrière sur la première file libre). Case d'arrivée vide → file de droite (file A).
- **Decks** : Les cartes jouées sont retirées du jeu ; les cartes non jouées sont recyclées. Les decks s'épuisent au fil de la course.
- **Montées** (rouge) : deux cas selon la distance à la montée — si le coureur part d'une montée ou y **entre dans ses 5 premières cases**, son énergie est plafonnée à 5 (il peut la traverser) ; si sa carte l'y ferait entrer à la **6ᵉ case ou plus**, il **stoppe son mouvement sur la dernière file libre avant la montée** (le déplacement peut alors atteindre 6-7 cases de plaine). Pour l'aspiration : un coureur en montée ne donne ni ne reçoit ; dans un pack qui aspire, il reste sur place et bloque ceux derrière lui, mais ses coéquipiers hors montée glissent quand même (le pack peut se séparer).
- **Descentes** (bleu) : un coureur qui **part** d'une descente avance d'au minimum 5 cases ; l'aspiration s'y applique normalement.
- **Fin de course** : la course se termine dès qu'un coureur franchit la ligne d'arrivée — concrètement à la fin du tour où au moins un coureur la franchit (le tour se joue jusqu'au bout : mouvement, aspiration, fatigue). **Elle ne continue pas après un gagnant** : la partie est terminée (`game_over`). Le **vainqueur** est le coureur allé **le plus loin au-delà de la ligne** parmi ceux qui l'ont franchie ce tour ; en cas d'égalité, c'est celui de la **file de droite (A)** qui gagne. Un coureur ne peut de toute façon pas dépasser la dernière case de la piste.

---

## 🚀 Installation

### Prérequis
- Python 3.10 ou supérieur
- Pygame

### Étapes d'installation

1. **Cloner le dépôt** :
   ```bash
   git clone https://github.com/ThDuf/FlmRge.git
   cd FlmRge
   ```

2. **Installer les dépendances** :
   ```bash
   pip install pygame
   ```

3. **Lancer le jeu** :
   ```bash
   python src/main.py
   ```

---

## 🎮 Contrôles

| Touche / souris | Action |
|--------|--------|
| **Clic gauche** | Sélectionner une carte pour la jouer (surbrillance au survol) ; **drag sur le parcours** = déplacer la caméra |
| **Clic droit (drag)** | Déplacer aussi la caméra |
| **Molette** | Zoom sur le parcours (au-dessus du log : fait défiler l'historique) |
| **ENTRÉE / Bouton d'action** | Avancer d'une étape : lancer le mouvement, puis **un coureur à la fois**, puis l'aspiration **pack par pack** |
| **+ / -** | Zoom avant / arrière |
| **Flèches** | Panoramique de la caméra |
| **H** | Masquer/Afficher les cartes des joueurs |
| **D** | Afficher/Masquer les decks restants |
| **J** | Overlay de l'historique complet |
| **Ctrl+A / Ctrl+C** (dans le log) | Tout sélectionner / copier le texte sélectionné |
| **TAB** (partie terminée) | Basculer podium ↔ état final du circuit |
| **R** | Recommencer l'étape en cours |
| **Échap** | Retour au menu de sélection |

**Disposition de l'écran** : un **bandeau de titre** (fanion rouge, FLAMME ROUGE, étape et tour en cours) et un **bandeau de phase** coloré avec la description de la phase en cours surplombent la fenêtre. **Tout le reste au-dessus de la barre du bas est le parcours** dans son cadre (tracé réel des tuiles, zoom molette ou +/-, panoramique flèches ou drag souris, tracé clippé dans le cadre). **En bas du cadre**, la **légende sur fond blanc** (Départ jaune clair, Arrivée jaune vif, Montée rouge, Descente bleu) avec à sa droite les boutons caméra **« Tête de course »**, **« Peloton »** et **« Vue d'ensemble »**. **Barre du bas** : à gauche le panneau des cartes d'**un joueur à la fois** (onglets de joueur au-dessus), au centre le **log / historique des coups** (texte sélectionnable Ctrl+A/Ctrl+C, scrollable à la molette, overlay avec J), à droite le **bouton d'action** et le bouton violet **« Tour aléatoire »**. Fenêtre **redimensionnable** (min 900x600).

---

## 📁 Structure du projet

```
FlmRge/
├── assets/                 # (aucun asset embarqué : tout est dessiné en vectoriel)
├── saves/                  # Parcours personnalisés sauvegardés en JSON (éditeur de piste)
├── src/
│   ├── __init__.py
│   ├── main.py             # Point d'entrée : menu, éditeur de piste, partie, podium
│   ├── game/
│   │   ├── __init__.py
│   │   ├── card.py         # Cartes Énergie/Fatigue
│   │   ├── runner.py       # Coureurs (Rouleur/Sprinteur)
│   │   ├── player.py       # Joueurs et leurs decks
│   │   ├── track.py        # Piste, cellules, tuiles (géographie case par case)
│   │   └── game.py         # Moteur du jeu (tours, règles, étapes officielles, sauvegarde JSON)
│   └── ui/                 # Réservé (scènes)
├── tests/                  # Tests unitaires (unittest)
├── requirements.txt
└── README.md
```

---

## 🛠️ Développement

### Lancer les tests
```bash
python -m unittest discover -s tests
```

### Ajouter une nouvelle étape
1. Ajouter son code de tuiles (lettres) dans `OFFICIAL_STAGES` dans `src/game/game.py` — la piste est construite par `_build_track` / `build_track_from_code`.

Un parcours personnalisé se crée directement dans l'**éditeur de piste** (menu) et se sauvegarde en JSON dans `saves/` (`save_track_json` / `load_track_json` / `list_saved_tracks`).

### Personnaliser les decks
- Modifier la méthode `_generate_energy_deck` dans `src/game/game.py` pour ajuster la distribution des cartes.

---

## 🎨 Assets

Aucun asset (image, son) n'est embarqué : tout est dessiné en vectoriel par le code (piste, coureurs, cartes). Vous pouvez créer vos propres assets (ex. [Kenney.nl](https://kenney.nl/)) si vous le souhaitez. Vous pouvez :
- **Créer vos propres assets** (recommandé pour un projet personnel).
- **Utiliser des assets libres de droits** (ex: [Kenney.nl](https://kenney.nl/)).
- **Ajouter des placeholders** pour tester le jeu.

### Structure recommandée pour les assets
```
assets/
├── sprites/
│   ├── runners/
│   │   ├── sprinter_red.png
│   │   ├── sprinter_blue.png
│   │   ├── roller_red.png
│   │   └── roller_blue.png
│   └── cards/
│       ├── card_2.png
│       ├── card_3.png
│       └── ...
└── tracks/
    ├── straight.png
    ├── turn_light.png
    ├── turn_sharp.png
    ├── uphill.png
    └── downhill.png
```

---

## 🤝 Contribuer

Les contributions sont les bienvenues ! Voici comment contribuer :
1. **Forker** le dépôt.
2. **Créer une branche** pour votre fonctionnalité (`git checkout -b feature/ma-fonctionnalité`).
3. **Commiter** vos changements (`git commit -m "Ajout de ma fonctionnalité"`).
4. **Pousser** vers la branche (`git push origin feature/ma-fonctionnalité`).
5. **Ouvrir une Pull Request**.

---

## 📜 Licence

Ce projet est sous licence **MIT**. Vous êtes libre de l'utiliser, le modifier et le distribuer.

---

## 📬 Contact

Pour toute question ou suggestion, ouvrez une **Issue** sur GitHub ou contactez-moi via [mon profil GitHub](https://github.com/ThDuf).

---

## 🗺️ Étapes disponibles

Menu de sélection au lancement : choix de l'étape (clic ou flèches + ENTRÉE ; `Échap` y retourne en pleine partie, `R` relance l'étape en cours) **avec prévisualisation du tracé** de l'étape survolée à droite (panneau qui grandit avec la fenêtre, avec profil d'altitude km/D+ en grand sous le tracé), puis choix du **nombre de joueurs (2 à 4)**. La liste est scrollable, filtrable via une barre de recherche, et organisée en catégories : circuits du jeu de base, circuits perso (`saves/*.json`), plus le bouton « Créer un circuit » (éditeur de piste) toujours visible en bas. Les **6 étapes officielles de la boîte de base** sont codées par les lettres de leurs 21 tuiles (correspondance officielle : `a`=départ, `u`=arrivée, droites `b c d f l m n`, virages légers `h k q r s t`, virages serrés `e g i j o p`, majuscule = face montagne) :

| Étape | Code | Profil |
|-------|------|--------|
| Avenue Corso Paseo | `abcdefghijklmnopqrstu` | plat (tutoriel) |
| Firenze - Milano | `abcgi D H qntm K O L rep J sfu` | vallonné |
| Ronde van Wevelgem | `abcmgfteqon L P jk I D H r S u` | vallonné |
| La Haut Montagne | `abcfimet K G L H J sdop R Q N U` | très montagneuse |
| La Classicissima | `A eb Q R N H P cgik D F s L ojmtu` | vallonné |
| Col du Ballon | `AnLHgceqtrMBoipjDFkSu` | montagne (Vosges) |

> **Modèle de tuile** : chaque tuile = `(virage, largeur, cases)` dans `src/game/game.py` (`TILE_DEFS`, `MOUNTAIN_DEFS` pour les faces majuscules). `virage` = (angle en radians, sens +1/-1), `None` = droite ; `largeur` = nombre de files (2 en base) ; `cases` = alphabet `CELL_CHARS` de `src/game/track.py` (initiales anglaises : `f`=flat, `u`=uphill, `d`=downhill, `s`=ligne de départ, `e`=ligne d'arrivée) — ex. `a` = `"sssssf"` (6 cases, ligne sur les 5 premières), `B` = `"ddddff"` (descente sur les 4 premières cases seulement). Une tuile majuscule est la **face montagne** de la tuile : géographie case par case (`CellGeographyType` : FLAT/UPHILL/DOWNHILL) et virage propre relevé sur la tuile physique (pas forcément le miroir de la face plate — voir `MOUNTAIN_DEFS`) ; la ligne de course vit sur la case (`CellRunType` : NONE/START/END). Longueurs officielles : départ 6, arrivée 6 (`u` = `"feeeee"`, ligne sur les 5 dernières), droites 6, virages 2 → étapes officielles = 78 cases. Angles des virages officiels : 45° (léger) / 90° (serré). Dans la prévisualisation du menu (panneau de droite), le tracé est coloré **case par case** : départ jaune clair, arrivée jaune vif (deux jaunes différents), montées en rouge vif, descentes en bleu vif, avec la lettre de chaque tuile. Dans l'**éditeur de piste**, la palette de sélection montre chaque tuile sous forme de **mini-preview cliquable** (bout de piste : forme droite/virage, cases colorées rouge/bleu selon la géographie) tandis que l'**aperçu global à droite** affiche le tracé avec la **lettre** de chaque tuile. Le panneau affiche aussi le **profil d'altitude** de l'étape (montée +1/case, descente -1/case, segments orange doux/bleu doux) avec **échelle de distance (1 case = 1 km), distance totale et D+**, les mots « départ »/« arrivée » et un **petit drapeau damier** sur la ligne d'arrivée. Le panneau de preview **grandit avec la fenêtre** (largeur proportionnelle, profil en grand sous le tracé). L'application a un **thème clair** ; dans l'écran de course, un panneau « Groupes » (en haut à gauche du cadre du parcours) liste **une ligne par pack** : « Tête de course » (premier), « Peloton » (plus gros groupe), « Lanterne rouge » (dernier), « Groupe \<cycliste connu\> » pour les autres, avec les coureurs et la case de chacun.

> Les 21 faces majuscules sont définies **explicitement** dans `MOUNTAIN_DEFS` (relevées une par une sur les tuiles physiques : cases case par case + virage propre — qui n'est pas toujours le miroir de la face plate, ex. `K` tourne à gauche comme la face montagne imprimée, `H` à droite alors que `h` va à gauche). Sens des virages minuscules relevés sur la carte imprimée Corso Paseo.

## 🎯 Roadmap

- [x] **Moteur de jeu de base** (logique des tours, cartes, coureurs)
- [x] **Phase de placement au départ** : chaque joueur place ses 2 coureurs un par un derrière la ligne DÉPART (clic sur une case, cases surlignées) ; placement aléatoire via le bouton d'action en phase de placement (`tests/test_placement.py`)
- [x] **Bouton « Tour aléatoire »** : en un clic, placement auto si besoin + une carte au hasard par coureur + mouvement/aspiration/fatigue d'un coup (pratique pour tester)
- [x] **Écran des logs / historique des coups** dans la barre du bas : historique par tour (TOUR X, cartes face cachée, mouvements « de y→z », aspirations), couleurs d'équipe, phases en gras, nouvelles lignes qui poussent les anciennes vers le haut, scrollable à la molette, texte sélectionnable (Ctrl+A / Ctrl+C), overlay complet avec **J**
- [x] **Fin de course** : fin du tour où un coureur franchit la ligne d'arrivée (la course ne continue pas après), vainqueur = le plus loin au-delà de la ligne, égalité → file A de droite (`Game._check_win_condition`)
- [x] **Écran de victoire avec podium** des 3 premiers coureurs (classement `Game.ranking()` : position puis file A)
- [x] **Interface Pygame minimale** (affichage de la piste et des coureurs)
- [x] **Implémentation complète de l'aspiration** (packs arrière→avant, fusion + revérification, pas-à-pas animé — vérifiée par `tests/test_aspiration.py`)
- [x] **Implémentation complète de la fatigue** (chaque coureur avec une CASE vide devant reçoit une carte, pas seulement le leader — vérifiée par les tests)
- [x] **Montées/descentes** (plafond 5 / minimum 5, pas d'aspiration en montée — vérifiées par `tests/test_mountains.py`)
- [x] **Multijoueur local 2-4 joueurs sur un même écran** (hotseat) : nombre de joueurs demandé au lancement (2 à 4, boutons ou flèches + ENTRÉE), passé au moteur qui crée les joueurs/coureurs en conséquence ; onglets de joueur dans la barre du bas
- [x] **Interface revue** : menu avec catégories (circuits de base / persos) + recherche + preview du parcours, éditeur de piste, écran de jeu avec cadre parcours dédié, légende sur fond blanc et boutons caméra, boutons avec effet d'enfoncement
- [x] **Zoom / panoramique caméra** sur le circuit (molette, +/-, flèches, drag clic gauche ou droit) + boutons **Tête de course** / **Peloton** / **Vue d'ensemble**
- [x] **Déplacements pas à pas** : la séquence de mouvement demande un clic (ou ENTRÉE) à chaque mouvement pour bien voir ce qui se passe
- [x] **Thème clair** de l'interface + **panneau des groupes** dans l'écran de course (tête de course / peloton / lanterne rouge / groupe <cycliste>)
- [x] **Animations fluides des déplacements** : les coureurs glissent le long du tracé (interpolation de l'abscisse curviligne + de la file, easing ease-out, durée proportionnelle à la distance) lors des mouvements et de l'aspiration ; les clics sont bloqués pendant l'animation (`tests/test_animation.py`, `tests/sim_animation.py`)
- [ ] **Ajout des sprites** (remplacer les cercles par des images)
- [ ] **Mode multijoueur en ligne** (via WebSocket)
- [x] **Étapes officielles** : les 6 étapes de la boîte de base codées en lettres de tuiles (Avenue Corso Paseo, Firenze-Milano, Ronde van Wevelgem, La Haut Montagne, La Classicissima, Col du Ballon) + **choix au menu** avec preview, profil et image de carte (`tests/test_stages.py`)
- [x] **Éditeur de piste** : entrée « Créer un circuit » au menu — palette des 42 tuiles (21 faces plates a-u + 21 faces montagne A-U) en mini-previews cliquables, regroupées par catégorie (droites, virages 90°, virages 45°, départ/arrivée), aperçu global du tracé (lettres des tuiles) + profil d'altitude en direct, description de la tuile survolée, boutons Retirer/Effacer ; départ `a` pré-ajouté, la tuile d'arrivée se place en dernier (les autres sont alors grisées) et les boutons JOUER/Sauvegarder sont grisés tant qu'il n'y a pas d'arrivée. Partie jouable sur le code perso via `Game(custom_code=...)` (`tests/test_placement.py::TestTrackEditor`). **Sauvegarde JSON** des parcours sous un nom choisi, fichiers dans `saves/*.json` (`save_track_json`/`load_track_json`/`list_saved_tracks`), rechargeables depuis le menu (catégorie « Circuits perso »)
- [ ] **Extensions** : possibilité d'ajouter des extensions (ex. Peloton : pavés, sections à une/trois voies, coureurs échappés, tuiles d'approvisionnement)
- [ ] **Système de sauvegarde/reprise**

---

*Bon jeu ! 🚴‍♂️💨*
