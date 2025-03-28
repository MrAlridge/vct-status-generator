# manage.py
import logging
import sys
import os
from pathlib import Path
import typer # Using Typer for CLI commands
from typing import Optional # Needed for potential future use, good practice

# Adjust sys.path if necessary (shouldn't be needed if run from root)
project_root = os.path.dirname(os.path.abspath(__file__))
# src_path = os.path.join(project_root, 'src')
# if src_path not in sys.path:
#     sys.path.insert(0, src_path)

# --- Configuration and Database Setup ---
try:
    from src.core.config import load_config, get_database_url, Config
    from src.core.database import SessionLocal, init_db as initialize_database, engine
    from src.core.models import Player, Match, PlayerMatchStats, Region, CompetitionType # Ensure all needed models are imported
    from sqlalchemy.orm import Session, joinedload
    from sqlalchemy import select, exists, func

    # --- Updated Scraper Imports ---
    # Import the functions defined in the latest vlr_scraper.py
    from src.scraping.vlr_scraper import (
        scrape_matches,                 # Replaces scrape_matches_list/scrape_match_results_page
        scrape_single_match_details     # Replaces scrape_and_save_match_details
    )

    from src.data_visualization.image_generator import (
        generate_match_summary_image,
        generate_player_card_image
    )

    GENERATOR_AVAILABLE = True
    CONFIG = load_config() # Load config once
    DATABASE_URL = get_database_url(CONFIG) # Determine DB URL
    print(f"使用的数据库 URL: {DATABASE_URL}") # Keep user informed

except ImportError as e:
    if 'src.data_visualization.image_generator' in str(e):
        print("\n警告: 图片生成模块 'src.data_visualization.image_generator' 未找到或其依赖项 (如 Pillow) 有问题。")
        print("'generate-images' 命令将不可用，除非该模块和依赖项被正确设置。")
        # Define placeholder functions to avoid NameError during app setup
        def generate_match_summary_image(*args, **kwargs):
            print("错误：图片生成功能未配置。")
            raise NotImplementedError("generate_match_summary_image 未实现或未加载")
        def generate_player_card_image(*args, **kwargs):
            print("错误：图片生成功能未配置。")
            raise NotImplementedError("generate_player_card_image 未实现或未加载")
        GENERATOR_AVAILABLE = False
    else:
        # Handle other critical import errors
        print(f"严重导入错误: {e}")
        print("请确保所有核心依赖都已安装，并检查环境。")
    sys.exit(1)
except Exception as e:
    print(f"加载配置或数据库/核心模块设置时出错: {e}")
    sys.exit(1)

# --- Logging Setup ---
# Configure root logger or specific loggers as needed
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__) # Logger for manage.py specific messages

# --- Typer App ---
app = typer.Typer()

# --- Database Commands (Unchanged from previous correct version) ---
@app.command(name="init-db")
def init_db_command(drop: bool = typer.Option(False, "--drop", "-d", help="先删除所有表。警告：将丢失所有数据！")):
    """
    初始化数据库：创建所有表。
    使用 --drop 选项可在创建前删除现有表。
    """
    logger.info("Initializing database...")
    if drop:
        logger.warning("Dropping existing tables as requested.")
        if not typer.confirm("警告：确定要删除所有表吗？此操作不可逆！"):
            print("操作已取消。")
            raise typer.Exit()
    try:
        initialize_database(drop_all=drop)
        logger.info("Database initialization complete.")
        print("数据库初始化完成。")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        print(f"数据库初始化失败: {e}")
        raise typer.Exit(code=1)

@app.command(name="seed-db")
def seed_database():
    """
    用初始数据（如赛区、赛事类型）填充数据库。
    确保在调用此命令前已运行 'init-db'。
    """
    logger.info("Starting database seeding...")
    print("开始填充数据库种子数据...")

    regions_data = [
        {"name": "North America", "abbreviation": "NA", "tag": "na"},
        {"name": "EMEA", "abbreviation": "EMEA", "tag": "emea"},
        {"name": "Pacific", "abbreviation": "PAC", "tag": "pac"},
        {"name": "China", "abbreviation": "CN", "tag": "cn"},
        {"name": "LATAM", "abbreviation": "LATAM", "tag": "latam"},
        {"name": "Korea", "abbreviation": "KR", "tag": "kr"},
        {"name": "Brazil", "abbreviation": "BR", "tag": "br"},
        {"name": "Japan", "abbreviation": "JP", "tag": "jp"},
        {"name": "Oceania", "abbreviation": "OCE", "tag": "oce"},
        {"name": "TBD", "abbreviation": "TBD", "tag": "tbd"}, # TBD 也需要 tag
        {"name": "International", "abbreviation": "INTL", "tag": "intl"}, # 全球赛事
    ]
    competition_types_data = [
        {"name": "Challengers League", "description": "Regional tier 2 competition", "tag": "challengers"},
        {"name": "International League", "description": "Tier 1 regional leagues", "tag": "intl_league"},
        {"name": "Masters", "description": "International S-Tier tournament", "tag": "masters"},
        {"name": "Champions", "description": "World Championship S-Tier tournament", "tag": "champions"},
        {"name": "Game Changers", "description": "Competition for women and marginalized genders", "tag": "game_changers"},
        {"name": "Qualifier", "description": "Tournament to qualify for another event", "tag": "qualifier"},
        {"name": "Other", "description": "Other types of tournaments", "tag": "other"},
        {"name": "TBD", "description": "To Be Determined / Placeholder", "tag": "tbd"},
    ]

    db: Session | None = None
    try:
        db = SessionLocal()
        print("数据库连接成功!")
        regions_added, types_added = 0, 0

        # Seed Regions
        print("填充赛区 (Regions)...")
        for region_data in regions_data:
            stmt = select(exists().where(Region.tag == region_data["tag"]))
            if not db.execute(stmt).scalar():
                db.add(Region(**region_data))
                regions_added += 1
                print(f"  [+] 添加赛区: {region_data['name']} (Tag: {region_data['tag']})")
            else:
                print(f"  [=] 赛区 (Tag: {region_data['tag']}) 已存在: {region_data['name']}")

        # Seed Competition Types
        print("\n填充赛事类型 (Competition Types)...")
        for comp_type_data in competition_types_data:
            stmt = select(exists().where(CompetitionType.tag == comp_type_data["tag"]))
            if not db.execute(stmt).scalar():
                db.add(CompetitionType(**comp_type_data))
                types_added += 1
                print(f"  [+] 添加赛事类型: {comp_type_data['name']} (Tag: {comp_type_data['tag']})")
            else:
                print(f"  [=] 赛事类型 (Tag: {comp_type_data['tag']}) 已存在: {comp_type_data['name']}")

        if regions_added > 0 or types_added > 0:
            db.commit()
            print(f"\n成功添加 {regions_added} 个新赛区和 {types_added} 个新赛事类型。")
        else:
            print("\n没有新的基础数据需要添加。")
        logger.info(f"Database seeding completed. Added {regions_added} regions, {types_added} types.")
    except Exception as e:
        logger.error(f"Database seeding failed: {e}", exc_info=True)
        print(f"\n数据库种子数据填充失败: {e}")
        if db: db.rollback()
        raise typer.Exit(code=1)
    finally:
        if db: db.close()
    print("数据库种子数据填充完成。")

@app.command(name="test-db")
def test_db_connection():
    """测试数据库连接。"""
    logger.info("Testing database connection...")
    print("正在测试数据库连接...")
    db: Session | None = None
    try:
        db = SessionLocal()
        # Simple query to test connection
        db.execute(select(1))
        db.close() # Close immediately after successful connection test
        db = None # Ensure it's None for the finally block check
        logger.info("Database connection successful.")
        print("数据库连接成功！")
    except Exception as e:
        logger.error(f"Database connection failed: {e}", exc_info=True)
        print(f"数据库连接失败: {e}")
        raise typer.Exit(code=1)
    finally:
        # This check might be redundant if db.close() is called within try,
        # but ensures closure if an error happens after SessionLocal() but before execute(select(1))
        if db:
             db.close()

# --- Scraping Commands (Updated) ---

@app.command(name="scrape-list")
def scrape_list_command():
    """
    从 vlr.gg 抓取比赛列表 (包括 /matches 和 /matches/results)。
    保存或更新比赛的基础信息 (ID, URL, 状态, 队伍, 事件, 赛区推断等)。
    """
    logger.info("Scraping basic match info from /matches and /matches/results...")
    print("开始抓取比赛概览信息 (近期 & 结果)...")
    db: Session | None = None
    try:
        db = SessionLocal()
        print("数据库连接成功！")

        # Call the updated scraper function which handles both pages
        # Assuming scrape_matches handles its own internal logging for counts etc.
        scrape_matches(db)

        # scrape_matches handles its own commit/rollback
        print("\n比赛概览信息抓取和处理完成。")
        logger.info("Basic match info scraping process finished.")

    except Exception as e:
        logger.error(f"Scraping basic match info failed: {e}", exc_info=True)
        print(f"\n抓取比赛概览信息过程中发生错误: {e}")
        # Rollback might be redundant if scrape_matches rolls back internally on error,
        # but doesn't hurt as a safety measure if an error occurs outside scrape_matches
        # but within this command's try block.
        # If scrape_matches guarantees its own rollback, this isn't strictly needed.
        # if db: db.rollback()
        raise typer.Exit(code=1)
    finally:
        if db:
            db.close()
            logger.debug("Database session closed for scrape-list.")

@app.command(name="scrape-details")
def scrape_details_command(
    match_source_id: int = typer.Argument(..., help="要抓取详情的比赛的 vlr.gg ID (例如 450059)")
):
    """根据 vlr.gg 比赛 ID 抓取并存储详细比赛数据（例如玩家统计数据）。"""
    logger.info(f"Scraping details initiated for match VLR ID: {match_source_id}")
    print(f"开始抓取比赛详情任务，Match VLR ID: {match_source_id}...")
    db: Session | None = None
    try:
        logger.info("Attempting to connect to database for detailed scraping...")
        db = SessionLocal()
        logger.info("Database session acquired successfully.")
        print("数据库连接成功！")

        print(f"即将执行 {match_source_id} 的详细抓取逻辑...")
        # Call the updated detailed scraping function
        scrape_single_match_details(db, str(match_source_id)) # Ensure ID is passed as string if expected by scraper
        print(f"比赛 {match_source_id} 的详细抓取逻辑执行完毕。")
        # Assuming scrape_single_match_details handles its own commit/rollback per match
        logger.info(f"Detailed scraping task finished or terminated for match VLR ID: {match_source_id}")

    except Exception as e:
        # Catch errors that might occur *outside* scrape_single_match_details
        # or if it re-raises exceptions.
        logger.error(f"Scraping details for match {match_source_id} failed: {e}", exc_info=True)
        print(f"\n抓取比赛 {match_source_id} 详情时发生错误: {e}")
        # Rollback here might be too broad if scrape_single_match_details commits partially.
        # It's safer to rely on the inner function's error handling.
        # if db: db.rollback()
        raise typer.Exit(code=1)
    finally:
        if db:
            db.close()
            logger.debug(f"Database session closed for scrape-details (match {match_source_id}).")
    print("详细抓取任务结束。")

# --- Image Generation Command ---
@app.command(name="generate-images")
def generate_images_command(
    match_source_id: int = typer.Argument(..., help="要生成图片的比赛的 vlr.gg ID (例如 450059)"),
    output_dir: str = typer.Option("./generated_images", "--output-dir", "-o", help="保存生成图片的目录"),
    expected_players: int = typer.Option(10, "--expected-players", "-p", help="期望的比赛玩家数量 (用于检查数据完整性)"),
    skip_summary: bool = typer.Option(False, "--skip-summary", help="跳过生成比赛总结图片"),
    skip_player: bool = typer.Option(False, "--skip-player", help="跳过生成玩家卡片图片")
):
    """
    为指定的比赛生成总结图片和玩家数据卡片。
    如果数据不存在或不完整，会尝试自动抓取。
    需要 Pillow 库: pip install Pillow
    """
    if not GENERATOR_AVAILABLE:
         print("\n错误：图片生成功能因模块导入失败而不可用。请检查 'src.data_visualization.image_generator' 及其依赖项。")
         raise typer.Exit(code=1)
    # Check Pillow again specifically for this command
    try:
         from PIL import Image, ImageDraw, ImageFont
    except ImportError:
         print("\n错误：执行此命令需要 Pillow 库。请运行 'pip install Pillow'")
         raise typer.Exit(code=1)

    logger.info(f"开始为比赛 VLR ID: {match_source_id} 生成图片...")
    print(f"开始为比赛 VLR ID: {match_source_id} 生成图片...")

    # --- 确保输出目录存在 ---
    try:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"图片将保存到: {output_path.absolute()}")
        print(f"图片将保存到: {output_path.absolute()}")
    except OSError as e:
        logger.error(f"创建输出目录 '{output_dir}' 失败: {e}", exc_info=True)
        print(f"错误: 无法创建输出目录 '{output_dir}': {e}")
        raise typer.Exit(code=1)
    
    db: Session | None = None
    try:
        db = SessionLocal()
        logger.info("数据库连接成功。")

        # --- 数据检查、抓取、查询逻辑 (与上一版本相同) ---
        # 1. 检查 Match
        match = db.scalar(select(Match).where(Match.match_source_id == str(match_source_id)))
        # 2. 检查 Stats 完整性
        stats_count = 0
        if match and match.id:
            stats_count = db.scalar(select(func.count(PlayerMatchStats.id)).where(PlayerMatchStats.match_id == match.id))
            logger.info(f"数据库中找到比赛 ID {match.id} 的 {stats_count} 条玩家统计记录。")
        else:
             logger.info(f"数据库中未找到比赛 VLR ID {match_source_id} 的基础信息。")
        # 3. 判断是否需抓取
        needs_scraping = False
        if not match:
            logger.info(f"需要抓取：比赛基础信息不存在。")
            needs_scraping = True
        elif stats_count < expected_players:
            logger.info(f"需要抓取：玩家统计数据不完整 (找到 {stats_count}, 期望 {expected_players})。")
            needs_scraping = True
        # 抓取逻辑... (省略，与上个版本相同, 包含错误处理和重新检查)
        if needs_scraping:
            logger.info(f"正在尝试为比赛 VLR ID {match_source_id} 抓取/更新详细数据...")
            print(f"数据不完整或未找到，尝试抓取比赛 {match_source_id} 的详细数据...")
            try:
                scrape_single_match_details(db, str(match_source_id))
                print(f"数据抓取尝试完成。")
                # 抓取后重新查询数据
                match = db.scalar(select(Match).where(Match.match_source_id == str(match_source_id)))
                if match and match.id:
                     stats_count = db.scalar(select(func.count(PlayerMatchStats.id)).where(PlayerMatchStats.match_id == match.id))
                     logger.info(f"抓取后，数据库中找到比赛 ID {match.id} 的 {stats_count} 条玩家统计记录。")
                else:
                     logger.error(f"尝试抓取后，仍然无法在数据库中找到比赛 VLR ID {match_source_id} 的基础信息。")
                     print(f"错误: 尝试抓取后，仍未找到比赛 {match_source_id} 的基础信息。")
                     raise typer.Exit(code=1)
                 # 再次检查完整性
                if stats_count < expected_players:
                     logger.warning(f"警告: 抓取后数据仍不完整 (找到 {stats_count}, 期望 {expected_players})。将基于现有数据生成图片。")
                     print(f"警告: 抓取后数据仍可能不完整 (找到 {stats_count} 条记录)。")
                #else: # 不需要 else 里的日志了
                 #    logger.info("数据抓取/更新成功，数据完整。")
                 #    print("数据抓取/更新成功。")

            except Exception as scrape_exc:
                 logger.error(f"抓取比赛 {match_source_id} 数据时出错: {scrape_exc}", exc_info=True)
                 print(f"错误: 抓取比赛 {match_source_id} 数据时出错: {scrape_exc}")
                 raise typer.Exit(code=1)
        # 4. 查询数据
        if not match or not match.id or stats_count == 0:
             logger.error(f"无法继续：比赛 {match_source_id} 的数据缺失。")
             print(f"错误: 无法为比赛 {match_source_id} 生成图片，数据缺失。")
             raise typer.Exit(code=1)

        logger.info("正在从数据库查询详细数据用于生成图片...")
        stmt = (
            select(PlayerMatchStats)
            .options(joinedload(PlayerMatchStats.player))
            .join(PlayerMatchStats.player)
            .where(PlayerMatchStats.match_id == match.id)
        )
        player_stats_results = db.scalars(stmt).all()
        if not player_stats_results:
             logger.error(f"查询到 Match (ID: {match.id}) 但未找到关联的 PlayerMatchStats。")
             print(f"错误：无法获取比赛 {match_source_id} 的玩家统计数据 (查询结果为空)。")
             raise typer.Exit(code=1)

        player_stats_list = []
        for ps in player_stats_results:
            if not ps.player: continue
            stats_dict = {k: getattr(ps, k, None) for k in PlayerMatchStats.__table__.columns.keys()} # Get all columns
            stats_dict['player_name'] = ps.player.name
            stats_dict['player_source_id'] = ps.player.player_source_id
            stats_dict['player_db_id'] = ps.player.id
            # Clean up potential SQLAlchemy internal keys if any (unlikely with getattr)
            stats_dict.pop('_sa_instance_state', None)
            player_stats_list.append(stats_dict)
        logger.info(f"成功查询到 {len(player_stats_list)} 条玩家统计信息。")

        # 5. --- 调用图片生成函数 ---
        match_summary_data = {k: getattr(match, k, None) for k in Match.__table__.columns.keys()}
        match_summary_data.pop('_sa_instance_state', None)
        # 添加默认值 (如果需要的话)
        match_summary_data['team1_name'] = match_summary_data.get('team1_name') or "Team A"
        match_summary_data['team2_name'] = match_summary_data.get('team2_name') or "Team B"
        match_summary_data['event_name'] = match_summary_data.get('event_name') or "Unknown Event"

        if not skip_summary:
            summary_image_path = output_path / f"{match_source_id}_summary.png"
            logger.info("调用 generate_match_summary_image...")
            try:
                 generate_match_summary_image(
                     match_data=match_summary_data,
                     player_stats_list=player_stats_list,
                     output_path=str(summary_image_path)
                 )
                 print(f"比赛总结图片已生成: {summary_image_path}")
            except NotImplementedError:
                 print("错误: generate_match_summary_image 功能尚未实现。")
            except Exception as img_exc:
                 logger.error(f"生成比赛总结图片时出错: {img_exc}", exc_info=True)
                 print(f"错误: 生成比赛总结图片失败: {img_exc}")
        else:
            logger.info("根据选项跳过生成比赛总结图片。")

        if not skip_player:
            logger.info("开始生成玩家卡片...")
            for i, player_stat in enumerate(player_stats_list):
                 player_name = player_stat.get('player_name', f'player_{i}')
                 player_name_safe = "".join(c if c.isalnum() or c in ('_','-') else '_' for c in player_name)
                 player_card_path = output_path / f"{match_source_id}_{player_name_safe}_card.png"
                 logger.info(f"  调用 generate_player_card_image for {player_name}...")
                 try:
                    generate_player_card_image(
                        player_stats=player_stat,
                        output_path=str(player_card_path)
                    )
                    print(f"  玩家卡片已生成: {player_card_path.name}")
                 except NotImplementedError:
                    print(f"错误: generate_player_card_image 功能尚未实现 (Player: {player_name})。停止生成玩家卡片。")
                    break # Stop if not implemented
                 except Exception as img_exc:
                     logger.error(f"生成玩家 {player_name} 卡片时出错: {img_exc}", exc_info=True)
                     print(f"错误: 生成玩家 {player_name} 卡片失败: {img_exc}")
                     # Continue to next player card on error
            logger.info("玩家卡片生成完成（或因错误/未实现而停止）。")
        else:
            logger.info("根据选项跳过生成玩家卡片图片。")

        print(f"\n图片生成任务完成。")
        logger.info(f"图片生成任务完成 for match VLR ID: {match_source_id}")

    except Exception as e:
        logger.error(f"执行 generate-images 命令时出错: {e}", exc_info=True)
        print(f"\n执行图片生成命令时发生意外错误: {e}")
        if db: db.rollback()
        raise typer.Exit(code=1)
    finally:
        if db: db.close()
        logger.debug("Database session closed for generate-images.")

# --- Main Execution ---
if __name__ == "__main__":
    logger.info("VCT-Status Manager executing command...")
    app()
    logger.info("VCT-Status Manager command finished.")