from django.contrib import admin

from user.models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['get_full_name', 'is_staff', 'date_joined', 'tg_id',]
    list_filter = ['is_staff', 'is_active', 'date_joined']
    search_fields = ['first_name', 'last_name']
    readonly_fields = ['id', 'date_joined', 'last_login']
    fieldsets = (
        ('Personal Information', {
            'fields': ('id', 'first_name', 'last_name', 'tg_id')
        }),
        ('Account', {
            'fields': ('password',)
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions','is_trainer'),
            'classes': ('collapse',)
        }),
        ('Important Dates', {
            'fields': ('date_joined', 'last_login'),
            'classes': ('collapse',)
        }),
    )

    def get_full_name(self, obj):
        return obj.get_full_name() or 'N/A'

    get_full_name.short_description = 'Full Name'
