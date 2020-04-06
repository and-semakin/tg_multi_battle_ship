import telebot
from dotenv import load_dotenv
from telebot.types import Message

from config import Config
from game import GameError, Player
from game_master import GameMaster, GameMasterError

load_dotenv()

config = Config()

bot = telebot.TeleBot(config.bot_token)

master = GameMaster()


def _get_game_id(message: Message) -> str:
    return str(message.chat.id)


def _get_sender_player(message: Message) -> Player:
    return Player(str(message.from_user.id), message.from_user.first_name)


def _next_move(chat_id: int, game_id: str) -> None:
    game = master.games[game_id]
    attacker, victim = next(game)
    bot.send_message(chat_id, f"{attacker.name} ходит на {victim.name}...")


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


bot.polling()
