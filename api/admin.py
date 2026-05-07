from django.contrib import admin
from django.contrib.auth.models import Group, Permission

from .models import PasswordResetOTP, SupportTicket, User

for model in (Group, Permission):
    try:
        admin.site.unregister(model)
    except admin.sites.NotRegistered:
        pass


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'full_name', 'is_staff', 'is_active', 'role_list')
    list_filter = ('is_staff', 'is_active', 'is_superuser', 'groups')
    search_fields = ('email', 'full_name')
    ordering = ('email',)
    filter_horizontal = ('groups', 'user_permissions')
    readonly_fields = ('date_joined',)

    fieldsets = (
        (None, {'fields': ('email',)}),
        ('Personal info', {'fields': ('full_name', 'phone_number', 'profile_picture_url', 'profile_picture')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('date_joined',)}),
    )

    def role_list(self, obj):
        return ', '.join(group.name for group in obj.groups.all())

    role_list.short_description = 'Roles'


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'member_count')
    search_fields = ('name',)
    filter_horizontal = ('permissions',)

    def member_count(self, obj):
        return obj.user_set.count()

    member_count.short_description = 'Member count'


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ('name', 'codename', 'content_type')
    list_filter = ('content_type',)
    search_fields = ('name', 'codename')


@admin.register(PasswordResetOTP)
class PasswordResetOTPAdmin(admin.ModelAdmin):
    list_display = ('user', 'code', 'expires_at', 'used')
    list_filter = ('used',)
    search_fields = ('user__email', 'code')


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('subject', 'user', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at')
    search_fields = ('subject', 'description', 'response', 'user__email')
