from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    AdminAssignPermissionToRoleView,
    AdminCreateUserView,
    AdminDeleteUserView,
    AdminPermissionListView,
    AdminPlaceViewSet,
    AdminRemovePermissionFromRoleView,
    AdminRemoveRoleView,
    AdminRoleListView,
    AdminUserListView,
    AdminCategoryViewSet,
    AdminGeneralStatsView,
    AdminLocationViewSet,
    SuperAdminNotificationSettingsView,
    SuperAdminPermissionsMatrixView,
    SuperAdminRoleDetailView,
    SuperAdminRoleListCreateView,
    SuperAdminRolePermissionsView,
    SuperAdminStatsView,
    SuperAdminUserDetailView,
    SuperAdminUserListCreateView,
    RegisterVerifyView,
    RegisterView,
    LoginView,
    GoogleAuthView,
    PasswordResetConfirmView,
    ChangePasswordView,
    PasswordResetRequestView,
    PasswordResetVerifyView,
    UserProfileView,
    LogoutView,
    AdminAssignRoleView,
    SupportTicketDetailView,
    SupportTicketListCreateView,
    SupportTicketRespondView,
    ContactCreateView,
    AdminContactListView,
    AdminContactDetailView,
    PlaceListView,
    PlaceDetailView,
    CategoryListView,
    LocationListView,
    TagListView,
)

urlpatterns = [
    path('places/', PlaceListView.as_view(), name='place-list'),
    path('places/<int:pk>/', PlaceDetailView.as_view(), name='place-detail'),
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('locations/', LocationListView.as_view(), name='location-list'),
    path('tags/', TagListView.as_view(), name='tag-list'),
    path('register/', RegisterView.as_view(), name='account-register'),
    path('register/verify/', RegisterVerifyView.as_view(), name='account-register-verify'),
    path('login/', LoginView.as_view(), name='account-login'),
    # Backwards-compatible /auth/ prefixed routes expected by frontend
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/google/', GoogleAuthView.as_view(), name='auth-google'),
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/verify-otp/', RegisterVerifyView.as_view(), name='auth-verify-otp'),
    path('password-reset/request/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset/verify/', PasswordResetVerifyView.as_view(), name='password-reset-verify'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('auth/forgot-password/', PasswordResetRequestView.as_view(), name='auth-forgot-password'),
    path('auth/verify-reset-otp/', PasswordResetVerifyView.as_view(), name='auth-verify-reset-otp'),
    path('auth/reset-password/', PasswordResetConfirmView.as_view(), name='auth-reset-password'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='auth-change-password'),
    path('me/', UserProfileView.as_view(), name='account-profile'),
    path('me/change-password/', ChangePasswordView.as_view(), name='account-change-password'),
    path('logout/', LogoutView.as_view(), name='account-logout'),
    path('admin/users/', AdminUserListView.as_view(), name='admin-user-list'),
    path('admin/users/create/', AdminCreateUserView.as_view(), name='admin-create-user'),
    path('admin/users/<int:pk>/delete/', AdminDeleteUserView.as_view(), name='admin-delete-user'),
    path('admin/roles/', AdminRoleListView.as_view(), name='admin-role-list'),
    path('admin/roles/assign/', AdminAssignRoleView.as_view(), name='admin-assign-role'),
    path('admin/roles/remove/', AdminRemoveRoleView.as_view(), name='admin-remove-role'),
    path('admin/permissions/', AdminPermissionListView.as_view(), name='admin-permission-list'),
    path('admin/roles/permissions/assign/', AdminAssignPermissionToRoleView.as_view(), name='admin-role-permission-assign'),
    path('admin/roles/permissions/remove/', AdminRemovePermissionFromRoleView.as_view(), name='admin-role-permission-remove'),
    path('support-tickets/', SupportTicketListCreateView.as_view(), name='support-ticket-list-create'),
    path('support-tickets/<int:pk>/', SupportTicketDetailView.as_view(), name='support-ticket-detail'),
    path('support-tickets/<int:pk>/respond/', SupportTicketRespondView.as_view(), name='support-ticket-respond'),
    path('contacts/', ContactCreateView.as_view(), name='contact-create'),
    path('admin/contacts/', AdminContactListView.as_view(), name='admin-contact-list'),
    path('admin/contacts/<int:pk>/', AdminContactDetailView.as_view(), name='admin-contact-detail'),
    path('admin/general-stats/', AdminGeneralStatsView.as_view(), name='admin-general-stats'),
    path('admin/super/stats/', SuperAdminStatsView.as_view(), name='super-admin-stats'),
    path('admin/super/users/', SuperAdminUserListCreateView.as_view(), name='super-admin-users'),
    path('admin/super/users/<int:pk>/', SuperAdminUserDetailView.as_view(), name='super-admin-user-detail'),
    path('admin/super/roles/', SuperAdminRoleListCreateView.as_view(), name='super-admin-roles'),
    path('admin/super/roles/<int:pk>/', SuperAdminRoleDetailView.as_view(), name='super-admin-role-detail'),
    path('admin/super/roles/<int:pk>/permissions/', SuperAdminRolePermissionsView.as_view(), name='super-admin-role-permissions'),
    path('admin/super/permissions/matrix/', SuperAdminPermissionsMatrixView.as_view(), name='super-admin-permissions-matrix'),
    path('admin/super/settings/notifications/', SuperAdminNotificationSettingsView.as_view(), name='super-admin-settings-notifications'),
]

from .views import ItineraryViewSet, ItineraryItemViewSet, ReviewViewSet

router = DefaultRouter()
router.register(r'itineraries', ItineraryViewSet, basename='itinerary')
router.register(r'itinerary-items', ItineraryItemViewSet, basename='itinerary-item')
router.register(r'reviews', ReviewViewSet, basename='review')

admin_router = DefaultRouter()
admin_router.register(r'places', AdminPlaceViewSet, basename='admin-place')
admin_router.register(r'categories', AdminCategoryViewSet, basename='admin-category')
admin_router.register(r'locations', AdminLocationViewSet, basename='admin-location')

urlpatterns += [
    path('admin/', include(admin_router.urls)),
    path('', include(router.urls)),
]
