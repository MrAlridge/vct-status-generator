from io import BytesIO
import json
import os
import requests
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError

def download_image(url, base_url="https://web.haojiao.cc"):
    """下载图片并处理可能的 URL 格式, 并缓存"""
    if not hasattr(download_image, "cache"):
        download_image.cache = {}  # 初始化缓存

    if url.startswith("http"):
        full_url = url
    else:
        full_url = base_url + url

    if full_url in download_image.cache:
        return download_image.cache[full_url]  # 从缓存返回

    try:
        response = requests.get(full_url)
        response.raise_for_status()
        image = Image.open(BytesIO(response.content))
        download_image.cache[full_url] = image  # 存入缓存
        return image
    except (requests.RequestException, UnidentifiedImageError) as e:
        print(f"下载或打开图片失败: {url}, 错误: {e}")
        return None

def create_player_image(player_data, font_path="msyh.ttc"):
    """为单个选手生成数据图"""

    WIDTH, HEIGHT = 450, 220  # 调整宽度
    BG_COLOR = (240, 240, 240)
    TEXT_COLOR = (50, 50, 50)
    FONT_SIZE = 16
    try:
      FONT = ImageFont.truetype(font_path, FONT_SIZE)
    except IOError:
        print(f"找不到字体文件: {font_path}，请检查字体是否存在或使用其他字体")
        return None

    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    d = ImageDraw.Draw(img)

    # 头像和国旗
    icon = download_image(player_data["player_info"]["icon"])
    if icon:
        icon = icon.resize((60, 60))
        mask = Image.new("L", (60, 60), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 60, 60), fill=255)
        icon.putalpha(mask)
        img.paste(icon, (10, 10), icon)

    flag_icon = download_image(player_data["player_info"]["nationality_icon"])
    if flag_icon:
        flag_icon = flag_icon.resize((20, 20))
        img.paste(flag_icon, (50, 50), flag_icon)  # 国旗位置

    # 选手信息
    x, y = 80, 10
    d.text((x, y), player_data['player_info']['real_name'], font=FONT, fill=TEXT_COLOR)
    y += FONT_SIZE + 5
    d.text((x, y), player_data['career_info']['id_name'], font=FONT, fill=TEXT_COLOR)
    y += FONT_SIZE + 5
    d.text((x, y), "位置: " + player_data['career_info']['position'], font=FONT, fill=TEXT_COLOR)
    y += FONT_SIZE + 10

    # 英雄图标
    hero_x = 10
    # for hero_data in player_data['hero']:
    #     hero_icon = download_image(hero_data["icon"])
    #     if hero_icon:
    #         hero_icon = hero_icon.resize((30, 30))
    #         img.paste(hero_icon, (hero_x, y), hero_icon)
    #         hero_x += 30 + 5

    # 数据 (重新排版)
    y += 40
    data_fields = [
        ("ACS", "acs"),
        ("Rating", "rating"),
        ("KAST", "kast"),
        ("ADR", "adr"),
        ("HS%", "hs"),
        ("FK", "fk"),
        ("FD", "fd"),
        ("K", "kills"),
        ("D", "deaths"),
        ("A", "assists"),
    ]
    data_x = 10

    # 自己来排版
    d.text((data_x, y), f"Rating  ACS  K / D / A   +/-", font=FONT, fill=TEXT_COLOR)
    d.text((data_x, y + 20), f"{player_data["rating"]} {player_data["acs"]} {player_data["kills"]} {player_data["deaths"]} {player_data["assists"]}", font=FONT, fill=TEXT_COLOR)
    # line_height = FONT_SIZE + 2
    # for i, (label, key) in enumerate(data_fields):
    #     value = player_data[key]
    #     if isinstance(value, float):
    #         value = f"{value:.2f}"  # 格式化
    #     d.text((data_x, y + (i % 5) * line_height), f"{label}: {value}", font=FONT, fill=TEXT_COLOR)
    #     data_x += 20
        # if (i + 1) % 5 == 0:
        #     data_x += 90 # 换列
        #     y = y - 4 * line_height if i < 5 else y # 调整位置

    return img

def create_combined_image(map_data, font_path="msyh.ttc"):
    """为一张地图创建合并图像"""
    if not map_data:
      print("地图数据为空")
      return

    # 分组
    team1_data = [player for player in map_data['player_info'] if not player['is_main']]
    team2_data = [player for player in map_data['player_info'] if player['is_main']]

    if not team1_data or not team2_data:
        print("队伍数据不完整")
        return

    # 选手图像
    team1_images = [create_player_image(player, font_path) for player in team1_data]
    team2_images = [create_player_image(player, font_path) for player in team2_data]

    team1_images = [img for img in team1_images if img]
    team2_images = [img for img in team2_images if img]
    if not team1_images or not team2_images:
        print("没有可生成的选手图像")
        return

    # 画布尺寸
    player_width, player_height = team1_images[0].size
    width = player_width * 2 + 40  # 间隔
    height = max(len(team1_images), len(team2_images)) * player_height + 100

    combined_img = Image.new("RGB", (width, height), (255, 255, 255))
    d = ImageDraw.Draw(combined_img)

    try:
        title_font = ImageFont.truetype(font_path, 24)
        team_font = ImageFont.truetype(font_path, 20)
    except IOError:
        print(f"找不到字体文件: {font_path}，请检查字体是否存在或使用其他字体")
        return None

    # 地图和队伍标题
    map_name = map_data['map']['name_zh']
    d.text((width // 2, 10), f"地图: {map_name}", font=title_font, fill=(0, 0, 0), anchor="mt")

    #队伍1
    team1_name = map_data['main_team']['team_name_short']
    team1_score = map_data['main_score']['total']
    #队伍2
    team2_name = map_data['guest_team']['team_name_short']
    team2_score = map_data['guest_score']['total']
    
    #队伍logo
    team1_logo = download_image(map_data["main_team"]["team_icon"])
    if team1_logo:
      team1_logo = team1_logo.resize((40,40))
      combined_img.paste(team1_logo, (10, 50), team1_logo)
    team2_logo = download_image(map_data["guest_team"]["team_icon"])
    if team2_logo:
      team2_logo = team2_logo.resize((40,40))
      combined_img.paste(team2_logo, (width-50, 50), team2_logo)

    d.text((10, 40), f"{team1_name}: {team1_score}", font=team_font, fill=(0, 0, 0))
    d.text((width - 10, 40), f"{team2_name}: {team2_score}", font=team_font, fill=(0, 0, 0), anchor="rt")
    # 绘制
    y_offset = 100
    for img in team1_images:
        combined_img.paste(img, (10, y_offset))
        y_offset += player_height
    y_offset = 100
    for img in team2_images:
        combined_img.paste(img, (width - player_width - 10, y_offset))
        y_offset += player_height

    return combined_img

def create_individual_images(all_players_data, output_folder="player_images", font_path="msyh.ttc"):
    """创建单个选手的图像, 使用所有的数据"""
    os.makedirs(output_folder, exist_ok=True)

    for player_data in all_players_data:
        player_image = create_player_image(player_data, font_path)
        if player_image:
            player_id = player_data['career_info']['id_name']
            filename = f"{player_id}.png"
            filepath = os.path.join(output_folder, filename)
            player_image.save(filepath)
            print(f"已生成选手图像: {filepath}")

def main(json_data, mode="both", map_index=None):
  if not json_data or 'data' not in json_data or 'all' not in json_data['data'] or 'list' not in json_data['data']:
        print("JSON 数据无效")
        return
  
  all_players_data = json_data['data']['all']
  maps_data = json_data['data']['list']

    # 根据模式生成
  if mode in ("combined", "both"):
    if map_index is not None: # 指定地图
        if 0 <= map_index < len(maps_data):
            combined_image = create_combined_image(maps_data[map_index])
            if combined_image:
                combined_image.save(f"combined_map_{map_index + 1}.png")
                print(f"合并图像已保存为 combined_map_{map_index + 1}.png")
        else:
            print("无效的地图索引")
    else:  # 所有地图
        for i, map_data in enumerate(maps_data):
          if not map_data['is_drop']: #跳过丢弃对局
            combined_image = create_combined_image(map_data)
            if combined_image:
                combined_image.save(f"combined_map_{i + 1}.png")
                print(f"合并图像已保存为 combined_map_{i + 1}.png")

  if mode in ("individual", "both"):
        create_individual_images(all_players_data)

testdata = json.loads("""
{
    "code": 200,
    "data": {
        "all": [
            {
                "round_times": 45,
                "is_main": true,
                "player_info": {
                    "person_id": "CiHR4Im1lhdIJxyn",
                    "real_name": "赵泽骏",
                    "real_name_en": "ZEJUN ZHAO",
                    "icon": "/cms/20240613/1718256981089.png",
                    "nationality_icon": "/wiki/flag/cn.png"
                },
                "career_info": {
                    "career_id": "O7GWBtpva7GOdWWW",
                    "career_type": 1,
                    "id_name": "Ezeir",
                    "position": "控场",
                    "career_status": 1
                },
                "hero": [
                    {
                        "unique_id": "3ntjS4vcKwLTKLw7",
                        "hero_zh": "幽影",
                        "hero_en": "Omen",
                        "icon": "/cms/20230704/1688450092152.png",
                        "times": 0
                    },
                    {
                        "unique_id": "WPMz4M4DZfc6cgsp",
                        "hero_zh": "钛狐",
                        "hero_en": "Tejo",
                        "icon": "/cms/20250109/1736404558645.png",
                        "times": 0
                    }
                ],
                "acs": 225,
                "rating": 0,
                "kast": 0,
                "adr": 143.46666,
                "hs": 18.5,
                "fk": 4,
                "fd": 2,
                "kills": 37,
                "deaths": 32,
                "assists": 12
            },
            {
                "round_times": 45,
                "is_main": false,
                "player_info": {
                    "person_id": "tdCCAx4WWFzTYc6K",
                    "real_name": "郑永康",
                    "real_name_en": "Zheng Yongkang",
                    "icon": "/cms/20250219/1739955437805.png",
                    "nationality_icon": "/wiki/flag/cn.png"
                },
                "career_info": {
                    "career_id": "mRRLRqtYmWktOZwu",
                    "career_type": 1,
                    "id_name": "ZmjjKK",
                    "position": "决斗",
                    "career_status": 1
                },
                "hero": [
                    {
                        "unique_id": "RvHqTTeGB1oM3vOP",
                        "hero_zh": "捷风",
                        "hero_en": "Jett",
                        "icon": "/cms/20230704/1688450106179.png",
                        "times": 0
                    },
                    {
                        "unique_id": "EWxouSwDbS4ogTAe",
                        "hero_zh": "幻棱",
                        "hero_en": "Waylay",
                        "icon": "/cms/20250310/1741598188505.jpg",
                        "times": 0
                    }
                ],
                "acs": 214.5,
                "rating": 0,
                "kast": 0,
                "adr": 138.4,
                "hs": 23,
                "fk": 14,
                "fd": 11,
                "kills": 32,
                "deaths": 39,
                "assists": 11
            },
            {
                "round_times": 45,
                "is_main": false,
                "player_info": {
                    "person_id": "e9SBp4UPUSzSx9F6",
                    "real_name": "王森旭",
                    "real_name_en": "Wang Senxu",
                    "icon": "/cms/20250219/1739955913106.png",
                    "nationality_icon": "/wiki/flag/cn.png"
                },
                "career_info": {
                    "career_id": "pREeITp7ZkSSITdi",
                    "career_type": 1,
                    "id_name": "nobody",
                    "position": "指挥/先锋位",
                    "career_status": 1
                },
                "hero": [
                    {
                        "unique_id": "lds498UwiiY5OC6L",
                        "hero_zh": "猎枭",
                        "hero_en": "Sova",
                        "icon": "/cms/20230704/1688450134462.png",
                        "times": 0
                    },
                    {
                        "unique_id": "WPMz4M4DZfc6cgsp",
                        "hero_zh": "钛狐",
                        "hero_en": "Tejo",
                        "icon": "/cms/20250109/1736404558645.png",
                        "times": 0
                    }
                ],
                "acs": 203.5,
                "rating": 0,
                "kast": 0,
                "adr": 134.2,
                "hs": 24.5,
                "fk": 0,
                "fd": 5,
                "kills": 33,
                "deaths": 35,
                "assists": 8
            },
            {
                "round_times": 45,
                "is_main": false,
                "player_info": {
                    "person_id": "OkARoS17U86SnGbG",
                    "real_name": "万顺治",
                    "real_name_en": "Wan Shunzhi",
                    "icon": "/cms/20250219/1739955925114.png",
                    "nationality_icon": "/wiki/flag/cn.png"
                },
                "career_info": {
                    "career_id": "OJrRmS6GIIuQ5rtN",
                    "career_type": 1,
                    "id_name": "CHICHOO",
                    "position": "哨位/控场",
                    "career_status": 1
                },
                "hero": [
                    {
                        "unique_id": "Nv78xV9chJnSUNiL",
                        "hero_zh": "维斯",
                        "hero_en": "Vyse",
                        "icon": "/cms/20240911/1726019301433.png",
                        "times": 0
                    },
                    {
                        "unique_id": "wuySQOUgOWWPhg6P",
                        "hero_zh": "零",
                        "hero_en": "Cypher",
                        "icon": "/cms/20230704/1688450120784.png",
                        "times": 0
                    }
                ],
                "acs": 188,
                "rating": 0,
                "kast": 0,
                "adr": 132,
                "hs": 27,
                "fk": 2,
                "fd": 3,
                "kills": 30,
                "deaths": 31,
                "assists": 10
            },
            {
                "round_times": 45,
                "is_main": false,
                "player_info": {
                    "person_id": "Iz8LRJH2eOUsyrYM",
                    "real_name": "张钊",
                    "real_name_en": "Zhang Zhao",
                    "icon": "/cms/20250219/1739955933534.png",
                    "nationality_icon": "/wiki/flag/cn.png"
                },
                "career_info": {
                    "career_id": "5keqHlY6GBMTnMRs",
                    "career_type": 1,
                    "id_name": "Smoggy",
                    "position": "先锋/决斗",
                    "career_status": 1
                },
                "hero": [
                    {
                        "unique_id": "3ntjS4vcKwLTKLw7",
                        "hero_zh": "幽影",
                        "hero_en": "Omen",
                        "icon": "/cms/20230704/1688450092152.png",
                        "times": 0
                    },
                    {
                        "unique_id": "vs6LUy7isxmOZSeh",
                        "hero_zh": "炼狱",
                        "hero_en": "Brimstone",
                        "icon": "/cms/20230704/1688450086146.png",
                        "times": 0
                    }
                ],
                "acs": 161,
                "rating": 0,
                "kast": 0,
                "adr": 103.26667,
                "hs": 33,
                "fk": 1,
                "fd": 1,
                "kills": 23,
                "deaths": 35,
                "assists": 25
            },
            {
                "round_times": 45,
                "is_main": true,
                "player_info": {
                    "person_id": "ScpMeMTfFhBMwFaB",
                    "real_name": "光洪霖",
                    "real_name_en": "honglin guang",
                    "icon": "/cms/20240613/1718271435824.png",
                    "nationality_icon": "/wiki/flag/cn.png"
                },
                "career_info": {
                    "career_id": "75c2Zru9iF9Zz3OV",
                    "career_type": 1,
                    "id_name": "GuanG",
                    "position": "先锋/哨卫",
                    "career_status": 1
                },
                "hero": [
                    {
                        "unique_id": "qD3eU2ZI2tzKsPHI",
                        "hero_zh": "奇乐",
                        "hero_en": "Killjoy",
                        "icon": "/cms/20230704/1688450077170.png",
                        "times": 0
                    },
                    {
                        "unique_id": "wuySQOUgOWWPhg6P",
                        "hero_zh": "零",
                        "hero_en": "Cypher",
                        "icon": "/cms/20230704/1688450120784.png",
                        "times": 0
                    }
                ],
                "acs": 231.5,
                "rating": 0,
                "kast": 0,
                "adr": 148.6,
                "hs": 28,
                "fk": 8,
                "fd": 5,
                "kills": 39,
                "deaths": 34,
                "assists": 8
            },
            {
                "round_times": 45,
                "is_main": true,
                "player_info": {
                    "person_id": "f3BZoKewkvMOQ1lr",
                    "real_name": "陈羿杰",
                    "real_name_en": "YIJIE CHEN",
                    "icon": "/cms/20240613/1718271533289.png",
                    "nationality_icon": "/wiki/flag/cn.png"
                },
                "career_info": {
                    "career_id": "swmIl4cSz1JIVtMe",
                    "career_type": 1,
                    "id_name": "OBONE",
                    "position": "控场",
                    "career_status": 1
                },
                "hero": [
                    {
                        "unique_id": "poElQUh43oancODD",
                        "hero_zh": "夜露",
                        "hero_en": "Yoru",
                        "icon": "/cms/20230704/1688450140124.png",
                        "times": 0
                    },
                    {
                        "unique_id": "vs6LUy7isxmOZSeh",
                        "hero_zh": "炼狱",
                        "hero_en": "Brimstone",
                        "icon": "/cms/20230704/1688450086146.png",
                        "times": 0
                    }
                ],
                "acs": 167.5,
                "rating": 0,
                "kast": 0,
                "adr": 104.933334,
                "hs": 19.5,
                "fk": 3,
                "fd": 4,
                "kills": 27,
                "deaths": 30,
                "assists": 15
            },
            {
                "round_times": 45,
                "is_main": true,
                "player_info": {
                    "person_id": "2gvTTzVGI6HTTcp8",
                    "real_name": "王晴川",
                    "real_name_en": "Qingchuan Wang",
                    "icon": "/cms/20240613/1718271457183.png",
                    "nationality_icon": "/wiki/flag/cn.png"
                },
                "career_info": {
                    "career_id": "cY1VMMZ24dGypV3D",
                    "career_type": 1,
                    "id_name": "cb",
                    "position": "先锋/信息位",
                    "career_status": 1
                },
                "hero": [
                    {
                        "unique_id": "WPMz4M4DZfc6cgsp",
                        "hero_zh": "钛狐",
                        "hero_en": "Tejo",
                        "icon": "/cms/20250109/1736404558645.png",
                        "times": 0
                    },
                    {
                        "unique_id": "SoSejIZ8GUxSy8nz",
                        "hero_zh": "霓虹",
                        "hero_en": "Neon",
                        "icon": "/cms/20230704/1688450070312.png",
                        "times": 0
                    }
                ],
                "acs": 274,
                "rating": 0,
                "kast": 0,
                "adr": 180.26666,
                "hs": 19.5,
                "fk": 8,
                "fd": 6,
                "kills": 41,
                "deaths": 29,
                "assists": 15
            },
            {
                "round_times": 45,
                "is_main": false,
                "player_info": {
                    "person_id": "1zOfDgEqh8B7336j",
                    "real_name": "谢孟勳",
                    "real_name_en": "MENG-HSUN HSIEH",
                    "icon": "/cms/20250219/1739955511481.png",
                    "nationality_icon": "/wiki/flag/cn.png"
                },
                "career_info": {
                    "career_id": "UROKp13ClABcVeOo",
                    "career_type": 1,
                    "id_name": "S1Mon",
                    "position": "控场/哨位/信息位",
                    "career_status": 1
                },
                "hero": [
                    {
                        "unique_id": "EhjoYKfVgxMwj48e",
                        "hero_zh": "K/O",
                        "hero_en": "KAY/O",
                        "icon": "/cms/20230704/1688450023389.png",
                        "times": 0
                    },
                    {
                        "unique_id": "Ivpz3Lel7O5wNTrp",
                        "hero_zh": "铁臂",
                        "hero_en": "Breach",
                        "icon": "/cms/20230704/1688450113156.png",
                        "times": 0
                    }
                ],
                "acs": 241.5,
                "rating": 0,
                "kast": 0,
                "adr": 156.26666,
                "hs": 37,
                "fk": 3,
                "fd": 5,
                "kills": 39,
                "deaths": 36,
                "assists": 18
            },
            {
                "round_times": 45,
                "is_main": true,
                "player_info": {
                    "person_id": "sWMSaayCtS2z36IQ",
                    "real_name": "叶晓栋",
                    "real_name_en": "XIAODONG YE",
                    "icon": "/cms/20240613/1718271395624.png",
                    "nationality_icon": "/wiki/flag/cn.png"
                },
                "career_info": {
                    "career_id": "n8iSPU2QPGyUojqB",
                    "career_type": 1,
                    "id_name": "o0o0o",
                    "position": "决斗/控场/指挥",
                    "career_status": 1
                },
                "hero": [
                    {
                        "unique_id": "Ivpz3Lel7O5wNTrp",
                        "hero_zh": "铁臂",
                        "hero_en": "Breach",
                        "icon": "/cms/20230704/1688450113156.png",
                        "times": 0
                    },
                    {
                        "unique_id": "Ivpz3Lel7O5wNTrp",
                        "hero_zh": "铁臂",
                        "hero_en": "Breach",
                        "icon": "/cms/20230704/1688450113156.png",
                        "times": 0
                    }
                ],
                "acs": 201,
                "rating": 0,
                "kast": 0,
                "adr": 136,
                "hs": 39,
                "fk": 2,
                "fd": 3,
                "kills": 32,
                "deaths": 32,
                "assists": 19
            }
        ],
        "list": [
            {
                "unique_id": "3AtklNurFVRF9inb",
                "match_id": "IJ2Nr2rJM9NjQJMO",
                "box_number": 1,
                "time": "0'0",
                "is_overtime": false,
                "round_detail": [
                    {
                        "win_team": 2,
                        "win_camp": 2,
                        "mode": 3
                    },
                    {
                        "win_team": 2,
                        "win_camp": 2,
                        "mode": 3
                    },
                    {
                        "win_team": 1,
                        "win_camp": 1,
                        "mode": 3
                    },
                    {
                        "win_team": 1,
                        "win_camp": 1,
                        "mode": 3
                    },
                    {
                        "win_team": 2,
                        "win_camp": 2,
                        "mode": 3
                    },
                    {
                        "win_team": 1,
                        "win_camp": 1,
                        "mode": 3
                    },
                    {
                        "win_team": 1,
                        "win_camp": 1,
                        "mode": 1
                    },
                    {
                        "win_team": 2,
                        "win_camp": 2,
                        "mode": 2
                    },
                    {
                        "win_team": 1,
                        "win_camp": 1,
                        "mode": 3
                    },
                    {
                        "win_team": 2,
                        "win_camp": 2,
                        "mode": 3
                    },
                    {
                        "win_team": 1,
                        "win_camp": 1,
                        "mode": 4
                    },
                    {
                        "win_team": 2,
                        "win_camp": 2,
                        "mode": 3
                    },
                    {
                        "win_team": 2,
                        "win_camp": 1,
                        "mode": 3
                    },
                    {
                        "win_team": 2,
                        "win_camp": 1,
                        "mode": 3
                    },
                    {
                        "win_team": 1,
                        "win_camp": 2,
                        "mode": 3
                    },
                    {
                        "win_team": 1,
                        "win_camp": 2,
                        "mode": 3
                    },
                    {
                        "win_team": 1,
                        "win_camp": 2,
                        "mode": 3
                    },
                    {
                        "win_team": 2,
                        "win_camp": 1,
                        "mode": 4
                    },
                    {
                        "win_team": 1,
                        "win_camp": 2,
                        "mode": 2
                    },
                    {
                        "win_team": 1,
                        "win_camp": 2,
                        "mode": 3
                    },
                    {
                        "win_team": 2,
                        "win_camp": 1,
                        "mode": 4
                    },
                    {
                        "win_team": 2,
                        "win_camp": 1,
                        "mode": 3
                    },
                    {
                        "win_team": 1,
                        "win_camp": 2,
                        "mode": 3
                    },
                    {
                        "win_team": 1,
                        "win_camp": 2,
                        "mode": 3
                    }
                ],
                "map": {
                    "map_id": "CAFdIk65WNDxDpHt",
                    "name_zh": "亚海悬城",
                    "name_en": "Ascent",
                    "icon": "/cms/20230519/1684480489944.jpg"
                },
                "is_decider_map": false,
                "is_drop": false,
                "is_main_select_map": false,
                "is_main_select_first_strike": false,
                "mvp": null,
                "main_team": {
                    "team_id": "lAvuB3JCl3CVSHmt",
                    "team_name": "NOVA电子竞技俱乐部",
                    "team_name_short": "NOVA",
                    "team_icon": "/cms/20230530/1685429449194.png"
                },
                "guest_team": {
                    "team_id": "5gjweC11brGhuRBR",
                    "team_name": "EDward Gaming",
                    "team_name_short": "EDG",
                    "team_icon": "/cms/20230704/1688439753798.png"
                },
                "main_score": {
                    "total": 13,
                    "atk": 7,
                    "def": 6,
                    "over_time_atk": 0,
                    "over_time_def": 0
                },
                "guest_score": {
                    "total": 11,
                    "atk": 6,
                    "def": 5,
                    "over_time_atk": 0,
                    "over_time_def": 0
                },
                "vlr_player_relation": {},
                "vlr_url": "https://www.vlr.gg/450053/nova-esports-vs-edward-gaming-champions-tour-2025-china-stage-1-w2/?game=203472\u0026tab=overview",
                "is_auto_update_vlr": true,
                "is_vlr_analysis": true,
                "player_info": [
                    {
                        "unique_id": "O1lZR9JPz7gall9l",
                        "match_id": "IJ2Nr2rJM9NjQJMO",
                        "valorant_round_id": "3AtklNurFVRF9inb",
                        "is_main": true,
                        "player_info": {
                            "person_id": "sWMSaayCtS2z36IQ",
                            "real_name": "叶晓栋",
                            "real_name_en": "XIAODONG YE",
                            "icon": "/cms/20240613/1718271395624.png",
                            "nationality_icon": "/wiki/flag/cn.png"
                        },
                        "career_info": {
                            "career_id": "n8iSPU2QPGyUojqB",
                            "career_type": 1,
                            "id_name": "o0o0o",
                            "position": "决斗/控场/指挥",
                            "career_status": 1
                        },
                        "hero": {
                            "unique_id": "Ivpz3Lel7O5wNTrp",
                            "hero_zh": "铁臂",
                            "hero_en": "Breach",
                            "icon": "/cms/20230704/1688450113156.png",
                            "times": 0
                        },
                        "acs": 203,
                        "rating": 0,
                        "kast": 0,
                        "adr": 143,
                        "hs": 36,
                        "fk": 2,
                        "fd": 2,
                        "kills": 17,
                        "deaths": 18,
                        "assists": 12,
                        "sort": 2
                    },
                    {
                        "unique_id": "7JwtaSV7buAqolsL",
                        "match_id": "IJ2Nr2rJM9NjQJMO",
                        "valorant_round_id": "3AtklNurFVRF9inb",
                        "is_main": true,
                        "player_info": {
                            "person_id": "f3BZoKewkvMOQ1lr",
                            "real_name": "陈羿杰",
                            "real_name_en": "YIJIE CHEN",
                            "icon": "/cms/20240613/1718271533289.png",
                            "nationality_icon": "/wiki/flag/cn.png"
                        },
                        "career_info": {
                            "career_id": "swmIl4cSz1JIVtMe",
                            "career_type": 1,
                            "id_name": "OBONE",
                            "position": "控场",
                            "career_status": 1
                        },
                        "hero": {
                            "unique_id": "poElQUh43oancODD",
                            "hero_zh": "夜露",
                            "hero_en": "Yoru",
                            "icon": "/cms/20230704/1688450140124.png",
                            "times": 0
                        },
                        "acs": 125,
                        "rating": 0,
                        "kast": 0,
                        "adr": 83,
                        "hs": 19,
                        "fk": 2,
                        "fd": 2,
                        "kills": 11,
                        "deaths": 17,
                        "assists": 2,
                        "sort": 5
                    },
                    {
                        "unique_id": "Cf7NzcbNb1sh55SS",
                        "match_id": "IJ2Nr2rJM9NjQJMO",
                        "valorant_round_id": "3AtklNurFVRF9inb",
                        "is_main": true,
                        "player_info": {
                            "person_id": "2gvTTzVGI6HTTcp8",
                            "real_name": "王晴川",
                            "real_name_en": "Qingchuan Wang",
                            "icon": "/cms/20240613/1718271457183.png",
                            "nationality_icon": "/wiki/flag/cn.png"
                        },
                        "career_info": {
                            "career_id": "cY1VMMZ24dGypV3D",
                            "career_type": 1,
                            "id_name": "cb",
                            "position": "先锋/信息位",
                            "career_status": 1
                        },
                        "hero": {
                            "unique_id": "WPMz4M4DZfc6cgsp",
                            "hero_zh": "钛狐",
                            "hero_en": "Tejo",
                            "icon": "/cms/20250109/1736404558645.png",
                            "times": 0
                        },
                        "acs": 306,
                        "rating": 0,
                        "kast": 0,
                        "adr": 212,
                        "hs": 29,
                        "fk": 4,
                        "fd": 3,
                        "kills": 24,
                        "deaths": 14,
                        "assists": 8,
                        "sort": 1
                    },
                    {
                        "unique_id": "JakOA7fYEzfGwH1r",
                        "match_id": "IJ2Nr2rJM9NjQJMO",
                        "valorant_round_id": "3AtklNurFVRF9inb",
                        "is_main": true,
                        "player_info": {
                            "person_id": "ScpMeMTfFhBMwFaB",
                            "real_name": "光洪霖",
                            "real_name_en": "honglin guang",
                            "icon": "/cms/20240613/1718271435824.png",
                            "nationality_icon": "/wiki/flag/cn.png"
                        },
                        "career_info": {
                            "career_id": "75c2Zru9iF9Zz3OV",
                            "career_type": 1,
                            "id_name": "GuanG",
                            "position": "先锋/哨卫",
                            "career_status": 1
                        },
                        "hero": {
                            "unique_id": "qD3eU2ZI2tzKsPHI",
                            "hero_zh": "奇乐",
                            "hero_en": "Killjoy",
                            "icon": "/cms/20230704/1688450077170.png",
                            "times": 0
                        },
                        "acs": 200,
                        "rating": 0,
                        "kast": 0,
                        "adr": 136,
                        "hs": 25,
                        "fk": 3,
                        "fd": 3,
                        "kills": 18,
                        "deaths": 18,
                        "assists": 2,
                        "sort": 4
                    },
                    {
                        "unique_id": "epi3SDbw36ZRbp6N",
                        "match_id": "IJ2Nr2rJM9NjQJMO",
                        "valorant_round_id": "3AtklNurFVRF9inb",
                        "is_main": true,
                        "player_info": {
                            "person_id": "CiHR4Im1lhdIJxyn",
                            "real_name": "赵泽骏",
                            "real_name_en": "ZEJUN ZHAO",
                            "icon": "/cms/20240613/1718256981089.png",
                            "nationality_icon": "/wiki/flag/cn.png"
                        },
                        "career_info": {
                            "career_id": "O7GWBtpva7GOdWWW",
                            "career_type": 1,
                            "id_name": "Ezeir",
                            "position": "控场",
                            "career_status": 1
                        },
                        "hero": {
                            "unique_id": "3ntjS4vcKwLTKLw7",
                            "hero_zh": "幽影",
                            "hero_en": "Omen",
                            "icon": "/cms/20230704/1688450092152.png",
                            "times": 0
                        },
                        "acs": 201,
                        "rating": 0,
                        "kast": 0,
                        "adr": 129,
                        "hs": 17,
                        "fk": 1,
                        "fd": 2,
                        "kills": 17,
                        "deaths": 17,
                        "assists": 5,
                        "sort": 3
                    },
                    {
                        "unique_id": "xNz61WyjJ8EcUSuL",
                        "match_id": "IJ2Nr2rJM9NjQJMO",
                        "valorant_round_id": "3AtklNurFVRF9inb",
                        "is_main": false,
                        "player_info": {
                            "person_id": "tdCCAx4WWFzTYc6K",
                            "real_name": "郑永康",
                            "real_name_en": "Zheng Yongkang",
                            "icon": "/cms/20250219/1739955437805.png",
                            "nationality_icon": "/wiki/flag/cn.png"
                        },
                        "career_info": {
                            "career_id": "mRRLRqtYmWktOZwu",
                            "career_type": 1,
                            "id_name": "ZmjjKK",
                            "position": "决斗",
                            "career_status": 1
                        },
                        "hero": {
                            "unique_id": "RvHqTTeGB1oM3vOP",
                            "hero_zh": "捷风",
                            "hero_en": "Jett",
                            "icon": "/cms/20230704/1688450106179.png",
                            "times": 0
                        },
                        "acs": 233,
                        "rating": 0,
                        "kast": 0,
                        "adr": 151,
                        "hs": 24,
                        "fk": 9,
                        "fd": 5,
                        "kills": 19,
                        "deaths": 19,
                        "assists": 8,
                        "sort": 2
                    },
                    {
                        "unique_id": "W94Y3CNtEpzvLZYS",
                        "match_id": "IJ2Nr2rJM9NjQJMO",
                        "valorant_round_id": "3AtklNurFVRF9inb",
                        "is_main": false,
                        "player_info": {
                            "person_id": "e9SBp4UPUSzSx9F6",
                            "real_name": "王森旭",
                            "real_name_en": "Wang Senxu",
                            "icon": "/cms/20250219/1739955913106.png",
                            "nationality_icon": "/wiki/flag/cn.png"
                        },
                        "career_info": {
                            "career_id": "pREeITp7ZkSSITdi",
                            "career_type": 1,
                            "id_name": "nobody",
                            "position": "指挥/先锋位",
                            "career_status": 1
                        },
                        "hero": {
                            "unique_id": "lds498UwiiY5OC6L",
                            "hero_zh": "猎枭",
                            "hero_en": "Sova",
                            "icon": "/cms/20230704/1688450134462.png",
                            "times": 0
                        },
                        "acs": 207,
                        "rating": 0,
                        "kast": 0,
                        "adr": 130,
                        "hs": 21,
                        "fk": 0,
                        "fd": 3,
                        "kills": 17,
                        "deaths": 17,
                        "assists": 6,
                        "sort": 3
                    },
                    {
                        "unique_id": "TbOjDSMo9QASPML1",
                        "match_id": "IJ2Nr2rJM9NjQJMO",
                        "valorant_round_id": "3AtklNurFVRF9inb",
                        "is_main": false,
                        "player_info": {
                            "person_id": "OkARoS17U86SnGbG",
                            "real_name": "万顺治",
                            "real_name_en": "Wan Shunzhi",
                            "icon": "/cms/20250219/1739955925114.png",
                            "nationality_icon": "/wiki/flag/cn.png"
                        },
                        "career_info": {
                            "career_id": "OJrRmS6GIIuQ5rtN",
                            "career_type": 1,
                            "id_name": "CHICHOO",
                            "position": "哨位/控场",
                            "career_status": 1
                        },
                        "hero": {
                            "unique_id": "Nv78xV9chJnSUNiL",
                            "hero_zh": "维斯",
                            "hero_en": "Vyse",
                            "icon": "/cms/20240911/1726019301433.png",
                            "times": 0
                        },
                        "acs": 193,
                        "rating": 0,
                        "kast": 0,
                        "adr": 146,
                        "hs": 31,
                        "fk": 0,
                        "fd": 1,
                        "kills": 16,
                        "deaths": 14,
                        "assists": 8,
                        "sort": 4
                    },
                    {
                        "unique_id": "f2ZhicwWQcbiyKdq",
                        "match_id": "IJ2Nr2rJM9NjQJMO",
                        "valorant_round_id": "3AtklNurFVRF9inb",
                        "is_main": false,
                        "player_info": {
                            "person_id": "Iz8LRJH2eOUsyrYM",
                            "real_name": "张钊",
                            "real_name_en": "Zhang Zhao",
                            "icon": "/cms/20250219/1739955933534.png",
                            "nationality_icon": "/wiki/flag/cn.png"
                        },
                        "career_info": {
                            "career_id": "5keqHlY6GBMTnMRs",
                            "career_type": 1,
                            "id_name": "Smoggy",
                            "position": "先锋/决斗",
                            "career_status": 1
                        },
                        "hero": {
                            "unique_id": "3ntjS4vcKwLTKLw7",
                            "hero_zh": "幽影",
                            "hero_en": "Omen",
                            "icon": "/cms/20230704/1688450092152.png",
                            "times": 0
                        },
                        "acs": 96,
                        "rating": 0,
                        "kast": 0,
                        "adr": 58,
                        "hs": 30,
                        "fk": 0,
                        "fd": 0,
                        "kills": 7,
                        "deaths": 18,
                        "assists": 16,
                        "sort": 5
                    },
                    {
                        "unique_id": "it3bllwqCsm44SN7",
                        "match_id": "IJ2Nr2rJM9NjQJMO",
                        "valorant_round_id": "3AtklNurFVRF9inb",
                        "is_main": false,
                        "player_info": {
                            "person_id": "1zOfDgEqh8B7336j",
                            "real_name": "谢孟勳",
                            "real_name_en": "MENG-HSUN HSIEH",
                            "icon": "/cms/20250219/1739955511481.png",
                            "nationality_icon": "/wiki/flag/cn.png"
                        },
                        "career_info": {
                            "career_id": "UROKp13ClABcVeOo",
                            "career_type": 1,
                            "id_name": "S1Mon",
                            "position": "控场/哨位/信息位",
                            "career_status": 1
                        },
                        "hero": {
                            "unique_id": "EhjoYKfVgxMwj48e",
                            "hero_zh": "K/O",
                            "hero_en": "KAY/O",
                            "icon": "/cms/20230704/1688450023389.png",
                            "times": 0
                        },
                        "acs": 273,
                        "rating": 0,
                        "kast": 0,
                        "adr": 167,
                        "hs": 36,
                        "fk": 3,
                        "fd": 3,
                        "kills": 25,
                        "deaths": 19,
                        "assists": 8,
                        "sort": 1
                    }
                ]
            },
            {
                "unique_id": "lskaQU9QySMh2PsT",
                "match_id": "IJ2Nr2rJM9NjQJMO",
                "box_number": 2,
                "time": "0'0",
                "is_overtime": false,
                "round_detail": [
                    {
                        "win_team": 1,
                        "win_camp": 1,
                        "mode": 3
                    },
                    {
                        "win_team": 2,
                        "win_camp": 2,
                        "mode": 2
                    },
                    {
                        "win_team": 2,
                        "win_camp": 2,
                        "mode": 3
                    },
                    {
                        "win_team": 1,
                        "win_camp": 1,
                        "mode": 4
                    },
                    {
                        "win_team": 2,
                        "win_camp": 2,
                        "mode": 3
                    },
                    {
                        "win_team": 2,
                        "win_camp": 2,
                        "mode": 3
                    },
                    {
                        "win_team": 1,
                        "win_camp": 1,
                        "mode": 3
                    },
                    {
                        "win_team": 1,
                        "win_camp": 1,
                        "mode": 4
                    },
                    {
                        "win_team": 1,
                        "win_camp": 1,
                        "mode": 4
                    },
                    {
                        "win_team": 2,
                        "win_camp": 2,
                        "mode": 3
                    },
                    {
                        "win_team": 1,
                        "win_camp": 1,
                        "mode": 3
                    },
                    {
                        "win_team": 2,
                        "win_camp": 2,
                        "mode": 3
                    },
                    {
                        "win_team": 1,
                        "win_camp": 2,
                        "mode": 3
                    },
                    {
                        "win_team": 1,
                        "win_camp": 2,
                        "mode": 3
                    },
                    {
                        "win_team": 2,
                        "win_camp": 1,
                        "mode": 4
                    },
                    {
                        "win_team": 1,
                        "win_camp": 2,
                        "mode": 3
                    },
                    {
                        "win_team": 1,
                        "win_camp": 2,
                        "mode": 3
                    },
                    {
                        "win_team": 1,
                        "win_camp": 2,
                        "mode": 3
                    },
                    {
                        "win_team": 1,
                        "win_camp": 2,
                        "mode": 3
                    },
                    {
                        "win_team": 2,
                        "win_camp": 1,
                        "mode": 3
                    },
                    {
                        "win_team": 1,
                        "win_camp": 2,
                        "mode": 3
                    }
                ],
                "map": {
                    "map_id": "72KGCA5ngDaUj954",
                    "name_zh": "裂变峡谷",
                    "name_en": "Fracture",
                    "icon": "/cms/20230519/1684480006415.jpg"
                },
                "is_decider_map": false,
                "is_drop": false,
                "is_main_select_map": false,
                "is_main_select_first_strike": false,
                "mvp": null,
                "main_team": {
                    "team_id": "lAvuB3JCl3CVSHmt",
                    "team_name": "NOVA电子竞技俱乐部",
                    "team_name_short": "NOVA",
                    "team_icon": "/cms/20230530/1685429449194.png"
                },
                "guest_team": {
                    "team_id": "5gjweC11brGhuRBR",
                    "team_name": "EDward Gaming",
                    "team_name_short": "EDG",
                    "team_icon": "/cms/20230704/1688439753798.png"
                },
                "main_score": {
                    "total": 13,
                    "atk": 7,
                    "def": 6,
                    "over_time_atk": 0,
                    "over_time_def": 0
                },
                "guest_score": {
                    "total": 8,
                    "atk": 6,
                    "def": 2,
                    "over_time_atk": 0,
                    "over_time_def": 0
                },
                "vlr_player_relation": {},
                "vlr_url": "https://www.vlr.gg/450053/nova-esports-vs-edward-gaming-champions-tour-2025-china-stage-1-w2/?game=203473\u0026tab=overview",
                "is_auto_update_vlr": true,
                "is_vlr_analysis": true,
                "player_info": [
                    {
                        "unique_id": "5YrARFyrrgTQ8vYS",
                        "match_id": "IJ2Nr2rJM9NjQJMO",
                        "valorant_round_id": "lskaQU9QySMh2PsT",
                        "is_main": true,
                        "player_info": {
                            "person_id": "sWMSaayCtS2z36IQ",
                            "real_name": "叶晓栋",
                            "real_name_en": "XIAODONG YE",
                            "icon": "/cms/20240613/1718271395624.png",
                            "nationality_icon": "/wiki/flag/cn.png"
                        },
                        "career_info": {
                            "career_id": "n8iSPU2QPGyUojqB",
                            "career_type": 1,
                            "id_name": "o0o0o",
                            "position": "决斗/控场/指挥",
                            "career_status": 1
                        },
                        "hero": {
                            "unique_id": "Ivpz3Lel7O5wNTrp",
                            "hero_zh": "铁臂",
                            "hero_en": "Breach",
                            "icon": "/cms/20230704/1688450113156.png",
                            "times": 0
                        },
                        "acs": 199,
                        "rating": 0,
                        "kast": 0,
                        "adr": 128,
                        "hs": 42,
                        "fk": 0,
                        "fd": 1,
                        "kills": 15,
                        "deaths": 14,
                        "assists": 7,
                        "sort": 5
                    },
                    {
                        "unique_id": "G1n5A5OWEk6dDwsM",
                        "match_id": "IJ2Nr2rJM9NjQJMO",
                        "valorant_round_id": "lskaQU9QySMh2PsT",
                        "is_main": true,
                        "player_info": {
                            "person_id": "f3BZoKewkvMOQ1lr",
                            "real_name": "陈羿杰",
                            "real_name_en": "YIJIE CHEN",
                            "icon": "/cms/20240613/1718271533289.png",
                            "nationality_icon": "/wiki/flag/cn.png"
                        },
                        "career_info": {
                            "career_id": "swmIl4cSz1JIVtMe",
                            "career_type": 1,
                            "id_name": "OBONE",
                            "position": "控场",
                            "career_status": 1
                        },
                        "hero": {
                            "unique_id": "vs6LUy7isxmOZSeh",
                            "hero_zh": "炼狱",
                            "hero_en": "Brimstone",
                            "icon": "/cms/20230704/1688450086146.png",
                            "times": 0
                        },
                        "acs": 210,
                        "rating": 0,
                        "kast": 0,
                        "adr": 130,
                        "hs": 20,
                        "fk": 1,
                        "fd": 2,
                        "kills": 16,
                        "deaths": 13,
                        "assists": 13,
                        "sort": 4
                    },
                    {
                        "unique_id": "BZeiR4J54NEGhpxK",
                        "match_id": "IJ2Nr2rJM9NjQJMO",
                        "valorant_round_id": "lskaQU9QySMh2PsT",
                        "is_main": true,
                        "player_info": {
                            "person_id": "2gvTTzVGI6HTTcp8",
                            "real_name": "王晴川",
                            "real_name_en": "Qingchuan Wang",
                            "icon": "/cms/20240613/1718271457183.png",
                            "nationality_icon": "/wiki/flag/cn.png"
                        },
                        "career_info": {
                            "career_id": "cY1VMMZ24dGypV3D",
                            "career_type": 1,
                            "id_name": "cb",
                            "position": "先锋/信息位",
                            "career_status": 1
                        },
                        "hero": {
                            "unique_id": "SoSejIZ8GUxSy8nz",
                            "hero_zh": "霓虹",
                            "hero_en": "Neon",
                            "icon": "/cms/20230704/1688450070312.png",
                            "times": 0
                        },
                        "acs": 242,
                        "rating": 0,
                        "kast": 0,
                        "adr": 144,
                        "hs": 10,
                        "fk": 4,
                        "fd": 3,
                        "kills": 17,
                        "deaths": 15,
                        "assists": 7,
                        "sort": 3
                    },
                    {
                        "unique_id": "WjSjNqjqjF9ZiVQB",
                        "match_id": "IJ2Nr2rJM9NjQJMO",
                        "valorant_round_id": "lskaQU9QySMh2PsT",
                        "is_main": true,
                        "player_info": {
                            "person_id": "ScpMeMTfFhBMwFaB",
                            "real_name": "光洪霖",
                            "real_name_en": "honglin guang",
                            "icon": "/cms/20240613/1718271435824.png",
                            "nationality_icon": "/wiki/flag/cn.png"
                        },
                        "career_info": {
                            "career_id": "75c2Zru9iF9Zz3OV",
                            "career_type": 1,
                            "id_name": "GuanG",
                            "position": "先锋/哨卫",
                            "career_status": 1
                        },
                        "hero": {
                            "unique_id": "wuySQOUgOWWPhg6P",
                            "hero_zh": "零",
                            "hero_en": "Cypher",
                            "icon": "/cms/20230704/1688450120784.png",
                            "times": 0
                        },
                        "acs": 263,
                        "rating": 0,
                        "kast": 0,
                        "adr": 163,
                        "hs": 31,
                        "fk": 5,
                        "fd": 2,
                        "kills": 21,
                        "deaths": 16,
                        "assists": 6,
                        "sort": 1
                    },
                    {
                        "unique_id": "Yt1rTHF1zcQgHPPG",
                        "match_id": "IJ2Nr2rJM9NjQJMO",
                        "valorant_round_id": "lskaQU9QySMh2PsT",
                        "is_main": true,
                        "player_info": {
                            "person_id": "CiHR4Im1lhdIJxyn",
                            "real_name": "赵泽骏",
                            "real_name_en": "ZEJUN ZHAO",
                            "icon": "/cms/20240613/1718256981089.png",
                            "nationality_icon": "/wiki/flag/cn.png"
                        },
                        "career_info": {
                            "career_id": "O7GWBtpva7GOdWWW",
                            "career_type": 1,
                            "id_name": "Ezeir",
                            "position": "控场",
                            "career_status": 1
                        },
                        "hero": {
                            "unique_id": "WPMz4M4DZfc6cgsp",
                            "hero_zh": "钛狐",
                            "hero_en": "Tejo",
                            "icon": "/cms/20250109/1736404558645.png",
                            "times": 0
                        },
                        "acs": 249,
                        "rating": 0,
                        "kast": 0,
                        "adr": 160,
                        "hs": 20,
                        "fk": 3,
                        "fd": 0,
                        "kills": 20,
                        "deaths": 15,
                        "assists": 7,
                        "sort": 2
                    },
                    {
                        "unique_id": "Omzs7iqa5QzhOc52",
                        "match_id": "IJ2Nr2rJM9NjQJMO",
                        "valorant_round_id": "lskaQU9QySMh2PsT",
                        "is_main": false,
                        "player_info": {
                            "person_id": "tdCCAx4WWFzTYc6K",
                            "real_name": "郑永康",
                            "real_name_en": "Zheng Yongkang",
                            "icon": "/cms/20250219/1739955437805.png",
                            "nationality_icon": "/wiki/flag/cn.png"
                        },
                        "career_info": {
                            "career_id": "mRRLRqtYmWktOZwu",
                            "career_type": 1,
                            "id_name": "ZmjjKK",
                            "position": "决斗",
                            "career_status": 1
                        },
                        "hero": {
                            "unique_id": "EWxouSwDbS4ogTAe",
                            "hero_zh": "幻棱",
                            "hero_en": "Waylay",
                            "icon": "/cms/20250310/1741598188505.jpg",
                            "times": 0
                        },
                        "acs": 196,
                        "rating": 0,
                        "kast": 0,
                        "adr": 124,
                        "hs": 22,
                        "fk": 5,
                        "fd": 6,
                        "kills": 13,
                        "deaths": 20,
                        "assists": 3,
                        "sort": 4
                    },
                    {
                        "unique_id": "z2wgS4D8ao5OQsQt",
                        "match_id": "IJ2Nr2rJM9NjQJMO",
                        "valorant_round_id": "lskaQU9QySMh2PsT",
                        "is_main": false,
                        "player_info": {
                            "person_id": "e9SBp4UPUSzSx9F6",
                            "real_name": "王森旭",
                            "real_name_en": "Wang Senxu",
                            "icon": "/cms/20250219/1739955913106.png",
                            "nationality_icon": "/wiki/flag/cn.png"
                        },
                        "career_info": {
                            "career_id": "pREeITp7ZkSSITdi",
                            "career_type": 1,
                            "id_name": "nobody",
                            "position": "指挥/先锋位",
                            "career_status": 1
                        },
                        "hero": {
                            "unique_id": "WPMz4M4DZfc6cgsp",
                            "hero_zh": "钛狐",
                            "hero_en": "Tejo",
                            "icon": "/cms/20250109/1736404558645.png",
                            "times": 0
                        },
                        "acs": 200,
                        "rating": 0,
                        "kast": 0,
                        "adr": 139,
                        "hs": 28,
                        "fk": 0,
                        "fd": 2,
                        "kills": 16,
                        "deaths": 18,
                        "assists": 2,
                        "sort": 3
                    },
                    {
                        "unique_id": "bUccDIldck7caedI",
                        "match_id": "IJ2Nr2rJM9NjQJMO",
                        "valorant_round_id": "lskaQU9QySMh2PsT",
                        "is_main": false,
                        "player_info": {
                            "person_id": "OkARoS17U86SnGbG",
                            "real_name": "万顺治",
                            "real_name_en": "Wan Shunzhi",
                            "icon": "/cms/20250219/1739955925114.png",
                            "nationality_icon": "/wiki/flag/cn.png"
                        },
                        "career_info": {
                            "career_id": "OJrRmS6GIIuQ5rtN",
                            "career_type": 1,
                            "id_name": "CHICHOO",
                            "position": "哨位/控场",
                            "career_status": 1
                        },
                        "hero": {
                            "unique_id": "wuySQOUgOWWPhg6P",
                            "hero_zh": "零",
                            "hero_en": "Cypher",
                            "icon": "/cms/20230704/1688450120784.png",
                            "times": 0
                        },
                        "acs": 183,
                        "rating": 0,
                        "kast": 0,
                        "adr": 116,
                        "hs": 23,
                        "fk": 2,
                        "fd": 2,
                        "kills": 14,
                        "deaths": 17,
                        "assists": 2,
                        "sort": 5
                    },
                    {
                        "unique_id": "1OEdH5hAk5gPoVPQ",
                        "match_id": "IJ2Nr2rJM9NjQJMO",
                        "valorant_round_id": "lskaQU9QySMh2PsT",
                        "is_main": false,
                        "player_info": {
                            "person_id": "Iz8LRJH2eOUsyrYM",
                            "real_name": "张钊",
                            "real_name_en": "Zhang Zhao",
                            "icon": "/cms/20250219/1739955933534.png",
                            "nationality_icon": "/wiki/flag/cn.png"
                        },
                        "career_info": {
                            "career_id": "5keqHlY6GBMTnMRs",
                            "career_type": 1,
                            "id_name": "Smoggy",
                            "position": "先锋/决斗",
                            "career_status": 1
                        },
                        "hero": {
                            "unique_id": "vs6LUy7isxmOZSeh",
                            "hero_zh": "炼狱",
                            "hero_en": "Brimstone",
                            "icon": "/cms/20230704/1688450086146.png",
                            "times": 0
                        },
                        "acs": 226,
                        "rating": 0,
                        "kast": 0,
                        "adr": 155,
                        "hs": 36,
                        "fk": 1,
                        "fd": 1,
                        "kills": 16,
                        "deaths": 17,
                        "assists": 9,
                        "sort": 1
                    },
                    {
                        "unique_id": "FguU2yxtz5mcZOLM",
                        "match_id": "IJ2Nr2rJM9NjQJMO",
                        "valorant_round_id": "lskaQU9QySMh2PsT",
                        "is_main": false,
                        "player_info": {
                            "person_id": "1zOfDgEqh8B7336j",
                            "real_name": "谢孟勳",
                            "real_name_en": "MENG-HSUN HSIEH",
                            "icon": "/cms/20250219/1739955511481.png",
                            "nationality_icon": "/wiki/flag/cn.png"
                        },
                        "career_info": {
                            "career_id": "UROKp13ClABcVeOo",
                            "career_type": 1,
                            "id_name": "S1Mon",
                            "position": "控场/哨位/信息位",
                            "career_status": 1
                        },
                        "hero": {
                            "unique_id": "Ivpz3Lel7O5wNTrp",
                            "hero_zh": "铁臂",
                            "hero_en": "Breach",
                            "icon": "/cms/20230704/1688450113156.png",
                            "times": 0
                        },
                        "acs": 210,
                        "rating": 0,
                        "kast": 0,
                        "adr": 144,
                        "hs": 38,
                        "fk": 0,
                        "fd": 2,
                        "kills": 14,
                        "deaths": 17,
                        "assists": 10,
                        "sort": 2
                    }
                ]
            },
            {
                "unique_id": "pJH4Ahu14hCvgnEO",
                "match_id": "IJ2Nr2rJM9NjQJMO",
                "box_number": 3,
                "time": "0'0",
                "is_overtime": false,
                "round_detail": [
                    {
                        "win_team": 0,
                        "win_camp": 0,
                        "mode": 0
                    },
                    {
                        "win_team": 0,
                        "win_camp": 0,
                        "mode": 0
                    },
                    {
                        "win_team": 0,
                        "win_camp": 0,
                        "mode": 0
                    },
                    {
                        "win_team": 0,
                        "win_camp": 0,
                        "mode": 0
                    },
                    {
                        "win_team": 0,
                        "win_camp": 0,
                        "mode": 0
                    },
                    {
                        "win_team": 0,
                        "win_camp": 0,
                        "mode": 0
                    },
                    {
                        "win_team": 0,
                        "win_camp": 0,
                        "mode": 0
                    },
                    {
                        "win_team": 0,
                        "win_camp": 0,
                        "mode": 0
                    },
                    {
                        "win_team": 0,
                        "win_camp": 0,
                        "mode": 0
                    },
                    {
                        "win_team": 0,
                        "win_camp": 0,
                        "mode": 0
                    },
                    {
                        "win_team": 0,
                        "win_camp": 0,
                        "mode": 0
                    },
                    {
                        "win_team": 0,
                        "win_camp": 0,
                        "mode": 0
                    },
                    {
                        "win_team": 0,
                        "win_camp": 0,
                        "mode": 0
                    },
                    {
                        "win_team": 0,
                        "win_camp": 0,
                        "mode": 0
                    },
                    {
                        "win_team": 0,
                        "win_camp": 0,
                        "mode": 0
                    },
                    {
                        "win_team": 0,
                        "win_camp": 0,
                        "mode": 0
                    },
                    {
                        "win_team": 0,
                        "win_camp": 0,
                        "mode": 0
                    },
                    {
                        "win_team": 0,
                        "win_camp": 0,
                        "mode": 0
                    },
                    {
                        "win_team": 0,
                        "win_camp": 0,
                        "mode": 0
                    },
                    {
                        "win_team": 0,
                        "win_camp": 0,
                        "mode": 0
                    },
                    {
                        "win_team": 0,
                        "win_camp": 0,
                        "mode": 0
                    },
                    {
                        "win_team": 0,
                        "win_camp": 0,
                        "mode": 0
                    },
                    {
                        "win_team": 0,
                        "win_camp": 0,
                        "mode": 0
                    },
                    {
                        "win_team": 0,
                        "win_camp": 0,
                        "mode": 0
                    }
                ],
                "map": {
                    "map_id": "SM14pNGuEEQ2xzeM",
                    "name_zh": "深海明珠",
                    "name_en": "Pearl",
                    "icon": "/cms/20230519/1684480093099.jpg"
                },
                "is_decider_map": false,
                "is_drop": true,
                "is_main_select_map": false,
                "is_main_select_first_strike": false,
                "mvp": null,
                "main_team": {
                    "team_id": "lAvuB3JCl3CVSHmt",
                    "team_name": "NOVA电子竞技俱乐部",
                    "team_name_short": "NOVA",
                    "team_icon": "/cms/20230530/1685429449194.png"
                },
                "guest_team": {
                    "team_id": "5gjweC11brGhuRBR",
                    "team_name": "EDward Gaming",
                    "team_name_short": "EDG",
                    "team_icon": "/cms/20230704/1688439753798.png"
                },
                "main_score": {
                    "total": 0,
                    "atk": 0,
                    "def": 0,
                    "over_time_atk": 0,
                    "over_time_def": 0
                },
                "guest_score": {
                    "total": 0,
                    "atk": 0,
                    "def": 0,
                    "over_time_atk": 0,
                    "over_time_def": 0
                },
                "vlr_player_relation": {},
                "vlr_url": "https://www.vlr.gg/450053/nova-esports-vs-edward-gaming-champions-tour-2025-china-stage-1-w2/?game=203474\u0026tab=overview",
                "is_auto_update_vlr": true,
                "is_vlr_analysis": true,
                "player_info": [
                    {
                        "unique_id": "ziuyRhVv68TGAvOl",
                        "match_id": "IJ2Nr2rJM9NjQJMO",
                        "valorant_round_id": "pJH4Ahu14hCvgnEO",
                        "is_main": true,
                        "player_info": {
                            "person_id": "sWMSaayCtS2z36IQ",
                            "real_name": "叶晓栋",
                            "real_name_en": "XIAODONG YE",
                            "icon": "/cms/20240613/1718271395624.png",
                            "nationality_icon": "/wiki/flag/cn.png"
                        },
                        "career_info": {
                            "career_id": "n8iSPU2QPGyUojqB",
                            "career_type": 1,
                            "id_name": "o0o0o",
                            "position": "决斗/控场/指挥",
                            "career_status": 1
                        },
                        "hero": null,
                        "acs": 0,
                        "rating": 0,
                        "kast": 0,
                        "adr": 0,
                        "hs": 0,
                        "fk": 0,
                        "fd": 0,
                        "kills": 0,
                        "deaths": 0,
                        "assists": 0,
                        "sort": 0
                    },
                    {
                        "unique_id": "ytF36867PLE8yodC",
                        "match_id": "IJ2Nr2rJM9NjQJMO",
                        "valorant_round_id": "pJH4Ahu14hCvgnEO",
                        "is_main": true,
                        "player_info": {
                            "person_id": "f3BZoKewkvMOQ1lr",
                            "real_name": "陈羿杰",
                            "real_name_en": "YIJIE CHEN",
                            "icon": "/cms/20240613/1718271533289.png",
                            "nationality_icon": "/wiki/flag/cn.png"
                        },
                        "career_info": {
                            "career_id": "swmIl4cSz1JIVtMe",
                            "career_type": 1,
                            "id_name": "OBONE",
                            "position": "控场",
                            "career_status": 1
                        },
                        "hero": null,
                        "acs": 0,
                        "rating": 0,
                        "kast": 0,
                        "adr": 0,
                        "hs": 0,
                        "fk": 0,
                        "fd": 0,
                        "kills": 0,
                        "deaths": 0,
                        "assists": 0,
                        "sort": 0
                    },
                    {
                        "unique_id": "HRyDsAaUweEFAlJQ",
                        "match_id": "IJ2Nr2rJM9NjQJMO",
                        "valorant_round_id": "pJH4Ahu14hCvgnEO",
                        "is_main": true,
                        "player_info": {
                            "person_id": "2gvTTzVGI6HTTcp8",
                            "real_name": "王晴川",
                            "real_name_en": "Qingchuan Wang",
                            "icon": "/cms/20240613/1718271457183.png",
                            "nationality_icon": "/wiki/flag/cn.png"
                        },
                        "career_info": {
                            "career_id": "cY1VMMZ24dGypV3D",
                            "career_type": 1,
                            "id_name": "cb",
                            "position": "先锋/信息位",
                            "career_status": 1
                        },
                        "hero": null,
                        "acs": 0,
                        "rating": 0,
                        "kast": 0,
                        "adr": 0,
                        "hs": 0,
                        "fk": 0,
                        "fd": 0,
                        "kills": 0,
                        "deaths": 0,
                        "assists": 0,
                        "sort": 0
                    },
                    {
                        "unique_id": "n8dSn2tuZuB8ihfg",
                        "match_id": "IJ2Nr2rJM9NjQJMO",
                        "valorant_round_id": "pJH4Ahu14hCvgnEO",
                        "is_main": true,
                        "player_info": {
                            "person_id": "ScpMeMTfFhBMwFaB",
                            "real_name": "光洪霖",
                            "real_name_en": "honglin guang",
                            "icon": "/cms/20240613/1718271435824.png",
                            "nationality_icon": "/wiki/flag/cn.png"
                        },
                        "career_info": {
                            "career_id": "75c2Zru9iF9Zz3OV",
                            "career_type": 1,
                            "id_name": "GuanG",
                            "position": "先锋/哨卫",
                            "career_status": 1
                        },
                        "hero": null,
                        "acs": 0,
                        "rating": 0,
                        "kast": 0,
                        "adr": 0,
                        "hs": 0,
                        "fk": 0,
                        "fd": 0,
                        "kills": 0,
                        "deaths": 0,
                        "assists": 0,
                        "sort": 0
                    },
                    {
                        "unique_id": "VLd2Jd11IL92wZ3j",
                        "match_id": "IJ2Nr2rJM9NjQJMO",
                        "valorant_round_id": "pJH4Ahu14hCvgnEO",
                        "is_main": true,
                        "player_info": {
                            "person_id": "CiHR4Im1lhdIJxyn",
                            "real_name": "赵泽骏",
                            "real_name_en": "ZEJUN ZHAO",
                            "icon": "/cms/20240613/1718256981089.png",
                            "nationality_icon": "/wiki/flag/cn.png"
                        },
                        "career_info": {
                            "career_id": "O7GWBtpva7GOdWWW",
                            "career_type": 1,
                            "id_name": "Ezeir",
                            "position": "控场",
                            "career_status": 1
                        },
                        "hero": null,
                        "acs": 0,
                        "rating": 0,
                        "kast": 0,
                        "adr": 0,
                        "hs": 0,
                        "fk": 0,
                        "fd": 0,
                        "kills": 0,
                        "deaths": 0,
                        "assists": 0,
                        "sort": 0
                    },
                    {
                        "unique_id": "2LZkdL5i8GroEyBQ",
                        "match_id": "IJ2Nr2rJM9NjQJMO",
                        "valorant_round_id": "pJH4Ahu14hCvgnEO",
                        "is_main": false,
                        "player_info": {
                            "person_id": "tdCCAx4WWFzTYc6K",
                            "real_name": "郑永康",
                            "real_name_en": "Zheng Yongkang",
                            "icon": "/cms/20250219/1739955437805.png",
                            "nationality_icon": "/wiki/flag/cn.png"
                        },
                        "career_info": {
                            "career_id": "mRRLRqtYmWktOZwu",
                            "career_type": 1,
                            "id_name": "ZmjjKK",
                            "position": "决斗",
                            "career_status": 1
                        },
                        "hero": null,
                        "acs": 0,
                        "rating": 0,
                        "kast": 0,
                        "adr": 0,
                        "hs": 0,
                        "fk": 0,
                        "fd": 0,
                        "kills": 0,
                        "deaths": 0,
                        "assists": 0,
                        "sort": 0
                    },
                    {
                        "unique_id": "MHYSgaI9JLF6hc2G",
                        "match_id": "IJ2Nr2rJM9NjQJMO",
                        "valorant_round_id": "pJH4Ahu14hCvgnEO",
                        "is_main": false,
                        "player_info": {
                            "person_id": "e9SBp4UPUSzSx9F6",
                            "real_name": "王森旭",
                            "real_name_en": "Wang Senxu",
                            "icon": "/cms/20250219/1739955913106.png",
                            "nationality_icon": "/wiki/flag/cn.png"
                        },
                        "career_info": {
                            "career_id": "pREeITp7ZkSSITdi",
                            "career_type": 1,
                            "id_name": "nobody",
                            "position": "指挥/先锋位",
                            "career_status": 1
                        },
                        "hero": null,
                        "acs": 0,
                        "rating": 0,
                        "kast": 0,
                        "adr": 0,
                        "hs": 0,
                        "fk": 0,
                        "fd": 0,
                        "kills": 0,
                        "deaths": 0,
                        "assists": 0,
                        "sort": 0
                    },
                    {
                        "unique_id": "SrvqidiskQWshBGy",
                        "match_id": "IJ2Nr2rJM9NjQJMO",
                        "valorant_round_id": "pJH4Ahu14hCvgnEO",
                        "is_main": false,
                        "player_info": {
                            "person_id": "OkARoS17U86SnGbG",
                            "real_name": "万顺治",
                            "real_name_en": "Wan Shunzhi",
                            "icon": "/cms/20250219/1739955925114.png",
                            "nationality_icon": "/wiki/flag/cn.png"
                        },
                        "career_info": {
                            "career_id": "OJrRmS6GIIuQ5rtN",
                            "career_type": 1,
                            "id_name": "CHICHOO",
                            "position": "哨位/控场",
                            "career_status": 1
                        },
                        "hero": null,
                        "acs": 0,
                        "rating": 0,
                        "kast": 0,
                        "adr": 0,
                        "hs": 0,
                        "fk": 0,
                        "fd": 0,
                        "kills": 0,
                        "deaths": 0,
                        "assists": 0,
                        "sort": 0
                    },
                    {
                        "unique_id": "5cVEvbqiodDS65QG",
                        "match_id": "IJ2Nr2rJM9NjQJMO",
                        "valorant_round_id": "pJH4Ahu14hCvgnEO",
                        "is_main": false,
                        "player_info": {
                            "person_id": "Iz8LRJH2eOUsyrYM",
                            "real_name": "张钊",
                            "real_name_en": "Zhang Zhao",
                            "icon": "/cms/20250219/1739955933534.png",
                            "nationality_icon": "/wiki/flag/cn.png"
                        },
                        "career_info": {
                            "career_id": "5keqHlY6GBMTnMRs",
                            "career_type": 1,
                            "id_name": "Smoggy",
                            "position": "先锋/决斗",
                            "career_status": 1
                        },
                        "hero": null,
                        "acs": 0,
                        "rating": 0,
                        "kast": 0,
                        "adr": 0,
                        "hs": 0,
                        "fk": 0,
                        "fd": 0,
                        "kills": 0,
                        "deaths": 0,
                        "assists": 0,
                        "sort": 0
                    },
                    {
                        "unique_id": "jkit1cUWcjqWz6y7",
                        "match_id": "IJ2Nr2rJM9NjQJMO",
                        "valorant_round_id": "pJH4Ahu14hCvgnEO",
                        "is_main": false,
                        "player_info": {
                            "person_id": "1zOfDgEqh8B7336j",
                            "real_name": "谢孟勳",
                            "real_name_en": "MENG-HSUN HSIEH",
                            "icon": "/cms/20250219/1739955511481.png",
                            "nationality_icon": "/wiki/flag/cn.png"
                        },
                        "career_info": {
                            "career_id": "UROKp13ClABcVeOo",
                            "career_type": 1,
                            "id_name": "S1Mon",
                            "position": "控场/哨位/信息位",
                            "career_status": 1
                        },
                        "hero": null,
                        "acs": 0,
                        "rating": 0,
                        "kast": 0,
                        "adr": 0,
                        "hs": 0,
                        "fk": 0,
                        "fd": 0,
                        "kills": 0,
                        "deaths": 0,
                        "assists": 0,
                        "sort": 0
                    }
                ]
            }
        ]
    }
}
""")
main(testdata)