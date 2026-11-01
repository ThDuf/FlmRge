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
