import os
import sys
from datetime import datetime

from django.utils import timezone

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__))
)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    'beach_ball_club_bot.settings'
)
import django
django.setup()
from user.models import CustomUser
from event.models import Event
for trainer in CustomUser.objects.filter(is_trainer=True):
    print(trainer.first_name)

