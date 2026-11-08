"""Tests de l'extension Peloton (modèle : pavés + zones d'approvisionnement).

Règles officielles (docs/extension-peloton.md) :
- les cases peuvent faire 1 à 3 files (pas seulement 2) ;
- PAVÉS : section à 1 file, AUCUNE aspiration donnée ni reçue dessus (comme une montée) ;
- ZONE D'APPROVISIONNEMENT : 3 files, vitesse minimale 4 si on y commence son tour.

Lancé :  python -m unittest tests.test_peloton -v
"""
import os
import sys
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from game.track import Track, make_tile, CellGeographyType  # noqa: E402
from game.runner import Runner, RunnerType  # noqa: E402
from game.game import Game, tile_def_for_letter, build_tile  # noqa: E402
from game.card import CardType  # noqa: E402


def make_runner(name):
    return Runner(id=name, type=RunnerType.SPRINTER)


def place(track, runner, x, y):
    cell = track.get_cell(x, y)
    assert cell is not None, f"case ({x},{y}) hors piste"
    assert cell.set_runner(runner, y), f"case ({x},{y}) occupée"
    return runner


class TestPelotonTiles(unittest.TestCase):
    def test_peloton_tile_defs(self):
        """Tuiles Peloton : v = pavés 1 file, w = appro 3 files, x/y = pavés en virage."""
        v = build_tile('v')
        self.assertEqual(v.width, 1)
        self.assertTrue(all(c.geography == CellGeographyType.COBBLE for c in v.cells))
        w = build_tile('w')
        self.assertEqual(w.width, 3)
        self.assertTrue(all(c.geography == CellGeographyType.SUPPLY for c in w.cells))
        self.assertEqual(tile_def_for_letter('x')[1], 1)

    def test_game_peloton_flag(self):
        g = Game(stage="test", player_count=2, peloton=True)
        self.assertTrue(g.peloton)
        g2 = Game(stage="test", player_count=2)
        self.assertFalse(g2.peloton)

    def test_wide_start_finish_at_5_6_players(self):
        """En 5-6 joueurs avec Peloton, départ/arrivée passent en tuiles LARGES
        (z/Z, 3 files) ; sinon départ 'a' classique 2 files."""
        g4 = Game(stage="Avenue Corso Paseo", player_count=4, peloton=True)
        self.assertEqual(g4.track.tiles[0].letter, "a")
        self.assertEqual(g4.track.tiles[0].width, 2)
        for n in (5, 6):
            g = Game(stage="Avenue Corso Paseo", player_count=n, peloton=True,
                     auto_place=True)
            self.assertEqual(g.track.tiles[0].letter, "z")
            self.assertEqual(g.track.tiles[0].width, 3)   # les 3 cases de départ
            self.assertEqual(g.track.tiles[-1].letter, "Z")
            self.assertEqual(g.track.tiles[-1].width, 3)
            placed = sum(1 for t in g.track.tiles for c in t.cells
                         for l in range(len(c.runners)) if c.runners[l])
            self.assertEqual(placed, 2 * n)  # tous les coureurs placés au départ

    def test_menu_checkbox_wires_peloton(self):
        import main
        ui = main.FlammeRougeGame()
        ui.ext_peloton = True
        ui._select_stage("Avenue Corso Paseo")
        self.assertTrue(ui.game.peloton)
        ui2 = main.FlammeRougeGame()
        ui2._select_stage("Avenue Corso Paseo")
        self.assertFalse(ui2.game.peloton)

    def test_ai_team_modes_force_peloton(self):
        """Moteur : une équipe en IA Peloton/Muscle rend l'extension Peloton
        obligatoire (même si peloton=False passé au constructeur)."""
        g = Game(stage="test", team_modes=["human", "peloton"])
        self.assertTrue(g.peloton)
        g = Game(stage="test", team_modes=["human", "muscle"])
        self.assertTrue(g.peloton)
        # 5 équipes dont une IA Muscle, peloton non demandé -> 5 joueurs conservés
        g = Game(stage="test", team_modes=["human"] * 4 + ["muscle"])
        self.assertTrue(g.peloton)
        self.assertEqual(g.player_count, 5)
        # sans IA Peloton/Muscle, l'extension reste optionnelle
        g = Game(stage="test", team_modes=["human", "human"])
        self.assertFalse(g.peloton)


class TestCobblestones(unittest.TestCase):
    def _track(self):
        # tuile plate 0-5, tuile pavés 6-11 (1 file), tuile plate 12-17
        track = Track()
        track.add_tile(make_tile("ffffff"))
        track.add_tile(build_tile('v'))
        track.add_tile(make_tile("ffffff"))
        return track

    def test_no_slipstream_on_cobbles_giver_or_receiver(self):
        """Pavés : aucune aspiration donnée ni reçue (donneur et receveur)."""
        track = self._track()
        # donneur en case 6 (pavés), receveur en case 4, case 5 vide entre les deux
        giver = place(track, make_runner("g"), 6, 0)
        rear = place(track, make_runner("r"), 4, 0)
        self.assertEqual(track.compute_slipstream_steps(), [])
        track.apply_aspiration()
        self.assertEqual(rear.x, 4)
        # contrôle : même config sur plat -> aspiration
        track2 = Track()
        for _ in range(3):
            track2.add_tile(make_tile("ffffff"))
        place(track2, make_runner("g"), 6, 0)
        rear2 = place(track2, make_runner("r"), 4, 0)
        self.assertEqual(len(track2.compute_slipstream_steps()), 1)

    def test_single_lane_cell(self):
        """Case pavée = 1 file : un 2e coureur ne peut pas s'y mettre (recul)."""
        track = self._track()
        place(track, make_runner("a"), 7, 0)
        b = place(track, make_runner("b"), 6, 0)
        track.move_runner(b, 2)  # viserait case 8 (libre) ; case 7 pleine à 1 file
        self.assertEqual(b.x, 8)  # a pu avancer (case 8 libre)
        # si la case visée est pleine à 1 file -> recul derrière
        track2 = self._track()
        place(track2, make_runner("a"), 8, 0)
        b2 = place(track2, make_runner("b"), 6, 0)
        track2.move_runner(b2, 2)  # case 8 pleine (1 file) -> s'arrête en 7
        self.assertEqual(b2.x, 7)


class TestSupplyZone(unittest.TestCase):
    def test_min_speed_4_when_starting_in_supply(self):
        """Zone d'approvisionnement : commencer son tour là-dedans = minimum 4."""
        track = Track()
        track.add_tile(make_tile("ffffff"))
        track.add_tile(build_tile('w'))  # cases 6-11 en appro, 3 files
        track.add_tile(make_tile("ffffff"))
        steps, reason = track.effective_steps(6, 2)
        self.assertEqual(steps, 4)
        self.assertIn("approvisionnement", reason)
        # case 5 (plat) : pas de minimum
        steps2, _ = track.effective_steps(5, 2)
        self.assertEqual(steps2, 2)
        # carte >= 4 : inchangé
        steps3, _ = track.effective_steps(6, 7)
        self.assertEqual(steps3, 7)

    def test_three_lanes_fit(self):
        """Case d'approvisionnement = 3 files : 3 coureurs côte à côte."""
        track = Track()
        track.add_tile(make_tile("ffffff"))
        track.add_tile(build_tile('w'))
        for lane in range(3):
            place(track, make_runner(f"r{lane}"), 6, lane)
        self.assertTrue(track.get_cell(6, 0).is_full())
        self.assertEqual(len(track.get_cell(6, 0).runners), 3)


class TestDummyTeams(unittest.TestCase):
    """Équipes factices (Peloton/Muscle IA) choisies sur l'écran d'options
    (mode par équipe : Joueur / IA), plus d'écran « équipes en course » séparé."""

    def _game(self, modes, auto_place=False):
        return Game(stage="test", player_count=len(modes), peloton=True,
                    team_modes=modes, auto_place=auto_place)

    def test_peloton_dummy_creation(self):
        g = self._game(["human", "human", "peloton"])
        self.assertEqual(len(g.players), 3)
        dummy = g.players[2]
        self.assertEqual(dummy.ai, "peloton")
        self.assertIsNone(dummy.controller)
        self.assertTrue(g._is_ai(dummy))
        self.assertEqual(len(dummy.ai_deck), 17)  # deck rouleur 15 + 2 Attack!
        self.assertEqual(sum(1 for c in dummy.ai_deck if c.type == CardType.ATTACK), 2)
        # les équipes humaines ne sont pas des IA
        self.assertFalse(g._is_ai(g.players[0]))

    def test_muscle_dummy_creation(self):
        g = self._game(["human", "human", "muscle"])
        dummy = g.players[2]
        self.assertEqual(dummy.ai, "muscle")
        self.assertTrue(g._is_ai(dummy))
        self.assertEqual(sum(1 for c in dummy.sprinter.energy_deck
                             if c.type == CardType.MUSCLE), 1)

    def test_ai_peloton_plays_one_card_for_both_riders(self):
        g = self._game(["human", "human", "peloton"])
        g.start_turn()
        dummy = g.players[2]
        for r in dummy.get_runners():
            self.assertIsNotNone(r.played_card)

    def test_ai_peloton_attack_card_gives_2_and_9(self):
        from game.card import Card
        g = self._game(["human", "human", "peloton"])
        dummy = g.players[2]
        dummy.ai_deck = [Card(0, CardType.ATTACK, "R")] + dummy.ai_deck  # Attack! au dessus
        g.start_turn()
        values = sorted(r.played_card.value for r in dummy.get_runners())
        self.assertEqual(values, [2, 9])  # avant 2, arrière 9

    def test_ai_muscle_plays_own_decks(self):
        g = self._game(["human", "human", "muscle"])
        g.start_turn()
        dummy = g.players[2]
        self.assertIsNotNone(dummy.sprinter.played_card)
        self.assertIsNotNone(dummy.roller.played_card)

    def test_ai_never_gets_fatigue(self):
        g = self._game(["human", "human", "peloton"], auto_place=True)
        g._assign_fatigue_cards()
        dummy = g.players[2]
        self.assertEqual(dummy.sprinter.discard_pile, [])
        self.assertEqual(dummy.roller.discard_pile, [])

    def test_options_screen_team_mode_and_start(self):
        """UI : écran d'options (après sélection du parcours) avec le choix
        Joueur/IA par équipe ; JOUER démarre directement (plus d'écran teams)."""
        import main, pygame
        ui = main.FlammeRougeGame()
        entries = ui._menu_entries()
        stage = next(e for e in entries if e[4] == "base")
        ui.menu_index = entries.index(stage)
        ui._menu_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(ui.menu_step, "options")            # options après le parcours
        self.assertFalse(hasattr(ui, "_draw_teams_menu"))     # plus d'écran équipes séparé
        # 3 équipes, la 3e en IA Peloton
        ui.width, ui.height = 1280, 920
        ui.screen = pygame.display.set_mode((1280, 920), pygame.RESIZABLE)
        opts = ui._player_count_option_rects()
        ui._menu_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                          pos=opts[3].center))  # 3 joueurs
        self.assertEqual(ui.player_count, 3)
        rows = ui._team_mode_row_rects()
        self.assertEqual(len(rows), 3)
        # cycle le mode de l'équipe 3 : human -> peloton
        ui._menu_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                          pos=ui._team_mode_button_rect(rows[2][1]).center))
        self.assertEqual(ui._team_mode(2), "peloton")
        self.assertEqual(ui._team_modes_list(), ["human", "human", "peloton"])
        ui.screen.fill((255, 255, 255))
        ui._draw_header(); ui._draw_menu()                     # rendu options, sans erreur
        # JOUER démarre directement la partie avec l'équipe IA
        ui._menu_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                          pos=ui._next_button_rect().center))
        self.assertIsNotNone(ui.game)
        self.assertEqual(ui.menu_step, "options")  # plus passé par un écran teams
        self.assertTrue(any(p.ai == "peloton" for p in ui.game.players))
        self.assertEqual(len(ui.game.players), 3)

    def test_options_peloton_locked_by_ai(self):
        """UI : IA Peloton/Muscle verrouille l'extension Peloton (forcée, non
        désactivable, cadenas affiché) ; 5/6 joueurs verrouille aussi."""
        import main, pygame
        ui = main.FlammeRougeGame()
        entries = ui._menu_entries()
        stage = next(e for e in entries if e[4] == "base")
        ui.menu_index = entries.index(stage)
        ui._menu_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(ui.menu_step, "options")
        ui.width, ui.height = 1280, 920
        ui.screen = pygame.display.set_mode((1280, 920), pygame.RESIZABLE)
        opts = ui._player_count_option_rects()
        ui._menu_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                          pos=opts[3].center))  # 3 joueurs
        self.assertFalse(ui.ext_peloton)
        rows = ui._team_mode_row_rects()
        pel = ui._ext_tick_rects()["peloton"]
        # équipe 2 en IA Peloton -> Peloton forcé
        ui._menu_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                          pos=ui._team_mode_button_rect(rows[1][1]).center))
        self.assertEqual(ui._team_mode(1), "peloton")
        self.assertTrue(ui.ext_peloton)
        self.assertTrue(ui._peloton_required())
        # clic sur le bloc Peloton : reste actif (verrouillé)
        ui._menu_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pel.center))
        self.assertTrue(ui.ext_peloton)
        # retour en Joueur (2 clics : peloton -> muscle -> human) -> déverrouillé
        for _ in range(2):
            ui._menu_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                              pos=ui._team_mode_button_rect(rows[1][1]).center))
        self.assertEqual(ui._team_mode(1), "human")
        self.assertFalse(ui._peloton_required())
        ui._menu_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pel.center))
        self.assertFalse(ui.ext_peloton)
        # 5 joueurs -> verrouillé aussi
        ui._menu_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                          pos=opts[5].center))
        self.assertTrue(ui.ext_peloton)
        self.assertTrue(ui._peloton_required())
        ui.screen.fill((255, 255, 255))
        ui._draw_header(); ui._draw_menu()  # rendu avec cadenas, sans erreur

    def test_options_single_peloton_ai(self):
        """UI : une seule équipe IA Peloton par partie — le cycle des autres
        équipes saute 'peloton' tant qu'une équipe l'est déjà."""
        import main, pygame
        ui = main.FlammeRougeGame()
        entries = ui._menu_entries()
        stage = next(e for e in entries if e[4] == "base")
        ui.menu_index = entries.index(stage)
        ui._menu_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        ui.width, ui.height = 1280, 920
        ui.screen = pygame.display.set_mode((1280, 920), pygame.RESIZABLE)
        opts = ui._player_count_option_rects()
        ui._menu_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                          pos=opts[3].center))  # 3 joueurs
        rows = ui._team_mode_row_rects()
        btn = [ui._team_mode_button_rect(r[1]) for r in rows]
        clic = lambda b: ui._menu_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=b.center))
        clic(btn[0])  # équipe 1 -> IA Peloton
        self.assertEqual(ui._team_mode(0), "peloton")
        self.assertTrue(ui.ext_peloton)
        # équipe 2 : le cycle saute peloton (human -> muscle -> human -> ...)
        seen = set()
        for _ in range(6):
            clic(btn[1])
            seen.add(ui._team_mode(1))
        self.assertEqual(seen, {"human", "muscle"})
        self.assertNotIn("peloton", seen)
        # équipe 1 repassée en Joueur -> équipe 2 peut devenir IA Peloton
        clic(btn[0]); clic(btn[0])  # peloton -> muscle -> human
        self.assertEqual(ui._team_mode(0), "human")
        clic(btn[1])  # human -> peloton (plus de conflit)
        self.assertEqual(ui._team_mode(1), "peloton")
        ui.screen.fill((255, 255, 255))
        ui._draw_header(); ui._draw_menu()  # rendu avec la note, sans erreur

if __name__ == "__main__":
    unittest.main()
