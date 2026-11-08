"""Tests de l'extension Météo (Flamme Rouge: Meteo) — règles officielles vérifiées en ligne.

Règles officielles (rulebook Meteo, cf. zatu/board-game.co.uk/passionludique) :
- Contenu : 4 panneaux + 13 jetons météo = 9 jetons VIERGES + 4 jetons événement
  (1 vent arrière, 1 vent de face, 1 vent de travers, 1 pluie).
- Mise en place : on mélange les 13 jetons et on en pose un FACE VISIBLE sur
  chaque tuile DROITE du parcours, EN EXCLUANT les tuiles de départ et
  d'arrivée ; les jetons à effet reçoivent un panneau, puis tous les jetons
  sont retirés -> la météo est publique dès le départ.
- Vent de travers (vert) : aucune aspiration donnée ni reçue sur toute la tuile
  (comme une côte, des pavés ou une arrivée).
- Vent arrière (jaune) : le coureur sur la tuile pioche 5 cartes au lieu de 4.
- Vent de face (bleu) : il pioche 3 cartes au lieu de 4.
- Pluie (Wet, noir) : si le coureur TERMINE son mouvement dans une zone humide
  en ayant perdu des cases à cause d'un blocage (case d'arrivée pleine), il
  CHUTE, couché sur la case où il s'est arrêté. Une case entièrement
  accidentée est impassable (on s'arrête une case avant ; si elle est humide,
  nouvelle chute — effet domino). Un coureur couché ne donne ni ne reçoit
  l'aspiration. Pour se relever à son prochain tour, il soustrait 2 à sa carte
  APRÈS les modificateurs (min 5 en descente, plafond 5 en montée) : une carte 2
  en descente vaut 5 normalement, 3 après une chute.

Lancé :  python -m unittest tests.test_meteo -v
"""
import os
import sys
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from game.track import Track, make_tile, WeatherType, WEATHER_TOKENS, CellRunType  # noqa: E402
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


def start_finish_tiles(track):
    return [t for t in track.tiles
            if any(c.run in (CellRunType.START, CellRunType.END) for c in t.cells)]


class TestWeatherAssignment(unittest.TestCase):
    def test_token_bag_official_composition(self):
        """13 jetons : 9 vierges + 1 de chaque événement."""
        self.assertEqual(len(WEATHER_TOKENS), 13)
        self.assertEqual(WEATHER_TOKENS.count(WeatherType.NONE), 9)
        self.assertEqual(WEATHER_TOKENS.count(WeatherType.TAILWIND), 1)
        self.assertEqual(WEATHER_TOKENS.count(WeatherType.HEADWIND), 1)
        self.assertEqual(WEATHER_TOKENS.count(WeatherType.CROSSWIND), 1)
        self.assertEqual(WEATHER_TOKENS.count(WeatherType.RAIN), 1)

    def test_tokens_on_straights_excluding_start_finish_and_face_up(self):
        """Un jeton sur chaque tuile droite SAUF départ/arrivée, face visible
        dès la mise en place (plus de jeton caché « ? »)."""
        game = Game(stage="test", player_count=2, auto_place=False, meteo=True)
        track = game.track
        sf = set(id(t) for t in start_finish_tiles(track))
        n_event_tiles = 0
        for tile in track.tiles:
            for c in tile.cells:
                if tile.turn is None and id(tile) not in sf:
                    self.assertTrue(c.weather_revealed)  # face visible
                else:
                    self.assertEqual(c.weather, WeatherType.NONE)
            if tile.turn is None and id(tile) not in sf and tile.cells[0].weather != WeatherType.NONE:
                n_event_tiles += 1
        self.assertLessEqual(n_event_tiles, 4)  # au plus les 4 jetons événement

        game2 = Game(stage="test", player_count=2, auto_place=False, meteo=False)
        for tile in game2.track.tiles:
            for c in tile.cells:
                self.assertEqual(c.weather, WeatherType.NONE)

    def test_custom_code_start_finish_excluded(self):
        """Code perso 'abcu' : seules les droites b et c portent un jeton."""
        game = Game(custom_code="abcu", player_count=2, auto_place=False, meteo=True)
        track = game.track
        letters = [t.letter for t in track.tiles]
        self.assertEqual(letters, ['a', 'b', 'c', 'u'])
        sf = set(id(t) for t in start_finish_tiles(track))
        for tile in track.tiles:
            for c in tile.cells:
                if id(tile) in sf:
                    self.assertEqual(c.weather, WeatherType.NONE)
                else:
                    self.assertTrue(c.weather_revealed)

    def test_reveal_weather_at_is_idempotent(self):
        track = make_flat_track(2)
        set_tile_weather(track, 0, WeatherType.RAIN, revealed=False)
        self.assertEqual(track.reveal_weather_at(3), WeatherType.RAIN)
        self.assertIsNone(track.reveal_weather_at(4))  # déjà révélé
        self.assertTrue(all(c.weather_revealed for c in track.tiles[0].cells))


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

    def test_crashed_runner_gives_and_receives_no_slipstream(self):
        """Coureur couché : aucune aspiration ni donnée ni reçue."""
        track, giver, rear = self._two_packs()
        giver.crashed = True
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

    def test_crash_when_blocked_and_ending_in_wet_cell(self):
        """Pluie : case d'arrivée pleine -> le coureur se recale derrière MAIS
        comme il termine dans une zone humide en ayant été bloqué, il chute
        sur la case où il s'est arrêté."""
        track, runner = self._full_cell_setup()
        set_tile_weather(track, 2, WeatherType.RAIN)  # tuile 0 (cases 0-5) humide
        reason = track.move_runner(runner, 3)  # arrivée case 5 pleine
        self.assertTrue(runner.crashed)
        self.assertEqual(runner.x, 4)  # couché sur la case d'arrêt (recul d'1)
        self.assertIn("chute", reason)

    def test_no_crash_outside_wet_area(self):
        """Contrôle : même blocage hors zone humide = recul normal, pas de chute."""
        track, runner = self._full_cell_setup()
        track.move_runner(runner, 3)
        self.assertFalse(runner.crashed)
        self.assertEqual(runner.x, 4)

    def test_no_crash_in_wet_area_when_not_blocked(self):
        """Pluie mais case d'arrivée libre : rien ne se passe."""
        track, runner = self._full_cell_setup()
        track.get_cell(5, 0).remove_runner(0)
        track.get_cell(5, 1).remove_runner(1)
        set_tile_weather(track, 2, WeatherType.RAIN)
        track.move_runner(runner, 3)
        self.assertFalse(runner.crashed)
        self.assertEqual(runner.x, 5)

    def test_fully_crashed_cell_is_impassable_domino(self):
        """Case entièrement accidentée : impassable, on s'arrête 1 case avant ;
        si cette case est humide -> nouvelle chute (effet domino)."""
        track = make_flat_track(3)
        b1 = place(track, make_runner("b1"), 5, 0)
        b2 = place(track, make_runner("b2"), 5, 1)
        b1.crashed = b2.crashed = True  # case 5 entièrement accidentée
        runner = place(track, make_runner("r"), 2, 0)
        set_tile_weather(track, 2, WeatherType.RAIN)  # cases 0-5 humides
        reason = track.move_runner(runner, 5)  # viserait la case 7
        self.assertEqual(runner.x, 4)   # stoppé une case avant l'amas (case 5)
        self.assertTrue(runner.crashed)  # case 4 humide + bloqué -> chute
        self.assertIn("chute", reason)

    def test_fully_crashed_cell_blocks_without_crash_outside_wet(self):
        """Case entièrement accidentée hors zone humide : impassable mais
        pas de chute (on s'arrête juste avant)."""
        track = make_flat_track(3)
        b1 = place(track, make_runner("b1"), 5, 0)
        b2 = place(track, make_runner("b2"), 5, 1)
        b1.crashed = b2.crashed = True
        runner = place(track, make_runner("r"), 2, 0)
        track.move_runner(runner, 5)
        self.assertEqual(runner.x, 4)
        self.assertFalse(runner.crashed)

    def test_crashed_runner_gets_up_with_minus_2_after_modifiers(self):
        """Se relever : carte -2 APRÈS modificateurs. Carte 5 -> 3 cases ;
        carte 2 -> se relève sans bouger."""
        track, runner = self._full_cell_setup()
        set_tile_weather(track, 2, WeatherType.RAIN)
        track.move_runner(runner, 3)          # chute en case 4
        self.assertTrue(runner.crashed)
        track.get_cell(5, 0).remove_runner(0)  # case 5 libérée
        track.get_cell(5, 1).remove_runner(1)
        reason = track.move_runner(runner, 5)  # 5 - 2 = 3 cases
        self.assertFalse(runner.crashed)
        self.assertEqual(runner.x, 7)
        self.assertIn("-2", reason)
        runner.crashed = True
        track.move_runner(runner, 2)           # 2 - 2 = 0 : reste sur place
        self.assertFalse(runner.crashed)
        self.assertEqual(runner.x, 7)

    def test_downhill_modifier_then_minus_2(self):
        """Exemple du rulebook : carte 2 en descente = 5 normalement,
        3 après une chute (modificateur d'abord, puis -2)."""
        track = Track()
        track.add_tile(make_tile("ffffff"))  # cases 0-5
        track.add_tile(make_tile("dddddd"))  # cases 6-11 en descente
        runner = place(track, make_runner("r"), 6, 0)
        runner.crashed = True
        track.move_runner(runner, 2)
        self.assertEqual(runner.x, 6 + 5 - 2)  # min 5 (descente) puis -2
        self.assertFalse(runner.crashed)

    def test_mountain_cap_then_minus_2(self):
        """Carte 9 en approche de montée : plafonnée à 5, puis -2 -> 3 cases."""
        track = Track()
        track.add_tile(make_tile("ffffff"))   # cases 0-5 plat
        track.add_tile(make_tile("uuuuuu"))   # cases 6-11 montée
        runner = place(track, make_runner("r"), 2, 0)
        runner.crashed = True
        track.move_runner(runner, 9)  # plafonné à 5 (montée à d=4 <= 5) puis -2
        self.assertEqual(runner.x, 2 + 5 - 2)


class TestSetupLogAndHistory(unittest.TestCase):
    def test_weather_logged_at_setup(self):
        """La météo (face visible dès la mise en place) est loggée dans
        l'historique (entrée de mise en place, tour 0), événements seuls."""
        game = Game(stage="test", player_count=2, auto_place=False, meteo=True)
        self.assertTrue(game.history)
        entry = game.history[0]
        self.assertEqual(entry["turn"], 0)
        names = [w for _x, w in entry["weather"]]
        for w in names:
            self.assertNotEqual(w, "NONE")
        self.assertLessEqual(len(names), 4)
        # les tuiles loggées sont bien des tuiles droites hors départ/arrivée
        sf = set(id(t) for t in start_finish_tiles(game.track))
        for tile_x, _w in entry["weather"]:
            tile = game.track.tiles[game.track.tile_index_at(tile_x)]
            self.assertIsNone(tile.turn)
            self.assertNotIn(id(tile), sf)

    def test_no_weather_log_without_extension(self):
        game = Game(stage="test", player_count=2, auto_place=False, meteo=False)
        self.assertFalse(any(e.get("weather") for e in game.history))


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
        sf = set(id(t) for t in start_finish_tiles(ui2.game.track))
        straights = [t for t in ui2.game.track.tiles if t.turn is None]
        self.assertTrue(straights)
        for t in straights:
            for c in t.cells:
                if id(t) in sf:
                    self.assertEqual(c.weather, WeatherType.NONE)  # départ/arrivée exclues
                else:
                    self.assertTrue(c.weather_revealed)  # face visible dès le départ


class TestWeatherAnimationRaceScreen(unittest.TestCase):
    """Animations météo DANS l'écran de course (et plus sur le profil de
    sélection) : badge animé sur le profil de course + icônes animées sur les
    tuiles droites du parcours."""

    def test_assign_weather_deterministic_with_rng(self):
        import random
        def build():
            t = Track()
            for _ in range(4):
                t.add_tile(make_tile("ffffff"))
            return t
        t1, t2 = build(), build()
        t1.assign_weather(random.Random(42))
        t2.assign_weather(random.Random(42))
        self.assertEqual([c.weather for t in t1.tiles for c in t.cells],
                         [c.weather for t in t2.tiles for c in t.cells])

    def test_weather_badge_renders_pixels(self):
        """Le badge dessine bien quelque chose (soleil/vent/pluie) dans son rect."""
        import main, pygame
        ui = main.FlammeRougeGame()
        ui.screen = pygame.Surface((200, 60))
        for w in (WeatherType.NONE, WeatherType.TAILWIND, WeatherType.HEADWIND,
                  WeatherType.CROSSWIND, WeatherType.RAIN):
            ui.screen.fill((255, 255, 255))
            r = pygame.Rect(80, 10, 24, 24)
            ui._draw_weather_badge(r, [w])
            found = any(ui.screen.get_at((x, y))[:3] != (255, 255, 255)
                        for x in range(r.x, r.right) for y in range(r.y, r.bottom))
            self.assertTrue(found, f"badge {w.name} n'a rien dessiné")

    def test_badge_only_on_race_screen_not_on_selection_profile(self):
        """Le badge météo animé n'est PAS sur le profil de sélection du parcours,
        mais bien sur le profil de l'écran de course."""
        import main, pygame
        ui = main.FlammeRougeGame()
        ui.menu_step = "stage"
        ui.ext_meteo = True
        calls = []
        orig = main.FlammeRougeGame._draw_weather_badge
        ui._draw_weather_badge = lambda *a, **k: calls.append(a) or orig(ui, *a, **k)
        ui.width, ui.height = 1280, 800
        ui.screen = pygame.display.set_mode((1280, 800), pygame.RESIZABLE)
        ui.screen.fill((255, 255, 255))
        ui._draw_header()
        ui._draw_menu()  # écran de SÉLECTION : aucun badge
        self.assertEqual(calls, [])
        # écran de COURSE : le badge est bien là
        ui._select_stage("Avenue Corso Paseo")
        ui.game.auto_place_riders()
        calls.clear()
        ui.screen.fill((255, 255, 255))
        ui._draw_header(); ui._draw_phase_band()
        ui._draw_track(); ui._draw_runners(); ui._draw_ui()
        self.assertTrue(calls, "badge météo absent du profil de course")

    def test_weather_zones_in_profile_block_and_on_track(self):
        """Les animations météo sont dans le BLOC PROFIL de course (légende +
        zone sur toute la longueur de la tuile), et PLUS sur le parcours."""
        import main, pygame
        from game.track import CellRunType
        ui = main.FlammeRougeGame()
        ui.ext_meteo = True
        ui._select_stage("Avenue Corso Paseo")
        ui.game.auto_place_riders()
        game = ui.game
        types = [WeatherType.TAILWIND, WeatherType.HEADWIND,
                 WeatherType.CROSSWIND, WeatherType.RAIN]
        straights = [t for t in game.track.tiles if t.turn is None
                     and not any(c.run in (CellRunType.START, CellRunType.END) for c in t.cells)]
        for tile, w in zip(straights, types):
            for c in tile.cells:
                c.weather = w
        ui.width, ui.height = 1200, 920
        ui.screen = pygame.display.set_mode((1200, 920), pygame.RESIZABLE)
        ui.screen.fill((200, 200, 210))
        ui._draw_header(); ui._draw_phase_band(); ui._draw_track(); ui._draw_runners(); ui._draw_ui()
        colors = {(225, 185, 35), (60, 110, 220), (60, 170, 80), (90, 130, 210)}
        prof = ui._race_profile_rect()
        in_prof = set()
        for y in range(prof.y, prof.bottom):
            for x in range(prof.x, prof.right):
                p = ui.screen.get_at((x, y))[:3]
                if p in colors:
                    in_prof.add(p)
        self.assertEqual(in_prof, colors, f"zones météo manquantes dans le bloc profil: {colors - in_prof}")
        # les icônes sont AUSSI sur le parcours (une par tuile météo)
        frame = ui._frame_rect()
        in_track = set()
        for y in range(frame.y, frame.bottom, 2):
            for x in range(frame.x, frame.right, 2):
                p = ui.screen.get_at((x, y))[:3]
                if p in colors:
                    in_track.add(p)
        self.assertTrue(in_track, "icônes météo absentes du parcours")
        # la zone pluie couvre toute la longueur de sa tuile sur le profil
        rain_tile = straights[3]
        n = game.track.length
        x0 = prof.x + 6 + (prof.w - 12) * rain_tile.x / n
        x1 = prof.x + 6 + (prof.w - 12) * (rain_tile.x + rain_tile.length) / n
        rain_px = [x for x in range(int(x0), int(x1)) for y in range(prof.y, prof.bottom)
                   if ui.screen.get_at((x, y))[:3] in ((90, 130, 210), (60, 100, 190))]
        self.assertGreater(len(rain_px), (x1 - x0) * 0.5, "zone pluie trop courte")
        # couvre bien TOUTE la longueur de la tuile (du début à la fin)
        self.assertLessEqual(min(rain_px), x0 + 6)
        self.assertGreaterEqual(max(rain_px), x1 - 6)

    def test_weather_icons_on_profile_at_tile_positions(self):
        """Les icônes météo animées apparaissent sur le profil de course à
        l'EMPLACEMENT de la tuile qui porte le jeton."""
        import main, pygame
        from game.track import CellRunType
        ui = main.FlammeRougeGame()
        ui.ext_meteo = True
        ui._select_stage("Avenue Corso Paseo")
        ui.game.auto_place_riders()
        track = ui.game.track
        straights = [t for t in track.tiles if t.turn is None
                     and not any(c.run in (CellRunType.START, CellRunType.END) for c in t.cells)]
        target = straights[0]
        for c in target.cells:
            c.weather = WeatherType.RAIN
        tiles_w = ui._game_weather_tiles()
        self.assertIn((target.x, target.length, WeatherType.RAIN), tiles_w)
        ui.width, ui.height = 1200, 920
        ui.screen = pygame.display.set_mode((1200, 920), pygame.RESIZABLE)
        ui.screen.fill((200, 200, 210))
        ui._draw_header(); ui._draw_phase_band()
        ui._draw_track(); ui._draw_runners(); ui._draw_ui()
        r = ui._race_profile_rect()
        rain = sum(1 for x in range(r.x, r.right) for y in range(r.y, r.bottom)
                   if ui.screen.get_at((x, y))[:3] in ((90, 130, 210), (60, 100, 190)))
        self.assertGreater(rain, 0, "icône pluie absente du profil à l'emplacement de la tuile")


    def test_sun_when_no_specific_weather(self):
        """Si aucune tuile n'a de météo spécifique (jetons vierges), un petit
        soleil apparaît : légende 'soleil' dans le bloc profil + icône sur le
        parcours."""
        import main, pygame
        from game.track import CellRunType
        ui = main.FlammeRougeGame()
        ui.ext_meteo = True
        ui._select_stage("Avenue Corso Paseo")
        ui.game.auto_place_riders()
        for t in ui.game.track.tiles:  # tout en NONE (jetons vierges)
            for c in t.cells:
                c.weather = WeatherType.NONE
        tiles_w = ui._game_weather_tiles()
        self.assertTrue(tiles_w)  # toutes les tuiles droites à jeton, en NONE
        self.assertTrue(all(w == WeatherType.NONE for _x, _l, w in tiles_w))
        ui.width, ui.height = 1200, 920
        ui.screen = pygame.display.set_mode((1200, 920), pygame.RESIZABLE)
        ui.screen.fill((200, 200, 210))
        ui._draw_header(); ui._draw_phase_band(); ui._draw_track(); ui._draw_runners(); ui._draw_ui()
        sun = (250, 210, 60)
        prof = ui._race_profile_rect()
        sun_prof = any(ui.screen.get_at((x, y))[:3] == sun
                       for y in range(prof.y, prof.bottom) for x in range(prof.x, prof.right))
        self.assertTrue(sun_prof, "pas de soleil dans le bloc profil")
        frame = ui._frame_rect()
        sun_track = sum(1 for x in range(frame.x, frame.right) for y in range(frame.y, frame.bottom)
                        if ui.screen.get_at((x, y))[:3] == sun)
        self.assertTrue(sun_track > 0, "pas de soleil sur le parcours")
        # UN SEUL soleil par tuile (7 tuiles droites -> ~7 icônes, pas 6 par tuile)
        n_straights = len([t for t in ui.game.track.tiles if t.turn is None
                           and not any(c.run in (CellRunType.START, CellRunType.END) for c in t.cells)])
        self.assertLess(sun_track, n_straights * 200,  # ~130 px/icône soleil, 6x moins que 6 icônes/tuile
                        f"trop de soleils sur le parcours: {sun_track} px pour {n_straights} tuiles")



if __name__ == "__main__":
    unittest.main()
