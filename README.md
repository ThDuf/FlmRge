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
- **Montées/Descentes** : Les montées limitent le déplacement à 5 cases max, les descentes imposent un minimum de 5 cases.

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
| **Souris** | Sélectionner une carte pour la jouer |
| **H** | Masquer/Afficher les mains des coureurs |
| **R** | Recommencer la partie |
| **ESPACE** | Forcer le passage à la phase suivante (debug) |

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

## 🎯 Roadmap

- [x] **Moteur de jeu de base** (logique des tours, cartes, coureurs)
- [x] **Interface Pygame minimale** (affichage de la piste et des coureurs)
- [x] **Implémentation complète de l'aspiration** (packs arrière→avant, fusion + revérification, pas-à-pas animé — vérifiée par `tests/test_aspiration.py`)
- [x] **Implémentation complète de la fatigue** (chaque coureur avec une CASE vide devant reçoit une carte, pas seulement le leader — vérifiée par les tests)
- [ ] **Ajout des montées/descentes**
- [ ] **Amélioration de l'UI** (boutons, animations)
- [ ] **Ajout des sprites** (remplacer les cercles par des images)
- [ ] **Mode multijoueur local** (2-4 joueurs sur un écran)
- [ ] **Mode multijoueur en ligne** (via WebSocket)
- [ ] **Ajout des étapes officielles** (Avenue Corso Paseo, etc.)
- [ ] **Système de sauvegarde/reprise**

---

*Bon jeu ! 🚴‍♂️💨*
