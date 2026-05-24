from datetime import datetime

days = ['Понедельник', 'Вторник', 'Среда', 'Четверг',
        'Пятница', 'Суббота', 'Воскресенье']

today = datetime.now().weekday()  # 0-6 (пн-вс)
print(f"Сегодня: {days[today]}")