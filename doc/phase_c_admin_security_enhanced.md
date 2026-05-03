# Phase C: Django Admin Security (Weeks 4-6) - Enhanced Implementation Guide

## Overview
This phase focuses on hardening Django Admin access and control. The admin interface is a critical attack surface and requires multiple layers of protection: access restrictions, authentication enforcement, audit trails, and network-level controls.

**Estimated Duration:** Weeks 4-6 (3 weeks)  
**Difficulty Level:** Intermediate  
**Dependencies:** Django 6.0+, DRF, PostgreSQL (recommended for audit logging)

---

## 1. Admin Action Restrictions (Limit Who Can Delete Users)

### 1.1 Problem Statement
By default, Django admin users with `delete_user` permission can delete any user without restrictions. This poses risks:
- Accidental mass deletion
- Insider threats
- Account takeover/deletion by compromised admin accounts
- No audit trail for deletion actions

### 1.2 Implementation Strategy

#### Step 1: Custom Admin Actions with Permission Checks

Update [accounts/admin.py](../accounts/admin.py) to disable dangerous actions:

```python
from django.contrib import admin
from django.contrib.auth.models import Group, Permission
from django.utils.html import format_html
from django.http import HttpResponse
from django.core.exceptions import PermissionDenied
from django.contrib import messages

from .models import PasswordResetOTP, SupportTicket, User

# Unregister default Group and Permission admins
for model in (Group, Permission):
    try:
        admin.site.unregister(model)
    except admin.sites.NotRegistered:
        pass


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'full_name', 'is_staff', 'is_active', 'role_list', 'status_indicator')
    list_filter = ('is_staff', 'is_active', 'is_superuser', 'groups', 'date_joined')
    search_fields = ('email', 'full_name', 'phone_number')
    ordering = ('-date_joined',)
    filter_horizontal = ('groups', 'user_permissions')
    readonly_fields = ('date_joined', 'deletion_log')
    
    # Disable default delete action
    actions = ['deactivate_users']

    fieldsets = (
        (None, {'fields': ('email', 'deletion_log')}),
        ('Personal info', {'fields': ('full_name', 'phone_number', 'profile_picture_url', 'profile_picture')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('date_joined',)}),
    )

    def status_indicator(self, obj):
        """Visual indicator for user status"""
        color = 'green' if obj.is_active else 'red'
        status = 'Active' if obj.is_active else 'Inactive'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            status
        )
    status_indicator.short_description = 'Status'

    def role_list(self, obj):
        """Display all roles/groups for user"""
        return ', '.join(group.name for group in obj.groups.all())
    role_list.short_description = 'Roles'

    def deletion_log(self, obj):
        """Show user deletion history (linked to audit log)"""
        if obj.id:
            audit_logs = obj.admin_audit_logs.filter(action='delete').count()
            return f"User has {audit_logs} deletion attempts in audit log"
        return "No deletion attempts"
    deletion_log.short_description = 'Deletion History'

    @admin.action(
        description="Deactivate selected users (disable login instead of deletion)",
        permissions=['change']  # Users with 'change' perm can deactivate, not 'delete'
    )
    def deactivate_users(self, request, queryset):
        """
        Deactivate users instead of deleting them.
        This preserves data integrity and maintains audit trail.
        """
        if not request.user.is_superuser:
            raise PermissionDenied("Only superusers can deactivate users")
        
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} users deactivated successfully.')
    
    def has_delete_permission(self, request):
        """
        Restrict hard delete to superusers only AND
        only allow self-service deletion via secure endpoint, not via admin
        """
        # Even superusers should not delete via admin interface
        # Instead, implement secure deletion via API endpoint with 2FA confirmation
        return False
    
    def delete_model(self, request, obj):
        """
        Override delete to prevent it entirely.
        Force administrators to use audit-logged API endpoint instead.
        """
        raise PermissionDenied(
            "User deletion is disabled in admin panel for security. "
            "Use the secure deletion API endpoint instead with proper authorization."
        )
    
    def delete_queryset(self, request, queryset):
        """
        Prevent bulk deletion
        """
        raise PermissionDenied(
            "Bulk user deletion is disabled. "
            "Contact system administrator for user removal."
        )
    
    def get_actions(self, request):
        """
        Remove default delete action from admin
        """
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'member_count', 'permission_count')
    search_fields = ('name',)
    filter_horizontal = ('permissions',)
    readonly_fields = ('member_count', 'permission_count')

    def member_count(self, obj):
        return obj.user_set.count()
    member_count.short_description = 'Member count'

    def permission_count(self, obj):
        return obj.permissions.count()
    permission_count.short_description = 'Permission count'
    
    def has_delete_permission(self, request):
        """Only superusers can delete groups"""
        return request.user.is_superuser


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ('name', 'codename', 'content_type')
    list_filter = ('content_type',)
    search_fields = ('name', 'codename')
    readonly_fields = ('name', 'codename', 'content_type')
    
    def has_add_permission(self, request):
        """Permissions are auto-generated by Django migrations"""
        return False
    
    def has_delete_permission(self, request):
        """Permissions should not be deleted"""
        return False


@admin.register(PasswordResetOTP)
class PasswordResetOTPAdmin(admin.ModelAdmin):
    list_display = ('user', 'code', 'expires_at', 'is_valid_indicator', 'created_at')
    list_filter = ('used', 'created_at', 'expires_at')
    search_fields = ('user__email', 'code')
    readonly_fields = ('user', 'code', 'created_at', 'expires_at', 'used')
    
    def is_valid_indicator(self, obj):
        status = 'Valid' if obj.is_valid() else 'Expired/Used'
        color = 'green' if obj.is_valid() else 'red'
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            status
        )
    is_valid_indicator.short_description = 'Status'
    
    def has_add_permission(self, request):
        """OTPs are generated programmatically"""
        return False
    
    def has_delete_permission(self, request):
        """OTP records are audit-important"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """OTP records should not be modified"""
        return False


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('subject', 'user', 'status', 'created_at', 'updated_at', 'response_status')
    list_filter = ('status', 'created_at', 'updated_at')
    search_fields = ('subject', 'description', 'response', 'user__email')
    readonly_fields = ('user', 'subject', 'description', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Ticket Information', {'fields': ('user', 'subject', 'description', 'created_at')}),
        ('Response', {'fields': ('status', 'response', 'updated_at')}),
    )
    
    def response_status(self, obj):
        """Visual indicator for response status"""
        has_response = bool(obj.response)
        color = 'green' if has_response else 'orange'
        status = 'Responded' if has_response else 'Pending Response'
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            status
        )
    response_status.short_description = 'Response Status'
    
    def has_delete_permission(self, request):
        """Support tickets are audit-important"""
        return False
```

#### Step 2: Create AdminAuditLog Model

Create a new model in [accounts/models.py](../accounts/models.py) to track admin actions:

```python
class AdminAuditLog(models.Model):
    """
    Audit trail for all admin actions on critical models.
    Provides complete history of who changed what and when.
    """
    class ActionType(models.TextChoices):
        CREATE = 'create', 'Create'
        UPDATE = 'update', 'Update'
        DELETE = 'delete', 'Delete'
        LOGIN = 'login', 'Admin Login'
        LOGOUT = 'logout', 'Admin Logout'
        FAILED_LOGIN = 'failed_login', 'Failed Admin Login'
        PERMISSION_CHANGE = 'permission_change', 'Permission Changed'
        DEACTIVATE = 'deactivate', 'User Deactivated'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='admin_audit_logs',
        help_text="Admin user who performed the action"
    )
    action = models.CharField(max_length=20, choices=ActionType.choices)
    model_name = models.CharField(max_length=100, db_index=True)
    object_id = models.IntegerField(null=True, blank=True)
    object_repr = models.CharField(max_length=255, blank=True)
    changes_json = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['model_name', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
        ]
        verbose_name_plural = "Admin Audit Logs"
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.get_action_display()} - {self.model_name} ({self.object_id}) by {self.user} at {self.timestamp}"
```

---

## 2. Admin Login Security (Two-Factor Authentication)

### 2.1 Problem Statement
The Django admin login is as strong as the password. A compromised admin password grants full access to all user data. 2FA adds a second layer of verification.

### 2.2 Implementation Strategy

#### Option A: Time-Based OTP (TOTP) - Recommended
Use TOTP (Google Authenticator compatible):

```bash
pip install django-otp pyotp qrcode
```

Configure in [core/settings.py](../core/settings.py):

```python
INSTALLED_APPS = [
    # ... existing apps ...
    'django_otp',
    'django_otp.plugins.otp_totp',
    'django_otp.plugins.otp_static',
]

MIDDLEWARE = [
    # ... existing middleware ...
    'django_otp.middleware.OTPMiddleware',  # Add after AuthenticationMiddleware
]

OTP_LOGIN_URL = '/admin/login/'

# Require OTP for all admin access
ADMIN_REQUIRE_OTP = True
```

Create admin OTP enforcement in [accounts/admin.py](../accounts/admin.py):

```python
from django_otp.decorators import otp_required
from django.contrib.admin.views.decorators import staff_member_required

# Protect admin login
admin.site.login = otp_required(
    staff_member_required(admin.site.login)
)
```

#### Option B: Email-Based OTP - More User-Friendly
Create an email OTP system in [accounts/models.py](../accounts/models.py):

```python
class AdminLoginOTP(models.Model):
    """
    OTP for admin login - sent via email for additional security.
    More user-friendly than authenticator apps for occasional admin logins.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='admin_login_otps'
    )
    code = models.CharField(max_length=6, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'expires_at']),
            models.Index(fields=['code']),
        ]
    
    def is_valid(self):
        return not self.used and timezone.now() <= self.expires_at
    
    @classmethod
    def create_for_admin_login(cls, user, ip_address, user_agent, lifetime_minutes=15):
        """Generate and send OTP for admin login"""
        if not user.is_staff:
            raise ValueError("OTP can only be created for staff users")
        
        code = f'{random.randint(0, 999999):06d}'
        expires_at = timezone.now() + timedelta(minutes=lifetime_minutes)
        
        otp_record = cls.objects.create(
            user=user,
            code=code,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Send via email
        otp_record.send_email()
        return otp_record
    
    def send_email(self):
        """Send OTP to admin email"""
        from django.core.mail import send_mail
        send_mail(
            subject='Admin Login Verification Code',
            message=f'Your admin login code is: {self.code}\n\nValid for 15 minutes.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[self.user.email],
            fail_silently=False,
        )
```

#### Implement Admin Login View
Create [accounts/views_admin.py](../accounts/views_admin.py):

```python
from django.contrib.auth import authenticate, login
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect
from django.views.generic import FormView
from django import forms
from django.http import HttpRequest

from .models import AdminLoginOTP, User


class AdminOTPForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={'placeholder': '6-digit code'})
    )


class AdminLoginOTPView(FormView):
    """
    Second step of 2FA admin login - verify OTP
    """
    form_class = AdminOTPForm
    template_name = 'admin_login_otp.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Check if user is in OTP verification session
        if 'pending_admin_user_id' not in request.session:
            return redirect('admin:login')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_id = self.request.session.get('pending_admin_user_id')
        context['user'] = User.objects.get(id=user_id)
        return context
    
    def form_valid(self, form):
        code = form.cleaned_data['code']
        user_id = self.request.session.get('pending_admin_user_id')
        user = User.objects.get(id=user_id)
        
        # Verify OTP
        otp = AdminLoginOTP.objects.filter(
            user=user,
            code=code,
            used=False
        ).first()
        
        if otp and otp.is_valid():
            # Mark as used and log in
            otp.used = True
            otp.save()
            
            # Create audit log
            AdminAuditLog.objects.create(
                user=user,
                action='login',
                ip_address=self.get_client_ip(self.request),
                user_agent=self.request.META.get('HTTP_USER_AGENT', '')[:500]
            )
            
            login(self.request, user, backend='django.contrib.auth.backends.ModelBackend')
            del self.request.session['pending_admin_user_id']
            
            return redirect('admin:index')
        
        form.add_error('code', 'Invalid or expired OTP. Please try again.')
        return self.form_invalid(form)
    
    @staticmethod
    def get_client_ip(request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
```

---

## 3. Admin Audit Logging (Track Who Changes What)

### 3.1 Problem Statement
Without audit logging, there's no way to:
- Investigate security incidents
- Determine who made problematic changes
- Meet compliance requirements (GDPR, SOC 2)
- Detect insider threats

### 3.2 Implementation Strategy

#### Step 1: Create Audit Logging Middleware
Create [accounts/middleware.py](../accounts/middleware.py):

```python
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
from .models import AdminAuditLog
import json


class AdminAuditMiddleware(MiddlewareMixin):
    """
    Middleware to log all admin panel changes to AdminAuditLog.
    Captures IP address and user agent for each action.
    """
    
    def process_request(self, request):
        """Store original data for change detection"""
        request._admin_audit_start = self.get_request_data(request)
        return None
    
    def process_response(self, request, response):
        """Log changes after action is complete"""
        if self.should_audit(request, response):
            self.create_audit_log(request, response)
        return response
    
    def should_audit(self, request, response):
        """Determine if this request should be logged"""
        if not request.user or request.user.is_anonymous:
            return False
        
        if not request.user.is_staff:
            return False
        
        # Only log POST, PUT, PATCH, DELETE requests
        if request.method not in ('POST', 'PUT', 'PATCH', 'DELETE'):
            return False
        
        # Only log admin panel requests
        if not request.path.startswith('/admin/'):
            return False
        
        # Only log successful changes
        if response.status_code not in (200, 302):
            return False
        
        return True
    
    def create_audit_log(self, request, response):
        """Create audit log entry"""
        try:
            path_parts = request.path.strip('/').split('/')
            
            # Extract model name from URL: /admin/<app>/<model>/<action>/
            if len(path_parts) >= 3:
                app_label = path_parts[1]
                model_name = path_parts[2]
            else:
                return
            
            action = self.determine_action(request, response)
            
            AdminAuditLog.objects.create(
                user=request.user,
                action=action,
                model_name=model_name,
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            )
        except Exception as e:
            # Don't break the response if audit logging fails
            print(f"Audit logging error: {e}")
    
    def determine_action(self, request, response):
        """Determine what action was performed"""
        if request.method == 'POST':
            if 'add' in request.path:
                return AdminAuditLog.ActionType.CREATE
            elif 'change' in request.path:
                return AdminAuditLog.ActionType.UPDATE
            elif 'delete' in request.path:
                return AdminAuditLog.ActionType.DELETE
            else:
                return AdminAuditLog.ActionType.UPDATE
        elif request.method in ('PUT', 'PATCH'):
            return AdminAuditLog.ActionType.UPDATE
        elif request.method == 'DELETE':
            return AdminAuditLog.ActionType.DELETE
        
        return 'unknown'
    
    @staticmethod
    def get_client_ip(request):
        """Extract client IP"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
    
    @staticmethod
    def get_request_data(request):
        """Extract data from request"""
        try:
            if request.method in ('POST', 'PUT', 'PATCH'):
                return dict(request.POST)
        except Exception:
            pass
        return {}
```

Add middleware to [core/settings.py](../core/settings.py):

```python
MIDDLEWARE = [
    # ... existing middleware ...
    'accounts.middleware.AdminAuditMiddleware',  # Add near end
]
```

#### Step 2: Create Audit Log Admin View
Add to [accounts/admin.py](../accounts/admin.py):

```python
@admin.register(AdminAuditLog)
class AdminAuditLogAdmin(admin.ModelAdmin):
    """
    Read-only audit log view.
    Admins can review all changes made in the system.
    """
    list_display = ('timestamp', 'user', 'action', 'model_name', 'object_id', 'ip_address_display')
    list_filter = ('action', 'model_name', 'timestamp', 'user')
    search_fields = ('user__email', 'ip_address', 'object_repr')
    date_hierarchy = 'timestamp'
    
    readonly_fields = ('user', 'action', 'model_name', 'object_id', 'object_repr', 
                      'changes_json', 'ip_address', 'user_agent', 'timestamp')
    
    fieldsets = (
        ('Action Information', {
            'fields': ('user', 'action', 'timestamp')
        }),
        ('Object Details', {
            'fields': ('model_name', 'object_id', 'object_repr')
        }),
        ('Changes', {
            'fields': ('changes_json',)
        }),
        ('Request Information', {
            'fields': ('ip_address', 'user_agent')
        }),
    )
    
    def ip_address_display(self, obj):
        """Display IP with formatting"""
        return format_html('<code>{}</code>', obj.ip_address or 'N/A')
    ip_address_display.short_description = 'IP Address'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request):
        return False
```

#### Step 3: Admin Dashboard for Security Review
Create [accounts/admin.py](../accounts/admin.py) custom admin site with security summary:

```python
class SecurityAwareAdminSite(admin.AdminSite):
    site_header = "Travel Cambodia - Admin Panel (Secure)"
    site_title = "Travel Cambodia Admin"
    index_title = "System Overview"
    
    def index(self, request, extra_context=None):
        """
        Custom admin home with security information
        """
        from django.db.models import Q
        from django.utils import timezone
        from datetime import timedelta
        
        extra_context = extra_context or {}
        
        # Recent suspicious activity
        recent_deletes = AdminAuditLog.objects.filter(
            action=AdminAuditLog.ActionType.DELETE,
            timestamp__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        failed_logins = AdminAuditLog.objects.filter(
            action=AdminAuditLog.ActionType.FAILED_LOGIN,
            timestamp__gte=timezone.now() - timedelta(days=1)
        ).count()
        
        extra_context['security_info'] = {
            'recent_deletes': recent_deletes,
            'failed_logins': failed_logins,
            'active_admin_users': User.objects.filter(is_staff=True, is_active=True).count(),
        }
        
        return super().index(request, extra_context)

# Replace default admin site
admin.site = SecurityAwareAdminSite(name='admin')
```

---

## 4. Admin IP Whitelisting (Network-Level Access Control)

### 4.1 Problem Statement
Even with strong authentication, an attacker with admin credentials from any IP can access the system. IP whitelisting restricts access to known, trusted networks.

### 4.2 Implementation Strategy

#### Step 1: Create IP Whitelist Model
Add to [accounts/models.py](../accounts/models.py):

```python
class AdminIPWhitelist(models.Model):
    """
    Whitelist of approved IP addresses for admin access.
    Admins can only access the admin panel from these IPs.
    """
    ip_address = models.GenericIPAddressField(unique=True)
    description = models.CharField(max_length=255, help_text="e.g., 'Office', 'VPN', 'Home'")
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='whitelisted_ips_created'
    )
    added_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = "Admin IP Whitelists"
        ordering = ['-added_at']
    
    def __str__(self):
        return f"{self.ip_address} - {self.description}"


class AdminIPWhitelistException(models.Model):
    """
    Temporary IP whitelist exceptions for specific users.
    Useful for admins accessing from different locations with proper authorization.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ip_whitelist_exceptions'
    )
    ip_address = models.GenericIPAddressField()
    reason = models.TextField(help_text="Why is this exception needed?")
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='ip_exceptions_approved'
    )
    approved_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('user', 'ip_address')
        ordering = ['-approved_at']
    
    def is_valid(self):
        return self.is_active and timezone.now() <= self.expires_at
    
    def __str__(self):
        return f"{self.user.email} from {self.ip_address} until {self.expires_at}"
```

#### Step 2: Create IP Whitelisting Middleware
Add to [accounts/middleware.py](../accounts/middleware.py):

```python
class AdminIPWhitelistMiddleware(MiddlewareMixin):
    """
    Enforce IP whitelisting for admin panel access.
    Only allows access to /admin/ from whitelisted IPs.
    """
    
    def process_request(self, request):
        """Check IP whitelist before allowing admin access"""
        if not request.path.startswith('/admin/'):
            return None
        
        # Skip check for anonymous users (they'll be redirected to login)
        if request.user.is_anonymous:
            return None
        
        # Skip check for non-staff users
        if not request.user.is_staff:
            return None
        
        client_ip = self.get_client_ip(request)
        
        if not self.is_ip_whitelisted(request.user, client_ip):
            # Log the blocked attempt
            AdminAuditLog.objects.create(
                user=request.user,
                action=AdminAuditLog.ActionType.FAILED_LOGIN,
                ip_address=client_ip,
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            )
            
            from django.http import HttpResponse
            return HttpResponse(
                'Access denied: Your IP address is not whitelisted for admin access. '
                'Contact your system administrator.',
                status=403
            )
        
        return None
    
    def is_ip_whitelisted(self, user, ip_address):
        """Check if IP is whitelisted for this user"""
        from .models import AdminIPWhitelist, AdminIPWhitelistException
        
        # Check global whitelist
        global_whitelist = AdminIPWhitelist.objects.filter(
            ip_address=ip_address,
            is_active=True
        ).exists()
        
        if global_whitelist:
            return True
        
        # Check user-specific exceptions
        exception = AdminIPWhitelistException.objects.filter(
            user=user,
            ip_address=ip_address,
            is_active=True
        ).first()
        
        if exception and exception.is_valid():
            return True
        
        return False
    
    @staticmethod
    def get_client_ip(request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
```

Add to [core/settings.py](../core/settings.py):

```python
MIDDLEWARE = [
    # ... existing middleware ...
    'accounts.middleware.AdminIPWhitelistMiddleware',  # Add BEFORE AdminAuditMiddleware
]
```

#### Step 3: Admin Interface for IP Management
Add to [accounts/admin.py](../accounts/admin.py):

```python
@admin.register(AdminIPWhitelist)
class AdminIPWhitelistAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'description', 'is_active', 'added_by', 'added_at')
    list_filter = ('is_active', 'added_at')
    search_fields = ('ip_address', 'description')
    readonly_fields = ('added_by', 'added_at')
    
    fieldsets = (
        ('IP Information', {'fields': ('ip_address', 'description')}),
        ('Status', {'fields': ('is_active',)}),
        ('Audit Info', {'fields': ('added_by', 'added_at')}),
    )
    
    def save_model(self, request, obj, form, change):
        """Auto-assign who added this IP"""
        if not change:  # Only on creation
            obj.added_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(AdminIPWhitelistException)
class AdminIPWhitelistExceptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'ip_address', 'expires_at', 'is_valid_indicator', 'reason_preview')
    list_filter = ('is_active', 'approved_at', 'expires_at')
    search_fields = ('user__email', 'ip_address')
    readonly_fields = ('requested_by', 'approved_at')
    
    fieldsets = (
        ('User', {'fields': ('user',)}),
        ('Exception Details', {'fields': ('ip_address', 'reason')}),
        ('Expiration', {'fields': ('expires_at',)}),
        ('Approval', {'fields': ('requested_by', 'approved_at', 'is_active')}),
    )
    
    def save_model(self, request, obj, form, change):
        """Track who approved the exception"""
        if not change:
            obj.requested_by = request.user
        super().save_model(request, obj, form, change)
    
    def is_valid_indicator(self, obj):
        status = 'Valid' if obj.is_valid() else 'Expired/Inactive'
        color = 'green' if obj.is_valid() else 'red'
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            status
        )
    is_valid_indicator.short_description = 'Status'
    
    def reason_preview(self, obj):
        return obj.reason[:50] + '...' if len(obj.reason) > 50 else obj.reason
    reason_preview.short_description = 'Reason'
```

---

## 5. Implementation Checklist

### Week 1: Setup & Planning
- [ ] Review current Django admin configuration
- [ ] Design admin permission hierarchy
- [ ] Plan audit logging database schema
- [ ] Create migration files

### Week 2: Admin Actions & Restrictions
- [ ] Implement `AdminAuditLog` model
- [ ] Update `UserAdmin` with action restrictions
- [ ] Disable delete action in admin UI
- [ ] Add `deactivate_users` action
- [ ] Create migration: `python manage.py makemigrations`

### Week 3: Authentication & Whitelisting
- [ ] Choose 2FA approach (TOTP vs Email OTP)
- [ ] Implement 2FA model and views
- [ ] Create IP whitelist models
- [ ] Implement IP whitelisting middleware
- [ ] Test authentication flow

### Week 4: Audit Logging
- [ ] Create audit middleware
- [ ] Register `AdminAuditLog` in admin
- [ ] Test audit logging for all admin actions
- [ ] Create admin dashboard with security overview

### Week 5: Testing & Hardening
- [ ] Write tests for permission restrictions
- [ ] Test 2FA flow
- [ ] Test IP whitelist enforcement
- [ ] Perform security audit

### Week 6: Documentation & Deployment
- [ ] Document admin security procedures
- [ ] Create admin onboarding guide
- [ ] Deploy to staging environment
- [ ] Conduct final security review

---

## 6. Security Best Practices

### Do's ✅
- [ ] Always log failed login attempts
- [ ] Require strong passwords (min 12 characters)
- [ ] Use HTTPS only for admin access in production
- [ ] Rotate admin credentials regularly
- [ ] Audit logs should be immutable/append-only
- [ ] Set admin IP whitelist to known office/VPN IPs only
- [ ] Use environment-specific secrets (never hardcoded)
- [ ] Monitor for suspicious admin activity patterns

### Don'ts ❌
- ❌ Don't store admin passwords in plaintext anywhere
- ❌ Don't allow admin deletion of users via UI
- ❌ Don't disable 2FA even for superusers
- ❌ Don't allow direct database access via Django ORM
- ❌ Don't log sensitive data (passwords, tokens) in audit logs
- ❌ Don't trust IP whitelisting alone - always use 2FA
- ❌ Don't allow admin users to be created without 2FA
- ❌ Don't grant admin privileges to inactive users

---

## 7. Database Migrations

Create migrations for new models:

```bash
python manage.py makemigrations accounts
python manage.py migrate
```

### Migration Example
```python
# accounts/migrations/0005_admin_security.py
from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts', '0004_supportticket'),
    ]

    operations = [
        migrations.CreateModel(
            name='AdminAuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('create', 'Create'), ('update', 'Update'), ('delete', 'Delete'), ('login', 'Admin Login'), ('logout', 'Admin Logout'), ('failed_login', 'Failed Admin Login'), ('permission_change', 'Permission Changed'), ('deactivate', 'User Deactivated')], max_length=20)),
                ('model_name', models.CharField(db_index=True, max_length=100)),
                ('object_id', models.IntegerField(blank=True, null=True)),
                ('object_repr', models.CharField(blank=True, max_length=255)),
                ('changes_json', models.JSONField(blank=True, default=dict)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('user', models.ForeignKey(help_text='Admin user who performed the action', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='admin_audit_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Admin Audit Logs',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.CreateModel(
            name='AdminIPWhitelistException',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ip_address', models.GenericIPAddressField()),
                ('reason', models.TextField(help_text='Why is this exception needed?')),
                ('approved_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
                ('is_active', models.BooleanField(default=True)),
                ('requested_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ip_exceptions_approved', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ip_whitelist_exceptions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Admin IP Whitelist Exceptions',
                'ordering': ['-approved_at'],
                'unique_together': {('user', 'ip_address')},
            },
        ),
        migrations.CreateModel(
            name='AdminIPWhitelist',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ip_address', models.GenericIPAddressField(unique=True)),
                ('description', models.CharField(help_text="e.g., 'Office', 'VPN', 'Home'", max_length=255)),
                ('added_at', models.DateTimeField(auto_now_add=True)),
                ('is_active', models.BooleanField(default=True)),
                ('added_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='whitelisted_ips_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Admin IP Whitelists',
                'ordering': ['-added_at'],
            },
        ),
        migrations.AddIndex(
            model_name='adminauditlog',
            index=models.Index(fields=['user', 'timestamp'], name='accounts_ad_user_id_timestamp_idx'),
        ),
        migrations.AddIndex(
            model_name='adminauditlog',
            index=models.Index(fields=['model_name', 'timestamp'], name='accounts_ad_model_timestamp_idx'),
        ),
        migrations.AddIndex(
            model_name='adminauditlog',
            index=models.Index(fields=['action', 'timestamp'], name='accounts_ad_action_timestamp_idx'),
        ),
    ]
```

---

## 8. Testing

### Example Test Cases
```python
# accounts/tests.py
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from .models import AdminAuditLog, AdminIPWhitelist

User = get_user_model()

class AdminSecurityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            email='admin@example.com',
            password='SecureAdminPass123!'
        )
    
    def test_user_deletion_disabled(self):
        """Verify user deletion via admin is blocked"""
        user = User.objects.create_user(
            email='test@example.com',
            password='test123'
        )
        self.client.login(email='admin@example.com', password='SecureAdminPass123!')
        # Attempt to delete user - should fail
        # ... assertion
    
    def test_deactivate_action_available(self):
        """Verify deactivate action is available as safe alternative"""
        # ... test deactivate action
    
    def test_audit_log_created_on_user_change(self):
        """Verify audit logs are created for admin actions"""
        self.client.login(email='admin@example.com', password='SecureAdminPass123!')
        # Make change to user
        # Verify AdminAuditLog entry created
    
    def test_ip_whitelist_enforcement(self):
        """Verify IP whitelist blocks unauthorized access"""
        # Test with non-whitelisted IP
        # Should return 403
```

---

## 9. Deployment Checklist

### Pre-Production
- [ ] All tests passing
- [ ] Audit logs configured with persistent storage (not SQLite)
- [ ] 2FA enabled for all admin accounts
- [ ] IP whitelist configured for production IPs only
- [ ] Admin password reset via secure channel
- [ ] HTTPS enforced for admin panel
- [ ] Backup strategy for audit logs

### Production
- [ ] Monitor audit logs regularly
- [ ] Set up alerts for suspicious patterns
- [ ] Regular admin credential rotation
- [ ] Monthly security review of admin actions
- [ ] Maintain audit log archival for compliance

---

## References & Further Reading

- Django Admin Security: https://docs.djangoproject.com/en/6.0/ref/contrib/admin/
- OWASP Admin Panel Security: https://cheatsheetseries.owasp.org/
- Django 2FA Packages: django-otp, django-two-factor-auth
- IP Whitelisting Best Practices: https://en.wikipedia.org/wiki/Whitelist
