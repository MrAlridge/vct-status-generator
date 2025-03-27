import sys
import argparse
import os

# 在脚本开头添加 src 目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

# 导入数据库相关模块和模型
from core.database import init_db, test_connection, SessionLocal, get_db
from core.config import DATABASE_URL
from core.models import Region, CompetitionType # 导入新模型

# --- 导入抓取模块的函数 ---
try:
    # 尝试导入，如果 scraping 模块或其依赖项有问题，会在这里捕获
    from scraping.vlr_scraper import run_scrape_test, scrape_matches
except ImportError as e:
    print(f"无法导入抓取模块: {e}")
    print("请确保 'src/scraping' 目录存在且包含 'vlr_scraper.py'")
    # 可以定义一个虚拟函数，以防命令解析器失败
    def run_scrape_test(): print("Scraping test function not available due to import error.")
    def scrape_matches(): print("Scraping function not available due to import error.")

# --- 基础数据定义 ---
# ::SEED_DATA::
SEED_REGIONS = [
    {"name": "Americas", "abbreviation": "AMER"},
    {"name": "EMEA", "abbreviation": "EMEA"},
    {"name": "Pacific", "abbreviation": "PAC"},
    {"name": "China", "abbreviation": "CN"},
    {"name": "International", "abbreviation": "INTL"},
]

# ::SEED_DATA::
SEED_COMPETITION_TYPES = [
    {"name": "Kickoff", "description": "赛季初的启点赛"},
    {"name": "League Stage", "description": "常规联赛阶段"},
    {"name": "Masters", "description": "国际大师赛"},
    {"name": "Champions", "description": "全球冠军赛"},
    {"name": "LCQ", "description": "最终资格赛"},
    # 待补充
]
# --- End of SEED_DATA ---

def seed_data():
    """填充基础数据 (Regions, Competition Types)。"""
    print("正在填充基础数据...")
    db = SessionLocal() # 获取一个新的会话
    try:
        # --- 填充 Regions ---
        print("填充 Regions...")
        existing_region_names = {region.name for region in db.query(Region.name).all()}
        added_regions_count = 0
        skipped_regions_count = 0
        for region_data in SEED_REGIONS:
            if region_data["name"] not in existing_region_names:
                new_region = Region(**region_data)
                db.add(new_region)
                print(f"  添加 Region: {region_data['name']}")
                added_regions_count += 1
            else:
                # print(f"  跳过已存在的 Region: {region_data['name']}")
                skipped_regions_count += 1
        if skipped_regions_count > 0:
             print(f"  跳过 {skipped_regions_count} 个已存在的 Region。")

        # --- 填充 Competition Types ---
        print("填充 Competition Types...")
        existing_type_names = {ctype.name for ctype in db.query(CompetitionType.name).all()}
        added_types_count = 0
        skipped_types_count = 0
        for type_data in SEED_COMPETITION_TYPES:
            if type_data["name"] not in existing_type_names:
                new_type = CompetitionType(**type_data)
                db.add(new_type)
                print(f"  添加 Competition Type: {type_data['name']}")
                added_types_count += 1
            else:
                # print(f"  跳过已存在的 Competition Type: {type_data['name']}")
                skipped_types_count += 1
        if skipped_types_count > 0:
             print(f"  跳过 {skipped_types_count} 个已存在的 Competition Type。")

        if added_regions_count > 0 or added_types_count > 0:
            db.commit()
            print("数据已成功提交到数据库。")
        else:
            print("没有新的基础数据需要添加。")

    except Exception as e:
        print(f"填充数据时出错: {e}")
        db.rollback() # 如果出错，回滚事务
    finally:
        db.close() # 确保关闭会话
    print("基础数据填充完成。")

def main():
    parser = argparse.ArgumentParser(description="vct-status 项目管理脚本")
    subparsers = parser.add_subparsers(dest='command', help='可用的命令', required=True) # 使命令成为必需

    # 创建 'init-db' 子命令
    parser_init_db = subparsers.add_parser('init-db', help='初始化数据库 (创建所有表)')

    # 创建 'test-db' 子命令
    parser_test_db = subparsers.add_parser('test-db', help='测试数据库连接')

    # --- 新增 'seed-db' 子命令 ---
    parser_seed_db = subparsers.add_parser('seed-db', help='填充基础数据 (Regions, Competition Types)')
    # -----------------------------

    # --- 新增 'scrape' 子命令 ---
    parser_scrape = subparsers.add_parser('scrape', help='运行数据抓取器')
    parser_scrape.add_argument('--test', action='store_true', help='仅运行抓取功能的简单测试')
    # 可以添加更多参数，例如 --full 用于完整抓取，--recent 用于抓取最近比赛等

    args = parser.parse_args()

    print(f"使用的数据库 URL: {DATABASE_URL}")

    if args.command == 'init-db':
        print("正在尝试初始化数据库...")
        if test_connection():
            init_db()
            print("数据库初始化命令执行完毕。")
        else:
            print("数据库连接失败，无法初始化。请检查配置。")
            sys.exit(1) # 连接失败时退出，避免后续错误

    elif args.command == 'test-db':
        print("正在尝试测试数据库连接...")
        if test_connection():
            print("数据库连接测试成功。")
        else:
            print("数据库连接测试失败。")
            sys.exit(1)

    # --- 处理 'seed-db' 命令 ---
    elif args.command == 'seed-db':
        # 最好在填充数据前确保数据库连接正常
        if not test_connection():
             print("数据库连接失败，无法填充数据。请检查配置并运行 'init-db' (如果需要)。")
             sys.exit(1)
        seed_data()
    # --- 处理 'scrape' 命令 ---
    elif args.command == 'scrape':
        print("正在执行抓取任务...")
        # 优先检查数据库连接，因为抓取结果需要写入数据库
        if not test_connection():
             print("数据库连接失败，无法执行抓取。请检查配置。")
             sys.exit(1)

        if args.test:
            # 运行导入的测试函数
            run_scrape_test()
        else:
            # 运行主要的抓取函数 (待实现)
            print("即将执行完整抓取逻辑 (scrape_matches)...")
            scrape_matches()
            print("完整抓取逻辑执行完毕 (或尚未实现)。")
        print("抓取任务结束。")
    # -------------------------

    else:
        # 因为设置了 required=True, 理论上不会到这里，但保留以防万一
        parser.print_help()
        sys.exit(1)

    sys.exit(0) # 成功完成命令后退出

if __name__ == "__main__":
    main()