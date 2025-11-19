from django.urls import path
from .views import ChatHistoryView, ProfileView, SignupView, messages_view , ProfileDetailView , ChatListView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/<str:username>/', ProfileDetailView.as_view(), name='profile-detail'),
    # path("messages/<str:username>/", ChatHistoryView.as_view()),
    path("messages/<str:username>/", messages_view),
    path("chats/", ChatListView.as_view(), name="chat-list"),
]
