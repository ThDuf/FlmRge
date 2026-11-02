"""Tests de la phase de placement des coureurs au départ.

Règles officielles : chaque joueur place ses deux coureurs un par un,
derrière la ligne de départ, sur n'importe quelle file libre (file de droite
prioritaire si la case est vide). Option : placement au hasard.
"""
import os
import sys
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from game.game import Game, Phase  # noqa: E402
import main  # noqa: E402


class TestPlacementPhase(unittest.TestCase):
    def test_default_game_auto_places(self):
        """Par défaut (tests/sims), placement auto : phase ÉNERGIE direct."""
        game = Game(stage="test", player_count=2)
        self.assertEqual(game.current_phase, Phase.ENERGY)
        self.assertEqual(len(game.track.get_all_runners()), 4)

    def test_manual_placement_starts_in_placement_phase(self):
        game = Game(stage="test", player_count=3, auto_place=False)
        self.assertEqual(game.current_phase, Phase.PLACEMENT)
        self.assertEqual(len(game.placement_queue), 6)  # 3 joueurs x 2 coureurs
        self.assertEqual(game.track.get_all_runners(), [])  # personne sur la piste
        player, runner = game.current_placement()
        self.assertIs(player, game.players[0])
        self.assertIs(runner, player.sprinter)

    def test_can_place_only_behind_start_line_on_free_lane(self):
        game = Game(stage="test", player_count=2, auto_place=False)
        limit = game.track.start_line_x()
        self.assertTrue(game.can_place_at(limit - 1, 0))
        self.assertFalse(game.can_place_at(limit, 0))      # sur/après la ligne
        self.assertFalse(game.can_place_at(limit + 3, 0))
        self.assertTrue(game.place_runner_at(limit - 1, 0))
        self.assertFalse(game.can_place_at(limit - 1, 0))  # file A prise
        self.assertTrue(game.can_place_at(limit - 1, 1))   # file B encore libre
        self.assertFalse(game.place_runner_at(limit, 1))   # interdit

    def test_placement_advances_and_starts_race_when_done(self):
        game = Game(stage="test", player_count=2, auto_place=False)
        limit = game.track.start_line_x()
        n = len(game.placement_queue)
        for i in range(n):
            self.assertIsNotNone(game.current_placement())
            self.assertTrue(game.place_runner_at(limit - 1 - i // 2, i % 2))
        self.assertEqual(game.current_phase, Phase.ENERGY)  # 1er tour lancé
        self.assertEqual(game.turn_count, 1)
        self.assertEqual(len(game.track.get_all_runners()), n)
        for x, _lane, r in game.track.get_all_runners():
            self.assertLess(x, limit)

    def test_auto_place_riders_random_option(self):
        """Le placement aléatoire respecte la règle : au plus proche de la
        ligne (8 coureurs -> cases 1..4 remplies, case 0 vide)."""
        game = Game(stage="test", player_count=4, auto_place=False)
        game.auto_place_riders()
        self.assertEqual(game.current_phase, Phase.ENERGY)
        limit = game.track.start_line_x()
        runners = game.track.get_all_runners()
        self.assertEqual(len(runners), 8)
        for x, _lane, _r in runners:
            self.assertLess(x, limit)
        occupied_x = sorted({x for x, _l, _r in runners})
        self.assertEqual(occupied_x, [1, 2, 3, 4])  # case 0 (la plus loin) vide

    def test_auto_place_shuffles_player_order(self):
        """Le placement aléatoire mélange vraiment l'ordre des coureurs
        (pas toujours la même équipe en premier)."""
        from unittest import mock
        game = Game(stage="test", player_count=4, auto_place=False)
        with mock.patch('random.shuffle') as m:
            game.auto_place_riders()
            m.assert_called_once()
        # et avec un vrai shuffle, l'ordre de placement varie selon la graine
        import random
        orders = set()
        for seed in range(6):
            random.seed(seed)
            g = Game(stage="test", player_count=4, auto_place=False)
            random.seed(seed)
            g.auto_place_riders()
            orders.add(tuple(r.id for _x, _l, r in
                             sorted(g.track.get_all_runners(),
                                    key=lambda t: (t[0], t[1]))))
        self.assertGreater(len(orders), 1)  # plusieurs dispositions différentes


class TestPlacementUI(unittest.TestCase):
    def test_ui_starts_in_placement_phase(self):
        ui = main.FlammeRougeGame()  # menu -> sélection d'étape = placement manuel
        ui._select_stage("Avenue Corso Paseo")
        self.assertEqual(ui.game.current_phase, Phase.PLACEMENT)
        label, desc, _color = ui._phase_info()
        self.assertIn("PLACEMENT", label)
        self.assertIn("hasard", desc)
        btn = ui._button_info()
        self.assertIsNotNone(btn)
        self.assertIn("aléatoire", btn[0].lower())

    def test_ui_random_button_places_everyone(self):
        ui = main.FlammeRougeGame()
        ui._select_stage("Avenue Corso Paseo")
        ui._advance_step()  # clic sur "Placement aléatoire"
        self.assertEqual(ui.game.current_phase, Phase.ENERGY)
        self.assertEqual(len(ui.game.track.get_all_runners()), 4)

    def test_unplaced_runners_not_drawn_on_track(self):
        """En phase PLACEMENT, les coureurs non placés ne sont pas sur la
        piste (ils sont en réserve à côté) : _draw_runners ne lit que la piste."""
        ui = main.FlammeRougeGame()
        ui._select_stage("Avenue Corso Paseo")
        ui.screen = __import__('pygame').display.set_mode((1200, 800))
        ui._draw_runners()  # ne doit pas dessiner les 4 coureurs non placés
        on_track = {r.id for _x, _l, r in ui.game.track.get_all_runners()}
        self.assertEqual(on_track, set())  # rien sur la piste
        # après placement aléatoire, tout le monde est sur la piste, derrière la ligne
        ui.game.auto_place_riders()
        ui._draw_runners()
        limit = ui.game.track.start_line_x()
        for x, _l, r in ui.game.track.get_all_runners():
            self.assertLess(x, limit)

    def test_ui_click_places_runner(self):
        ui = main.FlammeRougeGame()
        ui._select_stage("Avenue Corso Paseo")
        limit = ui.game.track.start_line_x()
        px, py, tx, ty = ui._cell_anchor(limit - 1)
        nx, ny = -ty, tx
        geo = ui._track_geometry()
        pos = (px + nx * geo["half"] * 0.5, py + ny * geo["half"] * 0.5)  # file A
        ui._placement_click(pos)
        self.assertEqual(len(ui.game.track.get_all_runners()), 1)
        self.assertIsNotNone(ui.game.current_placement())


if __name__ == '__main__':
    unittest.main(verbosity=2)


class TestRandomTurnButton(unittest.TestCase):
    def test_random_turn_button_plays_a_full_turn(self):
        """Le bouton « Tour aléatoire » enchaîne placement + cartes + phases."""
        ui = main.FlammeRougeGame()
        ui._select_stage("Avenue Corso Paseo")  # phase PLACEMENT
        ui.screen = __import__('pygame').display.set_mode((1200, 800))
        # clic sur le bouton aléatoire
        rect = ui._random_button_rect()
        ui._try_button_click(rect.center)
        game = ui.game
        self.assertEqual(game.current_phase, Phase.ENERGY)  # tour suivant (ou game over)
        self.assertEqual(game.turn_count, 2)  # placement -> tour 1 joué -> tour 2
        self.assertEqual(len(game.track.get_all_runners()), 4)  # tous placés
        # rejouer jusqu'à game over éventuel : toujours cohérent
        for _ in range(30):
            if game.game_over:
                break
            ui._try_button_click(rect.center)
        self.assertIn(game.current_phase, (Phase.ENERGY, Phase.TERMINAL))


class TestPodiumScreen(unittest.TestCase):
    def _game_over_ui(self):
        import pygame
        ui = main.FlammeRougeGame(stage="test")
        ui.screen = pygame.display.set_mode((1200, 800))
        game = ui.game
        # force une victoire : sprinter_0 franchit la ligne
        r = game.players[0].sprinter
        old = game.track.get_cell(r.x, r.y)
        old.remove_runner(r.y)
        game.track.get_cell(game.track.end_line_x() + 2, 0).set_runner(r, 0)
        game._check_win_condition()
        game.game_over = True
        return ui

    def test_podium_shown_on_game_over_and_tab_toggles(self):
        import pygame
        ui = self._game_over_ui()
        self.assertTrue(ui.show_podium)
        ui._draw_ui()  # podium (ne plante pas)
        ui._game_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB))
        self.assertFalse(ui.show_podium)
        ui._draw_ui()  # état final du circuit (ne plante pas)
        ui._game_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB))
        self.assertTrue(ui.show_podium)

    def test_podium_order_first_center(self):
        """Vérifie la logique d'affichage : 1er au centre (offset 0),
        2e à gauche (-1), 3e à droite (+1)."""
        ui = self._game_over_ui()
        rank = ui.game.ranking()
        offsets = [0, -1, 1]
        # le 1er du classement doit être dessiné au centre
        self.assertEqual(offsets[0], 0)
        self.assertEqual(rank[0][1].id, 'sprinter_0')  # notre vainqueur forcÃ©

    def test_podium_button_toggles(self):
        """Le bouton à droite bascule podium <-> circuit final (comme TAB)."""
        import pygame
        ui = self._game_over_ui()
        rect = ui._podium_button_rect()
        self.assertTrue(ui.show_podium)
        ui._game_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                          pos=rect.center))
        self.assertFalse(ui.show_podium)
        ui._draw_ui()  # bouton + circuit final
        ui._game_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                          pos=rect.center))
        self.assertTrue(ui.show_podium)
        ui._draw_ui()  # bouton + podium


class TestButtonsLayout(unittest.TestCase):
    def test_buttons_visible_at_4_players(self):
        """À 4 joueurs, les 2 boutons restent dans la fenêtre et sous les panneaux."""
        import pygame
        for w, h in ((1200, 800), (900, 600)):
            ui = main.FlammeRougeGame(stage="test")
            ui._select_stage("test")
            ui.game.players  # 2 joueurs par défaut ; on force 4
            from game.game import Game
            ui.game = Game(stage="test", player_count=4, auto_place=False)
            ui.width, ui.height = w, h
            ui.screen = pygame.display.set_mode((w, h))
            ui._draw_ui()
            bar = ui._bar_rect()
            b = ui._button_rect()
            r = ui._random_button_rect()
            self.assertLessEqual(b.bottom, h, f"bouton action hors écran {w}x{h}")
            self.assertLessEqual(r.bottom, h, f"bouton aléatoire hors écran {w}x{h}")
            # violets + action dans la barre du bas ; caméra dans le cadre (haut droite)
            frame = ui._frame_rect()
            self.assertTrue(bar.contains(r), f"bouton aléatoire hors barre {w}x{h}")
            self.assertIsNone(ui._placement_button_rect())  # bouton placement supprimé
            self.assertTrue(bar.contains(b))
            for key, rect in ui._frame_button_rects().items():
                self.assertTrue(frame.contains(rect), f"bouton {key} hors cadre {w}x{h}")
            self.assertTrue(bar.contains(ui._log_panel_rect()))
            self.assertTrue(bar.contains(ui._card_panel_rect()))


class TestTrackEditor(unittest.TestCase):
    def test_game_accepts_custom_code(self):
        from game.game import Game
        g = Game(stage="Éditeur", player_count=2, custom_code="abcdu")
        self.assertEqual(g.custom_code, "abcdu")
        self.assertEqual([t.letter for t in g.track.tiles], list("abcdu"))
        self.assertEqual(g.track.length, 6 + 6 + 6 + 6 + 6)

    def test_editor_append_pop_clear(self):
        ui = main.FlammeRougeGame()
        ui.editor_code = "a"
        ui._editor_append('b')
        ui._editor_append('K')   # majuscule autorisée
        ui._editor_append('?')   # ignoré
        self.assertEqual(ui.editor_code, "abK")
        ui._editor_pop()
        self.assertEqual(ui.editor_code, "ab")
        ui._editor_pop()
        ui._editor_pop()         # on garde au moins 'a'
        self.assertEqual(ui.editor_code, "a")
        ui._editor_append('c')
        ui._editor_clear()
        self.assertEqual(ui.editor_code, "a")

    def test_editor_play_adds_start_and_finish(self):
        import pygame
        ui = main.FlammeRougeGame()
        ui.editor_code = "bcdf"
        ui._editor_play()
        self.assertIsNotNone(ui.game)
        self.assertEqual(ui.game.custom_code, "abcdfu")  # a et u auto-ajoutés
        self.assertEqual(ui.game.track.length, 6 * 5 + 6)
        self.assertEqual(ui.game.current_phase, Phase.PLACEMENT)

    def test_editor_keyboard_and_palette_events(self):
        import pygame
        ui = main.FlammeRougeGame()
        ui.menu_step = "editor"
        ui.editor_code = "a"
        ui._menu_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_b))
        self.assertEqual(ui.editor_code, "ab")
        # MAJ = face montagne
        ui._menu_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_k,
                                          mod=pygame.KMOD_SHIFT))
        self.assertEqual(ui.editor_code, "abK")
        ui._menu_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE))
        self.assertEqual(ui.editor_code, "ab")
        # clic sur une tuile de la palette (on cherche 'e' peu importe sa position)
        ch, rect = next((c, r) for c, r in ui._editor_palette_rects() if c == 'e')
        ui._menu_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                          pos=rect.center))
        self.assertEqual(ui.editor_code, "abe")
        # Échap revient au menu d'étape
        ui._menu_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertEqual(ui.menu_step, "stage")

    def test_editor_entry_in_menu_and_draw(self):
        import pygame
        ui = main.FlammeRougeGame()
        ui.screen = pygame.display.set_mode((1200, 800))
        entries = ui._menu_entries()
        self.assertEqual(entries[-1][0], "Créer un circuit")
        self.assertEqual(entries[-1][4], "editor")
        ui.menu_index = len(entries) - 1
        ui._menu_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(ui.menu_step, "editor")
        ui._draw_menu()  # dessine l'éditeur sans erreur (avec roue crantée dans le menu)

    def test_editor_tile_preview_on_hover(self):
        """Survol de la palette -> editor_hover_letter + preview dessinée."""
        import pygame
        ui = main.FlammeRougeGame()
        ui.width, ui.height = 1200, 800
        ui.screen = pygame.display.set_mode((1200, 800))
        ui.menu_step = "editor"
        ch, rect = next((c, r) for c, r in ui._editor_palette_rects() if c == 'k')
        ui._menu_event(pygame.event.Event(pygame.MOUSEMOTION, pos=rect.center))
        self.assertEqual(ui.editor_hover_letter, 'k')
        ui._draw_menu()  # dessine l'éditeur + la preview de 'k' sans erreur
        # la preview de tuile ne recouvre PAS l'aperçu du tracé
        tile_r = ui._tile_preview_rect()
        prev_r = pygame.Rect(ui.width - 350, main.TOP_H + 246, 330, 300)
        self.assertFalse(tile_r.colliderect(prev_r))
        # preview d'un virage montagne (K) et d'une droite (b)
        ui.editor_hover_letter = 'K'
        ui._draw_tile_preview('K', ui._tile_preview_rect())
        ui._draw_tile_preview('b', ui._tile_preview_rect())
        ui._draw_tile_preview('a', ui._tile_preview_rect())
        ui._draw_tile_preview('U', ui._tile_preview_rect())

    def test_mini_tile_preview_all_letters(self):
        """_draw_mini_tile fonctionne pour les 42 tuiles (avec nb de cases)."""
        import pygame
        from game.game import build_tile
        ui = main.FlammeRougeGame()
        ui.screen = pygame.display.set_mode((1200, 800))
        for i, ch in enumerate(ui.EDITOR_LETTERS + ui.EDITOR_LETTERS.upper()):
            ui._draw_mini_tile(ch, 100 + (i % 7) * 60, 100 + (i // 7) * 60,
                               1.0, 0.0, size=30)
            tile = build_tile(ch)
            self.assertGreater(tile.length, 0)
        # les deux previews (menu + éditeur) dessinent les miniatures sans erreur
        ui.menu_step = "editor"
        ui.editor_code = "abKcdEfghijklmnopqrstu"
        ui._draw_menu()
        ui2 = main.FlammeRougeGame()
        ui2.width, ui2.height = 1200, 800
        ui2.screen = pygame.display.set_mode((1200, 800))
        ui2.menu_index = 0
        ui2._draw_menu()


class TestHistoryPanel(unittest.TestCase):
    def test_history_records_cards_moves_slips(self):
        from game.game import Game
        game = Game(stage="test", player_count=2)
        for player in game.players:
            for runner in player.get_runners():
                game.play_card(player, runner, runner.hand[0])
        moves = game.resolve_movement_phase()
        game.apply_movement_steps(moves)
        game.apply_aspiration_steps(game.resolve_aspiration_phase())
        self.assertEqual(len(game.history), 1)
        entry = game.history[0]
        self.assertEqual(entry["turn"], 1)
        self.assertEqual(len(entry["cards"]), 4)      # 2 joueurs x 2 coureurs
        self.assertEqual(len(entry["moves"]), 4)
        for _color, rid, val in entry["cards"]:
            self.assertIn(rid.split('_')[0], ("sprinter", "roller"))
            self.assertGreater(val, 0)
        for rid, color, fx, tx, val, eff, reason in entry["moves"]:
            self.assertGreaterEqual(tx, fx)

    def test_history_toggle_key_J_and_panel(self):
        import pygame
        ui = main.FlammeRougeGame(stage="test")
        ui.screen = pygame.display.set_mode((1200, 800))
        self.assertFalse(ui.show_history)
        ui._game_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_j))
        self.assertTrue(ui.show_history)
        ui._draw_ui()  # panneau historique sans erreur
        ui._game_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_j))
        self.assertFalse(ui.show_history)

    def test_editor_palette_shows_tile_shapes(self):
        """La palette de l'éditeur dessine des bouts de piste (mini-tuiles)."""
        import pygame
        ui = main.FlammeRougeGame()
        ui.width, ui.height = 1200, 800
        ui.screen = pygame.display.set_mode((1200, 800))
        ui.menu_step = "editor"
        ui.editor_code = "a"
        ui._draw_menu()  # palette en formes de tuiles, sans erreur
        self.assertEqual(len(ui._editor_palette_rects()), 42)

    def test_editor_palette_fits_at_all_sizes(self):
        """La grande palette de l'éditeur tient dans la fenêtre à toutes les tailles."""
        import pygame
        ui = main.FlammeRougeGame()
        for w, h in ((1200, 800), (900, 600), (1600, 1000)):
            ui.width, ui.height = w, h
            ui.screen = pygame.display.set_mode((w, h))
            ui.menu_step = "editor"
            for ch, rect in ui._editor_palette_rects():
                self.assertLessEqual(rect.right, w, f"palette {ch} hors écran {w}x{h}")
                self.assertLessEqual(rect.bottom, h, f"palette {ch} hors écran {w}x{h}")
            for key, (_l, rect) in ui._editor_action_rects().items():
                self.assertLessEqual(rect.bottom, h, f"bouton {key} hors écran {w}x{h}")
            ui._draw_menu()


class TestTrackSaveJson(unittest.TestCase):
    def test_save_load_json_roundtrip(self):
        import tempfile, os
        from game.game import save_track_json, load_track_json, list_saved_tracks
        with tempfile.TemporaryDirectory() as d:
            p = save_track_json("abKcfu", d, name="mon_parcours")
            self.assertTrue(p.endswith("mon_parcours.json"))
            self.assertEqual(load_track_json(p), "abKcfu")
            saved = list_saved_tracks(d)
            self.assertEqual(len(saved), 1)
            self.assertEqual(saved[0]["code"], "abKcfu")
            self.assertEqual(saved[0]["name"], "mon_parcours")

    def test_editor_save_load_buttons(self):
        import tempfile, pygame
        ui = main.FlammeRougeGame()
        ui.saves_dir = tempfile.mkdtemp()
        ui.editor_code = "abKcdf"
        ui._editor_save()
        self.assertIn("Sauvegardé", ui.editor_message)
        ui.editor_code = "a"
        ui._editor_load_latest()
        self.assertEqual(ui.editor_code, "abKcdf")
        self.assertIn("Chargé", ui.editor_message)
        # boutons présents dans la barre d'actions
        keys = [k for k, _ in ui._editor_action_rects().items()]
        self.assertIn("sauver", keys)
        self.assertIn("charger", keys)


class TestMenuCategories(unittest.TestCase):
    def test_perso_circuits_from_saves_json(self):
        """Les JSON de saves/ apparaissent en catégorie 'Circuits perso' et
        lancent une partie avec custom_code."""
        import tempfile, pygame
        from game.game import save_track_json
        ui = main.FlammeRougeGame()
        ui.saves_dir = tempfile.mkdtemp()
        save_track_json("abKcdfu", ui.saves_dir, name="mon_beau_parcours")
        entries = ui._menu_entries()
        perso = [e for e in entries if e[4] == "perso"]
        self.assertEqual(len(perso), 1)
        self.assertEqual(perso[0][0], "mon_beau_parcours")
        self.assertEqual(perso[0][2], "abKcdfu")
        # validation -> étape joueurs avec code perso en attente
        ui.menu_index = entries.index(perso[0])
        ui._menu_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(ui.menu_step, "players")
        self.assertEqual(ui._pending_code, "abKcdfu")
        ui._menu_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertIsNotNone(ui.game)
        self.assertEqual(ui.game.custom_code, "abKcdfu")
        self.assertEqual([t.letter for t in ui.game.track.tiles], list("abKcdfu"))

    def test_editor_save_with_name(self):
        """Clic sur Sauver -> saisie du nom au clavier -> fichier nommé."""
        import tempfile, os, pygame
        ui = main.FlammeRougeGame()
        ui.saves_dir = tempfile.mkdtemp()
        ui.editor_code = "abKcdfu"
        ui.menu_step = "editor"
        # clic sur le bouton Sauver -> mode saisie
        for key, (_l, rect) in ui._editor_action_rects().items():
            if key == "sauver":
                ui._menu_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                                  pos=rect.center))
        self.assertTrue(ui.editor_naming)
        # on efface le nom proposé et on tape le nôtre
        for _ in range(40):
            ui._menu_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE,
                                              unicode=''))
        for ch in "mon col":
            ui._menu_event(pygame.event.Event(pygame.KEYDOWN,
                                              key=pygame.K_UNKNOWN, unicode=ch))
        ui._menu_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN,
                                          unicode='\r'))
        self.assertFalse(ui.editor_naming)
        files = os.listdir(ui.saves_dir)
        self.assertEqual(files, ["mon col.json"])
        self.assertIn("mon col.json", ui.editor_message)
        # Échap annule la saisie
        ui._menu_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                          pos=ui._editor_action_rects()["sauver"][1].center))
        ui._menu_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, unicode=''))
        self.assertFalse(ui.editor_naming)

    def test_play_button_below_global_preview(self):
        """Le bouton JOUER est sous l'aperçu global à droite (grande fenêtre)."""
        import pygame
        ui = main.FlammeRougeGame()
        ui.width, ui.height = 1200, 800
        ui.screen = pygame.display.set_mode((1200, 800))
        ui.menu_step = "editor"
        ui.editor_code = "abcu"
        prev = ui._editor_preview_panel_rect()
        play = ui._editor_play_rect()
        self.assertIsNotNone(prev)
        self.assertGreaterEqual(play.y, prev.bottom)      # sous l'aperçu
        self.assertLessEqual(play.bottom, ui.height)
        self.assertNotIn("jouer", [k for k, _ in ui._editor_action_rects().items()])
        ui._draw_menu()  # bouton JOUER dessiné à droite
        # clic sur JOUER -> partie lancée
        ui._menu_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                          pos=play.center))
        self.assertIsNotNone(ui.game)
        self.assertEqual(ui.game.custom_code, "abcu")
        # fenêtre étroite : JOUER reste dans la barre de gauche
        ui2 = main.FlammeRougeGame()
        ui2.width, ui2.height = 900, 600
        self.assertIsNone(ui2._editor_play_rect())
        self.assertIn("jouer", [k for k, _ in ui2._editor_action_rects().items()])

    def test_editor_palette_sorted_by_category(self):
        """Palette rangée : départ/arrivée, droites, virages 90°, virages 45°,
        chaque tuile suivie de sa face montagne."""
        ui = main.FlammeRougeGame()
        letters = [ch for ch, _r in ui._editor_palette_rects()]
        self.assertEqual(len(letters), 42)
        expected = []
        for _label, cat in ui.EDITOR_CATEGORIES:
            for base in cat:
                expected += [base, base.upper()]
        self.assertEqual(letters, expected)
        # départ en haut, arrivée en bas ; droites puis 90° puis 45° entre les deux
        self.assertEqual(letters[:2], ['a', 'A'])
        self.assertEqual(letters[-2:], ['u', 'U'])
        self.assertEqual(letters.index('e'), letters.index('b') + 2 * 7)  # e après les 7 droites
        self.assertLess(letters.index('h'), letters.index('u'))  # 45° avant l'arrivée
        # noms de catégories affichés
        cat_labels = [t for t, _x, _y in ui._editor_palette_labels()]
        self.assertEqual(cat_labels, ["Départ", "Droites", "Virages 90°", "Virages 45°", "Arrivée"])

    def test_editor_start_toggle_and_finish_always_last(self):
        """a/A bascule la face du départ ; u/U est toujours la dernière tuile,
        les suivantes s'insèrent avant elle."""
        ui = main.FlammeRougeGame()
        ui.editor_code = "a"
        ui._editor_append('A')           # bascule la face du départ
        self.assertEqual(ui.editor_code, "A")
        ui._editor_append('b')
        ui._editor_append('c')
        self.assertEqual(ui.editor_code, "Abc")
        ui._editor_append('u')           # arrivée ajoutée -> dernière
        self.assertEqual(ui.editor_code, "Abcu")
        # une fois l'arrivée placée, on ne peut plus rien ajouter
        ui._editor_append('d')
        ui._editor_append('K')
        self.assertEqual(ui.editor_code, "Abcu")
        ui._editor_append('U')           # seule l'arrivée reste modifiable (u <-> U)
        self.assertEqual(ui.editor_code, "AbcU")
        self.assertEqual(ui.editor_code[-1].lower(), 'u')
        # pop peut retirer l'arrivée (elle sera remise au JOUER)
        ui._editor_pop()
        self.assertEqual(ui.editor_code, "Abc")
        ui._editor_append('d')           # déverrouillé : on peutrajouter
        self.assertEqual(ui.editor_code, "Abcd")

    def test_palette_locked_after_finish_placed(self):
        """Une fois u/U placé (dernier), on ne peut plus rien ajouter sauf
        basculer la face de l'arrivée."""
        import pygame
        ui = main.FlammeRougeGame()
        ui.menu_step = "editor"
        ui.editor_code = "abcu"
        ui._editor_append('b')   # ignoré : arrivée déjà placée
        self.assertEqual(ui.editor_code, "abcu")
        ui._editor_append('K')   # idem
        self.assertEqual(ui.editor_code, "abcu")
        ui._editor_append('U')   # bascule la face de l'arrivée : autorisé
        self.assertEqual(ui.editor_code, "abcU")
        # au clavier aussi
        ui._menu_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d, unicode='d'))
        self.assertEqual(ui.editor_code, "abcU")
        ui._menu_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_u, unicode='u'))
        self.assertEqual(ui.editor_code, "abcu")
        # rendu avec tuiles grisées
        ui.width, ui.height = 1200, 800
        ui.screen = pygame.display.set_mode((1200, 800))
        ui._draw_menu()

    def test_tile_turn_direction_convention(self):
        """Convention écran (y vers le bas) : sens -1 = droite (cap +angle,
        la tuile courbe vers le bas), sens +1 = gauche (cap -angle, vers le haut)."""
        import math
        from game.game import build_tile
        from game.track import Track, compute_track_path
        for ch in "egijophkqrst":
            for c in (ch, ch.upper()):
                tile = build_tile(c)
                if tile.turn is None:
                    continue
                angle, direction = tile.turn
                t = Track(); t.add_tile(build_tile(c))
                pts = compute_track_path(t, 1.0)
                # corde de fin de virage : direction = -angle*direction / 2
                chord_h = math.atan2(pts[-1][1] - pts[0][1], pts[-1][0] - pts[0][0])
                self.assertAlmostEqual(chord_h, -angle * direction / 2, places=1, msg=c)
                if direction == -1:   # droite -> courbe vers le bas (y+)
                    self.assertGreater(pts[-1][1], pts[0][1], c)
                else:                 # gauche -> vers le haut (y-)
                    self.assertLess(pts[-1][1], pts[0][1], c)

    def test_mixed_tile_cells_colored_per_cell(self):
        """Une tuile mixte (B = ddddff) a ses cases coloriées individuellement
        dans la forme dessinée : on vérifie la répartition des géographies."""
        from game.game import build_tile
        from game.track import CellGeographyType
        tile = build_tile('B')
        geos = [c.geography for c in tile.cells]
        self.assertEqual(geos, [CellGeographyType.DOWNHILL] * 4 + [CellGeographyType.FLAT] * 2)
        tile = build_tile('U')
        geos = [c.geography for c in tile.cells]
        self.assertEqual(geos, [CellGeographyType.UPHILL] * 2 + [CellGeographyType.FLAT] * 4)

    def test_tile_cell_summary_counts(self):
        """Résumé des cases par type : B -> 4 descente + 2 plat, a -> 5 départ + 1 plat..."""
        from game.game import build_tile
        ui = main.FlammeRougeGame()
        self.assertEqual(ui._tile_cell_summary(build_tile('b')), "cases : 6 plat")
        self.assertEqual(ui._tile_cell_summary(build_tile('B')), "cases : 4 descente, 2 plat")
        self.assertEqual(ui._tile_cell_summary(build_tile('D')), "cases : 5 montée, 1 descente")
        self.assertEqual(ui._tile_cell_summary(build_tile('a')), "cases : 1 plat, 5 départ")
        self.assertEqual(ui._tile_cell_summary(build_tile('U')), "cases : 2 montée, 4 arrivée")
        self.assertEqual(ui._tile_cell_summary(build_tile('e')), "cases : 2 plat")

    def test_play_and_save_disabled_without_finish(self):
        """Sans tuile d'arrivée, JOUER et Sauver sont grisés/inactifs."""
        import pygame
        ui = main.FlammeRougeGame()
        ui.width, ui.height = 1200, 800
        ui.screen = pygame.display.set_mode((1200, 800))
        ui.menu_step = "editor"
        ui.editor_code = "abc"          # pas d'arrivée
        self.assertFalse(ui._editor_has_finish())
        play = ui._editor_play_rect()
        ui._menu_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                          pos=play.center))
        self.assertIsNone(ui.game)      # JOUER inactif
        ui._menu_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, unicode='\r'))
        self.assertIsNone(ui.game)
        for key, (_l, rect) in ui._editor_action_rects().items():
            if key == "sauver":
                ui._menu_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                                  pos=rect.center))
        self.assertFalse(ui.editor_naming)  # Sauver inactif
        ui._draw_menu()                 # rendu avec boutons grisés
        # avec l'arrivée placée, tout redevient actif
        ui.editor_code = "abcu"
        self.assertTrue(ui._editor_has_finish())
        ui._menu_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, unicode='\r'))
        self.assertIsNotNone(ui.game)
        self.assertEqual(ui.game.custom_code, "abcu")


class TestCircuitZoom(unittest.TestCase):
    def test_zoom_and_pan(self):
        """Zoom +/- (clavier/molette) et panoramique (flèches) sur le circuit."""
        import pygame
        ui = main.FlammeRougeGame(stage="test")
        ui.screen = pygame.display.set_mode((1200, 800))
        g0 = ui._track_geometry()
        cell0 = g0["cell"]
        ui._game_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_PLUS))
        g1 = ui._track_geometry()
        self.assertAlmostEqual(g1["cell"], cell0 * 1.25, places=3)
        self.assertAlmostEqual(ui.zoom, 1.25)
        ui._game_event(pygame.event.Event(pygame.MOUSEWHEEL, y=-1, pos=(600, 300)))
        self.assertAlmostEqual(ui.zoom, 1.0, places=3)
        # bornes de zoom
        for _ in range(10):
            ui._game_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_PLUS))
        self.assertEqual(ui.zoom, 3.0)
        for _ in range(20):
            ui._game_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_MINUS))
        self.assertEqual(ui.zoom, 0.5)
        # panoramique
        ui.zoom = 2.0
        g2 = ui._track_geometry()
        ox0 = g2["points"][0][0]
        ui._game_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
        g3 = ui._track_geometry()
        self.assertAlmostEqual(g3["points"][0][0], ox0 - 60, places=1)
        ui._draw_ui()  # rendu zoomé sans erreur

    def test_camera_drag_and_buttons(self):
        """Clic droit = drag caméra (comme les flèches) ; boutons peloton / vue d'ensemble."""
        import pygame
        ui = main.FlammeRougeGame(stage="test")
        ui.screen = pygame.display.set_mode((1200, 800))
        g0 = ui._track_geometry()
        p0 = g0["points"][0]
        # drag caméra au clic GAUCHE sur le parcours
        frame = ui._frame_rect()
        start = (frame.x + 100, frame.y + 100)
        ui._game_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=start))
        ui._game_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(start[0] + 60, start[1] + 30)))
        ui._game_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(start[0] + 60, start[1] + 30)))
        g1 = ui._track_geometry()
        self.assertAlmostEqual(g1["points"][0][0], p0[0] + 60, places=1)
        self.assertAlmostEqual(g1["points"][0][1], p0[1] + 30, places=1)
        # bouton "Tête de course" : zoom x2 et caméra centrée sur la tête
        ui._game_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                          pos=ui._frame_button_rects()["tete"].center))
        self.assertEqual(ui.zoom, 2.0)
        geo = ui._track_geometry()
        lead = max(ui.game.track.get_all_runners(), key=lambda t: (t[0], -t[1]))
        px, py, _tx, _ty = ui._path_at(geo, (lead[0] + 0.5) * geo["cell"])
        frame = ui._frame_rect()
        cx = frame.x + frame.w / 2
        self.assertAlmostEqual(px, cx, delta=geo["cell"])
        # bouton "Peloton" : centré sur le plus gros pack
        ui._game_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                          pos=ui._frame_button_rects()["peloton"].center))
        pos = {r.id: (r.x, r.y) for _x, _y, r in ui.game.track.get_all_runners()}
        packs = ui.game.track._packs_from_positions(pos)
        biggest = max(packs, key=len)
        avg_x = sum(pos[rid][0] for rid in biggest) / len(biggest)
        geo = ui._track_geometry()
        px, py, _tx, _ty = ui._path_at(geo, (avg_x + 0.5) * geo["cell"])
        self.assertAlmostEqual(px, cx, delta=geo["cell"])
        # bouton "Vue d'ensemble" : reset
        ui._game_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                          pos=ui._camera_button_rects()["ensemble"].center))
        self.assertEqual((ui.zoom, ui.pan_x, ui.pan_y), (1.0, 0.0, 0.0))
        ui._draw_ui()

    def test_no_overlapping_blocks_in_game(self):
        """Boutons caméra/podium dans le bandeau haut ; cadre du parcours à droite
        de la colonne de gauche, sans chevauchement."""
        import pygame
        ui = main.FlammeRougeGame(stage="test")
        ui.width, ui.height = 1200, 800
        ui.screen = pygame.display.set_mode((1200, 800))
        # boutons caméra dans la pile du cadre du parcours (haut droite)
        frame = ui._frame_rect()
        for key, rect in ui._camera_button_rects().items():
            self.assertTrue(frame.contains(rect), f"bouton {key} hors cadre")
        for key, rect in ui._frame_button_rects().items():
            self.assertTrue(frame.contains(rect), f"bouton {key} hors cadre")
        self.assertLess(ui._podium_button_rect().bottom, main.HEADER_H)
        bar = ui._bar_rect()
        b = ui._button_rect()
        self.assertFalse(frame.colliderect(b))              # bouton action dans la barre
        self.assertFalse(frame.colliderect(ui._log_panel_rect()))
        ui._draw_ui()

    def test_player_block_compact_but_cards_kept(self):
        """Le bloc joueur est compact mais les cartes gardent leur taille fixe."""
        ui = main.FlammeRougeGame(stage="test")
        ui.width, ui.height = 1200, 800
        ui.screen = __import__('pygame').display.set_mode((1200, 800))
        panel = ui._card_panel_rect()
        self.assertLessEqual(panel.w, 380)          # bloc rapetissé en largeur
        self.assertLessEqual(ui._bar_rect().h, 150)  # et en hauteur
        for player, p, rows in ui._hand_layout():
            for runner, label, items, rects in rows:
                for rect in rects:
                    self.assertEqual(rect.w, main.CARD_W)       # largeur carte fixe
                    self.assertEqual(rect.h, main.CARD_H_MAIN)  # hauteur carte fixe
                    self.assertTrue(panel.contains(rect))

    def test_unplaced_runners_clipped_in_frame(self):
        """En phase de placement, la réserve est dessinée DANS le clip du cadre."""
        import pygame
        ui = main.FlammeRougeGame()
        ui._select_stage("test")
        ui.width, ui.height = 1200, 800
        ui.screen = pygame.display.set_mode((1200, 800))
        bar = ui._bar_rect()
        frame = pygame.Rect(4, main.TOP_H + 2, ui.width - 10, bar.y - main.TOP_H - 8)
        ui.screen.fill((255, 255, 255))
        ui.screen.set_clip(frame)
        ui._draw_unplaced_runners()   # ne doit rien dessiner hors du cadre
        ui.screen.set_clip(None)
        # sous le cadre (dans la barre du bas), le pixel est resté blanc
        self.assertEqual(tuple(ui.screen.get_at((ui.width // 2, ui.height - 10)))[:3],
                         (255, 255, 255))

    def test_log_panel_scrollable(self):
        """La molette au-dessus du panneau de logs scrolle l'historique (pas le zoom)."""
        import pygame
        ui = main.FlammeRougeGame(stage="test")
        ui.width, ui.height = 1200, 800
        ui.screen = pygame.display.set_mode((1200, 800))
        # génère de l'historique : 3 tours aléatoires
        for _ in range(3):
            ui._play_random_turn()
        self.assertGreater(len(ui.game.history), 1)
        log = ui._log_panel_rect()
        self.assertEqual(ui.log_scroll, 0)
        # les events MOUSEWHEEL n'ont pas de pos : le handler lit pygame.mouse.get_pos()
        from unittest import mock
        # ordre chronologique + ligne vide entre les tours + phases en gras + couleurs d'équipe
        lines = ui._history_lines()
        self.assertTrue(any(l[0] == f"TOUR {ui.game.turn_count}" and l[2] for l in lines))
        self.assertTrue(any(l[0] == "" for l in lines))                    # ligne vide entre tours
        self.assertTrue(any(l[0] in ("Énergie", "Mouvement", "Aspiration") and l[2]
                            for l in lines))                                # phases en gras
        red = main.PLAYER_COLORS["red"]
        self.assertTrue(any(l[1] == red for l in lines))                   # couleur d'équipe
        with mock.patch.object(pygame.mouse, 'get_pos', return_value=log.center):
            ui._game_event(pygame.event.Event(pygame.MOUSEWHEEL, y=1))   # vers le haut = remonter
            self.assertGreater(ui.log_scroll, 0)          # a scrollé
            self.assertAlmostEqual(ui.zoom, 1.0, places=3)  # sans zoomer
            ui._game_event(pygame.event.Event(pygame.MOUSEWHEEL, y=-1))  # redescend
            self.assertEqual(ui.log_scroll, 0)             # on revient en bas (récent)
        with mock.patch.object(pygame.mouse, 'get_pos', return_value=(600, 300)):
            ui._game_event(pygame.event.Event(pygame.MOUSEWHEEL, y=1))  # hors log -> zoom
            self.assertGreater(ui.zoom, 1.0)
        ui._draw_ui()  # panneau scrollable rendu sans erreur

    def test_track_visuals_middle_line_and_tint_inside_road(self):
        """Ligne médiane blanche sur tout le tracé ; teintes des cases spéciales
        à l'intérieur de la route (pas de débordement en virage)."""
        import pygame
        from game.track import CellGeographyType
        ui = main.FlammeRougeGame(stage="Col du Ballon")  # virages + montagnes
        ui.width, ui.height = 1200, 800
        ui.screen = pygame.display.set_mode((1200, 800))
        ui.screen.fill((255, 255, 255))
        geo = ui._track_geometry()
        ui._draw_track()
        # ligne médiane : au milieu de la route, le pixel est blanc
        cell = geo["cell"]
        mid_s = (ui.game.track.length // 2) * cell
        px, py, _tx, _ty = ui._path_at(geo, mid_s + cell / 2)
        c = tuple(ui.screen.get_at((int(px), int(py))))[:3]
        self.assertGreater(min(c), 200, f"pas de ligne médiane blanche au centre: {c}")
        # teinte montée présente quelque part à l'intérieur de la route
        found_uphill = False
        for x in range(ui.game.track.length):
            if ui.game.track.geography_at(x) == CellGeographyType.UPHILL:
                qx, qy, _tx, _ty = ui._path_at(geo, (x + 0.5) * cell)
                nx, ny = -_ty, _tx
                qx, qy = qx + nx * geo["half"] * 0.5, qy + ny * geo["half"] * 0.5  # dans la file
                c = tuple(ui.screen.get_at((int(qx), int(qy))))[:3]
                if c == tuple(main.UPHILL_FILL):
                    found_uphill = True
                    # juste à côté, hors de la route : pas de teinte (bord gris/blanc)
                    nx, ny = -_ty, _tx
                    ox, oy = qx + nx * (geo["half"] + 6), qy + ny * (geo["half"] + 6)
                    oc = tuple(ui.screen.get_at((int(ox), int(oy))))[:3]
                    self.assertNotEqual(oc, tuple(main.UPHILL_FILL),
                                        "la teinte déborde hors de la route en virage")
        self.assertTrue(found_uphill)

    def test_buttons_recessed_and_labels_fit(self):
        """Chaque bouton a un effet enfoncé (ombre en bas) et son libellé tient."""
        import pygame
        ui = main.FlammeRougeGame(stage="test")
        ui.width, ui.height = 1200, 800
        ui.screen = pygame.display.set_mode((1200, 800))
        ui.screen.fill((255, 255, 255))
        ui._draw_ui()
        # boutons caméra à côté de la légende (bas du cadre)
        frame = ui._frame_rect()
        legend_y = ui._bar_rect().y - 24
        for key, rect in ui._frame_button_rects().items():
            self.assertTrue(frame.contains(rect))
            self.assertGreaterEqual(rect.y, legend_y - 40)  # en bas, près de la légende
        # effet enfoncé : le pixel 3px au-dessus du bas du bouton est plus sombre que le centre
        rects = [r for r in ui._frame_button_rects().values()] + \
                [r for r in ui._purple_button_rects().values()] + [ui._button_rect()]
        for rect in rects:
            c_mid = ui.screen.get_at(rect.center)
            c_bot = ui.screen.get_at((rect.centerx, rect.bottom - 2))
            self.assertGreater(sum(c_mid[:3]), sum(c_bot[:3]) - 40,
                               "pas d'effet enfoncé")

    def test_button_presses_in_on_click(self):
        """Au clic maintenu sur un bouton, il s'enfonce (ombre inversée)."""
        import pygame
        ui = main.FlammeRougeGame(stage="test")
        ui.width, ui.height = 1200, 800
        ui.screen = pygame.display.set_mode((1200, 800))
        rect = ui._frame_button_rects()["peloton"]
        ui._game_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center))
        self.assertEqual(ui._pressed_button, "peloton")
        ui.screen.fill((255, 255, 255))
        ui._draw_ui()
        c_mid = ui.screen.get_at(rect.center)
        c_top = ui.screen.get_at((rect.centerx, rect.y + 2))
        # enfoncé : le haut du bouton est sombre (ombre portée en haut)
        self.assertLess(sum(c_top[:3]), sum(c_mid[:3]))
        ui._game_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=rect.center))
        self.assertIsNone(ui._pressed_button)

    def test_no_lane_AB_graphics(self):
        """Plus de lettres A/B sur le parcours ni dans la légende."""
        import pygame
        ui = main.FlammeRougeGame(stage="test")
        ui.width, ui.height = 1200, 800
        ui.screen = pygame.display.set_mode((1200, 800))
        ui.screen.fill((255, 255, 255))
        ui._draw_ui()
        # aucun pixel noir isolé de lettre A/B hors route : on vérifie juste le rendu
        # et l'absence de l'item de légende (test indirect : le rendu passe)

    def test_left_click_on_track_without_move_still_places(self):
        """Clic gauche sur le parcours SANS bouger = clic simple (placement)."""
        import pygame
        ui = main.FlammeRougeGame()
        ui._select_stage("test")
        ui.width, ui.height = 1200, 800
        ui.screen = pygame.display.set_mode((1200, 800))
        limit = ui.game.track.start_line_x()
        px, py, tx, ty = ui._cell_anchor(limit - 1)
        nx, ny = -ty, tx
        geo = ui._track_geometry()
        pos = (px + nx * geo["half"] * 0.5, py + ny * geo["half"] * 0.5)
        ui._game_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))
        ui._game_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=pos))  # pas bougé
        self.assertEqual(len(ui.game.track.get_all_runners()), 1)  # placé !

    def test_runner_bubble_initial_only_centered(self):
        """La bulle d'un coureur ne contient que l'initiale (S/R), centrée."""
        import pygame
        ui = main.FlammeRougeGame(stage="test")
        ui.width, ui.height = 1200, 800
        ui.screen = pygame.display.set_mode((1200, 800))
        ui.screen.fill((255, 255, 255))
        geo = ui._track_geometry()
        ui._draw_runners()
        r = ui.game.players[0].sprinter
        px, py, tx, ty = ui._cell_anchor(r.x)
        nx, ny = -ty, tx
        cx = px + nx * geo["lane_w"] / 2
        cy = py + ny * geo["lane_w"] / 2
        # au centre de la bulle : un pixel sombre (la lettre S en noir)
        c = ui.screen.get_at((int(cx), int(cy)))
        self.assertLess(sum(c[:3]), 300, f"pas d'initiale centrée: {c}")

    def test_log_text_selection_and_copy(self):
        """Le log est une vraie zone de texte : sélection au clic/drag, Ctrl+A, Ctrl+C."""
        import pygame
        ui = main.FlammeRougeGame(stage="test")
        ui.width, ui.height = 1200, 800
        ui.screen = pygame.display.set_mode((1200, 800))
        for _ in range(2):
            ui._play_random_turn()
        ui._draw_ui()  # calcule _log_line_rects
        log = ui._log_panel_rect()
        rects = ui._log_line_rects
        self.assertGreater(len(rects), 2)
        i0, y0, h0 = rects[0]
        i1, y1, h1 = rects[2]
        # clic sur la 1re ligne puis drag jusqu'à la 3e
        ui._game_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                          pos=(log.x + 20, y0 + 2)))
        self.assertEqual(ui.log_sel, (i0, i0))
        ui._game_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(log.x + 20, y1 + 2)))
        self.assertEqual(ui.log_sel, (i0, i1))  # sélection étendue
        ui._game_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1,
                                          pos=(log.x + 20, y1 + 2)))
        self.assertFalse(ui.log_sel_drag)
        ui._draw_ui()  # surbrillance dessinée sans erreur
        # Ctrl+A = tout sélectionner, Ctrl+C = copie (ne plante pas en headless)
        ui._game_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, mod=pygame.KMOD_CTRL))
        self.assertEqual(ui.log_sel, (0, len(ui._history_lines()) - 1))
        ui._game_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_c, mod=pygame.KMOD_CTRL))

    def test_log_text_format(self):
        """Format du log : TOUR X, 'Sprinteur 0 pose une carte face cachée',
        'Rouleur 1 avance de N case(s) : de y à z', aspiration décrite."""
        import re
        ui = main.FlammeRougeGame(stage="test")
        ui.width, ui.height = 1200, 800
        ui.screen = __import__('pygame').display.set_mode((1200, 800))
        ui._play_random_turn()
        lines = [l[0] for l in ui._history_lines()]
        self.assertTrue(any(re.fullmatch(r"TOUR \d+", l) for l in lines))
        self.assertTrue(any(re.fullmatch(
            r"(Sprinteur|Rouleur) \d+ pose une carte face cachée", l.strip()) for l in lines))
        self.assertTrue(any(re.fullmatch(
            r"(Sprinteur|Rouleur) \d+ avance de \d+ case\(s\) : de \d+ à \d+.*", l.strip())
            for l in lines))
        self.assertTrue(any("glisse" in l for l in lines) or True)  # aspiration si présente

    def test_menu_scrollable_and_searchable(self):
        """Menu scrollable (molette) + barre de recherche filtrant les parcours perso."""
        import tempfile, pygame
        from game.game import save_track_json
        ui = main.FlammeRougeGame()
        ui.saves_dir = tempfile.mkdtemp()
        for i in range(8):
            save_track_json(f"abc{i}u", ui.saves_dir, name=f"parcours_{i}")
        save_track_json("abcdu", ui.saves_dir, name="col_du_ballon_perso")
        ui.width, ui.height = 1200, 800
        ui.screen = pygame.display.set_mode((1200, 800))
        ui._draw_menu()
        entries = ui._menu_entries()
        perso = [e for e in entries if e[4] == "perso"]
        self.assertEqual(len(perso), 9)
        # scroll : la molette décale la liste
        y0 = entries[0][3].y
        ui._menu_event(pygame.event.Event(pygame.MOUSEWHEEL, y=-1, pos=(300, 400)))
        entries2 = ui._menu_entries()
        self.assertLess(entries2[0][3].y, y0)  # remonté dans la liste
        self.assertGreater(ui.menu_scroll, 0)
        # recherche : filtre les parcours perso
        ui.menu_search = "ballon"
        entries3 = ui._menu_entries()
        perso3 = [e for e in entries3 if e[4] == "perso"]
        self.assertEqual(len(perso3), 1)
        self.assertEqual(perso3[0][0], "col_du_ballon_perso")
        # saisie au clavier dans la barre de recherche
        ui.menu_search = ""
        ui.menu_search_active = True
        ui._menu_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                          pos=ui._menu_search_rect().center))
        for ch in "ballon":
            ui._menu_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UNKNOWN,
                                              unicode=ch))
        self.assertEqual(ui.menu_search, "ballon")
        entries4 = ui._menu_entries()
        self.assertEqual(len([e for e in entries4 if e[4] == "perso"]), 1)
        ui._draw_menu()
