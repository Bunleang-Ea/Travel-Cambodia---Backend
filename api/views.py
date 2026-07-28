import logging
import os
from datetime import timedelta

import requests
from django.contrib.auth import authenticate, logout
from django.contrib.auth.models import Group, Permission
from django.db.models import F, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import ListCreateAPIView, ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    PasswordResetOTP, SupportTicket, User, 
    Category, Tag, Place, Itinerary, ItineraryItem, Review, ReviewPhoto,
    RoleProfile, SystemNotificationSetting, Location,
)
from .models import Contact
from .email_service import EmailDeliveryError, send_transactional_email
from .permissions import (
    IsAdminOrSuperAdmin,
    IsSuperAdminOnly,
    is_admin_like,
    normalize_role_name,
)
from .serializers import (
    AdminCategorySerializer,
    AdminCreateUserSerializer,
    AdminPlaceSerializer,
    GroupSerializer,
    GoogleAuthSerializer,
    LoginSerializer,
    PermissionSerializer,
    RegistrationOTPVerifySerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PasswordResetVerifySerializer,
    RegistrationSerializer,
    RoleAssignmentSerializer,
    RolePermissionAssignmentSerializer,
    ProfileUpdateSerializer,
    SuperAdminNotificationSettingsSerializer,
    SuperAdminRolePermissionsUpdateSerializer,
    SuperAdminRoleSerializer,
    SuperAdminRoleUpsertSerializer,
    SuperAdminUserUpdateSerializer,
    SupportTicketResponseSerializer,
    SupportTicketSerializer,
    ChangePasswordSerializer,
    UserSerializer,
    PlaceSerializer,
    CategorySerializer,
    TagSerializer,
    ItinerarySerializer,
    ItineraryItemSerializer,
    ReviewSerializer,
    ReviewPhotoSerializer,
    ContactSerializer,
    AdminContactSerializer,
    LocationSerializer,
    AdminLocationSerializer,
)
from .throttles import (
    LoginAttemptThrottle,
    RegistrationThrottle,
    PasswordResetThrottle,
    AdminActionThrottle,
)

logger = logging.getLogger(__name__)

PERMISSION_MATRIX = [
    {
        "section": "CONTENT MANAGEMENT",
        "items": [
            {
                "id": "manage_places",
                "name": "Can Manage Places",
                "desc": "Full access to add, edit, and remove destinations from the directory",
                "permission_keys": ["api.add_place", "api.change_place", "api.delete_place"],
            },
            {
                "id": "manage_categories",
                "name": "Can Manage Categories",
                "desc": "Create, update, and deactivate place categories",
                "permission_keys": ["api.add_category", "api.change_category", "api.delete_category"],
            },
            {
                "id": "edit_reviews",
                "name": "Can Edit Reviews",
                "desc": "Moderate and update user-submitted reviews",
                "permission_keys": ["api.change_review", "api.delete_review"],
            },
        ],
    },
    {
        "section": "SYSTEM MANAGEMENT",
        "items": [
            {
                "id": "manage_users",
                "name": "Can Manage Users",
                "desc": "Create, update, and deactivate system user accounts",
                "permission_keys": ["api.add_user", "api.change_user", "api.delete_user"],
            },
            {
                "id": "modify_roles",
                "name": "Can Modify Roles",
                "desc": "Adjust the hierarchy and naming of system roles",
                "permission_keys": ["auth.change_group"],
            },
        ],
    },
    {
        "section": "VIEW CONTENTS",
        "items": [
            {
                "id": "view_contents",
                "name": "Can View Contents",
                "desc": "Permission to browse and view all public content.",
                "permission_keys": ["api.view_place", "api.view_category", "api.view_tag"],
            },
            {
                "id": "submit_reviews",
                "name": "Can Submit Reviews",
                "desc": "Permission to post ratings, comments, and photos on places.",
                "permission_keys": ["api.add_review"],
            },
        ],
    },
]


def _permission_key(permission):
    return f"{permission.content_type.app_label}.{permission.codename}"


def _load_permission_map(permission_keys):
    if not permission_keys:
        return {}

    key_set = set(permission_keys)
    permissions = Permission.objects.select_related("content_type").all()
    return {_permission_key(permission): permission for permission in permissions if _permission_key(permission) in key_set}


def _admin_like_role_names():
    return {
        "admin",
        "administrator",
        "superadmin",
        "super-admin",
        "super_admin",
        "super admin",
    }


def _apply_group_role_flags(user):
    role_names = {normalize_role_name(group.name) for group in user.groups.all()}
    
    super_admin_roles = {
        "superadmin",
        "super-admin",
        "super_admin",
        "super admin",
    }
    
    should_be_superuser = bool(role_names & super_admin_roles)
    should_be_staff = should_be_superuser or bool(role_names & _admin_like_role_names())
    
    updated_fields = []
    if user.is_superuser != should_be_superuser:
        user.is_superuser = should_be_superuser
        updated_fields.append("is_superuser")
        
    if user.is_staff != should_be_staff:
        user.is_staff = should_be_staff
        updated_fields.append("is_staff")
        
    if updated_fields:
        user.save(update_fields=updated_fields)


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [RegistrationThrottle]

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        email = validated_data['email']

        user = User.objects.filter(email=email).first()
        if user and user.is_active:
            return Response(
                {'errors': {'email': ['This email is already registered.']}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user is None:
            user = User.objects.create_user(
                email=email,
                password=validated_data['password'],
                full_name=validated_data['full_name'],
                phone_number=validated_data.get('phone_number', ''),
                is_active=False,
            )
        else:
            user.full_name = validated_data['full_name']
            user.phone_number = validated_data.get('phone_number', '')
            user.is_active = False
            user.set_password(validated_data['password'])
            user.save(update_fields=['full_name', 'phone_number', 'is_active', 'password'])

        PasswordResetOTP.objects.filter(user=user, used=False).update(used=True)
        otp_record = PasswordResetOTP.create_otp(user)
        try:
            send_transactional_email(
                subject='Travel Cambodia Registration OTP',
                message=f'Your registration verification code is: {otp_record.code}',
                recipients=[email],
            )
        except EmailDeliveryError as exc:
            logger.exception('Registration OTP email delivery failed for %s', email)
            otp_record.used = True
            otp_record.save(update_fields=['used'])
            return Response(
                {'detail': str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception:
            logger.exception('Failed to send registration OTP email to %s', email)
            otp_record.used = True
            otp_record.save(update_fields=['used'])
            return Response(
                {'detail': 'Unable to send OTP email right now. Please verify mail server configuration and try again.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(
            {'detail': 'OTP sent to email. Please verify to complete registration.'},
            status=status.HTTP_200_OK,
        )


class RegisterVerifyView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [RegistrationThrottle]

    def post(self, request):
        serializer = RegistrationOTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        otp_record = serializer.validated_data['otp_record']

        user.is_active = True
        user.save(update_fields=['is_active'])
        otp_record.used = True
        otp_record.save(update_fields=['used'])

        token, _ = Token.objects.get_or_create(user=user)
        data = UserSerializer(user).data
        data['token'] = token.key
        return Response(data, status=status.HTTP_200_OK)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [LoginAttemptThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, _ = Token.objects.get_or_create(user=user)
        data = UserSerializer(user).data
        data['token'] = token.key
        return Response(data)


class GoogleAuthView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [LoginAttemptThrottle]

    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        id_token = serializer.validated_data['id_token']

        google_client_id = str(os.environ.get('GOOGLE_OAUTH_CLIENT_ID', '')).strip()
        if not google_client_id:
            raise ValidationError('Google sign-in is not configured on the server.')

        try:
            google_response = requests.get(
                'https://oauth2.googleapis.com/tokeninfo',
                params={'id_token': id_token},
                timeout=10,
            )
        except requests.RequestException:
            logger.exception('Failed to verify Google ID token')
            return Response(
                {'detail': 'Unable to verify Google sign-in right now. Please try again.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if google_response.status_code != status.HTTP_200_OK:
            raise ValidationError('Invalid Google ID token.')

        payload = google_response.json()
        if str(payload.get('aud', '')).strip() != google_client_id:
            raise ValidationError('Google token audience mismatch.')

        email = str(payload.get('email', '')).strip().lower()
        if not email:
            raise ValidationError('Google account email is missing.')

        email_verified = payload.get('email_verified')
        if str(email_verified).lower() != 'true':
            raise ValidationError('Google account email is not verified.')

        full_name = str(payload.get('name', '')).strip()
        picture_url = str(payload.get('picture', '')).strip()

        user = User.objects.filter(email=email).first()
        created = user is None
        if created:
            user = User.objects.create_user(
                email=email,
                password=None,
                full_name=full_name,
                profile_picture_url=picture_url,
                is_active=True,
            )

        updated_fields = []
        if not user.is_active:
            user.is_active = True
            updated_fields.append('is_active')
        if full_name and not user.full_name:
            user.full_name = full_name
            updated_fields.append('full_name')
        if picture_url and not user.profile_picture_url:
            user.profile_picture_url = picture_url
            updated_fields.append('profile_picture_url')
        if updated_fields:
            user.save(update_fields=updated_fields)

        token, _ = Token.objects.get_or_create(user=user)
        data = UserSerializer(user).data
        data['token'] = token.key
        return Response(data, status=status.HTTP_200_OK)


class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        user = User.objects.get(email=email)
        otp_record = PasswordResetOTP.create_otp(user)
        try:
            send_transactional_email(
                subject='Travel Cambodia Password Reset OTP',
                message=f'Your password reset code is: {otp_record.code}',
                recipients=[email],
            )
        except EmailDeliveryError as exc:
            logger.exception('Password-reset OTP email delivery failed for %s', email)
            otp_record.used = True
            otp_record.save(update_fields=['used'])
            return Response(
                {'detail': str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception:
            logger.exception('Failed to send password-reset OTP email to %s', email)
            otp_record.used = True
            otp_record.save(update_fields=['used'])
            return Response(
                {'detail': 'Unable to send OTP email right now. Please verify mail server configuration and try again.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({'detail': 'OTP sent to email.'}, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'Password updated successfully.'}, status=status.HTTP_200_OK)


class PasswordResetVerifyView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        serializer = PasswordResetVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({'detail': 'OTP verified.'}, status=status.HTTP_200_OK)


class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data)

    def put(self, request):
        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user, context={'request': request}).data)


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'Password changed successfully.'}, status=status.HTTP_200_OK)


class ContactCreateView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ContactSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        contact = serializer.save()
        # attach authenticated user if available
        try:
            if request.user and request.user.is_authenticated:
                contact.user = request.user
                contact.save(update_fields=['user'])
        except Exception:
            # avoid failing the request if attaching user fails
            logger.exception('Failed to attach user to contact')
        return Response(AdminContactSerializer(contact, context={'request': request}).data, status=status.HTTP_201_CREATED)


class AdminContactListView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    def get(self, request):
        contacts = Contact.objects.all().order_by('-created_at')
        serializer = AdminContactSerializer(contacts, many=True)
        return Response(serializer.data)


class AdminContactDetailView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    def get(self, request, pk):
        contact = get_object_or_404(Contact, pk=pk)
        serializer = AdminContactSerializer(contact)
        return Response(serializer.data)

    def patch(self, request, pk):
        contact = get_object_or_404(Contact, pk=pk)
        
        old_reply = contact.admin_reply
        new_reply = request.data.get("admin_reply", contact.admin_reply)
        
        contact.admin_reply = new_reply
        contact.is_resolved = request.data.get("is_resolved", contact.is_resolved)
        contact.save()
        
        # Send email notification if there is a new or updated reply
        if new_reply and new_reply != old_reply:
            try:
                from api.email_service import send_transactional_email
                subject = f"Re: {contact.subject} - Travel Cambodia"
                message = (
                    f"Hi {contact.name},\n\n"
                    f"Thank you for contacting Travel Cambodia. An administrator has replied to your message.\n\n"
                    f"--- Your Message ---\n"
                    f"Subject: {contact.subject}\n"
                    f"Message: {contact.message}\n\n"
                    f"--- Our Reply ---\n"
                    f"{new_reply}\n\n"
                    f"If you have any further questions, feel free to reply directly to this email.\n\n"
                    f"Best regards,\n"
                    f"The Travel Cambodia Team"
                )
                send_transactional_email(
                    subject=subject,
                    message=message,
                    recipients=[contact.email]
                )
            except Exception:
                logger.exception("Failed to send contact reply email")
                
        return Response(AdminContactSerializer(contact).data)

    def delete(self, request, pk):
        contact = get_object_or_404(Contact, pk=pk)
        contact.delete()
        return Response({'detail': 'Contact deleted.'}, status=status.HTTP_204_NO_CONTENT)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.auth is not None:
            request.auth.delete()
        else:
            logout(request)
        return Response({'detail': 'Logged out successfully.'}, status=status.HTTP_200_OK)


class AdminUserListView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]
    throttle_classes = [AdminActionThrottle]

    def get(self, request):
        serializer = UserSerializer(User.objects.all(), many=True)
        return Response(serializer.data)


class AdminCreateUserView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]
    throttle_classes = [AdminActionThrottle]

    def post(self, request):
        serializer = AdminCreateUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class AdminDeleteUserView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]
    throttle_classes = [AdminActionThrottle]

    def delete(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        if user == request.user:
            return Response(
                {'detail': 'Admins cannot delete their own account while authenticated.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.is_superuser and not request.user.is_superuser:
            return Response({'detail': 'Only superusers may delete superuser accounts.'}, status=status.HTTP_403_FORBIDDEN)

        user.delete()
        return Response({'detail': 'User deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)


class AdminRoleListView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    def get(self, request):
        serializer = GroupSerializer(Group.objects.all(), many=True)
        return Response(serializer.data)


class AdminAssignRoleView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    def post(self, request):
        serializer = RoleAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        role_name = serializer.validated_data['role']
        group, _ = Group.objects.get_or_create(name=role_name)
        group.user_set.add(user)

        _apply_group_role_flags(user)

        return Response({'detail': f'Role \"{role_name}\" assigned to {user.email}.'})


class AdminRemoveRoleView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    def post(self, request):
        serializer = RoleAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        role_name = serializer.validated_data['role']
        try:
            group = Group.objects.get(name=role_name)
        except Group.DoesNotExist:
            return Response({'detail': 'Role not found.'}, status=status.HTTP_404_NOT_FOUND)
        group.user_set.remove(user)

        _apply_group_role_flags(user)

        return Response({'detail': f'Role \"{role_name}\" removed from {user.email}.'})


class AdminPermissionListView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    def get(self, request):
        serializer = PermissionSerializer(Permission.objects.all(), many=True)
        return Response(serializer.data)


class AdminAssignPermissionToRoleView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    def post(self, request):
        serializer = RolePermissionAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group = serializer.validated_data['group']
        permission = serializer.validated_data['permission']
        group.permissions.add(permission)
        return Response({'detail': f'Permission {permission.codename} assigned to role {group.name}.'})


class AdminRemovePermissionFromRoleView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    def post(self, request):
        serializer = RolePermissionAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group = serializer.validated_data['group']
        permission = serializer.validated_data['permission']
        group.permissions.remove(permission)
        return Response({'detail': f'Permission {permission.codename} removed from role {group.name}.'})


class AdminGeneralStatsView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]
    throttle_classes = [AdminActionThrottle]

    def get(self, request):
        total_users = User.objects.count()
        total_places = Place.objects.count()
        total_categories = Category.objects.count()
        total_reviews = Review.objects.count()
        total_contacts = Contact.objects.count()
        unresolved_contacts = Contact.objects.filter(is_resolved=False).count()
        
        # Get recent items
        recent_reviews = ReviewSerializer(Review.objects.order_by('-created_at')[:5], many=True).data
        recent_contacts = AdminContactSerializer(Contact.objects.order_by('-created_at')[:5], many=True).data
        
        return Response({
            "total_users": total_users,
            "total_places": total_places,
            "total_categories": total_categories,
            "total_reviews": total_reviews,
            "total_contacts": total_contacts,
            "unresolved_contacts": unresolved_contacts,
            "recent_reviews": recent_reviews,
            "recent_contacts": recent_contacts,
        })


class SuperAdminStatsView(APIView):
    permission_classes = [IsSuperAdminOnly]
    throttle_classes = [AdminActionThrottle]

    def get(self, request):
        now = timezone.now()
        users_qs = User.objects.all()
        return Response(
            {
                "total_users": users_qs.count(),
                "active_users": users_qs.filter(is_active=True).count(),
                "new_signups_24h": users_qs.filter(date_joined__gte=now - timedelta(hours=24)).count(),
                "total_roles": Group.objects.count(),
                "total_permissions": Permission.objects.count(),
            }
        )


class SuperAdminUserListCreateView(APIView):
    permission_classes = [IsSuperAdminOnly]
    throttle_classes = [AdminActionThrottle]

    def get(self, request):
        serializer = UserSerializer(User.objects.all().order_by("email"), many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = AdminCreateUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        roles = request.data.get("roles")
        if isinstance(roles, list):
            groups = []
            for role_name in [str(item).strip() for item in roles if str(item).strip()]:
                group, _ = Group.objects.get_or_create(name=role_name)
                groups.append(group)
            if groups:
                user.groups.set(groups)
                _apply_group_role_flags(user)

        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class SuperAdminUserDetailView(APIView):
    permission_classes = [IsSuperAdminOnly]
    throttle_classes = [AdminActionThrottle]

    def patch(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        serializer = SuperAdminUserUpdateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        _apply_group_role_flags(user)

        if user.is_superuser and not user.is_staff:
            user.is_staff = True
            user.save(update_fields=["is_staff"])

        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user == request.user:
            return Response(
                {"detail": "Super admins cannot delete their own account while authenticated."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.delete()
        return Response({"detail": "User deleted successfully."}, status=status.HTTP_204_NO_CONTENT)


class SuperAdminRoleListCreateView(APIView):
    permission_classes = [IsSuperAdminOnly]
    throttle_classes = [AdminActionThrottle]

    def get(self, request):
        groups = Group.objects.all().order_by("name")
        serializer = SuperAdminRoleSerializer(groups, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = SuperAdminRoleUpsertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role_name = serializer.validated_data["name"]
        description = serializer.validated_data.get("description", "")

        if Group.objects.filter(name=role_name).exists():
            return Response({"detail": "Role name already exists."}, status=status.HTTP_400_BAD_REQUEST)

        group = Group.objects.create(name=role_name)
        RoleProfile.objects.update_or_create(group=group, defaults={"description": description})
        return Response(SuperAdminRoleSerializer(group).data, status=status.HTTP_201_CREATED)


class SuperAdminRoleDetailView(APIView):
    permission_classes = [IsSuperAdminOnly]
    throttle_classes = [AdminActionThrottle]
    protected_roles = {"super_admin", "superadmin", "admin", "user"}

    def patch(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        serializer = SuperAdminRoleUpsertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role_name = serializer.validated_data["name"]
        description = serializer.validated_data.get("description", "")

        if Group.objects.exclude(pk=group.pk).filter(name=role_name).exists():
            return Response({"detail": "Role name already exists."}, status=status.HTTP_400_BAD_REQUEST)

        group.name = role_name
        group.save(update_fields=["name"])
        RoleProfile.objects.update_or_create(group=group, defaults={"description": description})
        return Response(SuperAdminRoleSerializer(group).data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        normalized = normalize_role_name(group.name)
        if normalized in self.protected_roles:
            return Response(
                {"detail": "This core role cannot be deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        group.delete()
        return Response({"detail": "Role deleted successfully."}, status=status.HTTP_204_NO_CONTENT)


class SuperAdminRolePermissionsView(APIView):
    permission_classes = [IsSuperAdminOnly]
    throttle_classes = [AdminActionThrottle]

    def get(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        permissions = Permission.objects.select_related("content_type").order_by(
            "content_type__app_label",
            "content_type__model",
            "codename",
        )
        return Response(
            {
                "role": {"id": group.id, "name": group.name},
                "assigned_permission_ids": list(group.permissions.values_list("id", flat=True)),
                "available_permissions": [
                    {
                        "id": permission.id,
                        "name": permission.name,
                        "codename": permission.codename,
                        "app_label": permission.content_type.app_label,
                        "model": permission.content_type.model,
                    }
                    for permission in permissions
                ],
            }
        )

    def put(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        serializer = SuperAdminRolePermissionsUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        permission_ids = serializer.validated_data["permission_ids"]
        permissions = Permission.objects.filter(id__in=permission_ids)
        group.permissions.set(permissions)
        return Response({"detail": "Role permissions updated successfully."}, status=status.HTTP_200_OK)


class SuperAdminPermissionsMatrixView(APIView):
    permission_classes = [IsSuperAdminOnly]
    throttle_classes = [AdminActionThrottle]

    def _get_role_groups(self):
        super_admin_group, _ = Group.objects.get_or_create(name="super_admin")
        editor_group, _ = Group.objects.get_or_create(name="admin")
        user_group, _ = Group.objects.get_or_create(name="user")
        return super_admin_group, editor_group, user_group

    def get(self, request):
        _, editor_group, user_group = self._get_role_groups()

        all_keys = []
        for section in PERMISSION_MATRIX:
            for item in section["items"]:
                all_keys.extend(item["permission_keys"])
        permission_map = _load_permission_map(all_keys)

        editor_keys = {_permission_key(permission) for permission in editor_group.permissions.select_related("content_type")}
        user_keys = {_permission_key(permission) for permission in user_group.permissions.select_related("content_type")}

        response_sections = []
        for section in PERMISSION_MATRIX:
            items = []
            for item in section["items"]:
                available_keys = [key for key in item["permission_keys"] if key in permission_map]
                items.append(
                    {
                        "id": item["id"],
                        "name": item["name"],
                        "desc": item["desc"],
                        "superAdmin": True,
                        "editor": bool(available_keys) and all(key in editor_keys for key in available_keys),
                        "user": bool(available_keys) and all(key in user_keys for key in available_keys),
                    }
                )
            response_sections.append({"section": section["section"], "items": items})

        return Response(response_sections)

    def put(self, request):
        payload = request.data
        sections = payload if isinstance(payload, list) else payload.get("permissions")
        if not isinstance(sections, list):
            return Response(
                {"detail": "Permissions payload must be a list."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        _, editor_group, user_group = self._get_role_groups()

        all_keys = []
        matrix_lookup = {}
        for section in PERMISSION_MATRIX:
            for item in section["items"]:
                matrix_lookup[item["id"]] = item
                all_keys.extend(item["permission_keys"])
        permission_map = _load_permission_map(all_keys)

        for section in sections:
            for item in section.get("items", []):
                matrix_item = matrix_lookup.get(item.get("id"))
                if not matrix_item:
                    continue
                mapped_permissions = [
                    permission_map[key]
                    for key in matrix_item["permission_keys"]
                    if key in permission_map
                ]
                if not mapped_permissions:
                    continue

                editor_enabled = bool(item.get("editor", False))
                user_enabled = bool(item.get("user", False))

                if editor_enabled:
                    editor_group.permissions.add(*mapped_permissions)
                else:
                    editor_group.permissions.remove(*mapped_permissions)

                if user_enabled:
                    user_group.permissions.add(*mapped_permissions)
                else:
                    user_group.permissions.remove(*mapped_permissions)

        return Response({"detail": "Permissions matrix updated successfully."}, status=status.HTTP_200_OK)


class SuperAdminNotificationSettingsView(APIView):
    permission_classes = [IsSuperAdminOnly]
    throttle_classes = [AdminActionThrottle]

    def get(self, request):
        instance = SystemNotificationSetting.get_solo()
        serializer = SuperAdminNotificationSettingsSerializer(instance)
        return Response(serializer.data)

    def put(self, request):
        instance = SystemNotificationSetting.get_solo()
        serializer = SuperAdminNotificationSettingsSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SupportTicketListCreateView(ListCreateAPIView):
    serializer_class = SupportTicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if is_admin_like(self.request.user):
            return SupportTicket.objects.all()
        return SupportTicket.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SupportTicketDetailView(RetrieveAPIView):
    serializer_class = SupportTicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if is_admin_like(self.request.user):
            return SupportTicket.objects.all()
        return SupportTicket.objects.filter(user=self.request.user)


class SupportTicketRespondView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    def post(self, request, pk):
        ticket = get_object_or_404(SupportTicket, pk=pk)
        serializer = SupportTicketResponseSerializer(ticket, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(SupportTicketSerializer(ticket).data)


class AdminCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = AdminCategorySerializer
    permission_classes = [IsAdminOrSuperAdmin]
    throttle_classes = [AdminActionThrottle]

    def get_queryset(self):
        return Category.objects.all().order_by('name')


class AdminLocationViewSet(viewsets.ModelViewSet):
    serializer_class = AdminLocationSerializer
    permission_classes = [IsAdminOrSuperAdmin]
    throttle_classes = [AdminActionThrottle]

    def get_queryset(self):
        return Location.objects.all().order_by('name')


class AdminPlaceViewSet(viewsets.ModelViewSet):
    serializer_class = AdminPlaceSerializer
    permission_classes = [IsAdminOrSuperAdmin]
    throttle_classes = [AdminActionThrottle]

    def get_queryset(self):
        return Place.objects.select_related('category', 'location').prefetch_related(
            'tags', 'gallery_images'
        ).order_by('-created_at')

class PlacePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class PlaceListView(ListAPIView):
    serializer_class = PlaceSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = PlacePagination

    def get_queryset(self):
        queryset = Place.objects.filter(publishing_status='Published').select_related(
            'category', 'location'
        ).prefetch_related('tags', 'gallery_images')
        
        keyword = self.request.query_params.get('keyword', None)
        if keyword:
            queryset = queryset.filter(
                Q(name__icontains=keyword) |
                Q(description__icontains=keyword) |
                Q(location__name__icontains=keyword)
            )

        category_id = self.request.query_params.get('category_id', None)
        if category_id:
            try:
                category_id = int(category_id)
            except (TypeError, ValueError):
                raise ValidationError({'category_id': 'A valid integer is required.'})
            queryset = queryset.filter(category_id=category_id)
            
        category_name = self.request.query_params.get('category', None)
        if category_name:
            queryset = queryset.filter(category__name__icontains=category_name)

        tags = self.request.query_params.get('tags', None)
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',')]
            queryset = queryset.filter(tags__name__in=tag_list).distinct()

        return queryset

class PlaceDetailView(RetrieveAPIView):
    queryset = Place.objects.filter(publishing_status='Published').select_related(
        'category', 'location'
    ).prefetch_related('tags', 'gallery_images')
    serializer_class = PlaceSerializer
    permission_classes = [permissions.AllowAny]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        Place.objects.filter(pk=instance.pk).update(view_count=F('view_count') + 1)
        instance.refresh_from_db(fields=['view_count'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

class CategoryListView(ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

class LocationListView(ListAPIView):
    queryset = Location.objects.all().order_by('name')
    serializer_class = LocationSerializer
    permission_classes = [permissions.AllowAny]

class TagListView(ListAPIView):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [permissions.AllowAny]

class ItineraryViewSet(viewsets.ModelViewSet):
    serializer_class = ItinerarySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Itinerary.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ItineraryItemViewSet(viewsets.ModelViewSet):
    serializer_class = ItineraryItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = ItineraryItem.objects.filter(itinerary__user=self.request.user)
        itinerary_id = self.request.query_params.get('itinerary')
        if itinerary_id:
            qs = qs.filter(itinerary_id=itinerary_id)
        return qs.order_by('day_number', 'item_id')

class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        queryset = Review.objects.all()
        place_id = self.request.query_params.get('place_id', None)
        if place_id:
            queryset = queryset.filter(place_id=place_id)
        if not is_admin_like(self.request.user):
            queryset = queryset.filter(is_approved=True)
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def _can_manage_review(self, review):
        return bool(
            getattr(self.request, 'user', None)
            and self.request.user.is_authenticated
            and (
                review.user_id == self.request.user.id
                or is_admin_like(self.request.user)
            )
        )

    def perform_update(self, serializer):
        if not self._can_manage_review(serializer.instance):
            raise PermissionDenied('You can only edit your own review.')
        serializer.save()

    def perform_destroy(self, instance):
        if not self._can_manage_review(instance):
            raise PermissionDenied('You can only delete your own review.')
        instance.delete()
