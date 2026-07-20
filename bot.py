import os
import sys
import time
import django
import threading
from datetime import datetime, timedelta

import telebot
from telebot import types
from telebot.apihelper import ApiTelegramException
from environs import Env
from apscheduler.schedulers.background import BackgroundScheduler

from django.db.models import Q, Count
from django.utils import timezone
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__))
)

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    'beach_ball_club_bot.settings'
)

django.setup()

from user.models import CustomUser  # noqa: E402
from event.models import Event, Reserve, Member  # noqa: E402

user_state = {}
user_data = {}
edit_state = {}
edit_data = {}


env = Env()
env.read_env()
group_id=-5244172242 #-5244172242 test group
bot = telebot.TeleBot(env.str("TG_TOKEN"))
scheduler = BackgroundScheduler()
days = ['Понедельник', 'Вторник', 'Среда', 'Четверг',
            'Пятница', 'Суббота', 'Воскресенье']
def menu(message):
    """Отображение главного меню с кнопками навигации.

    Показывает опции для просмотра тренировок, присоединения к ним,
    и панель администратора для персонала и суперпользователей.

    Args:
        message: объект сообщения Telegram с информацией о чате
    """
    markup = types.InlineKeyboardMarkup()
    registered_btn = types.InlineKeyboardButton(text="Мои тренировки", callback_data="my_events")
    register_btn = types.InlineKeyboardButton(text="Присоединиться", callback_data="event")
    user = CustomUser.objects.get(tg_id=message.chat.id)

    markup.row(registered_btn)
    markup.row(register_btn)
    if user.is_staff or user.is_superuser:
        admin_btn = types.InlineKeyboardButton(text="Панель администратора", callback_data="admin")
        markup.row(admin_btn)
    bot.send_message(message.chat.id, "Выберите опцию:", reply_markup=markup)


def create_user(message):
    if message.chat.id == group_id:
        return
    if CustomUser.objects.filter(tg_id=message.from_user.id).exists():
        pass
    else:
        bot.send_message(message.chat.id, """ПРАВИЛА ОПЛАТЫ:

        ‼️Разовая тренировка оплачивается заранее.
        ‼️При отмене брони с вашей стороны менее, чем за сутки, вычитается/оплачивается полная стоимость тренировки.


        Тренировка состоится при наборе от 4х человек""")
    markup = types.InlineKeyboardMarkup()

    CustomUser.objects.update_or_create(tg_id=message.chat.id,defaults={
		"first_name":message.chat.first_name if message.chat.first_name else message.chat.username,
		"tg_id":message.chat.id,

	})
    user = CustomUser.objects.get(tg_id=message.chat.id)
    bot.send_message(message.chat.id, f"Вы вошли как {user.first_name}", reply_markup=markup)
    menu(message)

def start_adding_event(tg_id):
    user_id = tg_id
    user_state[user_id] = "measure"
    user_data[user_id] = {}
    bot.send_message(user_id, text="Введите название тренировки:")

def start_editing_event(tg_id,state,event_id):
    user_id = tg_id
    edit_state[user_id] = state
    edit_data[user_id] = {}
    edit_data[user_id]["event_id"] = event_id
    bot.send_message(user_id, text="Введите название тренировки:")

@bot.message_handler(func=lambda msg: msg.chat.id in edit_state, content_types=['photo', 'text'])
def handle_edit_steps(message):
    """Обработка шагов редактирования тренировки.

    Обрабатывает ввод названия и других параметров для редактирования.

    Args:
        message: сообщение Telegram с текстом или фото
    """
    user_id = message.chat.id
    state = edit_state.get(user_id)
    markup = types.InlineKeyboardMarkup()
    if state == "measure":
        edit_data[user_id]["measure"] = message.text.strip()
        confirm_btn = types.InlineKeyboardButton(text="Подтвердить", callback_data="finish_edit|measure")
        cancel_btn = types.InlineKeyboardButton(text="Отменить", callback_data="admin")
        markup.row(confirm_btn)
        markup.row(cancel_btn)
        bot.send_message(user_id, text="Выберите:",reply_markup=markup)
    elif state == "place":
        edit_data[user_id]["place"] = message.text.strip()
        confirm_btn = types.InlineKeyboardButton(text="Подтвердить", callback_data="finish_edit|place")
        cancel_btn = types.InlineKeyboardButton(text="Отменить", callback_data="admin")
        markup.row(confirm_btn)
        markup.row(cancel_btn)
        bot.send_message(user_id, text="Выберите:", reply_markup=markup)
    elif state == "link":
        validate = URLValidator()

        url = message.text.strip()

        try:
            validate(url)
            edit_data[user_id]["link"] = message.text.strip()
            confirm_btn = types.InlineKeyboardButton(text="Подтвердить", callback_data="finish_edit|link")
            cancel_btn = types.InlineKeyboardButton(text="Отменить", callback_data="admin")
            markup.row(confirm_btn)
            markup.row(cancel_btn)
            bot.send_message(user_id, text="Выберите:", reply_markup=markup)
        except ValidationError:
            bot.send_message(user_id, text="Это не ссылка. Вставьте ссылку:")
            edit_state[user_id] = "link"
    elif state == "max_member":
        edit_data[user_id]["max_member"] = message.text.strip()
        confirm_btn = types.InlineKeyboardButton(text="Подтвердить", callback_data="finish_edit|max_member")
        cancel_btn = types.InlineKeyboardButton(text="Отменить", callback_data="admin")
        markup.row(confirm_btn)
        markup.row(cancel_btn)
        bot.send_message(user_id, text="Выберите:", reply_markup=markup)
    elif state == "date":
        edit_data[user_id]["date"] = message.text.strip()
        edit_state[user_id] = "time"
        bot.send_message(user_id, text="Напишите время(08:30):")
    elif state == "time":
        edit_data[user_id]["time"] = message.text.strip()
        info = edit_data[user_id]
        date = info["date"].split("/")
        event_time = info["time"].split(":")
        edit_data[user_id]["date"] = timezone.make_aware(
            datetime(int(date[2]), int(date[1]), int(date[0]), int(event_time[0]), int(event_time[1])))
        confirm_btn = types.InlineKeyboardButton(text="Подтвердить", callback_data="finish_edit|date")
        cancel_btn = types.InlineKeyboardButton(text="Отменить", callback_data="admin")
        markup.row(confirm_btn)
        markup.row(cancel_btn)
        bot.send_message(user_id, text="Выберите:", reply_markup=markup)
    del edit_state[user_id]


@bot.message_handler(func=lambda msg: msg.chat.id in user_state, content_types=['photo', 'text'])
def handle_event_steps(message):
    """Обработка шагов создания тренировки.

    Обрабатывает ввод названия и фото для новых тренировок.

    Args:
        message: сообщение Telegram с текстом или фото
    """
    user_id = message.chat.id
    state = user_state.get(user_id)

    if state == "measure":
        user_data[user_id]["measure"] = message.text.strip()
        user_state[user_id] = "place"
        bot.send_message(user_id, text="Напишите название места:")
    elif state == "place":
        user_data[user_id]["place"] = message.text.strip()
        user_state[user_id] = "link"
        bot.send_message(user_id, text="Вставьте ссылку на место:")
    elif state == "link":
        validate = URLValidator()

        url = message.text.strip()

        try:
            validate(url)
            user_data[user_id]["link"] = message.text.strip()
            user_state[user_id] = "max_member"
            bot.send_message(user_id, text="Напишите максимальное количество участников(4):")
        except ValidationError:
            bot.send_message(user_id, text="Это не ссылка. Вставьте ссылку:")
            user_state[user_id] = "link"
    elif state == "max_member":
        if int(message.text.strip()) < 4:
            bot.send_message(user_id, text="Максимум участников не может быть менее 4:")
            user_state[user_id] = "max_member"
        else:
            user_data[user_id]["max_member"] = message.text.strip()
            user_state[user_id] = "photo"
            bot.send_message(user_id, text="Прикрепите картинку:")
    elif state == "photo":
        if message.content_type == "photo":
            file_path = bot.get_file(message.photo[-1].file_id).file_path
            file = bot.download_file(file_path)
            with open(f"media/events/{message.photo[-1].file_unique_id}.png", "wb") as code:
                user_data[user_id]["photo"] = f"events/{message.photo[-1].file_unique_id}.png"
                code.write(file)
            user_state[user_id] = "date"
            bot.send_message(user_id, text="Напишите дату(21/12/2026)")
        else:
            bot.send_message(user_id, text="Это не картинка! Прикрепите картинку:")

    elif state == "date":
        user_data[user_id]["date"] = message.text.strip()
        user_state[user_id] = "time"
        bot.send_message(user_id, text="Напишите время(08:30):")
    elif state == "time":
        user_data[user_id]["time"] = message.text.strip()
        del user_state[user_id]
        markup = types.InlineKeyboardMarkup()
        for trainer in CustomUser.objects.filter(is_trainer=True):
            btn = types.InlineKeyboardButton(text=f"{trainer.first_name}", callback_data=f"trainer|{trainer.id}")
            markup.row(btn)
        bot.send_message(user_id, text="Выберите тренера:", reply_markup=markup)
def add_0(date):
    return f"0{date}" if len(str(date)) == 1 else date

def info_text(event):
    members_list = Member.objects.filter(event=event).order_by('pos')
    members = "\n".join([f"{m.pos}. {m.member.first_name}" for m in members_list])
    reserved_list = Reserve.objects.filter(event=event).order_by('pos')
    reserved_users = "\n".join([f"{r.pos}. {r.reserve.first_name}" for r in reserved_list])
    if event.members.count() == 0:
        return f"{event.measure}\n\n📆Дата {add_0(event.date.day)}/{add_0(event.date.month)}/{event.date.year} {days[event.date.weekday()]}\n⏳Время {add_0(event.date.hour)}:{add_0(event.date.minute)}\n📊 Уровень:{event.get_level_display()}\n📍Локация <a href='{event.link}'>{event.place}</a>\n👨‍🏫 Тренер:{event.trainer.first_name}\n\n👥 Участники({event.members.count() + event.reserve.count()}/{event.max_member})\nПока никто не записался\n\n💬 По вопросам стоимости, тренировочного уровня и другим обращаться в лс @allo_litvinova"

    elif event.max_member > event.members.count():
        return f"{event.measure}\n\n📆Дата {add_0(event.date.day)}/{add_0(event.date.month)}/{event.date.year} {days[event.date.weekday()]}\n⏳Время {add_0(event.date.hour)}:{add_0(event.date.minute)}\n📊 Уровень:{event.get_level_display()}\n📍Локация <a href='{event.link}'>{event.place}</a>\n👨‍🏫 Тренер:{event.trainer.first_name}\n\n👥 Участники({event.members.count() + event.reserve.count()}/{event.max_member})\n{members}\n\n💬 По вопросам стоимости, тренировочного уровня и другим обращаться в лс @allo_litvinova"

    elif event.max_member == event.members.count() + event.reserve.count():
        return f"{event.measure}\n\n📆Дата {add_0(event.date.day)}/{add_0(event.date.month)}/{event.date.year} {days[event.date.weekday()]}\n⏳Время {add_0(event.date.hour)}:{add_0(event.date.minute)}\n📊 Уровень:{event.get_level_display()}\n📍Локация <a href='{event.link}'>{event.place}</a>\n👨‍🏫 Тренер:{event.trainer.first_name}\n\n👥 Участники({event.members.count() + event.reserve.count()}/{event.max_member})\n{members}\n\n**🔒 Набор закрыт!**\n\n💬 По вопросам стоимости, тренировочного уровня и другим обращаться в лс @allo_litvinova"

    else:
        return f"{event.measure}\n\n📆Дата {add_0(event.date.day)}/{add_0(event.date.month)}/{event.date.year} {days[event.date.weekday()]}\n⏳Время {add_0(event.date.hour)}:{add_0(event.date.minute)}\n📊 Уровень:{event.get_level_display()}\n📍Локация <a href='{event.link}'>{event.place}</a>\n👨‍🏫 Тренер:{event.trainer.first_name}\n\n👥 Участники({event.members.count() + event.reserve.count()}/{event.max_member})\n{members}\n\n**🔒 Набор закрыт!**\n\n📋 Резерв (если вы в резерве — приходить не нужно):\n{reserved_users} \n\n💬 По вопросам стоимости, тренировочного уровня и другим обращаться в лс @allo_litvinova"

def delete_event(event):
    """Delete an event and its Telegram message safely."""
    if hasattr(event, 'message_id') and event.message_id:
        try:
            bot.delete_message(group_id, event.message_id)
        except ApiTelegramException as e:
            if "message to delete not found" not in str(e).lower():
                bot.send_message(380869029, text=f"Ошибка удаления сообщения события: {e}")
    event.delete()


def send_event_message(event_id,status):
    markup = types.InlineKeyboardMarkup()
    event = Event.objects.get(id=event_id)
    leave_btn = types.InlineKeyboardButton(text="Выйти", callback_data=f"leave|{event.id}")
    if event.members.count() < event.max_member:
        btn = types.InlineKeyboardButton(text="Присоединиться", callback_data=f"join|join|{event.id}")
    elif event.members.count() >= event.max_member:
        btn = types.InlineKeyboardButton(text="Резерв", callback_data=f"join|reserve|{event.id}")
    markup.add(btn, leave_btn)
    if status == "old":
        try:
            if event.message_id:
                bot.delete_message(group_id, event.message_id)
        except ApiTelegramException:
            bot.send_message(380869029, text="Обнаружена ошибка. Обратитесь к разработчику! @chipsinkayt")
    elif status == "delete":
        delete_event(event)
        return
    if event:
        message = bot.send_photo(group_id,photo=event.photo, caption=info_text(event), reply_markup=markup,parse_mode="HTML")
        event.message_id = message.message_id
        event.save()


def send_daily_training():
    for event in Event.objects.all():
        send_event_message(event.id,"old")

scheduler.add_job(
    send_daily_training,
    "cron",
    hour=12,
    minute=0
)

def start_scheduler():
    scheduler.start()

threading.Thread(target=start_scheduler).start()

def delete_expired_events():
    while True:
        try:
            expired_events=Event.objects.filter(
                date__lte=timezone.now()
            )
            no_member_events=Event.objects.annotate(
                member_count=Count('members')
            ).filter(
                date__lte=timezone.now()+timedelta(days=1),
                member_count__lt=4
            )
            for event in expired_events:
                try:
                    for member in event.members.all():
                        if member.tg_id:
                            bot.send_message(member.tg_id, f"{event.measure} отменена")
                    for reserve in event.reserve.all():
                        if reserve.tg_id:
                            bot.send_message(reserve.tg_id, f"{event.measure} отменена")
                    Member.objects.filter(event=event).delete()
                    Reserve.objects.filter(event=event).delete()
                    delete_event(event)
                except Exception as e:
                    print(f"Error processing expired event {event.id}: {e}")
            
            for event in no_member_events:
                try:
                    for member in event.members.all():
                        if member.tg_id:
                            bot.send_message(member.tg_id, f"{event.measure} отменена - недостаточно участников")
                    Member.objects.filter(event=event).delete()
                    Reserve.objects.filter(event=event).delete()
                    delete_event(event)
                except Exception as e:
                    print(f"Error processing no-member event {event.id}: {e}")
        except Exception as e:
            print(f"Error in delete_expired_events: {e}")
        time.sleep(60)

threading.Thread(
    target=delete_expired_events,
    daemon=True
).start()

@bot.message_handler(commands=['start'])
def start(message):
    create_user(message)


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "admin":
        markup = types.InlineKeyboardMarkup()
        add_event_btn = types.InlineKeyboardButton(text="Добавить тренировку", callback_data="add_event")
        edit_event_btn = types.InlineKeyboardButton(text="Редактировать тренировку", callback_data="select_event|edit_event")
        cancel_event_btn = types.InlineKeyboardButton(text="Отменить тренировку", callback_data="select_event|cancel_event")
        reload_event_btn = types.InlineKeyboardButton(text="Перепост всех тренировок", callback_data="reload_events")
        back_btn = types.InlineKeyboardButton(text="Назад", callback_data="menu")
        markup.row(add_event_btn)
        markup.row(edit_event_btn)
        markup.row(cancel_event_btn)
        markup.row(reload_event_btn)
        markup.row(back_btn)
        bot.send_message(call.from_user.id, "Привет!!!", reply_markup=markup)
    if call.data == "event":
        markup = types.InlineKeyboardMarkup()
        user=CustomUser.objects.get(tg_id=call.from_user.id)
        for event in Event.objects.exclude(Q(members=user)|Q(reserve=user)):
            if event.members.count() < event.max_member:
                btn = types.InlineKeyboardButton(text=f"Информация Дата&Время:📆Дата {add_0(event.date.day)}/{add_0(event.date.month)}/{event.date.year} {days[event.date.weekday()]}\n⏳Время {add_0(event.date.hour)}:{add_0(event.date.minute)} ({event.members.count()+event.reserve.count()}/{event.max_member})", callback_data=f"info|join|{event.id}")
            else:
                btn = types.InlineKeyboardButton(
                    text=f"Информация Дата&Время: 📆Дата {add_0(event.date.day)}/{add_0(event.date.month)}/{event.date.year} {days[event.date.weekday()]}\n⏳Время {add_0(event.date.hour)}:{add_0(event.date.minute)} Участники: ({event.members.count()+event.reserve.count()}/{event.max_member})",
                    callback_data=f"info|reserve|{event.id}")
            markup.row(btn)
        back_btn = types.InlineKeyboardButton(text="Назад",callback_data="menu")
        markup.row(back_btn)
        bot.send_message(call.from_user.id, "Выберите опцию:", reply_markup=markup)
    if call.data == "menu":
        menu(call.message)
    if call.data.split("|")[0] == "join":
        if CustomUser.objects.filter(tg_id=call.from_user.id).exists():
            markup = types.InlineKeyboardMarkup()
            user=CustomUser.objects.get(tg_id=call.from_user.id)
            event=Event.objects.get(id=call.data.split("|")[2])

            if not event.members.filter(id=user.id).exists() and not event.reserve.filter(id=user.id).exists():
                back_btn = types.InlineKeyboardButton(text="Назад", callback_data="menu")
                markup.row(back_btn)
                if call.data.split("|")[1] == "reserve":
                    Reserve.objects.create(event=event,reserve=user,pos=event.reserve.count()+1)
                    event.reserve.add(user)
                    bot.send_message(call.from_user.id, f"В РЕЗЕРВЕ\nНа {event.measure}\n📆Дата: {add_0(event.date.day)}/{add_0(event.date.month)}/{event.date.year} {days[event.date.weekday()]}\n⏳Время {add_0(event.date.hour)}:{add_0(event.date.minute)}\n📍Локация: <a href='{event.link}'>{event.place}</a>\n👨‍🎓Тренер: {event.trainer.first_name}\nВы записаны в ‼️РЕЗЕРВ‼️\nпри освобождении места на тренировку, Вы автоматически будете добавлены на неё, при этом Вам придёт об этом оповещение 🚨 ", reply_markup=markup,parse_mode="HTML")
                else:
                    Member.objects.create(event=event,member=user,pos=event.members.count()+1)
                    event.members.add(user)
                    bot.send_message(call.from_user.id, f"Вы записаны на {event.measure}\n📆Дата: {add_0(event.date.day)}/{add_0(event.date.month)}/{event.date.year} {days[event.date.weekday()]}\n⏳Время {add_0(event.date.hour)}:{add_0(event.date.minute)}\n📍Локация: <a href='{event.link}'>{event.place}</a>\n👨‍🎓Тренер: {event.trainer.first_name}\nНе забудьте с собой форму, головной убор и питьевую воду‼️\nДо встречи на корте 🙌", reply_markup=markup,parse_mode="HTML")
                send_event_message(event.id,"old")
            else:
                message = bot.send_message(group_id, f"Вы уже записаны на {event.measure}", reply_markup=markup)
                time.sleep(10)
                bot.delete_message(group_id, message.message_id)
        else:
            message = bot.send_message(group_id, "Вы не зарегистрированы, перейдите к:@beach_ball_club_bot")
            time.sleep(10)
            bot.delete_message(group_id, message.message_id)
    if call.data == "my_events":
        markup = types.InlineKeyboardMarkup()
        user = CustomUser.objects.get(tg_id=call.from_user.id)
        reserved_events = Event.objects.filter(reserve=user)
        events = Event.objects.filter(members=user)
        for event in events:
            btn = types.InlineKeyboardButton(text=f"Выйти Дата&Время:📆Дата {add_0(event.date.day)}/{add_0(event.date.month)}/{event.date.year} {days[event.date.weekday()]}\n⏳Время {add_0(event.date.hour)}:{add_0(event.date.minute)} ({event.members.count()+event.reserve.count()}/{event.max_member})", callback_data=f"info|leave|{event.id}")
            markup.row(btn)
        for event in reserved_events:
            btn = types.InlineKeyboardButton(text=f"Отменить резерв Дата&Время:📆Дата {add_0(event.date.day)}/{add_0(event.date.month)}/{event.date.year} {days[event.date.weekday()]}\n⏳Время {add_0(event.date.hour)}:{add_0(event.date.minute)} ({event.members.count()+event.reserve.count()}/{event.max_member})", callback_data=f"info|leave|{event.id}")
            markup.row(btn)
        back_btn = types.InlineKeyboardButton(text="Назад", callback_data="menu")
        markup.row(back_btn)
        bot.send_message(call.from_user.id, "Вот ваши тренировки:", reply_markup=markup)
    if call.data.split("|")[0] == "info":
        markup = types.InlineKeyboardMarkup()
        event=Event.objects.get(id=call.data.split("|")[2])
        if call.data.split("|")[1] == "join":
            btn = types.InlineKeyboardButton(text="Присоединиться",callback_data=f"join|join|{event.id}")
            markup.row(btn)
        elif call.data.split("|")[1] == "reserve":
            btn = types.InlineKeyboardButton(text="Резерв",callback_data=f"join|reserve|{event.id}")
            markup.row(btn)
        else:
            btn = types.InlineKeyboardButton(text="Выйти", callback_data=f"leave|{event.id}")
            markup.row(btn)
        back_btn = types.InlineKeyboardButton(text="Назад", callback_data="my_events")
        markup.row(back_btn)
        bot.send_message(call.from_user.id, info_text(event), reply_markup=markup,parse_mode="HTML")
    if call.data.split("|")[0] == "leave":
        markup = types.InlineKeyboardMarkup()
        event = Event.objects.get(id=call.data.split("|")[1])
        user = CustomUser.objects.get(tg_id=call.from_user.id)
        back_btn = types.InlineKeyboardButton(text="Назад", callback_data="my_events")
        markup.row(back_btn)
        if event.members.filter(id=user.id).exists() or event.reserve.filter(id=user.id).exists():
            if event.members.filter(id=user.id).exists():
                # Remove member and delete Member record
                user_member = Member.objects.get(event=event, member=user)
                other_members = Member.objects.filter(event=event, pos__gt=user_member.pos)
                user_member.delete()
                event.members.remove(user)
                # Update positions of remaining members
                for member in other_members:
                    member.pos -= 1
                    member.save()

                try:
                    reserve_1 = Reserve.objects.get(event=event,pos=1)
                    Member.objects.create(event=event, member=reserve_1.reserve, pos=event.members.count()+1)
                    event.members.add(reserve_1.reserve)
                    event.reserve.remove(reserve_1.reserve)
                    bot.send_message(reserve_1.reserve.tg_id, f"«Вы добавлены в основу на {event.measure}\n📆Дата: {add_0(event.date.day)}/{add_0(event.date.month)}/{event.date.year} {days[event.date.weekday()]}\n⏳Время {add_0(event.date.hour)}:{add_0(event.date.minute)}\n📍Локация: <a href='{event.link}'>{event.place}</a>\n👨‍🎓Тренер: {event.trainer.first_name}\nНе забудьте с собой форму, головной убор и питьевую воду‼️\nДо встречи на корте 🙌",parse_mode="HTML")
                    reserve_1.delete()
                    for reserved in Reserve.objects.filter(event=event):
                        reserved.pos -= 1
                        reserved.save()
                except Reserve.DoesNotExist:
                    pass
                bot.send_message(call.from_user.id, f"Вы выписаны с {event.measure}\n📆Дата: {add_0(event.date.day)}/{add_0(event.date.month)}/{event.date.year} {days[event.date.weekday()]}\n⏳Время {add_0(event.date.hour)}:{add_0(event.date.minute)}\n📍Локация: <a href='{event.link}'>{event.place}</a>\n👨‍🎓Тренер: {event.trainer.first_name}\nБудем рады видеть Вас на следующей тренировке", reply_markup=markup,parse_mode="HTML")
            else:
                user_reserve=Reserve.objects.get(event=event,reserve=user)
                other_reserves=Reserve.objects.filter(event=event,pos__gt=user_reserve.pos)
                user_reserve.delete()
                event.reserve.remove(user)
                for reserve in other_reserves:
                    reserve.pos -= 1
                    reserve.save()
                bot.send_message(call.from_user.id, f"Вы отменили свой резерв с {event.measure}", reply_markup=markup)
            send_event_message(event.id,"old")
        else:
            message = bot.send_message(group_id, "Вы не записаны на эту тренировку")
            time.sleep(10)
            bot.delete_message(group_id, message.message_id)
    if call.data.split("|")[0] == "select_event":
        markup = types.InlineKeyboardMarkup()
        for event in Event.objects.all():
            if call.data.split("|")[1] == "edit_event":
                btn = types.InlineKeyboardButton(text=f"Редактировать Дата&Время:📆Дата {add_0(event.date.day)}/{add_0(event.date.month)}/{event.date.year} {days[event.date.weekday()]}\n⏳Время {add_0(event.date.hour)}:{add_0(event.date.minute)} ({event.members.count()+event.reserve.count()}/{event.max_member})", callback_data=f"{call.data.split("|")[1]}|{event.id}")
            elif call.data.split("|")[1] == "cancel_event":
                btn = types.InlineKeyboardButton(
                    text=f"Удалить Дата&Время:📆Дата {add_0(event.date.day)}/{add_0(event.date.month)}/{event.date.year} {days[event.date.weekday()]}\n⏳Время {add_0(event.date.hour)}:{add_0(event.date.minute)} ({event.members.count() + event.reserve.count()}/{event.max_member})",
                    callback_data=f"{call.data.split("|")[1]}|{event.id}")
            markup.row(btn)
        back_btn = types.InlineKeyboardButton(text="Назад", callback_data="admin")
        markup.row(back_btn)
        bot.send_message(call.from_user.id, "Вы хотите отредактировать тренировку:", reply_markup=markup) #TODO
    if call.data.split("|")[0] == "edit_event":
        markup = types.InlineKeyboardMarkup()
        measure_btn = types.InlineKeyboardButton(text="Редактировать название",callback_data=f"start_edit|measure|{call.data.split("|")[1]}")
        date_btn = types.InlineKeyboardButton(text="Редактировать дату",callback_data=f"start_edit|date|{call.data.split("|")[1]}")
        level_btn = types.InlineKeyboardButton(text="Редактировать уровень",callback_data=f"edit_level|{call.data.split("|")[1]}")
        place_btn = types.InlineKeyboardButton(text="Редактировать место",callback_data=f"start_edit|place|{call.data.split("|")[1]}")
        trainer_btn = types.InlineKeyboardButton(text="Редактировать тренера",callback_data=f"edit_trainer|{call.data.split("|")[1]}")
        link_btn = types.InlineKeyboardButton(text="Редактировать ссылку",callback_data=f"start_edit|link|{call.data.split("|")[1]}")
        max_member_btn = types.InlineKeyboardButton(text="Редактировать максимум участников", callback_data=f"start_edit|max_member|{call.data.split("|")[1]}")
        markup.row(measure_btn)
        markup.row(date_btn)
        markup.row(level_btn)
        markup.row(place_btn)
        markup.row(trainer_btn)
        markup.row(link_btn)
        markup.row(max_member_btn)
        back_btn = types.InlineKeyboardButton(text="Назад", callback_data="admin")
        markup.row(back_btn)
        bot.send_message(call.from_user.id, "Выберите:", reply_markup=markup)
    if call.data.split("|")[0] == "edit_level":
        markup = types.InlineKeyboardMarkup()
        event = Event.objects.get(id=call.data.split("|")[1])
        for level in event.StatusChoice.labels:
            btn = types.InlineKeyboardButton(text=level,callback_data=f"finish_level|{level}|{event.id}")
            markup.row(btn)
        back_btn = types.InlineKeyboardButton(text="Назад", callback_data="admin")
        markup.row(back_btn)
        bot.send_message(call.from_user.id, "Выберите:", reply_markup=markup)
    if call.data.split("|")[0] == "finish_level":
        markup = types.InlineKeyboardMarkup()
        event = Event.objects.get(id=call.data.split("|")[2])
        event.level = next((s for s in event.StatusChoice if s.label == call.data.split("|")[1]), None)
        event.save()
        back_btn = types.InlineKeyboardButton(text="Назад", callback_data="admin")
        markup.row(back_btn)
        bot.send_message(call.from_user.id, "редактирование завершено:", reply_markup=markup)
        bot.delete_message(group_id, event.message_id)
        send_event_message(event.id,"old")
    if call.data.split("|")[0] == "edit_trainer":
        markup = types.InlineKeyboardMarkup()
        for trainer in CustomUser.objects.filter(is_trainer=True):
            btn = types.InlineKeyboardButton(text=trainer.first_name, callback_data=f"finish_trainer|{trainer.id}|{call.data.split("|")[1]}")
            markup.row(btn)
        back_btn = types.InlineKeyboardButton(text="Назад", callback_data="admin")
        markup.row(back_btn)
        bot.send_message(call.from_user.id, "Выберите:", reply_markup=markup)
    if call.data.split("|")[0] == "finish_trainer":
        markup = types.InlineKeyboardMarkup()
        event = Event.objects.get(id=call.data.split("|")[2])
        user= CustomUser.objects.get(id=call.data.split("|")[1])
        event.trainer = user
        event.save()
        back_btn = types.InlineKeyboardButton(text="Назад", callback_data="admin")
        markup.row(back_btn)
        bot.send_message(call.from_user.id, "редактирование завершено:", reply_markup=markup)
        bot.delete_message(group_id, event.message_id)
        send_event_message(event.id,"old")
    if call.data.split("|")[0] == "cancel_event":
        markup = types.InlineKeyboardMarkup()
        event = Event.objects.get(id=call.data.split("|")[1])
        if event.members.exists():
            for member in event.members.all():
                if member.tg_id:
                    bot.send_message(member.tg_id, f"{event.measure} \n📆Дата {add_0(event.date.day)}/{add_0(event.date.month)}/{event.date.year} {days[event.date.weekday()]}\n⏳Время {add_0(event.date.hour)}:{add_0(event.date.minute)} отменена:")
            if event.reserve.exists():
                for reserve in event.reserve.all():
                    if reserve.tg_id:
                        Reserve.objects.get(event=event,reserve=reserve).delete()
                        bot.send_message(reserve.tg_id, f"Тренировка [{event.date.day}/{event.date.month}/{event.date.year}, {event.date.hour}:{event.date.minute}, <a href='{event.link}'>{event.place}</a>] у тренера [{event.trainer.first_name}] ОТМЕНЕНА‼️\nПриносим свои извинения",parse_mode="HTML")
        Member.objects.filter(event=event).delete()
        Reserve.objects.filter(event=event).delete()
        bot.send_message(group_id, f"{event.measure} \n📆Дата {add_0(event.date.day)}/{add_0(event.date.month)}/{event.date.year} {days[event.date.weekday()]}\n⏳Время {add_0(event.date.hour)}:{add_0(event.date.minute)} отменена:")
        delete_event(event)
        back_btn = types.InlineKeyboardButton(text="Назад", callback_data="admin")
        markup.row(back_btn)
        bot.send_message(call.from_user.id, "удаление завершено:", reply_markup=markup)
    if call.data == "add_event":
        start_adding_event(call.from_user.id)
    if call.data.split("|")[0] == "trainer":
        user_id = call.from_user.id
        user_data[user_id]["trainer"] = call.data.split("|")[1]
        markup = types.InlineKeyboardMarkup()
        for level in Event.StatusChoice.labels:
            btn = types.InlineKeyboardButton(text=f"{level}", callback_data=f"finish_add_event|{level}")
            markup.row(btn)
        bot.send_message(user_id, text="Выберите уровень:", reply_markup=markup)
    if call.data.split("|")[0] == "finish_add_event":
        markup = types.InlineKeyboardMarkup()
        user_id = call.from_user.id
        user_data[user_id]["level"] = call.data.split("|")[1]
        info = user_data[user_id]
        confirm_btn = types.InlineKeyboardButton(text="Подтвердить", callback_data="confirm")
        cancel_btn = types.InlineKeyboardButton(text="Отменить", callback_data="admin")
        markup.row(confirm_btn)
        markup.row(cancel_btn)
        with open(f'media/{info["photo"]}', "rb") as photo:
            bot.send_photo(user_id, photo=photo, caption=f"Проверьте вашу информацию:{info["measure"]} {info["date"]} {info["time"]} {info["level"]} {CustomUser.objects.get(id=info["trainer"]).first_name} {info["max_member"]} {info["link"]}",
                             reply_markup=markup)
    if call.data == "confirm":
        markup = types.InlineKeyboardMarkup()
        user_id = call.from_user.id
        info = user_data[user_id]
        date = info["date"].split("/")
        event_time = info["time"].split(":")
        final_date = timezone.make_aware(datetime(int(date[2]), int(date[1]), int(date[0]), int(event_time[0]), int(event_time[1])))
        trainer = CustomUser.objects.get(id=info["trainer"])
        event = Event.objects.create(photo=info["photo"],measure=info["measure"],date=final_date, level=next((s for s in Event.StatusChoice if s.label == info["level"]), None), place=info["place"], trainer=trainer, max_member=info["max_member"],link=info["link"])
        back_btn = types.InlineKeyboardButton(text="Назад", callback_data="admin")
        markup.row(back_btn)
        send_event_message(event.id,"new")
        bot.send_message(user_id, text="Добавление тренировки завершено",reply_markup=markup)
    if call.data.split("|")[0] == "start_edit":
        start_editing_event(call.from_user.id,call.data.split("|")[1],call.data.split("|")[2])
    if call.data.split("|")[0] == "finish_edit":
        markup = types.InlineKeyboardMarkup()
        user_id = call.from_user.id
        info = edit_data[user_id]
        event = Event.objects.get(id=info["event_id"])
        state=call.data.split("|")[1]
        if state == "measure":
            event.measure=info[state]
            event.save()
        elif state == "date":
            event.date=info[state]
            event.save()
        elif state == "place":
            event.place=info[state]
            event.save()
        elif state == "max_member":
            event.max_member=info[state]
            event.save()
        elif state == "link":
            event.link=info[state]
            event.save()
        back_btn = types.InlineKeyboardButton(text="Назад", callback_data="admin")
        markup.row(back_btn)
        bot.send_message(user_id, text="Редактирование завершено", reply_markup=markup)
        send_event_message(event.id,"old")
    if call.data == "reload_events":
        markup = types.InlineKeyboardMarkup()
        back_btn = types.InlineKeyboardButton(text="Назад", callback_data="admin")
        confirm_btn = types.InlineKeyboardButton(text="Подтвердить", callback_data="finish_reload_events")
        markup.row(confirm_btn)
        markup.row(back_btn)
        bot.send_message(call.from_user.id, text="Вы уверены, что хотите сделать перепост тренировок?", reply_markup=markup)
    if call.data == "finish_reload_events":
        markup = types.InlineKeyboardMarkup()
        for event in Event.objects.all():
            send_event_message(event.id,"old")
        back_btn = types.InlineKeyboardButton(text="Назад", callback_data="admin")
        markup.row(back_btn)
        bot.send_message(call.from_user.id, text="Репост выполнен",reply_markup=markup)

bot.infinity_polling()