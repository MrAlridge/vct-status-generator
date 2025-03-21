from cProfile import label
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
    FONT_TITLE_SIZE = 24    # 选手名字相关的字体
    FONT_TITLE_BG_COLOR = (88, 31, 31) # 名字背景的颜色
    FONT_TITLE_COLOR = (250, 250, 250)  # 背景的名字就用白色

    try:
      FONT = ImageFont.truetype(font_path, FONT_SIZE)
      TITLE_FONT = ImageFont.truetype(font_path, FONT_TITLE_SIZE)
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
    
    d.rectangle([(x,y+3),(x+100,y+FONT_TITLE_SIZE+3)], fill=FONT_TITLE_BG_COLOR)
    d.text((x, y), player_data['career_info']['id_name'], font=TITLE_FONT, fill=FONT_TITLE_COLOR)
    y += FONT_TITLE_SIZE + 5
    d.text((x, y), player_data['player_info']['real_name'], font=TITLE_FONT, fill=TEXT_COLOR)
    y += FONT_TITLE_SIZE + 5
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
        ("ADR", "adr"),
        # ("HS%", "hs"),
        # ("FK", "fk"),
        # ("FD", "fd"),
        ("K /", "kills"),
        ("D /", "deaths"),
        ("A", "assists"),
        ("KAST", "kast"),
    ]
    data_x = 10

    # 自己来排版
    for i, (label, key) in enumerate(data_fields):
        value = player_data[key]
        if isinstance(value, float):
            value = f"{value:.2f}"
        d.text((data_x, y), f"{label}\n{value}", font=FONT, fill=TEXT_COLOR)
        data_x += 60
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
testdata = json.loads("""""")# 这里直接load测试数据
main(testdata)