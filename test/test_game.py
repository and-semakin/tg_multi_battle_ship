import pytest

from battle_ship import CellState, Game, GameError, Player


class TestGame:
    def test_init_field(self) -> None:
        game = Game(size=3)
        field = game._init_field()
        assert len(field) == 3 ** 2
        assert all(cell == CellState.UNKNOWN for cell in field)

    def test_start_requires_at_least_two_players(self) -> None:
        players = [Player(id="a")]
        with pytest.raises(GameError):
            Game().start(players)

    def test_start(self) -> None:
        players = [Player("a"), Player("b")]
        game = Game()
        game.start(players)

        assert set(game.players) == set(players)
        assert len(game.fields) == len(players)

    def test_iter(self) -> None:
        game = Game()
        game.start([Player("a"), Player("b")])

        player_1 = game.players[0]
        player_2 = game.players[1]

        assert next(game) == (player_1, player_2)
        assert next(game) == (player_2, player_1)
        # and again
        assert next(game) == (player_1, player_2)
        assert next(game) == (player_2, player_1)
        # and again
        assert next(game) == (player_1, player_2)

    def test_iter_three(self) -> None:
        game = Game()
        game.start([Player("a"), Player("b"), Player("c")])

        player_1 = game.players[0]
        player_2 = game.players[1]
        player_3 = game.players[2]

        assert next(game) == (player_1, player_2)
        assert next(game) == (player_1, player_3)
        assert next(game) == (player_2, player_1)
        assert next(game) == (player_2, player_3)
        assert next(game) == (player_3, player_1)
        assert next(game) == (player_3, player_2)
        # and again
        assert next(game) == (player_1, player_2)
        assert next(game) == (player_1, player_3)
        assert next(game) == (player_2, player_1)
        assert next(game) == (player_2, player_3)
        assert next(game) == (player_3, player_1)
        assert next(game) == (player_3, player_2)
        # and again
        assert next(game) == (player_1, player_2)

    @pytest.mark.parametrize("wrong_position", ["а11", "аб1", "ё1", "й1", "а0", "л1"])
    def test_translate_position_raises_on_wrong_position(
        self, wrong_position: str
    ) -> None:
        game = Game(10)
        with pytest.raises(GameError):
            game._translate_position(wrong_position)

    @pytest.mark.parametrize(
        ("position", "expected_index"),
        [
            ("а1", 0),
            ("А1", 0),
            ("а2", 1),
            ("а10", 9),
            ("б1", 10),
            ("в1", 20),
            ("к10", 99),
        ],
    )
    def test_translate_position(self, position: str, expected_index: int) -> None:
        game = Game(10)
        assert game._translate_position(position) == expected_index

    def test_attack(self) -> None:
        game = Game(10)
        player_a = Player("a")
        player_b = Player("b")
        game.start([player_a, player_b])

        game.attack(player_b, "а1", CellState.WOUNDED)
        assert game.fields[player_b.id][0] == CellState.WOUNDED
