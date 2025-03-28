# src/data_visualization/image_generator.py

import logging
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import os

logger = logging.getLogger(__name__)

# --- 配置 ---
DEFAULT_FONT_PATH = "assets/fonts/NotoSansSC-VariableFont_wght.ttf"

#  --- 路径 ---
# 项目根目录 (假设 image_generator.py 在 src/data_visualization/ 下)
PROJECT_ROOT = Path(__file__).parent.parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
FONT_PATH = ASSETS_DIR / "fonts" / "NotoSansSC-Bold.otf" # <--- 确认这个字体存在!
TEAM_LOGO_BASE_DIR = ASSETS_DIR / "team" / "CN" # Logo 基础目录

LARGE_FONT_SIZE = 48   # 玩家名称
DEFAULT_FONT_SIZE = 36 # 主要统计数据 (KDA 值, ACS 值, Rating 值)
SMALL_FONT_SIZE = 28   # 次要信息 (例如 Agent)
LABEL_FONT_SIZE = 24   # 统计数据标签 (K/D/A, ACS, Rating)

# --- 卡片尺寸和颜色 ---
CARD_WIDTH = 600 # 加宽一点以容纳 Logo 和更多信息
CARD_HEIGHT = 500 # 增加高度
BACKGROUND_COLOR = (15, 25, 35) # 深蓝灰色背景，接近 Valorant UI
TEXT_COLOR = (230, 230, 230) # 浅灰色/接近白色文字
LABEL_COLOR = (180, 180, 180) # 标签用稍暗的灰色
VALORANT_RED = (255, 70, 85) # '#FF4655'
WHITE_COLOR = (255, 255, 255)

# --- 布局 ---
PADDING = 35
LOGO_SIZE = (100, 100) # Logo 显示大小
TEXT_SPACING = 12 # 不同文本块之间的垂直间距
STAT_SPACING = 70 # 统计数据块之间的水平间距
RECT_PADDING_X = 20 # 红色背景框的水平内边距
RECT_PADDING_Y = 8  # 红色背景框的垂直内边距

# --- 辅助函数：加载字体 ---
def _load_font(font_path: Path, size: int) -> ImageFont.FreeTypeFont | None:
    """尝试加载指定路径和大小的字体。"""
    if not font_path.is_file():
        # logger.error(f"字体文件未找到: {font_path.absolute()}")
        return None
    try:
        return ImageFont.truetype(str(font_path), size)
    except IOError as e:
        logger.error(f"加载字体失败: {font_path}. Error: {e}", exc_info=True)
        return None

# --- 辅助函数：获取文本绘制尺寸 ---
def get_text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
    """获取文本绘制的宽度和高度。"""
    if hasattr(draw, 'textbbox'): # Pillow 9.0.0+
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            return width, height
        except Exception: # Fallback if textbbox fails
            pass
    # Fallback for older Pillow or if bbox fails
    # getsize is deprecated but works as fallback
    try:
        width, height = draw.textlength(text, font=font), font.getbbox(text)[3] - font.getbbox(text)[1]

        return width, height
    except AttributeError: # Extremely old Pillow?
         return (len(text) * font.size / 2, font.size) # Very rough estimate
# --- 玩家卡片生成函数 ---
def generate_player_card_image(player_stats: dict, output_path: str):
    """
    根据玩家统计数据生成一张美化的玩家信息卡片图片。

    Args:
        player_stats (dict): 包含玩家统计信息的字典。
                               预期键: 'player_name', 'team_name', 'kills', 'deaths', 'assists',
                                       'acs', 'rating', 'agent'.
        output_path (str):  保存生成图片的完整路径。
    """
    player_name = player_stats.get('player_name', 'N/A')
    logger.info(f"开始为玩家 '{player_name}' 生成美化卡片图像: {output_path}")

    # --- 加载字体 ---
    font_large = _load_font(FONT_PATH, LARGE_FONT_SIZE)
    font_default = _load_font(FONT_PATH, DEFAULT_FONT_SIZE)
    font_small = _load_font(FONT_PATH, SMALL_FONT_SIZE)
    font_label = _load_font(FONT_PATH, LABEL_FONT_SIZE)

    # 使用 Pillow 默认字体作为后备
    fallback_font = ImageFont.load_default()
    if not font_large: logger.warning(f"字体文件 {FONT_PATH} (大号) 未找到或加载失败，将使用后备字体。"); font_large = fallback_font
    if not font_default: logger.warning(f"字体文件 {FONT_PATH} (默认) 未找到或加载失败，将使用后备字体。"); font_default = fallback_font
    if not font_small: logger.warning(f"字体文件 {FONT_PATH} (小号) 未找到或加载失败，将使用后备字体。"); font_small = fallback_font
    if not font_label: logger.warning(f"字体文件 {FONT_PATH} (标签) 未找到或加载失败，将使用后备字体。"); font_label = fallback_font

    # --- 创建画布 ---
    image = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(image)

    # --- 加载并处理队伍 Logo ---
    team_abbr = player_stats.get('team_name', '').upper()
    logo_image = None
    if team_abbr:
        logo_path = TEAM_LOGO_BASE_DIR / f"{team_abbr}.png"
        if logo_path.is_file():
            try:
                logo_image = Image.open(logo_path).convert("RGBA")
                logo_image.thumbnail(LOGO_SIZE, Image.Resampling.LANCZOS) # 调整大小并保持比例
                logger.debug(f"成功加载并调整 Logo: {logo_path}")
            except Exception as e:
                logger.error(f"加载或处理 Logo '{logo_path}' 失败: {e}", exc_info=True)
                logo_image = None # 明确设为 None
        else:
            logger.warning(f"队伍 Logo 文件未找到: {logo_path}")

    # --- 绘制 Logo (如果加载成功) ---
    logo_x = PADDING
    logo_y = PADDING
    actual_logo_width = LOGO_SIZE[0] # 默认用配置宽度
    if logo_image:
        try:
            actual_logo_width = logo_image.width # 获取缩放后的实际宽度
            # 使用 alpha 通道作为 mask 进行粘贴
            image.paste(logo_image, (logo_x, logo_y), mask=logo_image)
        except Exception as e:
             logger.error(f"粘贴 Logo 时出错: {e}", exc_info=True)
             # 可以在此处绘制占位符

    # --- 绘制玩家名称和红色背景 ---
    player_name_text = player_name
    # Logo 右侧 + 间距
    name_x_start = logo_x + actual_logo_width + PADDING
    # 垂直居中于 Logo （大约）
    name_y_start = logo_y + (LOGO_SIZE[1] // 2) - (LARGE_FONT_SIZE // 2) - 5 # 微调垂直位置

    name_width, name_height = get_text_size(draw, player_name_text, font_large)
    # 使用配置中的 RECT_PADDING
    rect_x0 = name_x_start - RECT_PADDING_X
    rect_y0 = name_y_start - RECT_PADDING_Y
    rect_x1 = name_x_start + name_width + RECT_PADDING_X
    rect_y1 = name_y_start + name_height + RECT_PADDING_Y

    try:
        # 确保矩形不会超出右边界太多 (简单检查)
        if rect_x1 > CARD_WIDTH - PADDING // 2:
            rect_x1 = CARD_WIDTH - PADDING // 2
            # 如果名字太长，可能需要截断或缩小字体，这里先简单限制矩形

        draw.rectangle([rect_x0, rect_y0, rect_x1, rect_y1], fill=VALORANT_RED)
        draw.text((name_x_start, name_y_start), player_name_text, fill=WHITE_COLOR, font=font_large)
    except Exception as e:
        logger.error(f"绘制玩家名称背景或文本时出错: {e}", exc_info=True)
        # Fallback: 只画文本
        draw.text((name_x_start, name_y_start), player_name_text, fill=TEXT_COLOR, font=font_large)

    # --- 绘制统计数据 ---
    # 从 Logo 和 Name 区域下方开始，留出足够间距
    current_y = max(logo_y + LOGO_SIZE[1], rect_y1) + PADDING * 1.5
    current_x = PADDING # 统计数据从左侧 PADDING 开始，垂直排列

    # -- 准备数据 --
    kills = player_stats.get('kills', '?')
    deaths = player_stats.get('deaths', '?')
    assists = player_stats.get('assists', '?')
    acs = _safe_cast(player_stats.get('acs'), int, '?') # 假设 ACS 是整数
    # rating = _safe_cast(player_stats.get('rating'), float, None) # 假设 Rating 是浮点数
    rating_raw = player_stats.get('rating')
    rating = f"{rating_raw:.2f}" if isinstance(rating_raw, (int, float)) else "?"
    adr = _safe_cast(player_stats.get('adr'), int, '?') # 添加 ADR
    hs_percent = _safe_cast(player_stats.get('headshot_percentage'), int, None) # 添加 HS%
    hs_text = f"{hs_percent}%" if hs_percent is not None else "?"

    # 定义一个辅助函数来绘制标签和值对
    def draw_stat(x, y, label, value, label_font, value_font):
        label_width, label_height = get_text_size(draw, label, label_font)
        value_width, value_height = get_text_size(draw, str(value), value_font)

        draw.text((x, y), label, fill=LABEL_COLOR, font=label_font)
        # 将值绘制在标签下方
        draw.text((x, y + label_height + TEXT_SPACING // 2), str(value), fill=TEXT_COLOR, font=value_font)
        # 返回这个块占用的总高度和宽度，用于布局
        total_height = label_height + TEXT_SPACING // 2 + value_height
        block_width = max(label_width, value_width)
        return total_height, block_width

    stats_to_draw = [
        ("K / D / A", f"{kills} / {deaths} / {assists}"),
        ("ACS", acs),
        ("Rating", rating),
        ("ADR", adr),
        ("HS%", hs_text),
        # 在这里添加更多你想显示的统计数据
    ]

    max_stat_height = 0 # 用于确定下一行的起始 Y

    try:
        for label, value in stats_to_draw:
            stat_height, stat_width = draw_stat(current_x, current_y, label, value, font_label, font_default)
            max_stat_height = max(max_stat_height, stat_height) # 记录这一行最高的块
            # 移动到下一个统计数据的位置（水平）
            current_x += stat_width + STAT_SPACING
            # 如果下一个块会超出宽度，考虑换行 (简单处理)
            # peek_width, _ = get_text_size(draw, stats_to_draw[stats_to_draw.index((label, value)) + 1][0] if stats_to_draw.index((label, value)) + 1 < len(stats_to_draw) else "", font_label)
            # if current_x + peek_width > CARD_WIDTH - PADDING:
            #      current_x = PADDING
            #      current_y += max_stat_height + PADDING # 换行增加垂直间距
            #      max_stat_height = 0
             # 更健壮的方式是预先计算所有宽度再决定布局

    except Exception as e:
         logger.error(f"绘制统计数据时出错: {e}", exc_info=True)
         try:
             draw.text((PADDING, current_y), f"Error drawing stats: {e}", fill=(255,0,0), font=fallback_font)
         except Exception: pass

    # --- 绘制 Agent (可选) ---
    # agent_name = player_stats.get('agent', None)
    # if agent_name:
        # 你可以找个合适的位置放 Agent 名称，例如放在统计数据下方
        # agent_y = current_y + max_stat_height + PADDING # 放在统计数据行的下方
        # agent_x = PADDING
        # try:
        #      draw.text((agent_x, agent_y), f"Agent: {agent_name}", fill=LABEL_COLOR, font=font_small)
        # except Exception as e:
        #      logger.warning(f"绘制 Agent 名称时出错: {e}")

    # --- 保存图片 ---
    try:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path, "PNG")
        logger.info(f"玩家卡片 (600x500) 已成功保存到: {output_path}")
    except IOError as e:
        logger.error(f"保存图片失败: {output_path}. Error: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"保存图片时发生未知错误: {output_path}. Error: {e}", exc_info=True)


# --- _safe_cast (从 vlr_scraper.py 复制过来，或者可以考虑放到一个 utils 模块中) ---
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

        if cleaned_value == '': return default # Handle empty string after cleaning

        if cast_type is int:
            # Handle negative numbers explicitly, isdigit doesn't handle '-'
            if cleaned_value.startswith('-') and cleaned_value[1:].isdigit():
                return cast_type(cleaned_value)
            elif cleaned_value.isdigit():
                return cast_type(cleaned_value)
            else: return default
        elif cast_type is float:
             # Try converting to float directly after cleaning known non-numeric chars
             return cast_type(cleaned_value)
        elif cast_type is str:
             return cleaned_value # Return the cleaned string
        return default # If cast_type is not known
    except (ValueError, TypeError):
        return default

# --- 比赛总结图片生成函数 (占位符保持不变) ---
def generate_match_summary_image(match_data: dict, player_stats_list: list[dict], output_path: str):
    """
    (尚未实现) 根据比赛数据和玩家统计列表生成比赛总结图片。
    """
    logger.warning("generate_match_summary_image 函数尚未实现。")
    print("提示: 比赛总结图片生成功能 (generate_match_summary_image) 尚未实现。")
    pass