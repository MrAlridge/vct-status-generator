import requests
import time
from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin # 用于处理相对 URL
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import sys # 导入 sys 来处理 potential import issues if needed, 但优先通过 manage.py 运行
import re

# --- 核心库导入 ---
# 使用绝对导入，因为 manage.py 会设置好路径
try:
    from core.database import SessionLocal, get_db
    from core.models import Match, Region, CompetitionType
except ImportError:
    print("Error: Failed to import core modules. Make sure 'src' is in PYTHONPATH or run via manage.py")
    # 提供一个假的 Match 类，防止在导入失败时后续代码完全崩溃
    class Match: pass
    class SessionLocal: pass
    # 在实际运行中，如果导入失败， manage.py 中的检查会阻止执行

# vlr.gg 基础 URL
BASE_VLR_URL = "https://vlr.gg"

# 设置请求头，模拟浏览器访问，避免被屏蔽
# ::SECURITY_HEADER:: - 使用明确的 User-Agent 是好习惯
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

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
        print(f"Successfully fetched HTML from: {url}")
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None
    # 添加短暂延迟，尊重服务器资源
    finally:
        # ::OPERATIONAL_CONCERN:: - 避免过快请求导致 IP 被封禁
        time.sleep(1.5)

# --- 2. 解析比赛列表 ---
def parse_match_list(html_content: str) -> list[dict]:
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
    soup = BeautifulSoup(html_content, 'lxml')
    matches_found = []

    # vlr.gg 的结构可能会变化，需要根据实际情况调整选择器。
    # 查找包含比赛链接的 <a> 标签。通常它们有特定的类名或在特定父元素下。
    # 假设比赛链接是 class="match-item" 的 <a> 标签 (需要验证!)
    # 或者查找包含多个比赛日的 wf-card, 再找里面的 a 标签
    match_elements = soup.select('a.match-item') # 使用 CSS 选择器

    if not match_elements:
        # 如果上面的选择器无效，尝试更通用的方式，例如查找所有指向 /<number>/ 形式的链接
        # 这是一种备选策略，可能不够精确
        print("Warning: CSS selector 'a.match-item' did not find any elements. Trying broader search.")
        match_elements = soup.find_all('a', href=re.compile(r'^/\d+/.+')) # 查找 href 以 /数字/ 开头的链接

    print(f"Found {len(match_elements)} potential match elements.")

    processed_ids = set() # 跟踪已处理的 ID，防止因 HTML 结构重复添加

    for element in match_elements:
        # 确保 element 是 Tag 类型并且有 href 属性
        if not isinstance(element, Tag) or not element.get('href'):
            continue

        relative_url = element['href']
        # match_url = urljoin(BASE_VLR_URL, relative_url)

        # 从 URL 中提取 match_id (数字部分)
        match_id_match = re.search(r'/(\d+)/', relative_url)
        if not match_id_match:
            # print(f"Could not extract match ID from URL: {relative_url}")
            continue # 如果无法提取 ID，跳过这个元素

        match_source_id = match_id_match.group(1)

        # 如果已经处理过这个 ID，则跳过（vlr 页面有时会重复列出比赛）
        if match_source_id in processed_ids:
            continue
        processed_ids.add(match_source_id)

        match_url = urljoin(BASE_VLR_URL, relative_url)

        # 尝试获取比赛状态 (可能在父元素或兄弟元素中)
        status = "Unknown"
        # 常见的状态文本或类名，需要根据实际 HTML 调整
        status_element = element.find(class_='ml-status') # 假设状态在 class="match-item-status" 的元素里
        if status_element:
            status_text = status_element.get_text(strip=True).lower()
            if 'upcoming' in status_text:
                status = 'Upcoming'
            elif 'live' in status_text:
                status = 'LIVE'
            elif element.find(class_='match-item-vs-team-score  js-spoiler '):
                status = 'Completed'

        # 尝试获取队伍和赛事信息作为上下文
        context = f"Match URL {match_url}" # 默认上下文

        matches_found.append({
            'match_source_id': match_source_id,
            'match_url': match_url,
            'status': status,
            'context': context # 用于日志或调试
        })

    print(f"Successfully parsed {len(matches_found)} unique matches from the list.")
    return matches_found

# --- 3. 解析比赛详情 ---
# (待实现)
def parse_match_details(match_url: str, html_content: str) -> dict | None:
     """解析单个比赛页面。"""
     # ... 实现细节将在这里 ...
     print(f"parse_match_details function needs implementation for {match_url}.")
     return None

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

# --- 5. 保存比赛数据 ---
# (待实现)
def save_basic_match_info(match_data: dict, db_session: Session):
    """
    保存或更新比赛的基本信息 (ID, URL, Status) 到数据库。
    仅处理来自比赛列表页面的信息。

    Args:
        match_data: 从 parse_match_list 获取的单个比赛字典。
        db_session: SQLAlchemy 数据库会话。
    """
    match_source_id = match_data.get('match_source_id')
    match_url = match_data.get('match_url')
    current_status = match_data.get('status', 'Unknown')

    if not match_source_id:
        print("  Skipping save: match_source_id is missing.")
        return

    try:
        # 尝试查找具有此 source_id 的现有比赛
        existing_match: Match | None = db_session.query(Match).filter(Match.match_source_id == match_source_id).first()

        if not existing_match:
            # --- 比赛不存在，插入新记录 ---
            print(f"  [+] Adding new match: ID {match_source_id}, Status: {current_status}")
            new_match = Match(
                match_source_id=match_source_id,
                match_url=match_url,
                status=current_status
                # 注意：match_date, team1_id, team2_id, region_id, competition_type_id,
                # score_t1, score_t2 等字段将保持默认值 (NULL)
            )
            db_session.add(new_match)

        else:
            # --- 比赛已存在，检查是否需要更新状态 ---
            # 仅当新状态不是 'Unknown' 且与数据库中的状态不同时才更新
            # 或者，如果数据库中是 'Unknown'，则可以用抓取到的状态覆盖
            should_update = (current_status != 'Unknown' and existing_match.status != current_status) or \
                            (existing_match.status == 'Unknown' and current_status != 'Unknown')

            if should_update:
                print(f"  [*] Updating match status: ID {match_source_id} ('{existing_match.status}' -> '{current_status}')")
                existing_match.status = current_status
            # 可选：如果状态相同，可以取消注释下面的行进行调试
            # else:
            #     print(f"  [=] Match ID {match_source_id} already exists with status '{existing_match.status}'. No update needed.")

    except IntegrityError:
        # 捕获唯一约束冲突（理论上不应该频繁发生，除非并发写入）
        db_session.rollback() # 回滚当前失败的操作
        print(f"  [!] IntegrityError for match ID {match_source_id}. Possible race condition? Skipped.")
    except Exception as e:
        # 捕获其他可能的数据库错误
        db_session.rollback() # 回滚以防会话状态损坏
        print(f"  [!] Error saving match ID {match_source_id}: {e}")


# --- 6. 主协调函数 ---
def scrape_matches():
    """
    协调抓取比赛列表，并将基础信息 (URL, ID, Status) 保存到数据库。
    不抓取详细信息。
    """
    print("--- Starting: Scrape Match List & Save Basic Info ---")
    # 目标可以是 /matches (主要看 upcoming/live) 或 /matches/results (看已完成)
    # 考虑将来让这个 URL 可配置或抓取多个页面
    matches_list_url = urljoin(BASE_VLR_URL, "/matches")
    # matches_list_url = urljoin(BASE_VLR_URL, "/matches/results") # 或者抓取结果页

    db: Session | None = None
    try:
        print(f"Attempting to connect to database...")
        db = SessionLocal()
        print("Database session acquired.")

        print(f"Fetching match list from {matches_list_url}...")
        html_content = fetch_html(matches_list_url)
        if not html_content:
            print("Failed to fetch match list HTML. Aborting.")
            return # 如果无法获取列表，则退出

        print("Parsing match list...")
        parsed_matches = parse_match_list(html_content)
        if not parsed_matches:
            print("No matches parsed from the list. Nothing to save.")
            return # 如果列表为空，则退出

        print(f"\n--- Processing {len(parsed_matches)} Matches ---")
        processed_count = 0
        for match_info in parsed_matches:
            if db: # 确保 db 可用
                save_basic_match_info(match_info, db)
                processed_count += 1
            else:
                print("Error: Database session is not available. Cannot save.")
                break # 如果会话无效，停止处理

            # ::OPERATIONAL_CONCERN:: - 可以在大量数据时考虑批量提交或小的暂停
            # time.sleep(0.05) # 可选：在每个保存操作后加入微小延迟

        if db: # 只有在会话有效时才提交
            print(f"\nProcessed {processed_count} matches. Committing changes to database...")
            db.commit()
            print("Database commit successful.")
        else:
             print("Database session was not available. No changes committed.")

    except Exception as e:
        print(f"\n--- An error occurred during the scraping process ---")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc() # 打印详细的回溯信息
        if db:
            print("Rolling back database changes due to error.")
            try:
                db.rollback()
            except Exception as rb_exc:
                print(f"Error during rollback: {rb_exc}")
    finally:
        if db:
            print("Closing database session.")
            db.close()

    print("--- Finished: Scrape Match List & Save Basic Info ---")

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
