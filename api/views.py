from django.contrib.auth import authenticate, logout
from django.contrib.auth.models import Group, Permission
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.generics import ListCreateAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    PasswordResetOTP, SupportTicket, User, 
    Category, Tag, Place
)
from .serializers import (
    AdminCreateUserSerializer,
    GroupSerializer,
    LoginSerializer,
    PermissionSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegistrationSerializer,
    RoleAssignmentSerializer,
    RolePermissionAssignmentSerializer,
    ProfileUpdateSerializer,
    SupportTicketResponseSerializer,
    SupportTicketSerializer,
    UserSerializer,
    PlaceSerializer,
    CategorySerializer,
    TagSerializer,
)
from .throttles import (
    LoginAttemptThrottle,
    RegistrationThrottle,
    PasswordResetThrottle,
    AdminActionThrottle,
)


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [RegistrationThrottle]

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        data = UserSerializer(user).data
        data['token'] = token.key
        return Response(data, status=status.HTTP_201_CREATED)


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


class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        user = User.objects.get(email=email)
        otp_record = PasswordResetOTP.create_otp(user)
        send_mail(
            subject='Travel Cambodia Password Reset OTP',
            message=f'Your password reset code is: {otp_record.code}',
            from_email=None,
            recipient_list=[email],
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


class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.auth is not None:
            request.auth.delete()
        else:
            logout(request)
        return Response({'detail': 'Logged out successfully.'}, status=status.HTTP_200_OK)


class AdminUserListView(APIView):
    permission_classes = [permissions.IsAdminUser]
    throttle_classes = [AdminActionThrottle]

    def get(self, request):
        serializer = UserSerializer(User.objects.all(), many=True)
        return Response(serializer.data)


class AdminCreateUserView(APIView):
    permission_classes = [permissions.IsAdminUser]
    throttle_classes = [AdminActionThrottle]

    def post(self, request):
        serializer = AdminCreateUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class AdminDeleteUserView(APIView):
    permission_classes = [permissions.IsAdminUser]
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
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        serializer = GroupSerializer(Group.objects.all(), many=True)
        return Response(serializer.data)


class AdminAssignRoleView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        serializer = RoleAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        role_name = serializer.validated_data['role']
        group, _ = Group.objects.get_or_create(name=role_name)
        group.user_set.add(user)
        return Response({'detail': f'Role \"{role_name}\" assigned to {user.email}.'})


class AdminRemoveRoleView(APIView):
    permission_classes = [permissions.IsAdminUser]

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
        return Response({'detail': f'Role \"{role_name}\" removed from {user.email}.'})


class AdminPermissionListView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        serializer = PermissionSerializer(Permission.objects.all(), many=True)
        return Response(serializer.data)


class AdminAssignPermissionToRoleView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        serializer = RolePermissionAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group = serializer.validated_data['group']
        permission = serializer.validated_data['permission']
        group.permissions.add(permission)
        return Response({'detail': f'Permission {permission.codename} assigned to role {group.name}.'})


class AdminRemovePermissionFromRoleView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        serializer = RolePermissionAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group = serializer.validated_data['group']
        permission = serializer.validated_data['permission']
        group.permissions.remove(permission)
        return Response({'detail': f'Permission {permission.codename} removed from role {group.name}.'})


class SupportTicketListCreateView(ListCreateAPIView):
    serializer_class = SupportTicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return SupportTicket.objects.all()
        return SupportTicket.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SupportTicketDetailView(RetrieveAPIView):
    serializer_class = SupportTicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return SupportTicket.objects.all()
        return SupportTicket.objects.filter(user=self.request.user)


class SupportTicketRespondView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        ticket = get_object_or_404(SupportTicket, pk=pk)
        serializer = SupportTicketResponseSerializer(ticket, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(SupportTicketSerializer(ticket).data)

from django.db.models import Q
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination

class PlacePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class PlaceListView(generics.ListAPIView):
    serializer_class = PlaceSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = PlacePagination

    def get_queryset(self):
        queryset = Place.objects.filter(publishing_status='Published')
        
        keyword = self.request.query_params.get('keyword', None)
        if keyword:
            queryset = queryset.filter(
                Q(name__icontains=keyword) |
                Q(description__icontains=keyword) |
                Q(location__name__icontains=keyword)
            )

        category_id = self.request.query_params.get('category_id', None)
        if category_id:
            queryset = queryset.filter(category_id=category_id)
            
        category_name = self.request.query_params.get('category', None)
        if category_name:
            queryset = queryset.filter(category__name__icontains=category_name)

        tags = self.request.query_params.get('tags', None)
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',')]
            queryset = queryset.filter(tags__name__in=tag_list).distinct()

        return queryset

class PlaceDetailView(generics.RetrieveAPIView):
    queryset = Place.objects.filter(publishing_status='Published')
    serializer_class = PlaceSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'place_id'

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.view_count += 1
        instance.save(update_fields=['view_count'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

class TagListView(generics.ListAPIView):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [permissions.AllowAny]
