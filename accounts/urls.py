from django.urls import path
from .views import ChatHistoryView, ProfileView, SignupView, messages_view
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', ProfileView.as_view(), name='profile'),
    # path("messages/<str:username>/", ChatHistoryView.as_view()),
    path("messages/<str:username>/", messages_view),

]
