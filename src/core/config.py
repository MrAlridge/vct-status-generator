import os
import yaml # 导入 PyYAML
from pathlib import Path

# 项目根目录 (vct-status)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_FILE_PATH = BASE_DIR / "config.yaml"

# --- 加载配置 ---
try:
    with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f)
        if config_data is None: # 处理空文件的情况
             config_data = {}
except FileNotFoundError:
    print(f"警告: 配置文件 '{CONFIG_FILE_PATH}' 未找到。将使用默认设置或环境变量。")
    config_data = {}
except Exception as e:
    print(f"错误: 加载配置文件 '{CONFIG_FILE_PATH}' 时出错: {e}")
    config_data = {} # 出错时使用空配置

# --- 数据库配置 ---
db_config = config_data.get('database', {}) # 获取数据库部分，如果不存在则为空字典

# 1. 环境变量优先 (推荐用于生产和覆盖)
#    读取 YAML 中指定的用于存储完整 URL 的环境变量名称
db_env_var = db_config.get('mariadb', {}).get('env_var_url', 'DATABASE_URL') # ::DATABASE_URL::
DATABASE_URL = os.environ.get(db_env_var)

# 2. 如果环境变量未设置，则使用 YAML 中定义的 SQLite 配置作为默认值
if DATABASE_URL is None:
    print(f"未找到环境变量 '{db_env_var}'。将使用 config.yaml 中的 SQLite 配置。")
    sqlite_config = db_config.get('sqlite', {})
    sqlite_path_str = sqlite_config.get('path', 'vct_data.db') # 默认文件名以防万一
    # 将相对路径转换为绝对路径 (相对于 BASE_DIR)
    sqlite_db_path = (BASE_DIR / sqlite_path_str).resolve()
    DATABASE_URL = f"sqlite+pysqlite:///{sqlite_db_path}"
    # <SECURITY_REVIEW>
    # 确保 config.yaml（如果包含密码）或包含 DATABASE_URL 的 .env 文件
    # 都在 .gitignore 中。当前代码优先环境变量，降低了硬编码风险。
    # SQLite 连接字符串本身不包含敏感凭证。
    # </SECURITY_REVIEW>

print(f"使用的数据库 URL: {DATABASE_URL}") # 调试输出最终使用的 URL

# --- 其他配置 (示例) ---
# 可以类似地从 config_data 中加载其他部分的配置
# scraping_settings = config_data.get('scraping_settings', {})
# api_key = os.environ.get('SOME_API_KEY') or config_data.get('api_keys', {}).get('some_api')