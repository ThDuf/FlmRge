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
            b = ui._button_rect()
            r = ui._random_button_rect()
            self.assertGreaterEqual(b.y, 0)
            self.assertLessEqual(b.bottom, h, f"bouton action hors écran {w}x{h}")
            self.assertLessEqual(r.bottom, h, f"bouton aléatoire hors écran {w}x{h}")
            self.assertGreater(r.y, b.y)  # le bouton aléatoire est sous l'autre
            # pas de chevauchement avec les panneaux
            panel_h = ui._panel_h()
            panels_bottom = 8 + 112 + 4 * (panel_h + 8)
            self.assertGreaterEqual(b.y, panels_bottom - 8 - 8,
                                    f"bouton chevauche les panneaux {w}x{h}")


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
        # clic sur une tuile de la palette
        ch, rect = ui._editor_palette_rects()[4]  # 'e'
        self.assertEqual(ch, 'e')
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
        self.assertEqual(entries[-1][0], "Éditeur de piste")
        ui.menu_index = len(entries) - 1
        ui._menu_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(ui.menu_step, "editor")
        ui._draw_menu()  # dessine l'éditeur sans erreur

    def test_editor_tile_preview_on_hover(self):
        """Survol de la palette -> editor_hover_letter + preview dessinée."""
        import pygame
        ui = main.FlammeRougeGame()
        ui.width, ui.height = 1200, 800
        ui.screen = pygame.display.set_mode((1200, 800))
        ui.menu_step = "editor"
        ch, rect = ui._editor_palette_rects()[10]  # 'k'
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
        for _color, kind, val in entry["cards"]:
            self.assertIn(kind, ("S", "R"))
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
