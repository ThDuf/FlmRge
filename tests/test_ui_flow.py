"""Test headless du flux UI de main.py (pilotage clavier simulé).

Vérifie le cycle complet d'un tour via la logique de FlammeRougeGame :
énergie -> mouvement -> aspiration (pas-à-pas APPLIQUÉ sur le plateau)
-> fatigue -> nouveau tour, avec contrôle de cohérence à chaque étape.
"""
import os
import sys
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import main  # noqa: E402  (importe pygame en mode dummy)
from game.game import Phase  # noqa: E402


def assert_board_consistent(testcase, ui):
    track = ui.game.track
    seen = set()
    for x, y, runner in track.get_all_runners():
        testcase.assertNotIn(runner.id, seen, f"{runner.id} dupliqué sur la piste")
        seen.add(runner.id)
        testcase.assertEqual((runner.x, runner.y), (x, y))


def sum_positions(ui):
    return sum(r.x for _x, _y, r in ui.game.track.get_all_runners())


class TestUiFlow(unittest.TestCase):
    def setUp(self):
        self.ui = main.FlammeRougeGame(stage="La Haut Montagne")

    def _play_energy_phase(self):
        """Joue la première carte de chaque coureur, comme les clics souris."""
        game = self.ui.game
        for player in game.players:
            for runner in player.get_runners():
                card = runner.hand[0]
                self.assertTrue(game.play_card(player, runner, card))
        self.assertTrue(game.all_players_ready())

    def test_full_turn_with_aspiration_steps(self):
        ui = self.ui
        game = ui.game

        # Phase d'énergie
        self.assertEqual(game.current_phase, Phase.ENERGY)
        self._play_energy_phase()

        # Phase de mouvement : le moteur CALCULE, l'UI applique pas-à-pas
        ui._start_movement_phase()
        self.assertTrue(ui.showing_movement)
        self.assertEqual(ui.movement_total, 4)  # 2 joueurs x 2 coureurs
        done = False
        guard = 0
        while not done:
            done = ui._next_movement_step()
            guard += 1
            self.assertLess(guard, 100, "pas-à-pas de mouvement sans fin")
            assert_board_consistent(self, ui)
        ui.showing_movement = False
        assert_board_consistent(self, ui)

        # Phase d'aspiration : le moteur CALCULE, l'UI applique pas-à-pas
        steps = game.resolve_aspiration_phase()
        if steps:
            ui.aspiration_movements = steps
            ui._initialize_aspiration()
            self.assertTrue(ui.showing_aspiration)
            self.assertEqual(ui.aspiration_total, len(steps))
            expected_total_moves = sum(len(s) for s in steps)

            before = sum_positions(ui)
            done = False
            guard = 0
            while not done:
                done = ui._next_aspiration_step()
                guard += 1
                self.assertLess(guard, 100, "pas-à-pas d'aspiration sans fin")
                assert_board_consistent(self, ui)
            # Chaque mouvement d'étape avance un coureur d'exactement 1 case
            self.assertEqual(sum_positions(ui), before + expected_total_moves)
            # Tout est appliqué : plus aucune aspiration possible
            self.assertEqual(game.track.compute_slipstream_steps(), [])
            ui._finish_aspiration_phase()
        else:
            ui._finish_aspiration_phase()

        # Fatigue + victoire éventuelle + nouveau tour direct
        self.assertFalse(ui.showing_aspiration)
        assert_board_consistent(self, ui)
        if not game.game_over:
            self.assertEqual(game.current_phase, Phase.ENERGY)
            self.assertEqual(game.turn_count, 2)
            for player in game.players:
                for runner in player.get_runners():
                    self.assertEqual(len(runner.hand), 4)
                    self.assertIsNone(runner.played_card)

    def test_button_drives_full_turn(self):
        """Le bouton cliquable doit piloter un tour complet comme ENTRÉE."""
        ui = self.ui
        game = ui.game
        rect = ui._button_rect()
        center = (rect.centerx, rect.centery)

        # Avant d'avoir joué : pas de bouton
        self.assertIsNone(ui._button_info())
        self.assertFalse(ui._try_button_click(center))

        # Cartes jouées -> bouton "Lancer le mouvement"
        self._play_energy_phase()
        label, _color = ui._button_info()
        self.assertEqual(label, "Lancer le mouvement")
        self.assertTrue(ui._try_button_click(center))
        self.assertTrue(ui.showing_movement)
        assert_board_consistent(self, ui)

        # Un clic = un coureur déplacé
        label, _color = ui._button_info()
        self.assertIn("Mouvement suivant", label)
        clicks = 0
        while ui.showing_movement:
            self.assertTrue(ui._try_button_click(center))
            clicks += 1
            self.assertLess(clicks, 100)
            assert_board_consistent(self, ui)
        self.assertEqual(clicks, 4)

        # Clic pour lancer l'aspiration puis la dérouler
        clicks = 0
        while not game.game_over and game.current_phase != Phase.ENERGY:
            if ui._button_info() is None:
                break
            ui._try_button_click(center)
            clicks += 1
            self.assertLess(clicks, 100)
            assert_board_consistent(self, ui)
        # soit la partie est finie, soit on est revenu en phase d'énergie
        self.assertTrue(game.game_over or game.current_phase == Phase.ENERGY)

    def test_finish_aspiration_resets_display_state(self):
        ui = self.ui
        ui.showing_aspiration = True
        ui.aspiration_step = 2
        ui.aspiration_total = 3
        ui.aspiration_movements = [(None, 1, 0, 2, 0)]
        ui._finish_aspiration_phase()
        self.assertFalse(ui.showing_aspiration)
        self.assertEqual(ui.aspiration_step, 0)
        self.assertEqual(ui.aspiration_movements, [])
        # Phase TERMINALE transitoire : nouveau tour démarré directement
        self.assertEqual(ui.game.current_phase, Phase.ENERGY)
        self.assertEqual(ui.game.turn_count, 2)


class TestHandLayout(unittest.TestCase):
    def setUp(self):
        self.ui = main.FlammeRougeGame(stage="La Haut Montagne")

    def test_panels_fit_window(self):
        layout = ui_layout = self.ui._hand_layout()
        self.assertEqual(len(layout), len(self.ui.game.players))
        for player, panel, rows in layout:
            self.assertLessEqual(panel.right, self.ui.width, "panneau hors écran à droite")
            self.assertLessEqual(panel.bottom, self.ui.height, "panneau hors écran en bas")
            self.assertGreaterEqual(panel.x, 0)
            for runner, label, items, rects in rows:
                self.assertEqual(len(rects), len(items))
                for rect in rects:
                    self.assertTrue(panel.contains(rect), "carte hors du panneau")

    def test_panels_do_not_overlap(self):
        layout = self.ui._hand_layout()
        for i in range(len(layout) - 1):
            self.assertFalse(layout[i][1].colliderect(layout[i + 1][1]),
                             "les panneaux de joueurs se chevauchent")

    def test_resize_updates_layout(self):
        self.ui.width, self.ui.height = 1600, 1000
        layout = self.ui._hand_layout()
        for player, panel, rows in layout:
            self.assertLessEqual(panel.right, 1600)
            self.assertLessEqual(panel.bottom, 1000)
        # géométrie du circuit recalculée : toutes les cases tiennent à l'écran
        geo = self.ui._track_geometry()
        half = geo["half"]
        for x in range(self.ui.game.track.length):
            ax, ay, _tx, _ty = self.ui._cell_anchor(x)
            self.assertLessEqual(ax + half, 1600)
            self.assertLessEqual(ay + half, 1000)

    def test_click_zone_matches_displayed_cards(self):
        """Le clic sur une carte affichée joue bien CETTE carte."""
        ui = self.ui
        self.assertEqual(ui.game.current_phase, Phase.ENERGY)
        layout = ui._hand_layout()
        player, panel, rows = layout[0]
        runner, label, items, rects = rows[0]
        card = items[0][0]
        ui._handle_click((rects[0].centerx, rects[0].centery))
        self.assertEqual(ui.game.cards_played_per_runner[runner.id], 1)
        self.assertIs(runner.played_card, card)
        # un second clic sur le même coureur ne fait rien
        ui._handle_click((rects[1].centerx, rects[1].centery))
        self.assertEqual(ui.game.cards_played_per_runner[runner.id], 1)

    def test_played_card_stays_visible_in_green(self):
        """La carte jouée ne disparait pas : elle reste affichée à sa
        position d'origine dans le panneau, marquée comme jouée (verte)."""
        ui = self.ui
        layout = ui._hand_layout()
        player, panel, rows = layout[0]
        runner, label, items, rects = rows[0]
        self.assertEqual(len(items), 4)

        # Clic sur la 2e carte (index 1)
        clicked_card = items[1][0]
        ui._handle_click((rects[1].centerx, rects[1].centery))
        self.assertIs(runner.played_card, clicked_card)

        # La carte jouée est toujours là, à la même position, marquée jouée
        runner2, label2, items2, rects2 = ui._hand_layout()[0][2][0]
        self.assertEqual(len(items2), 4, "la carte jouée doit rester affichée")
        card_at_index1, played_flag = items2[1]
        self.assertIs(card_at_index1, clicked_card)
        self.assertTrue(played_flag)
        self.assertEqual(len(runner2.hand), 3)
        # Un clic sur la carte verte ne rejoue rien
        ui._handle_click((rects2[1].centerx, rects2[1].centery))
        self.assertEqual(ui.game.cards_played_this_turn, 1)


class TestRemainingCounts(unittest.TestCase):
    def setUp(self):
        self.ui = main.FlammeRougeGame(stage="La Haut Montagne")

    def test_counts_full_deck_at_start(self):
        runner = self.ui.game.players[0].sprinter
        counts = self.ui._remaining_counts(runner)
        self.assertEqual(sum(counts.values()), 15)  # deck officiel de 15 cartes
        self.assertEqual(counts.get("8"), 1)
        self.assertEqual(counts.get("2F", 0), 0)
        roller = self.ui.game.players[0].roller
        self.assertEqual(sum(self.ui._remaining_counts(roller).values()), 15)

    def test_played_card_leaves_the_game(self):
        ui = self.ui
        runner = ui.game.players[0].sprinter
        before = ui._remaining_counts(runner)
        card = runner.hand[0]
        key = "2F" if card.type == main.CardType.FATIGUE else str(card.value)
        self.assertTrue(ui.game.play_card(ui.game.players[0], runner, card))
        after = ui._remaining_counts(runner)
        self.assertEqual(sum(after.values()), 14)
        self.assertEqual(after.get(key, 0), before[key] - 1)

    def test_fatigue_card_adds_to_remaining(self):
        from game.card import Card, CardType
        ui = self.ui
        runner = ui.game.players[0].sprinter
        before = sum(ui._remaining_counts(runner).values())
        runner.discard_pile.append(Card(2, CardType.FATIGUE, "S"))
        self.assertEqual(sum(ui._remaining_counts(runner).values()), before + 1)
        self.assertEqual(ui._remaining_counts(runner).get("2F"), 1)


class TestTrackLayout(unittest.TestCase):
    """Circuit organique : chemin continu, cases contiguës, tout visible."""

    def setUp(self):
        self.ui = main.FlammeRougeGame(stage="La Haut Montagne")

    def test_all_cells_fit_on_screen(self):
        ui = self.ui
        geo = ui._track_geometry()
        half = geo["half"]
        for x in range(ui.game.track.length):
            ax, ay, _tx, _ty = ui._cell_anchor(x)
            self.assertGreaterEqual(ax - half, ui._left_w() - 12,
                                    f"case {x} empiète sur la colonne de gauche")
            self.assertLessEqual(ax + half, ui.width, f"case {x} hors écran à droite")
            self.assertGreaterEqual(ay - half, 0)
            self.assertLessEqual(ay + half, ui.height, f"case {x} hors écran en bas")

    def test_all_cells_fit_at_minimum_window_size(self):
        ui = self.ui
        ui.width, ui.height = main.MIN_WIDTH, main.MIN_HEIGHT
        geo = ui._track_geometry()
        half = geo["half"]
        for x in range(ui.game.track.length):
            ax, ay, _tx, _ty = ui._cell_anchor(x)
            self.assertLessEqual(ax + half, ui.width)
            self.assertLessEqual(ay + half, ui.height)

    def test_no_jump_between_consecutive_cells(self):
        """Le circuit est CONTINU : deux cases consécutives sont espacées
        d'exactement une case le long du chemin (aucun saut de rangée)."""
        ui = self.ui
        cell = ui._track_geometry()["cell"]
        for x in range(ui.game.track.length - 1):
            ax, ay, _, _ = ui._cell_anchor(x)
            bx, by, _, _ = ui._cell_anchor(x + 1)
            dist = ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5
            self.assertLessEqual(dist, cell * 1.25,
                                 f"saut entre les cases {x} et {x + 1} ({dist:.0f}px)")

    def test_sharp_turn_bends_heading_90(self):
        """Un virage serré courbe le cap de 90° (pièce officielle 90°)."""
        import math
        from game.track import Track, make_tile, compute_track_path
        track = Track()
        track.add_tile(make_tile("sssssf"))
        track.add_tile(make_tile("ff", turn=(math.pi / 2, 1)))
        track.add_tile(make_tile("feeeee"))
        pts = compute_track_path(track, 1.0)
        # dernier segment (après le virage + ligne d'arrivée) : vertical
        (x0, y0), (x1, y1) = pts[-2], pts[-1]
        self.assertAlmostEqual(x1 - x0, 0, places=5)
        self.assertAlmostEqual(abs(y1 - y0), 6, places=5)

    def test_soft_turn_bends_heading_45(self):
        from game.track import Track, make_tile, compute_track_path
        import math
        track = Track()
        track.add_tile(make_tile("sssssf"))
        track.add_tile(make_tile("ff", turn=(math.pi / 4, 1)))
        track.add_tile(make_tile("feeeee"))
        pts = compute_track_path(track, 1.0)
        # cap final = 45° : dernier segment (ligne d'arrivée) à 45°
        (x0, y0), (x1, y1) = pts[-2], pts[-1]
        angle = math.atan2(y1 - y0, x1 - x0)
        self.assertAlmostEqual(abs(angle), math.radians(45), places=2)

    def test_track_has_turns(self):
        import math
        turns = [t.turn for t in self.ui.game.track.tiles]
        self.assertTrue(any(t and abs(t[0] - math.pi / 2) < 1e-9 for t in turns))

    def test_panels_and_button_stay_left_of_track(self):
        ui = self.ui
        geo = ui._track_geometry()
        leftmost = min(p[0] for p in geo["points"]) - geo["half"]
        for player, panel, rows in ui._hand_layout():
            self.assertLessEqual(panel.right, leftmost)
        self.assertLessEqual(ui._button_rect().right, leftmost)

    def test_geometry_total_arc_matches_cells(self):
        """L'arc total vaut exactement nb_cases * taille_de_case :
        chaque case occupe `cell` pixels de chemin, sans trou ni saut."""
        ui = self.ui
        geo = ui._track_geometry()
        # tolérance : les virages sont approchés par une polyligne inscrite,
        # l'erreur cumulée croît avec le nombre de virages de l'étape
        self.assertAlmostEqual(geo["total"], ui.game.track.length * geo["cell"],
                               delta=2.0)


    def test_action_banner_describes_each_step(self):
        """Chaque étape appliquée est décrite à l'écran (bandeau d'action)."""
        ui = self.ui
        game = ui.game
        for player in game.players:
            for runner in player.get_runners():
                game.play_card(player, runner, runner.hand[0])
        ui._start_movement_phase()

        runner, value = ui.movement_movements[0]
        from_x = runner.x
        self.assertIsNone(ui.last_action)  # rien n'a encore été appliqué
        ui._next_movement_step()
        self.assertIsNotNone(ui.last_action)
        text, _color = ui.last_action
        self.assertIn("case", text)
        self.assertIn(f"{from_x}", text)
        self.assertIn(str(runner.x), text)

        # Chaque mouvement suivant remplace le bandeau
        while ui.movement_movements:
            ui._next_movement_step()
            self.assertIsNotNone(ui.last_action)

        # La fatigue est annoncée en fin de tour
        steps = ui.game.resolve_aspiration_phase()
        ui.apply_steps = steps
        for step in steps:
            ui._next_aspiration_step()
        ui._finish_aspiration_phase()
        if any(r.discard_pile and r.discard_pile[-1].type == main.CardType.FATIGUE
               for p in ui.game.players for r in p.get_runners()):
            self.assertIsNotNone(ui.last_action)
            self.assertIn("Fatigue", ui.last_action[0])


if __name__ == '__main__':
    unittest.main(verbosity=2)
