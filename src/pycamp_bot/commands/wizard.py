from telegram.ext import CommandHandler

from pycamp_bot.models import Pycampista, Slot
from pycamp_bot.commands.auth import admin_needed
from pycamp_bot.commands.manage_pycamp import active_needed, get_active_pycamp
import random

def become_wizard(bot, update):
    current_wizards = Pycampista.select().where(Pycampista.wizard is True)

    for wizard in current_wizards:
        wizard.current = False
        wizard.save()

    username = update.message.from_user.username
    chat_id = update.message.chat_id

    user = Pycampista.get_or_create(username=username, chat_id=chat_id)[0]
    user.wizard = True
    user.save()

    bot.send_message(
        chat_id=update.message.chat_id,
        text="Felicidades! Eres el Magx de turno"
    )


def summon_wizard(bot, update):
    username = update.message.from_user.username
    try:
        wizard = Pycampista.get(Pycampista.wizard is True)
        bot.send_message(
            chat_id=wizard.chat_id,
            text="PING PING PING MAGX! @{} te necesesita!".format(username)
        )
    except Pycampista.DoesNotExist:
        bot.send_message(
            chat_id=update.chat_id,
            text="Hubo un accidente, el mago esta en otro plano.".format(username)
        )
@admin_needed
@active_needed
def assign_wizards(bot, update):
    shuffle_wizards()
    bot.send_message(
        chat_id=update.message.chat_id,
        text="Los magos han sido asignados."
    )
def shuffle_wizards():
    print("Shuffling wizards")
    candidates = Pycampista.select()
    slots = Slot.select()
    print("Candidates: {}".format(len(candidates)))
    print("Slots: {}".format(len(slots)))
    for slot in slots:
        slot.current_wizzard_id = random.choice(candidates).id
        print(f"Slot Current Wizard: {slot.current_wizzard_id}")
        slot.save()

def set_handlers(updater):
    updater.dispatcher.add_handler(
            CommandHandler('evocar_magx', summon_wizard))
    updater.dispatcher.add_handler(CommandHandler('ser_magx', become_wizard))
    updater.dispatcher.add_handler(CommandHandler('asignar_magos', assign_wizards))
