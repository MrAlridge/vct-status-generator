from django.db import models

class Region(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True, null=False)
    tag = models.CharField(max_length=50, unique=True, null=False, db_comment="赛区全称")
    abbreviation = models.CharField(max_length=10, unique=True, null=True, db_comment="赛区缩写 (e.g., AMER)")

class MatchType(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True, null=False, db_comment="赛事类型名称")
    tag = models.CharField(max_length=50, unique=True, null=False)

class Event(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=True, db_comment="赛事名称")
    type_id = models.ForeignKey(MatchType, on_delete=models.CASCADE, db_comment="赛事类型ID")
    region_id = models.ForeignKey(Region, on_delete=models.CASCADE, db_comment="所属赛区ID")

class Map(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, null=False, db_comment="地图名称")
    img = models.URLField(max_length=255, null=True, db_comment="地图图片链接")

class Team(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, null=False, db_comment="战队名称")
    full_name = models.CharField(max_length=255, null=True, db_comment="战队全称")
    region_id = models.ForeignKey(Region, on_delete=models.CASCADE, db_comment="所属赛区ID")

class Player(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, null=False, db_comment="选手名称")
    full_name = models.CharField(max_length=255, null=True, db_comment="选手全称")
    team_id = models.ForeignKey(Team, on_delete=models.CASCADE, db_comment="目前所属队伍ID")
    nation = models.CharField(max_length=100, null=True, db_comment="选手国籍")
    img = models.URLField(max_length=255, null=True, db_comment="选手图片链接")

class Agent(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, null=False, db_comment="特工名称")
    name_chs = models.CharField(max_length=100, null=True, db_comment="特工中文名")
    img = models.URLField(max_length=255, null=True, db_comment="特工图片链接")

class Match(models.Model):
    id = models.AutoField(primary_key=True)
    vlr_id = models.CharField(max_length=50, db_comment="来自 vlr.gg 的唯一比赛标识符")
    haojiao_id = models.CharField(max_length=50, db_comment="来自 号角 的唯一比赛标识符")
    vlr_url = models.URLField(max_length=255, null=True, db_comment="比赛的 vlr.gg 链接")
    haojiao_url = models.URLField(max_length=255, null=True, db_comment="比赛的 号角 链接")
    status = models.TextChoices('status', ['未开始', '进行中', '已结束'])
    match_data = models.DateTimeField(null=True, db_comment="比赛开始时间")
    event_id = models.ForeignKey(Event, on_delete=models.CASCADE, db_comment="所属赛事ID")
    team_1_id = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='team_1_matches', db_comment="队伍 1 ID")
    team_2_id = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='team_2_matches', db_comment="队伍 2 ID")
    team_1_score = models.IntegerField(null=True, db_comment="队伍 1 得分")
    team_2_score = models.IntegerField(null=True, db_comment="队伍 2 得分")

class MatchDetail(models.Model):
    id = models.AutoField(primary_key=True)
    match_id = models.ForeignKey(Match, on_delete=models.CASCADE, db_comment="所属比赛ID")
    map_id = models.ForeignKey(Map, on_delete=models.CASCADE, db_comment="地图ID")
    team_1_score = models.IntegerField(null=True, db_comment="队伍 1 得分")
    team_2_score = models.IntegerField(null=True, db_comment="队伍 2 得分")

class MatchPlayerDetail(models.Model):
    id = models.AutoField(primary_key=True)
    match_detail_id = models.ForeignKey(MatchDetail, on_delete=models.CASCADE, db_comment="所属比赛详情ID")
    player_id = models.ForeignKey(Player, on_delete=models.CASCADE, db_comment="选手ID")
    team_id = models.ForeignKey(Team, on_delete=models.CASCADE, db_comment="所属队伍ID")
    agent_id = models.ForeignKey(Agent, on_delete=models.CASCADE, db_comment="使用的特工ID")
    rating = models.FloatField(null=True, db_comment="选手Rating")
    acs = models.IntegerField(null=True, db_comment="选手ACS")
    KDA_K = models.IntegerField(null=True, db_comment="Kills")
    KDA_D = models.IntegerField(null=True, db_comment="Deaths")
    KDA_A = models.IntegerField(null=True, db_comment="Assists")
    KD_diff = models.IntegerField(null=True, db_comment="KDA差值")
    kast = models.FloatField(null=True, db_comment="KAST")
    adr = models.FloatField(null=True, db_comment="ADR")
    headshot = models.FloatField(null=True, db_comment="HS%")
    first_kill = models.IntegerField(null=True, db_comment="首杀数")
    first_death = models.IntegerField(null=True, db_comment="首死数")
    first_kill_diff = models.IntegerField(null=True, db_comment="FK-FD差值")



