import telebot
from dotenv import load_dotenv
from telebot.types import Message

from config import Config
from game import CellState, GameError, Player
from game_master import GameMaster, GameMasterError

load_dotenv()

config = Config()

bot = telebot.TeleBot(config.bot_token)

master = GameMaster()

STATE_ANSWERS = {
    "мимо": CellState.EMPTY,
    "пусто": CellState.EMPTY,
    "ранен": CellState.WOUNDED,
    "ранил": CellState.WOUNDED,
    "ранила": CellState.WOUNDED,
    "подбит": CellState.WOUNDED,
    "подбил": CellState.WOUNDED,
    "подбила": CellState.WOUNDED,
    "убит": CellState.WOUNDED,
    "убил": CellState.WOUNDED,
    "убила": CellState.WOUNDED,
}


def _get_game_id(message: Message) -> str:
    return str(message.chat.id)


def _get_sender_player(message: Message) -> Player:
    return Player(str(message.from_user.id), message.from_user.first_name)


def _next_move(chat_id: int, game_id: str) -> None:
    game = master.games[game_id]
    attacker, victim, number = game.current_move
    if number > 1:
        bot.send_message(
            chat_id, f"{attacker.name} ходит на {victim.name} {number} раз..."
        )

    else:
        bot.send_message(chat_id, f"{attacker.name} ходит на {victim.name}...")


def _check_if_message_is_game(message: Message) -> bool:
    if message.content_type != "text":
        return False

    game_id = _get_game_id(message)

    if game_id not in master.games:
        return False

    game = master.games[game_id]
    if not game.started:
        return False

    player = _get_sender_player(message)
    if player not in game.players:
        return False

    attacker, victim, _ = game.current_move
    text = message.text.strip().lower()

    if game_id not in master._moves:
        # attacker request
        if player != attacker:
            return False

        try:
            game._translate_position(text)
        except GameError:
            return False
    else:
        # victim response
        if player != victim:
            return False

        if text not in STATE_ANSWERS:
            return False

    return True


@bot.message_handler(commands=["create_game"])
def create_game(message: Message) -> None:
    game_id = _get_game_id(message)
    try:
        master.create_game(game_id)
    except (GameMasterError, GameError) as e:
        bot.send_message(message.chat.id, str(e))
    else:
        bot.reply_to(
            message,
            (
                "Начинаем играть в морской бой! Теперь рисуйте квадраты и расставляйте корабли! "
                "Все, кто хочет участвовать в игре, отправьте команду /join_game!"
            ),
        )


@bot.message_handler(commands=["join_game"])
def create_game(message: Message) -> None:
    game_id = _get_game_id(message)
    player = _get_sender_player(message)
    try:
        master.add_player(game_id, player)
    except (GameMasterError, GameError) as e:
        bot.send_message(message.chat.id, str(e))
    else:
        bot.reply_to(
            message, f"Добавлен игрок: {player.name}",
        )


@bot.message_handler(commands=["start_game"])
def start_game(message: Message) -> None:
    game_id = _get_game_id(message)
    try:
        master.start_game(game_id)
    except (GameMasterError, GameError) as e:
        bot.send_message(message.chat.id, str(e))
    else:
        players = master.games[game_id].players
        players = [f"{i}. {p.name}" for i, p in enumerate(players, start=1)]
        bot.reply_to(
            message, "Игра началась!",
        )
        bot.send_message(
            message.chat.id, "Порядок игроков будет следующий:\n" + "\n".join(players)
        )
        _next_move(message.chat.id, game_id)


@bot.message_handler(commands=["cancel_game"])
def cancel_game(message: Message) -> None:
    game_id = _get_game_id(message)
    try:
        master.cancel_game(game_id)
    except (GameMasterError, GameError) as e:
        bot.send_message(message.chat.id, str(e))
    else:
        bot.reply_to(
            message, "Ну все, доигрались!",
        )


@bot.message_handler(func=_check_if_message_is_game)
def handle_message(message: Message) -> None:
    game_id = _get_game_id(message)
    player = _get_sender_player(message)
    game = master.games[game_id]

    attacker, victim, _ = game.current_move
    text = message.text.strip().lower()

    if game_id not in master._moves:
        # attacker request
        master.attack_request(game_id, player, victim, text)
        bot.reply_to(
            message, f"Принято, {text.strip().upper()}. Что же там, {victim.name}?"
        )
    else:
        # victim response
        master.attack_response(game_id, player, STATE_ANSWERS[text])
        _next_move(message.chat.id, game_id)


bot.polling()
