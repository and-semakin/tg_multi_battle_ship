import logging
from typing import Union

import telebot
from dotenv import load_dotenv
from more_itertools import chunked
from telebot.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import Config
from game import LETTERS, CellState, GameError, Player
from game_master import GameMaster, GameMasterError

BUTTONS_IN_A_ROW = 5

logger = logging.getLogger(__name__)

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


_position_buffer: str = ""


def _get_game_id(message: Message) -> str:
    return str(message.chat.id)


def _get_sender_player(message: Union[Message, CallbackQuery]) -> Player:
    return Player(str(message.from_user.id), message.from_user.first_name)


def _create_letters_inline_markup() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    buttons = []
    for letter in LETTERS:
        button_text = letter.upper()
        buttons.append(InlineKeyboardButton(button_text, callback_data=button_text))
    for buttons_row in chunked(buttons, BUTTONS_IN_A_ROW):
        markup.row(*buttons_row)
    return markup


def _create_numbers_inline_markup() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    buttons = []
    for number in range(1, 11):
        button_text = str(number)
        buttons.append(InlineKeyboardButton(button_text, callback_data=button_text))
    for buttons_row in chunked(buttons, BUTTONS_IN_A_ROW):
        markup.row(*buttons_row)
    return markup


def _next_move(chat_id: int, game_id: str) -> None:
    game = master.games[game_id]
    attacker, victim, number = game.current_move

    markup = _create_letters_inline_markup()
    if number > 1:
        bot.send_message(
            chat_id,
            f"{attacker.name} ходит на {victim.name} {number} раз...",
            reply_markup=markup,
        )

    else:
        bot.send_message(
            chat_id, f"{attacker.name} ходит на {victim.name}...", reply_markup=markup,
        )


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
            if text != "/skip":
                return False
    else:
        # victim response
        if player != victim:
            return False

        if text not in STATE_ANSWERS:
            return False

    return True


def _check_if_callback_is_valid(call: CallbackQuery) -> bool:
    game_id = _get_game_id(call.message)

    if game_id not in master.games:
        return False

    game = master.games[game_id]
    if not game.started:
        return False

    player = _get_sender_player(call)
    if player not in game.players:
        return False

    attacker, victim, _ = game.current_move
    text = call.data.strip().lower()

    if game_id in master._moves:
        return False

    # attacker request
    if player != attacker:
        return False

    return True


@bot.message_handler(commands=["create"])
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
                "Все, кто хочет участвовать в игре, отправьте команду /join!"
            ),
        )


@bot.message_handler(commands=["join"])
def join_game(message: Message) -> None:
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


@bot.message_handler(commands=["start"])
def start_game(message: Message) -> None:
    game_id = _get_game_id(message)
    try:
        master.start_game(game_id)
    except (GameMasterError, GameError) as e:
        bot.send_message(message.chat.id, str(e))
    else:
        players = [
            f"{i}. {p.name}"
            for i, p in enumerate(master.games[game_id].players, start=1)
        ]
        bot.reply_to(
            message, "Игра началась!",
        )
        bot.send_message(
            message.chat.id, "Порядок игроков будет следующий:\n" + "\n".join(players)
        )
        _next_move(message.chat.id, game_id)


@bot.message_handler(commands=["cancel"])
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
        if text == "/skip":
            master.skip_move(game_id)
            _next_move(message.chat.id, game_id)
        else:
            master.attack_request(game_id, player, victim, text)
            bot.reply_to(
                message, f"Принято, {text.strip().upper()}. Что же там, {victim.name}?"
            )
    else:
        # victim response
        master.attack_response(game_id, player, STATE_ANSWERS[text])
        _next_move(message.chat.id, game_id)


@bot.callback_query_handler(func=_check_if_callback_is_valid)
def callback_handler(call: CallbackQuery) -> None:
    global _position_buffer

    logger.info(call)

    game_id = _get_game_id(call.message)
    player = _get_sender_player(call)
    game = master.games[game_id]

    attacker, victim, _ = game.current_move

    if str(call.data).isnumeric():
        # attack
        _position_buffer += call.data
        bot.edit_message_reply_markup(
            call.message.chat.id, call.message.message_id, reply_markup=None
        )
        master.attack_request(game_id, player, victim, _position_buffer)
        bot.reply_to(
            call.message,
            f"Принято, {_position_buffer.strip().upper()}. Что же там, {victim.name}?",
        )
        _position_buffer = ""
    else:
        # prepare attack
        numbers_markup = _create_numbers_inline_markup()
        _position_buffer += call.data
        bot.edit_message_reply_markup(
            call.message.chat.id, call.message.message_id, reply_markup=numbers_markup
        )


bot.polling()
