from django.urls import path
from . import views

urlpatterns = [
    # 获取所有比赛列表（基础信息）
    path('', views.match_list, name='match_list'),
    # 获取单场比赛详情（含地图和选手数据）
    path('match/<int:match_id>/', views.match_detail, name='match_detail'),
    # 获取某选手参与的比赛数据
    path('player/<int:player_id>/', views.player_matches, name='player_matches'),
]