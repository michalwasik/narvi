from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('username', 'email', 'phone_number', 'two_fa_method', 'is_active', 'is_staff')
    list_filter = ('two_fa_method', 'is_active', 'is_staff')
    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Two-Factor Authentication', {'fields': ('two_fa_method', 'phone_number', 'two_fa_secret')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'two_fa_method', 'phone_number')}
        ),
    )
    search_fields = ('username', 'email', 'phone_number')
    ordering = ('username',)

admin.site.register(CustomUser, CustomUserAdmin)
