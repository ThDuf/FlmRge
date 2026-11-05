"""Tests de l'extension Météo (Flamme Rouge: Meteo) — règles du livret.

- Mise en place : un jeton météo FACE CACHÉE sur chaque tuile droite,
  révélé au premier passage d'un coureur (13 jetons : 3 vent arrière,
  3 vent de face, 3 vent de travers, 4 pluie).
- Vent arrière (jaune) : le coureur sur la tuile pioche 5 cartes au lieu de 4.
- Vent de face (bleu) : il pioche 3 cartes au lieu de 4.
- Vent de travers (vert) : aucune aspiration donnée ni reçue sur la tuile.
- Pluie (noir) : si la case d'arrivée du coureur est pleine (mouvement
  bloqué) -> chute (coureur couché, ne donne plus d'aspiration) ; à son
  prochain tour il se relève et sa carte vaut −2 (après ajustements
  descente ; le plafond de 5 en montée n'est pas modifié).

Lancé :  python -m unittest tests.test_meteo -v
"""
import os
import sys
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from game.track import Track, make_tile, WeatherType, WEATHER_TOKENS  # noqa: E402
from game.runner import Runner, RunnerType  # noqa: E402
from game.game import Game  # noqa: E402


def make_flat_track(n_tiles=3):
    track = Track()
    for _ in range(n_tiles):
        track.add_tile(make_tile("ffffff"))
    return track


def make_runner(name):
    return Runner(id=name, type=RunnerType.SPRINTER)


def place(track, runner, x, y):
    cell = track.get_cell(x, y)
    assert cell is not None, f"case ({x},{y}) hors piste"
    assert cell.set_runner(runner, y), f"case ({x},{y}) occupée"
    return runner


def set_tile_weather(track, x, w, revealed=True):
    """Pose la météo w sur TOUTE la tuile contenant la case x."""
    tile = track.tiles[track.tile_index_at(x)]
    for c in tile.cells:
        c.weather = w
        c.weather_revealed = revealed


class TestWeatherAssignment(unittest.TestCase):
    def test_tokens_only_on_straight_tiles_hidden(self):
        """Extension active : jeton face cachée sur chaque tuile droite,
        aucun sur les virages ; extension inactive : rien du tout."""
        game = Game(stage="test", player_count=2, auto_place=False, meteo=True)
        track = game.track
        for tile in track.tiles:
            for c in tile.cells:
                if tile.turn is None:
                    self.assertNotEqual(c.weather, WeatherType.NONE)
                    self.assertFalse(c.weather_revealed)
                else:
                    self.assertEqual(c.weather, WeatherType.NONE)

        game2 = Game(stage="test", player_count=2, auto_place=False, meteo=False)
        for tile in game2.track.tiles:
            for c in tile.cells:
                self.assertEqual(c.weather, WeatherType.NONE)

    def test_turn_tiles_get_no_token(self):
        game = Game(custom_code="abhkeu", player_count=2, auto_place=False, meteo=True)
        turns = [t for t in game.track.tiles if t.turn is not None]
        straights = [t for t in game.track.tiles if t.turn is None]
        self.assertTrue(turns and straights)
        for t in turns:
            for c in t.cells:
                self.assertEqual(c.weather, WeatherType.NONE)
        for t in straights:
            self.assertNotEqual(t.cells[0].weather, WeatherType.NONE)

    def test_token_bag_has_13_tokens(self):
        self.assertEqual(len(WEATHER_TOKENS), 13)
        self.assertEqual(WEATHER_TOKENS.count(WeatherType.TAILWIND), 3)
        self.assertEqual(WEATHER_TOKENS.count(WeatherType.HEADWIND), 3)
        self.assertEqual(WEATHER_TOKENS.count(WeatherType.CROSSWIND), 3)
        self.assertEqual(WEATHER_TOKENS.count(WeatherType.RAIN), 4)

    def test_reveal_weather_reveals_whole_tile_once(self):
        track = make_flat_track(2)  # tuile 0 = cases 0-5, tuile 1 = 6-11
        set_tile_weather(track, 0, WeatherType.RAIN, revealed=False)
        w = track.reveal_weather_at(3)  # n'importe quelle case de la tuile
        self.assertEqual(w, WeatherType.RAIN)
        for c in track.tiles[0].cells:
            self.assertTrue(c.weather_revealed)
        self.assertIsNone(track.reveal_weather_at(4))  # déjà révélé
        # tuile suivante : toujours cachée
        self.assertFalse(track.tiles[1].cells[0].weather_revealed)


class TestWindDrawCount(unittest.TestCase):
    def test_draw_count_for(self):
        game = Game(stage="test", player_count=2, meteo=True)
        runner = game.players[0].sprinter
        set_tile_weather(game.track, runner.x, WeatherType.TAILWIND)
        self.assertEqual(game._draw_count_for(runner), 5)
        set_tile_weather(game.track, runner.x, WeatherType.HEADWIND)
        self.assertEqual(game._draw_count_for(runner), 3)
        for w in (WeatherType.CROSSWIND, WeatherType.RAIN, WeatherType.NONE):
            set_tile_weather(game.track, runner.x, w)
            self.assertEqual(game._draw_count_for(runner), 4)

    def test_draw_count_ignored_without_extension(self):
        game = Game(stage="test", player_count=2, meteo=False)
        runner = game.players[0].sprinter
        set_tile_weather(game.track, runner.x, WeatherType.TAILWIND)
        self.assertEqual(game._draw_count_for(runner), 4)

    def test_start_turn_draws_5_or_3_cards(self):
        """Intégration : au début du tour, la main grandit de 5 (vent
        arrière) ou 3 (vent de face) selon la tuile du coureur."""
        game = Game(stage="test", player_count=2, meteo=True)  # tour 1, mains de 4
        runners = [r for p in game.players for r in p.get_runners()]
        for r in runners:
            r.reset_hand()
            set_tile_weather(game.track, r.x, WeatherType.TAILWIND)
        game.start_turn()
        for r in runners:
            self.assertEqual(len(r.hand), 5)
        for r in runners:
            r.reset_hand()
            set_tile_weather(game.track, r.x, WeatherType.HEADWIND)
        game.start_turn()
        for r in runners:
            self.assertEqual(len(r.hand), 3)


class TestCrosswind(unittest.TestCase):
    def _two_packs(self):
        """Pack de devant (donneur) en case 7, pack arrière en case 5 :
        exactement UNE case vide (6) les sépare -> aspiration normale."""
        track = make_flat_track(3)  # tuile 0 = cases 0-5, tuile 1 = 6-11
        giver = place(track, make_runner("g"), 7, 0)
        rear = place(track, make_runner("r"), 5, 0)
        return track, giver, rear

    def test_no_slipstream_when_giver_on_crosswind(self):
        """Vent de travers : le donneur ne donne pas l'aspiration."""
        track, _giver, rear = self._two_packs()
        set_tile_weather(track, 7, WeatherType.CROSSWIND)  # tuile du donneur
        self.assertEqual(track.compute_slipstream_steps(), [])
        track.apply_aspiration()
        self.assertEqual(rear.x, 5)

    def test_no_slipstream_when_rear_on_crosswind(self):
        """Vent de travers : le receveur ne reçoit pas l'aspiration."""
        track, _giver, rear = self._two_packs()
        set_tile_weather(track, 5, WeatherType.CROSSWIND)  # tuile du receveur
        self.assertEqual(track.compute_slipstream_steps(), [])
        track.apply_aspiration()
        self.assertEqual(rear.x, 5)

    def test_slipstream_works_on_flat_control(self):
        track, _giver, rear = self._two_packs()
        steps = track.compute_slipstream_steps()
        self.assertEqual(len(steps), 1)
        track.apply_aspiration()
        self.assertEqual(rear.x, 6)

    def test_crashed_runner_gives_no_slipstream(self):
        track, giver, rear = self._two_packs()
        giver.crashed = True  # couché : ne donne plus d'aspiration
        self.assertEqual(track.compute_slipstream_steps(), [])
        track.apply_aspiration()
        self.assertEqual(rear.x, 5)


class TestRainCrash(unittest.TestCase):
    def _full_cell_setup(self):
        track = make_flat_track(3)
        place(track, make_runner("b1"), 5, 0)
        place(track, make_runner("b2"), 5, 1)  # case 5 pleine
        runner = place(track, make_runner("r"), 2, 0)
        return track, runner

    def test_crash_when_arrival_cell_full_on_rain_tile(self):
        track, runner = self._full_cell_setup()
        set_tile_weather(track, 2, WeatherType.RAIN)
        reason = track.move_runner(runner, 3)  # arrivée case 5 pleine
        self.assertTrue(runner.crashed)
        self.assertEqual(runner.x, 2)  # reste sur place
        self.assertIn("chute", reason)

    def test_no_crash_on_flat_tile_backs_up(self):
        """Contrôle : hors tuile pluie, case d'arrivée pleine = recul sur
        la première file libre (règle de base), pas de chute."""
        track, runner = self._full_cell_setup()
        track.move_runner(runner, 3)
        self.assertFalse(runner.crashed)
        self.assertEqual(runner.x, 4)  # première case libre derrière

    def test_crashed_runner_gets_up_with_minus_2(self):
        """Au tour suivant le couché se relève : carte −2 (après
        ajustements). Carte 5 -> avance de 3 ; carte 2 -> ne bouge pas."""
        track, runner = self._full_cell_setup()
        set_tile_weather(track, 2, WeatherType.RAIN)
        track.move_runner(runner, 3)
        self.assertTrue(runner.crashed)
        # case 5 libérée entre-temps
        track.get_cell(5, 0).remove_runner(0)
        track.get_cell(5, 1).remove_runner(1)
        reason = track.move_runner(runner, 5)  # 5 - 2 = 3 cases
        self.assertFalse(runner.crashed)  # relevé
        self.assertEqual(runner.x, 5)
        self.assertIn("-2", reason)
        # carte 2 = se relève sans bouger
        runner.crashed = True
        track.move_runner(runner, 2)
        self.assertFalse(runner.crashed)
        self.assertEqual(runner.x, 5)

    def test_mountain_cap_not_modified_by_crash_penalty(self):
        """Le plafond de 5 en montée s'applique à la carte d'origine ;
        la pénalité −2 s'applique après (elle ne fait pas passer le
        plafond à 3)."""
        track = Track()
        track.add_tile(make_tile("ffffff"))   # cases 0-5 plat
        track.add_tile(make_tile("uuuuuu"))   # cases 6-11 montée
        runner = place(track, make_runner("r"), 2, 0)
        runner.crashed = True
        track.move_runner(runner, 9)  # plafonné à 5 (montée à 6, d=4 <= 5) puis -2
        self.assertEqual(runner.x, 2 + 5 - 2)


class TestRevealAndHistory(unittest.TestCase):
    def test_placement_reveals_start_tile_and_logs(self):
        game = Game(stage="test", player_count=2, auto_place=False, meteo=True)
        # rien de révélé avant placement
        for t in game.track.tiles:
            for c in t.cells:
                self.assertFalse(c.weather_revealed)
        game.auto_place_riders()  # place les 4 coureurs + démarre le tour 1
        start_tile = game.track.tiles[0]
        self.assertTrue(all(c.weather_revealed for c in start_tile.cells))
        # l'historique contient la révélation (entrée du placement, tour 0)
        weather_events = [w for e in game.history for w in e["weather"]]
        self.assertTrue(weather_events)
        self.assertEqual(weather_events[0][0], 0)  # tuile de départ

    def test_movement_reveals_tile(self):
        game = Game(stage="test", player_count=2, meteo=True)
        runner = game.players[0].sprinter
        # téléporter le coureur sur une tuile droite non révélée
        cell = game.track.get_cell(runner.x, runner.y)
        cell.remove_runner(runner.y)
        game.track.get_cell(8, 0).set_runner(runner, 0)  # tuile 1 (cases 6-11)
        self.assertFalse(game.track.tiles[1].cells[0].weather_revealed)
        game._reveal_weather()
        self.assertTrue(game.track.tiles[1].cells[0].weather_revealed)


class TestUiWiring(unittest.TestCase):
    def test_select_stage_passes_meteo_flag(self):
        import main
        ui = main.FlammeRougeGame()  # stage=None -> menu
        self.assertFalse(ui.ext_meteo)
        ui._select_stage("Avenue Corso Paseo")
        self.assertFalse(ui.game.meteo)
        for t in ui.game.track.tiles:
            for c in t.cells:
                self.assertEqual(c.weather, WeatherType.NONE)

        ui2 = main.FlammeRougeGame()
        ui2.ext_meteo = True
        ui2._select_stage("Avenue Corso Paseo")
        self.assertTrue(ui2.game.meteo)
        straights = [t for t in ui2.game.track.tiles if t.turn is None]
        self.assertTrue(straights)
        for t in straights:
            self.assertNotEqual(t.cells[0].weather, WeatherType.NONE)


if __name__ == "__main__":
    unittest.main()
