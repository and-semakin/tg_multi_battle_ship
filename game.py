import itertools
import random
import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, List, Tuple, cast

FIELD_SIZE = 10


class GameError(Exception):
    """Game error."""


class CellState(Enum):
    UNKNOWN = "unknown"
    EMPTY = "empty"
    WOUNDED = "wounded"
    DEAD = "dead"


LETTERS = "абвгдежзик"
POSITION_PATTERN = r"[" + LETTERS + r"]{1}\d{1,2}"


@dataclass
class Player:
    id: str
    name: str = "Nameless"


class Game:
    def __init__(self, size: int = FIELD_SIZE) -> None:
        self.size = size
        self.players: List[Player] = []
        self.fields: Dict[str, List[CellState]] = {}
        self.started: bool = False

    def _init_field(self) -> List[CellState]:
        return [CellState.UNKNOWN for _ in range(self.size ** 2)]

    def start(self, players: List[Player]) -> None:
        if len(players) < 2:
            raise GameError("Need at least two players")

        self.players = players
        random.shuffle(self.players)
        self.__next_iter: Iterable[Tuple[Player, Player]] = cast(
            Iterable[Tuple[Player, Player]],
            itertools.cycle(itertools.permutations(self.players, 2)),
        )

        for player in players:
            self.fields[player.id] = self._init_field()

        self.started = True

    def __iter__(self) -> Iterable[Tuple[Player, Player]]:
        return self

    def __next__(self) -> Tuple[Player, Player]:
        if not self.started:
            raise GameError("Can't iter over not started game")

        self.current_move = next(self.__next_iter)

        return self.current_move

    def _translate_position(self, position: str) -> int:
        position = position.strip().lower()
        if not re.match(POSITION_PATTERN, position):
            raise GameError("Wrong position!")

        letter = position[0]
        number = int(position[1:]) - 1

        if number < 0 or number >= self.size:
            raise GameError("Wrong position!")

        return LETTERS.index(letter) * self.size + number

    def attack(self, victim: Player, position: str, new_state: CellState) -> None:
        if not self.started:
            raise GameError("Can't attack in not started game")

        position = self._translate_position(position)
        self.fields[victim.id][position] = new_state
