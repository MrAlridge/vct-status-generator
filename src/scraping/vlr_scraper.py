import requests
import time
from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin # 用于处理相对 URL
import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, exists

import re

# --- 核心库导入 ---
from src.core.database import SessionLocal # SessionLocal might be needed for direct testing if __name__ == '__main__'
from src.core.models import Match, Region, Player, PlayerMatchStats

logger = logging.getLogger(__name__)

# --- Constants ---
BASE_URL = "https://vlr.gg"
MATCHES_URL = f"{BASE_URL}/matches"
MATCHES_RESULTS_URL = f"{BASE_URL}/matches/results"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
def _safe_cast(value, cast_type, default=None):
    """尝试将值转换为指定类型，失败则返回默认值。 Handles %, +/-, surrounding /."""
    if value is None:
        return default
    try:
        # More robust cleaning
        cleaned_value = str(value).strip().replace('%', '').replace('/', '').strip()
        # Handle leading '+' explicitly if cast_type is numeric
        if cast_type in (int, float) and cleaned_value.startswith('+'):
             cleaned_value = cleaned_value[1:]

        if cast_type is int:
            # Handle negative numbers explicitly, isdigit doesn't handle '-'
            if cleaned_value.startswith('-') and cleaned_value[1:].isdigit():
                return cast_type(cleaned_value)
            elif cleaned_value.isdigit():
                return cast_type(cleaned_value)
            else: return default
        elif cast_type is float:
            # Allow negative floats and floats starting with '.'
            # Check if it looks like a number (potentially with one '.' and maybe a leading '-')
            if (cleaned_value.startswith('-') and cleaned_value[1:].replace('.', '', 1).isdigit()) or \
               (cleaned_value.replace('.', '', 1).isdigit()):
                 return cast_type(cleaned_value)
            elif cleaned_value.startswith(".") and cleaned_value[1:].isdigit(): # Handle cases like ".5"
                 return cast_type(f"0{cleaned_value}")
            elif cleaned_value.startswith("-.") and cleaned_value[2:].isdigit(): # Handle cases like "-.5"
                 return cast_type(f"-0{cleaned_value[1:]}")
            else: return default
        elif cast_type is str:
             return cleaned_value # Return the cleaned string
        return default # If cast_type is not int, float, or str
    except (ValueError, TypeError):
        return default

def _parse_player_source_id(player_url: str | None) -> str | None:
    """从 vlr.gg 玩家 URL (e.g., /player/123/xyz) 中提取 ID。"""
    if not player_url:
        return None
    match = re.search(r'/player/(\d+)/', player_url)
    if match:
        return match.group(1)
    logger.warning(f"Could not parse player source ID from URL: {player_url}")
    return None

# --- 1. 获取 HTML ---
def fetch_html(url: str) -> str | None:
    """
    获取指定 URL 的 HTML 内容。

    Args:
        url: 要抓取的 URL。

    Returns:
        HTML 内容字符串，如果请求失败则返回 None。
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=15) # 设置超时
        response.raise_for_status() # 如果状态码不是 2xx，则引发 HTTPError
        logger.info(f"成功抓取内容来自: {url}")
        return response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"抓取时出错 {url}: {e}")
        return None
    # 添加短暂延迟，尊重服务器资源
    finally:
        # ::OPERATIONAL_CONCERN:: - 避免过快请求导致 IP 被封禁
        time.sleep(1.5)

# --- 2. 解析比赛列表 ---
def parse_match_list(html_content: str, source_url: str) -> list[dict]:
    """
    解析 vlr.gg/matches 页面 HTML，提取比赛列表信息。

    Args:
        html_content: 包含 vlr.gg/matches 页面内容的 HTML 字符串。

    Returns:
        一个字典列表，每个字典代表一场比赛，包含:
        - 'match_source_id': 从 URL 中提取的 vlr.gg 比赛 ID (str)。
        - 'match_url': 比赛详情页的绝对 URL (str)。
        - 'status': 比赛状态 (e.g., 'Upcoming', 'Live') (str)。
        - 'context': 简短的描述信息，用于日志记录 (str)。
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    matches = []

    # vlr.gg 的结构可能会变化，需要根据实际情况调整选择器。
    match_elements = soup.select('a.match-item') # 使用 CSS 选择器
    logger.info(f"Found {len(match_elements)} potential match elements on {source_url}.")
    processed_ids = set() # 跟踪已处理的 ID，防止因 HTML 结构重复添加

    for element in match_elements:
        href = element.get('href')
        if not href or len(href.split('/')) < 2 or not href.split('/')[1].isdigit():
            logger.warning(f"跳过元素, 因为无法从链接中解压出有效的比赛ID: {element.get('href')}")
            continue # 跳过无效链接

        match_id = href.split('/')[1]
        if match_id in processed_ids: continue
        processed_ids.add(match_id)
        match_url = BASE_URL + href

        # 提取状态 (Live/Upcoming/Completed)
        status_element = element.find('div', class_='ml-status')
        status_text = status_element.text.strip() if status_element else 'Unknown'
        # 有时 'final' 状态会在一个 span 内，也提取一下
        if status_text == "" and status_element:
            final_span = status_element.find('span', class_='ml-status-label')
            if final_span: status_text = final_span.text.strip()

        # 标准化一下常见的完成状态
        if status_text.lower() == 'final': status_text = 'Completed'

        # 提取队伍名称 (需要更仔细地定位)
        team_elements = element.select('.match-item-vs-team-name .text-of')
        team1_name = team_elements[0].text.strip() if len(team_elements) > 0 else None
        team2_name = team_elements[1].text.strip() if len(team_elements) > 1 else None

        # 提取赛事名称
        event_element = element.select_one('.match-item-event .text-of')
        event_subtext_element = element.select_one('.match-item-event-series.text-of') # 有时赛事名称分两行
        event_name = event_element.text.strip() if event_element else None
        if event_subtext_element:
            sub_text = event_subtext_element.text.strip()
            if event_name and sub_text and sub_text.lower() not in event_name.lower():
                # 合并主赛事和子系列名称，用冒号分隔（或根据实际需要调整）
                # 检查子文本是否已包含在主事件名称中，避免重复 
                event_name = f"{event_name}: {sub_text}"
            elif sub_text:
                 event_name = sub_text # 如果只有子文本
        
        # 提取比分 (在结果页更常见)
        score_elements = element.select('match-item-vs-team-score  js-spoiler')
        team1_score_str = score_elements[0].text.strip() if len(score_elements) > 0 else None
        team2_score_str = score_elements[1].text.strip() if len(score_elements) > 1 else None
        team1_score = _safe_cast(team1_score_str, int)
        team2_score = _safe_cast(team2_score_str, int)

        match_data = {
            'match_source_id': match_id, 'match_url': match_url, 'status': status_text,
            'team1_name': team1_name, 'team2_name': team2_name,
            'team1_score': team1_score, 'team2_score': team2_score,
            'event_name': event_name,
        }
        matches.append(match_data)

    logger.info(f"成功向列表中传递了 {len(matches)} 独特的赛程.")
    return matches

# --- 5. 保存比赛数据 ---
def save_basic_match_info(db_session: Session, match_data: dict, region_mapping: dict[str, int]):
    """
    保存单场比赛的基础信息到数据库，并尝试推断赛区。

    Args:
        db_session: SQLAlchemy 数据库会话。
        match_data: 从 parse_match_list 获取的单个比赛字典。
        region_mapping: 赛区的映射
    """
    match_source_id = match_data['match_source_id']
    # ... (提取其他字段) ...
    determined_region_id = None
    event_name = match_data.get('event_name')
    team1_score = match_data.get('team1_score')
    team2_score = match_data.get('team2_score')
    status = match_data['status']
    team1_name = match_data['team1_name']
    team2_name = match_data['team2_name']
    match_url = match_data['match_url']

    # --- 区域推断逻辑 ---
    if event_name:
        event_name_upper = event_name.upper()
        for abbr, region_id in region_mapping.items():
             if abbr and abbr in event_name_upper: # 简单的子串检查
                determined_region_id = region_id
                break # 找到第一个就停止
    try:
        # 检查比赛是否已存在
        existing_match = db_session.query(Match).filter(Match.match_source_id == match_source_id).first()
        if existing_match:
            updated = False
            if existing_match.status != status: existing_match.status = status; updated = True
            if existing_match.team1_score is None and team1_score is not None: existing_match.team1_score = team1_score; updated = True
            if existing_match.team2_score is None and team2_score is not None: existing_match.team2_score = team2_score; updated = True
            if existing_match.team1_name is None and team1_name: existing_match.team1_name = team1_name; updated = True
            if existing_match.team2_name is None and team2_name: existing_match.team2_name = team2_name; updated = True
            if existing_match.event_name is None and event_name: existing_match.event_name = event_name; updated = True
            if existing_match.region_id is None and determined_region_id is not None: existing_match.region_id = determined_region_id; updated = True
            if updated: logger.info(f"[*] Updated details for existing match ID {match_source_id}.")
        else:
            # 添加新比赛
            logger.info(f"[+] Adding new match: ID {match_source_id}, Status: {status}, Event: '{event_name}', RegionID: {determined_region_id}")
            new_match = Match(
                match_source_id=match_source_id, match_url=match_url, status=status,
                team1_name=team1_name, team2_name=team2_name,
                team1_score=team1_score, team2_score=team2_score,
                event_name=event_name, region_id=determined_region_id
            )
            db_session.add(new_match)
    except Exception as e:
        db_session.rollback() # 重要：出错时回滚当前比赛的操作
        logger.error(f"  [!] Error saving match ID {match_source_id}: {e}")
        # 抛出异常或采取其他措施，取决于是否希望单个错误停止整个批处理
        # raise e # 如果希望停止

# --- 爬取页面用到的助手函数 ---
def _scrape_and_parse_page(url: str) -> list[dict]:
    """获取并解析指定 URL 的比赛列表。"""
    logger.info(f"--- Scraping page: {url} ---")
    html = fetch_html(url)
    if not html:
        logger.error(f"Failed to fetch HTML from {url}. Skipping this page.")
        return []
    parsed_data = parse_match_list(html, url)
    return parsed_data

# --- 6. 主协调函数 ---
def scrape_matches(db_session: Session):
    """
    执行抓取比赛列表并将基础信息保存到数据库的主逻辑。
    """
    logger.info("--- 开始: 抓取赛程列表&保存基础信息 ---")

    # --- 加载赛区映射 ---
    region_mapping = {}
    try:
        regions = db_session.query(Region).all()
        # 使用大写缩写作为键，方便不区分大小写比较
        # 只包含有缩写的赛区
        region_mapping = {
             r.abbreviation.upper(): r.id
             for r in regions if r.abbreviation
         }
        logger.info(f"加载了 {len(region_mapping)} 个带有缩写的赛区进映射.")
    except Exception as e:
         logger.error(f"从数据库中加载赛区映射失败: {e}")
         # 根据需要决定是否继续，这里选择继续但区域推断会失败
         region_mapping = {}

    upcoming_matches = _scrape_and_parse_page(MATCHES_URL)
    completed_matches = _scrape_and_parse_page(MATCHES_RESULTS_URL)

    # --- 合并列表 ---
    # 使用字典按 ID 合并，以处理可能在两页都短暂出现的比赛
    # 让来自 /matches/results 的数据（通常更新）覆盖 /matches 的数据
    all_matches_dict = {m['match_source_id']: m for m in upcoming_matches}
    for m in completed_matches:
        # 如果 ID 已存在，用结果页的数据更新；否则添加新的
        all_matches_dict[m['match_source_id']] = m

    all_parsed_matches = list(all_matches_dict.values())

    if not all_parsed_matches:
        logger.warning("No matches found or parsed from any page.")
        return

    # 3. 保存到数据库
    logger.info(f"\n--- 处理 {len(all_parsed_matches)} 场比赛 ---")
    processed_count = 0
    try:
        for match_data in all_parsed_matches:
            # 传入区域映射
            save_basic_match_info(db_session, match_data, region_mapping)
            processed_count += 1

        logger.info(f"\n处理了 {processed_count} 场比赛. 将改动提交至数据库...")
        db_session.commit() # 提交所有成功处理的比赛
        logger.info("成功提交至数据库.")
    except Exception as e:
        logger.error(f"在本批次处理或提交中发生错误: {e}")
        db_session.rollback() # 回滚整个批次以防部分提交
        logger.warning("数据库由于错误已回滚整个批次.")
    finally:
        # Session 的关闭由调用者 (manage.py 中的 with 语句) 处理
        logger.info("正在强制关闭数据库会话.")

    logger.info("--- 完成: 抓取赛程列表&保存基础信息 ---")

# --- 3. 解析比赛详情 ---
def parse_match_details(html_content: str, match_url: str) -> list[dict]:
    """
    从单个比赛详情页面的 HTML 中解析所有选手的统计数据 ("All Maps" tab)。
    返回一个包含每个选手统计信息的字典列表。
    """
    logger.info(f"Parsing detailed stats from URL: {match_url}")
    soup = BeautifulSoup(html_content, 'html.parser')
    all_player_stats = []
    # --- Find the 'All Maps' game container ---
    stats_container_all_maps = soup.select_one('div.vm-stats-game[data-game-id="all"]')

    if not stats_container_all_maps:
        logger.warning(f"Could not find the 'All Maps' stats container (div.vm-stats-game[data-game-id='all']) on {match_url}")
        # Optional Fallback: Try finding any stats container if 'all' does not exist (less reliable)
        stats_container_all_maps = soup.select_one('div.vm-stats-container div.vm-stats-game')
        if not stats_container_all_maps:
             logger.error(f"No stats container found at all on {match_url}")
             return [] # Return empty if no suitable container found
        else:
             logger.warning(f"Using the first available 'vm-stats-game' container as fallback on {match_url}")

    # --- Find *all* stats tables within the 'All Maps' container ---
    # These tables contain the player stats, usually one table per team.
    stats_tables = stats_container_all_maps.select('table.wf-table-inset.mod-overview')

    if not stats_tables:
        logger.warning(f"No stats tables (table.wf-table-inset.mod-overview) found within the stats container on {match_url}")
        return []

    logger.info(f"Found {len(stats_tables)} stats tables in the selected section.")

    # --- Iterate through each table (should be 2, one per team) ---
    for table_index, stats_table in enumerate(stats_tables):
        if not stats_table or not stats_table.tbody:
            logger.warning(f"Table {table_index+1} is missing a tbody on {match_url}. Skipping.")
            continue

        rows = stats_table.tbody.find_all('tr')
        logger.info(f"Processing Table {table_index+1}: Found {len(rows)} player rows.")

        for row_index, row in enumerate(rows):
            if not isinstance(row, Tag): continue # Skip non-Tag elements like NavigableString
            cells = row.find_all('td')

            # Expected columns: Player | Agent | R | ACS | K | D | A | +/- | KAST | ADR | HS% | FK | FD | +/-
            # Check based on the latest HTML snippet
            min_expected_cells = 14
            if len(cells) < min_expected_cells:
                logger.warning(f"Skipping row {row_index+1} in table {table_index+1}, expected >= {min_expected_cells} cells, found {len(cells)}. URL: {match_url}")
                continue

            try:
                # --- Player Info (Cell 0) ---
                player_cell = cells[0]
                player_link_tag = player_cell.find('a')
                player_name_tag = player_link_tag.find('div', class_='text-of') if player_link_tag else None
                team_name_tag = player_link_tag.find('div', class_='ge-text-light') if player_link_tag else None

                player_name = player_name_tag.text.strip() if player_name_tag else None
                # Make player URL absolute
                player_url_relative = player_link_tag['href'] if player_link_tag and player_link_tag.has_attr('href') else None
                player_url = urljoin(BASE_URL, player_url_relative) if player_url_relative else None
                player_source_id = _parse_player_source_id(player_url_relative) # Use relative for parsing ID
                team_name = team_name_tag.text.strip() if team_name_tag else None # Team abbreviation (e.g., JDG, TE)

                # --- Agents (Cell 1) ---
                agent_cell = cells[1]
                # Use more specific selector and get 'title' attribute which usually holds the name
                agent_imgs = agent_cell.select('span.stats-sq.mod-agent img')
                agents = [img.get('title', '').strip() for img in agent_imgs if img.get('title')]
                # Fallback to alt attribute if title is missing
                if not agents:
                    agents = [img.get('alt', '').strip() for img in agent_imgs if img.get('alt')]
                agent_str = "/".join(a for a in agents if a) if agents else None # Ensure empty names aren't joined

                # --- Helper to get stat text from the 'mod-both' span ---
                def get_stat_text(cell_index, nested_selector='span.mod-both'):
                    cell = cells[cell_index]
                    stat_tag = cell.select_one(nested_selector) if nested_selector else cell # If no nested, get cell text
                    # Handle cases where the stat is directly in the cell or in the nested span
                    if stat_tag:
                         return stat_tag.text.strip()
                    elif not nested_selector: # If we intended to get direct cell text
                         return cell.text.strip()
                    else: # Target span not found
                        # Sometimes the value might be directly in the cell if span structure is missing
                        direct_text = cell.text.strip()
                        # Basic check if direct text looks like a number or common stat format
                        if direct_text and (direct_text[0].isdigit() or direct_text[0] in "+-."):
                            logger.debug(f"Stat tag '{nested_selector}' not found in cell {cell_index}, using direct cell text: '{direct_text}'")
                            return direct_text
                        return None # Give up if neither span nor direct text seems valid

                # --- Extract Stats using the helper ---
                # Indices based on the provided HTML:
                # 0: Player, 1: Agent, 2: R, 3: ACS, 4: K, 5: D, 6: A, 7: KD+/-,
                # 8: KAST, 9: ADR, 10: HS%, 11: FK, 12: FD, 13: FKFD+/-
                rating_text = get_stat_text(2)
                acs_text = get_stat_text(3)
                kills_text = get_stat_text(4) # K/D/A use mod-both directly
                deaths_text = get_stat_text(5) # Has '/' around it
                assists_text = get_stat_text(6)
                kd_diff_text = get_stat_text(7)
                kast_text = get_stat_text(8) # KAST uses %
                adr_text = get_stat_text(9, nested_selector='span.mod-combat span.mod-both') # ADR is nested differently
                if not adr_text: adr_text = get_stat_text(9) # Fallback if specific ADR structure missing
                hs_percent_text = get_stat_text(10) # HS% uses %
                first_kills_text = get_stat_text(11)
                first_deaths_text = get_stat_text(12)
                fkfd_diff_text = get_stat_text(13)

                # --- Casting with updated _safe_cast ---
                rating = _safe_cast(rating_text, float)
                acs = _safe_cast(acs_text, int)
                kills = _safe_cast(kills_text, int)
                deaths = _safe_cast(deaths_text, int) # _safe_cast now handles '/'
                assists = _safe_cast(assists_text, int)
                kill_death_difference = _safe_cast(kd_diff_text, int) # _safe_cast handles '+'
                kast_percentage = _safe_cast(kast_text, float) # _safe_cast handles '%'
                adr = _safe_cast(adr_text, int) # Example showed ADR=158, seems int. Change to float if needed.
                headshot_percentage = _safe_cast(hs_percent_text, float) # _safe_cast handles '%'
                first_kills = _safe_cast(first_kills_text, int)
                first_deaths = _safe_cast(first_deaths_text, int)
                first_kill_first_death_difference = _safe_cast(fkfd_diff_text, int) # _safe_cast handles '+'

                # --- Recalculate differences (Safety Check) ---
                # Recalculate if direct parse failed/returned None but components are available
                if kill_death_difference is None and kills is not None and deaths is not None:
                     kill_death_difference = kills - deaths
                     logger.debug(f"Recalculated KD diff for {player_name}: {kill_death_difference}")
                if first_kill_first_death_difference is None and first_kills is not None and first_deaths is not None:
                     first_kill_first_death_difference = first_kills - first_deaths
                     logger.debug(f"Recalculated FKFD diff for {player_name}: {first_kill_first_death_difference}")

                # --- Assemble Dictionary ---
                player_stats = {
                    'player_name': player_name,
                    'player_source_id': player_source_id,
                    'team_name': team_name, # Store the team abbreviation found in this row
                    'agent': agent_str,
                    'rating': rating,
                    'acs': acs,
                    'kills': kills,
                    'deaths': deaths,
                    'assists': assists,
                    'kill_death_difference': kill_death_difference,
                    'kast_percentage': kast_percentage,
                    'adr': adr,
                    'headshot_percentage': headshot_percentage,
                    'first_kills': first_kills,
                    'first_deaths': first_deaths,
                    'first_kill_first_death_difference': first_kill_first_death_difference,
                 }
                # Log the parsed data for one player for verification
                # if row_index == 0: logger.debug(f"Parsed player data sample: {player_stats}")

                all_player_stats.append(player_stats)

            except Exception as e:
                # Log error with more context but continue processing other rows/tables
                logger.error(f"Failed to parse row {row_index+1} in table {table_index+1} on {match_url}. Error: {e}. Row HTML (truncated): {str(row)[:300]}...", exc_info=True)

    logger.info(f"Successfully parsed detailed stats for {len(all_player_stats)} players from {len(stats_tables)} tables on {match_url}")
    return all_player_stats

def _get_or_create_player(db_session: Session, player_name: str, player_source_id: str | None) -> Player | None: # Made async to align if needed, but sync Session used now
    """查找或创建 Player 记录。优先使用 player_source_id 查找。"""
    if not player_source_id and not player_name: return None
    player = None
    if player_source_id:
        stmt = select(Player).where(Player.player_source_id == player_source_id)
        player = db_session.execute(stmt).scalar_one_or_none()
    if player is None and player_name:
        stmt = select(Player).where(Player.name == player_name)
        player_tuple = db_session.execute(stmt).first()
        if player_tuple:
             player = player_tuple[0]
             if player_source_id and player.player_source_id is None:
                 logger.info(f"Updating existing player '{player_name}' (ID: {player.id}) with source ID: {player_source_id}")
                 player.player_source_id = player_source_id
    if player is None:
        if player_name:
            logger.info(f"Creating new player: Name='{player_name}', SourceID='{player_source_id or 'N/A'}'")
            new_player = Player(name=player_name, player_source_id=player_source_id)
            db_session.add(new_player)
            try:
                db_session.flush(); player = new_player
            except Exception as e:
                 logger.error(f"Failed to flush new player '{player_name}'. Error: {e}")
                 db_session.rollback(); return None
        else: return None
    return player

def save_match_details(db_session: Session, match: Match, detailed_stats: list[dict]):
    """将解析出的详细统计数据保存到数据库 (Player 和 PlayerMatchStats)。"""
    logger.info(f"Attempting to save detailed stats for Match ID: {match.match_source_id} (DB ID: {match.id})")
    if not match or match.id is None: logger.error("Invalid Match object"); return
    players_processed, stats_added, stats_existing = 0, 0, 0
    for player_data in detailed_stats:
        player_name = player_data.get('player_name')
        player_source_id = player_data.get('player_source_id')
        if not player_name and not player_source_id: continue
        try:
             player = _get_or_create_player(db_session, player_name, player_source_id) # Call sync version
             if not player or player.id is None: logger.error(f"Failed get/create player '{player_name}'."); continue
             players_processed += 1
             stmt = select(exists().where(
                 PlayerMatchStats.player_id == player.id,
                 PlayerMatchStats.match_id == match.id
             ))
             stat_exists = db_session.execute(stmt).scalar()

             if not stat_exists:
                 logger.info(f"  [+] Adding stats for Player ID: {player.id} ('{player.name}') in Match ID: {match.id}")
                 # * --- 新增：定义 PlayerMatchStats 的有效字段 ---
                 # * 这些字段名必须与 src/core/models.py 中 PlayerMatchStats 类的 Mapped 列名完全匹配
                 allowed_keys = {
                     'team_name',          # Team player played for IN THIS MATCH
                     'agent',              # Agent(s) played
                     'rating',
                     'acs',                # Average Combat Score
                     'kills',
                     'deaths',
                     'assists',
                     'kill_death_difference', # K-D
                     'adr',                # Average Damage per Round
                     'kast_percentage',    # Kill, Assist, Survive, Trade %
                     'headshot_percentage',# HS%
                     'first_kills',        # FK
                     'first_deaths',       # FD
                     'first_kill_first_death_difference' # FK-FD
                 }
                 # --- 新增：从 player_data 过滤出有效字段 ---
                 stats_payload = {
                     key: player_data.get(key) # 使用 .get() 更安全，尽管我们期望键存在
                     for key in allowed_keys
                     if key in player_data # 只包含 player_data 中实际存在的允许键
                 }
                 # 可选：记录一下最终要插入的 payload，用于调试
                 # logger.debug(f"    Payload for PlayerMatchStats: {stats_payload}")
                 # -------------------------------------------------
                 try:
                     # --- 修改：使用过滤后的 stats_payload ---
                     new_stats = PlayerMatchStats(
                         player_id=player.id,
                         match_id=match.id,
                         **stats_payload  # 使用过滤后的字典
                     )
                     db_session.add(new_stats)
                     stats_added += 1
                 except Exception as e_create:
                     # 捕获创建实例时可能发生的其他错误
                     logger.error(f"  [!] Error creating PlayerMatchStats instance for player {player.id} match {match.id}. Payload: {stats_payload}. Error: {e_create}", exc_info=True)
             else:
                 logger.info(f"  [=] Stats already exist for Player ID: {player.id} ('{player.name}') in Match ID: {match.id}. Skipping.")
                 stats_existing += 1
        except Exception as e:
            logger.error(f"Failed to process/save stats for player '{player_name}'. Error: {e}", exc_info=True)
    try:
         logger.info(f"Processed {players_processed} players for match {match.id}. Added: {stats_added}, Existing: {stats_existing}. Committing...")
         db_session.commit()
         logger.info(f"Successfully saved detailed stats for Match ID: {match.id}")
    except Exception as e:
         logger.error(f"COMMIT FAILED for Match ID {match.id}. Rolling back. Error: {e}", exc_info=True)
         db_session.rollback()

def scrape_single_match_details(db_session: Session, match_source_id: str):
    """
    Orchestrates the scraping of detailed stats for a single match.
    Finds the match, fetches HTML, parses details, and saves them.
    """
    logger.info(f"Starting detailed scrape process for Match Source ID: {match_source_id}")
    stmt = select(Match).where(Match.match_source_id == match_source_id)
    match = db_session.execute(stmt).scalar_one_or_none()
    if not match: logger.error(f"Match '{match_source_id}' not found."); print(f"错误：未找到比赛源 ID '{match_source_id}'"); return
    if not match.match_url: logger.error(f"Match {match.id} has no URL."); print(f"错误：比赛 {match_source_id} 无 URL"); return
    logger.info(f"Found Match: DB ID={match.id}, URL={match.match_url}"); print(f"找到比赛，抓取URL: {match.match_url}")
    html_content = fetch_html(match.match_url)
    if not html_content: logger.error(f"Failed fetch HTML: {match.match_url}"); print(f"错误：无法获取 HTML: {match.match_url}"); return
    detailed_stats = parse_match_details(html_content, match.match_url)
    if not detailed_stats: logger.warning(f"No detailed stats parsed from {match.match_url}."); print(f"警告：未解析出详细数据: {match.match_url}"); return
    save_match_details(db_session, match, detailed_stats)

# --- 4. 获取数据库 ID ---
# (待实现)
def get_db_ids_for_match(parsed_data: dict, db_session: Session) -> dict:
     """(占位符) 查找 Region 和 CompetitionType 的数据库 ID。"""
     print("Placeholder: Finding DB IDs for Region/CompetitionType not implemented yet.")
     # 稍后会根据解析出的赛事名称和可能的赛区信息查询数据库
     return parsed_data # 返回原数据，表示 ID 未填充

def save_detailed_match_data(match_data: dict, db_session: Session):
     """(占位符) 保存详细的比赛数据到数据库。"""
     print(f"Placeholder: Saving detailed data for match {match_data.get('match_source_id')} not implemented yet.")
     # 稍后会更新 Match 记录，填充日期、队伍、赛区ID、赛事ID、比分等
     pass

def run_scrape_test():
    """执行基本的抓取测试，获取并解析比赛列表。"""
    print("--- Running Scraping Test (List Parsing Only) ---")
    test_url_matches = urljoin(BASE_VLR_URL, "/matches") # 目标页面为 /matches
    html_content = fetch_html(test_url_matches)

    if html_content:
        print(f"Fetched {len(html_content)} bytes from {test_url_matches}.")
        # 调用 parse_match_list
        parsed_matches = parse_match_list(html_content)

        # 打印前几个结果进行验证
        print("\n--- Parsed Matches (sample) ---")
        for i, match in enumerate(parsed_matches[:5]): # 最多显示 5 个
            print(f"Match {i+1}: ID={match['match_source_id']}, Status='{match['status']}', URL={match['match_url']}")
        if not parsed_matches:
            print("No matches parsed.")

    else:
        print(f"Failed to fetch HTML from {test_url_matches}.")
    print("--- Scraping Test Finished ---")
