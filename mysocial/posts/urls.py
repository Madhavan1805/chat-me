from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('search/', views.search_view, name='search'),
    path('register/', views.register_view, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='posts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('create/', views.create_post_view, name='create_post'),
    path('update/<int:post_id>/', views.update_post_view, name='update_post'), 
    path('delete/<int:post_id>/', views.delete_post_view, name='delete_post'),
    path('like/<int:post_id>/', views.like_post, name='like_post'),
    path('comment/<int:post_id>/', views.add_comment, name='add_comment'),
    path('profile/edit/', views.update_profile_view, name='update_profile'),
    path('profile/<str:username>/', views.profile_view, name='profile'),
    path('follow/<int:user_id>/', views.toggle_follow_view, name='toggle_follow'),
    path('inbox/', views.inbox_view, name='inbox'),
    path('chat/start/<int:user_id>/', views.start_chat_view, name='start_chat'),
    path('chat/<int:convo_id>/', views.chat_detail_view, name='chat_detail'),
    path('admin/dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
]