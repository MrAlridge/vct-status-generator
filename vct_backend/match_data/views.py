from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import Match, MatchDetail, MatchPlayerDetail, Player, Agent

def match_list(request):
    """获取所有比赛的基础信息（名称、状态、队伍、时间）"""
    matches = Match.objects.select_related('event_id', 'team_1_id', 'team_2_id').all()
    data = []
    for match in matches:
        data.append({
            'id': match.id,
            'vlr_id': match.vlr_id,
            'status': match.status,
            'start_time': match.match_data.isoformat() if match.match_data else None,
            'event_name': match.event_id.name if match.event_id else None,
            'team_1': match.team_1_id.name,
            'team_2': match.team_2_id.name,
            'score': f"{match.team_1_score}-{match.team_2_score}"
        })
    return JsonResponse({'matches': data})

def match_detail(request, match_id):
    """获取单场比赛的详细信息（包含地图比分和选手数据）"""
    match = get_object_or_404(Match, id=match_id)
    details = MatchDetail.objects.filter(match_id=match).select_related('map_id')
    players = MatchPlayerDetail.objects.filter(match_detail_id__match_id=match).select_related('player_id', 'agent_id')

    # 整理地图数据
    map_data = []
    for detail in details:
        map_data.append({
            'map_name': detail.map_id.name,
            'map_img': detail.map_id.img,
            'team_1_score': detail.team_1_score,
            'team_2_score': detail.team_2_score
        })

    # 整理选手数据
    player_data = []
    for player_stat in players:
        player_data.append({
            'player_name': player_stat.player_id.name,
            'player_img': player_stat.player_id.img,
            'agent_name': player_stat.agent_id.name,
            'agent_img': player_stat.agent_id.img,
            'rating': player_stat.rating,
            'kills': player_stat.KDA_K,
            'deaths': player_stat.KDA_D,
            'assists': player_stat.KDA_A
        })

    return JsonResponse({
        'match_info': {
            'id': match.id,
            'vlr_url': match.vlr_url,
            'haojiao_url': match.haojiao_url,
            'status': match.status
        },
        'map_details': map_data,
        'player_stats': player_data
    })

def player_matches(request, player_id):
    """获取某选手参与的所有比赛数据"""
    player = get_object_or_404(Player, id=player_id)
    stats = MatchPlayerDetail.objects.filter(player_id=player).select_related('match_detail_id__match_id')

    data = []
    for stat in stats:
        match = stat.match_detail_id.match_id
        data.append({
            'match_id': match.id,
            'match_time': match.match_data.isoformat() if match.match_data else None,
            'opponent_team': (
                match.team_1_id.name if stat.team_id != match.team_1_id 
                else match.team_2_id.name
            ),
            'agent': stat.agent_id.name_chs or stat.agent_id.name,
            'rating': stat.rating,
            'kast': stat.kast,
            'adr': stat.adr
        })
    return JsonResponse({'player': player.name, 'matches': data})
