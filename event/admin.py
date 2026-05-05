from django.contrib import admin

from event.models import Event, Reserve


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    pass

@admin.register(Reserve)
class ReserveAdmin(admin.ModelAdmin):
    pass