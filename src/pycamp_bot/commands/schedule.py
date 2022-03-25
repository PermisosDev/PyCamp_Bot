import logging
import string
import datetime

from telegram.ext import (ConversationHandler, CommandHandler,
                          MessageHandler, Filters)

from pycamp_bot.models import Project, Slot, Pycampista
from pycamp_bot.commands.auth import admin_needed
from pycamp_bot.scheduler.db_to_json import export_db_2_json
from pycamp_bot.scheduler.schedule_calculator import export_scheduled_result


DAY_LETTERS = []

logger = logging.getLogger(__name__)

def _dictToString(dicto):
  if dicto:
    return str(dicto).replace(', ','\r\n').replace('}','\r\n').replace("u'","").replace("'","").replace('[','\r\n').replace(']','\r\n\r\n').replace(': {','\r\n')[1:-1]
  else:
    return "No tengo un cronograma para darte. Pedile a unx admin que haga /cronogramear"

def cancel(bot, update):
    bot.send_message(
        chat_id=update.message.chat_id,
        text="Has cancelado la carga de slots")
    return ConversationHandler.END


@admin_needed
def define_slot_days(bot, update):
    username = update.message.from_user.username
        
    bot.send_message(
        chat_id=update.message.chat_id,
        text="Cuantos dias tiene tu cronograma?"
    )
    return 1


def define_slot_times(bot, update):
    global DAY_LETTERS
    text = update.message.text
    if text not in ["1", "2", "3", "4", "5", "6", "7"]:
        bot.send_message(
            chat_id=update.message.chat_id,
            text="mmm eso no parece un numero de dias razonable, de nuevo?"
        )
        return 1

    DAY_LETTERS = list(string.ascii_uppercase[0:int(text)])

    bot.send_message(
        chat_id=update.message.chat_id,
        text="Cuantos slots tiene  tu dia {}".format(DAY_LETTERS[0])
        )
    return 2


def create_slot(bot, update):
    username = update.message.from_user.username
    chat_id = update.message.chat_id
    text = update.message.text
    times = list(range(int(text)+1))[1:]
    slot_date = datetime.datetime.today()
    slot_date.replace(hour=10, minute=0, second=0)

    while len(times)>0:
        new_slot = Slot(code=str(DAY_LETTERS[0]+str(times[0])))
        new_slot.start = slot_date

        pycampista = Pycampista.get_or_create(username=username, chat_id=chat_id)[0]
        new_slot.current_wizzard = pycampista

        new_slot.save()
        times.pop(0)
        new_slot.replace(start=new_slot.start+datetime.timedelta(hours=1))
    
    DAY_LETTERS.pop(0)
    
    if len(DAY_LETTERS) > 0:
        bot.send_message(
        chat_id=update.message.chat_id,
        text="Cuantos slots tiene tu dia {}".format(DAY_LETTERS[0])
        )
        return 2
    else:
        bot.send_message(
        chat_id=update.message.chat_id,
        text="Genial! Slots Asignados"
        )
        make_schedule(bot, update)
        return ConversationHandler.END


def make_schedule(bot, update):
    bot.send_message(
        chat_id=update.message.chat_id,
        text="Generando el Cronograma..."
        )

    data_json = export_db_2_json()
    my_schedule = export_scheduled_result(data_json)
    
    for relationship in my_schedule:
        slot = Slot.get(Slot.code == relationship[1])
        project = Project.get(Project.name == relationship[0])
        project.slot = slot.id
        project.save()
    
    bot.send_message(
        chat_id=update.message.chat_id,
        text="Cronograma Generado!"
        )

def show_schedule(bot, update):
    slots = Slot.select()
    projects = Project.select()
    cronograma = {}
    for slot in slots:
        cronograma[slot.code] = []
        for project in projects:
            if project.slot_id == slot.id:
                cronograma[slot.code].append(project.name)
    
    bot.send_message(
        chat_id=update.message.chat_id,
        text=_dictToString(cronograma)
        )


@admin_needed
def change_slot(bot, update):
    projects = Project.select()
    slots = Slot.select()
    text = update.message.text.split(' ')

    if not len(text) > 3:
        bot.send_message(
        chat_id=update.message.chat_id,
        text="""El formato de este comando es:
                /cambiar_slot NOMBRE_DEL_PROJECTO NUEVO_SLOT
            ej: /cambiar_slot fades AB
        """
        )
        return

    found = False
    project_name = text[1:-1]
    for project in projects:
        if project.name == project_name:
            for slot in slots:
                if slot.code == text[-1]:
                    found = True
                    project.slot = slot.id
                    project.save()
    if found:
        bot.send_message(
        chat_id=update.message.chat_id,
        text="Exito"
        )
    else:
        bot.send_message(
        chat_id=update.message.chat_id,
        text="O el slot o el nombre del projecto no estan en la db"
        )

load_schedule_handler = ConversationHandler(
    entry_points=[CommandHandler('cronogramear', define_slot_days)],
    states={
        1: [MessageHandler(Filters.text, define_slot_times)],
        2: [MessageHandler(Filters.text, create_slot)]},
    fallbacks=[CommandHandler('cancel', cancel)])

def set_handlers(updater):
    updater.dispatcher.add_handler(CommandHandler('cronograma', show_schedule))
    updater.dispatcher.add_handler(CommandHandler('cambiar_slot', change_slot))
    updater.dispatcher.add_handler(load_schedule_handler)
