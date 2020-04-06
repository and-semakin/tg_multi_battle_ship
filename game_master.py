from typing import Dict, List, Tuple

from game import CellState, Game, Player


class GameMasterError(Exception):
    """Game Master related error."""


class GameMaster:
    def __init__(self) -> None:
        self.games: Dict[str, Game] = {}
        self._moves: Dict[str, Tuple[Player, Player, str]] = {}
        self._players: Dict[str, List[Player]] = {}

    def create_game(self, game_id: str) -> None:
        if game_id in self.games:
            raise GameMasterError("Game already exists")

        self.games[game_id] = Game()

    def cancel_game(self, game_id: str) -> None:
        self.games.pop(game_id, None)
        self._moves.pop(game_id, None)
        self._players.pop(game_id, None)

    def add_player(self, game_id: str, id: str, name: str) -> None:
        if game_id not in self.games:
            raise GameMasterError("Game doesn't exist")

        self._players.setdefault(game_id, []).append(Player(id, name))

    def start_game(self, game_id: str) -> None:
        if game_id not in self.games:
            raise GameMasterError("Game doesn't exist")

        game = self.games[game_id]

        if game.started:
            raise GameMasterError("Game is already started")

        players = self._players.pop(game_id)

        game.start(players)

    def attack_request(
        self, game_id, attacker: Player, victim: Player, position: str
    ) -> None:
        if game_id not in self.games:
            raise GameMasterError("Game doesn't exist")

        game = self.games[game_id]

        if not game.started:
            raise GameMasterError("Game is not started yet")

        if game.current_move != (attacker, victim):
            raise GameMasterError("It's not your turn")

        self._moves[game_id] = (attacker, victim, position)

    def attack_response(
        self, game_id: str, victim: Player, new_state: CellState
    ) -> None:
        if game_id not in self.games:
            raise GameMasterError("Game doesn't exist")

        game = self.games[game_id]

        if not game.started:
            raise GameMasterError("Game is not started yet")

        attacker, expected_victim, position = self._moves[game_id]

        if game.current_move[1] != victim or expected_victim != victim:
            raise GameMasterError("It's not your turn")

        self.games[game_id].attack(victim, position, new_state)
