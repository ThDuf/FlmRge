# Flamme Rouge - Jeu de Société Numérique

Recréation numérique du jeu de société **Flamme Rouge** en Python avec Pygame.

![Flamme Rouge Logo](https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Flamme_Rouge_logo.svg/1200px-Flamme_Rouge_logo.svg.png)

## 📌 À propos du jeu

**Flamme Rouge** est un jeu de course cycliste tactique où chaque joueur contrôle une équipe de deux coureurs : un **rouleur** et un **sprinteur**. Le but est d'être le premier à franchir la ligne d'arrivée avec l'un de ses coureurs.

### Règles principales
- Chaque tour se divise en **3 phases** : Énergie, Mouvement, Terminale.
- **Phase d'Énergie** : Les joueurs piochent 4 cartes et en jouent une face cachée pour chaque coureur.
- **Phase de Mouvement** : Les cartes sont révélées et les coureurs avancent.
- **Phase Terminale** : Application de l'**aspiration** et de la **fatigue**.

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

| Touche | Action |
|--------|--------|
| **Souris** | Sélectionner une carte pour la jouer (surbrillance au survol) |
| **ENTRÉE / Bouton** | Avancer d'une étape : lancer le mouvement, puis **un coureur à la fois**, puis l'aspiration **pack par pack** |
| **H** | Masquer/Afficher les panneaux de cartes |
| **D** | Afficher/Masquer les cartes restantes |
| **R** | Recommencer la partie |

**Disposition de l'écran** : un **bandeau de titre** (fanion rouge, FLAMME ROUGE, étape et tour en cours) et un **bandeau de phase** coloré avec description (bleu = énergie, vert = mouvement, orange = aspiration, rouge = arrivée) surplombent la fenêtre. En dessous : les panneaux de cartes des joueurs empilés en colonne à gauche ; tout l'écran à droite affiche le **circuit complet**, tracé en suivant la séquence réelle des tuiles (chaque tuile = 2 cases, virages 45°/90° selon leur sens) et automatiquement mis à l'échelle pour tenir dans la zone. Une légende en bas d'écran explique les couleurs : **bande jaune « DÉPART » et damier « ARRIVÉE » en travers de la route, rouge clair + triangle rouge = montée, bleu clair + triangle bleu = descente**, ligne blanche = séparation des files A (droite) et B (gauche). La fenêtre est **redimensionnable** (minimum 900x600).

---

## 📁 Structure du projet

```
flamme_rouge/
├── assets/                  # Ressources graphiques et sonores
│   ├── sprites/            # Images des coureurs, cartes, etc.
│   └── tracks/             # Tuiles de piste
│
├── src/
│   ├── __init__.py
│   ├── main.py             # Point d'entrée (boucle principale)
│   ├── game/
│   │   ├── __init__.py
│   │   ├── card.py         # Cartes Énergie/Fatigue
│   │   ├── runner.py       # Coureurs (Rouleur/Sprinteur)
│   │   ├── player.py       # Joueurs
│   │   ├── track.py        # Piste et tuiles
│   │   └── game.py         # Moteur du jeu (règles, tours)
│   │
│   └── ui/
│       ├── __init__.py
│       └── scenes/         # Scènes du jeu (menu, jeu, fin)
│
├── tests/                  # Tests unitaires
└── README.md
```

---

## 🛠️ Développement

### Lancer les tests
```bash
python -m pytest tests/
```

### Ajouter une nouvelle piste
1. Modifier la méthode `_build_track` dans `src/game/game.py`.
2. Ajouter une nouvelle option dans le menu principal (à implémenter).

### Personnaliser les decks
- Modifier la méthode `_generate_energy_deck` dans `src/game/game.py` pour ajuster la distribution des cartes.

---

## 🎨 Assets

Les assets (images, sons) ne sont pas inclus dans ce dépôt pour des raisons de droits d'auteur. Vous pouvez :
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

Menu de sélection au lancement (clic ou flèches + ENTRÉE ; `Échap` y retourne en pleine partie, `R` relance l'étape en cours), **avec prévisualisation du tracé** de l'étape survolée à droite (grandes fenêtres). Les **6 étapes officielles de la boîte de base** sont codées par les lettres de leurs 21 tuiles (correspondance officielle : `a`=départ, `u`=arrivée, droites `b c d f l m n`, virages légers `h k q r s t`, virages serrés `e g i j o p`, majuscule = face montagne) :

| Étape | Code | Profil |
|-------|------|--------|
| Avenue Corso Paseo | `abcdefghijklmnopqrstu` | plat (tutoriel) |
| Firenze - Milano | `abcgi D H qntm K O L rep J sfu` | vallonné |
| Ronde van Wevelgem | `abcmgfteqon L P jk I D H r S u` | vallonné |
| La Haut Montagne | `abcfimet K G L H J sdop R Q N U` | très montagneuse |
| La Classicissima | `A eb Q R N H P cgik D F s L ojmtu` | vallonné |
| Col du Ballon | `AnLHgceqtrMBoipjDFkSu` | montagne (Vosges) |

> **Modèle de tuile** : chaque tuile = `(virage, largeur, cases)` dans `src/game/game.py` (`TILE_DEFS`, `MOUNTAIN_DEFS` pour les faces majuscules). `virage` = (angle en radians, sens +1/-1), `None` = droite ; `largeur` = nombre de files (2 en base) ; `cases` = alphabet `CELL_CHARS` de `src/game/track.py` (initiales anglaises : `f`=flat, `u`=uphill, `d`=downhill, `s`=ligne de départ, `e`=ligne d'arrivée) — ex. `a` = `"sssssf"` (6 cases, ligne sur les 5 premières), `B` = `"ddddff"` (descente sur les 4 premières cases seulement). Une tuile majuscule est la tuile **retournée** : virage en miroir (ex. `H` tourne à droite, `h` à gauche) et géographie case par case (`CellGeographyType` : FLAT/UPHILL/DOWNHILL) ; la ligne de course vit sur la case (`CellRunType` : NONE/START/END). Longueurs officielles : départ 6, arrivée 6 (`u` = `"feeeee"`, ligne sur les 5 dernières), droites 6, virages 2 → étapes officielles = 78 cases. Angles des virages officiels : 45° (léger) / 90° (serré). Dans la prévisualisation du menu (panneau de droite), le tracé est coloré **case par case** : départ jaune clair, arrivée jaune vif (deux jaunes différents), montées en rouge vif, descentes en bleu vif, avec la lettre de chaque tuile et un séparateur entre tuiles. Le panneau affiche aussi le **profil d'altitude** de l'étape (montée +1/case, descente -1/case) et, si tu déposes une photo de la vraie carte dans `assets/stages/<nom de l'étape>.jpg`, l'**image de la carte du jeu** à côté de la preview.

> Les 21 faces majuscules sont définies **explicitement** dans `MOUNTAIN_DEFS` (relevées une par une sur les tuiles physiques : cases case par case + virage propre — qui n'est pas toujours le miroir de la face plate, ex. `K` tourne à gauche comme la face montagne imprimée, `H` à droite alors que `h` va à gauche). Sens des virages minuscule relevés sur la carte imprimée Corso Paseo.

## 🎯 Roadmap

- [x] **Moteur de jeu de base** (logique des tours, cartes, coureurs)
- [x] **Phase de placement au départ** : chaque joueur place ses 2 coureurs un par un derrière la ligne DÉPART (clic sur une case, cases surlignées), avec bouton **« Placement aléatoire »** (`tests/test_placement.py`)
- [x] **Fin de course** : fin du tour où un coureur franchit la ligne d'arrivée (la course ne continue pas après), vainqueur = le plus loin au-delà de la ligne, égalité → file A de droite (`Game._check_win_condition`)
- [x] **Interface Pygame minimale** (affichage de la piste et des coureurs)
- [x] **Implémentation complète de l'aspiration** (packs arrière→avant, fusion + revérification, pas-à-pas animé — vérifiée par `tests/test_aspiration.py`)
- [x] **Implémentation complète de la fatigue** (chaque coureur avec une CASE vide devant reçoit une carte, pas seulement le leader — vérifiée par les tests)
- [x] **Montées/descentes** (plafond 5 / minimum 5, pas d'aspiration en montée — vérifiées par `tests/test_mountains.py`)
- [x] **Nombre de joueurs au départ** : demandé au menu de lancement (2 à 4 joueurs, boutons ou flèches + ENTRÉE), passé au moteur qui crée les joueurs/coureurs en conséquence
- [ ] **Amélioration de l'UI** (boutons, animations)
- [ ] **Animations des déplacements des coureurs** : animer les coureurs case par case lors des phases de mouvement, d'aspiration et de fatigue (glissade fluide le long du circuit, sans téléportation)
- [ ] **Ajout des sprites** (remplacer les cercles par des images)
- [ ] **Mode multijoueur local** (2-4 joueurs sur un écran)
- [ ] **Mode multijoueur en ligne** (via WebSocket)
- [ ] **Ajout des étapes officielles** (Avenue Corso Paseo, etc.)
- [x] **Choix de l'étape** : menu au lancement parmi les 6 étapes officielles de la boîte de base (`tests/test_stages.py`)
- [ ] **Éditeur de piste** : créer son propre terrain à partir des tuiles (droites, virages, montées, descentes)
- [ ] **Extensions** : possibilité d'ajouter des extensions (ex. Peloton : pavés, sections à une/trois voies, coureurs échappés, tuiles d'approvisionnement)
- [ ] **Système de sauvegarde/reprise**

---

*Bon jeu ! 🚴‍♂️💨*
