# src/core/models.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Index, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from datetime import datetime
from sqlalchemy.sql import func # 用于设置默认时间戳

# 从同一目录下的 database.py 导入 Base
from .database import Base

class Region(Base):
    """
    代表一个赛区 (e.g., Americas, EMEA, Pacific, China)。
    """
    __tablename__ = 'regions' # ::TABLE_NAME::

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    tag: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True, comment="赛区全称")
    abbreviation = Column(String(10), unique=True, nullable=True, comment="赛区缩写 (e.g., AMER)")

    # 反向关系：可以从 Region 访问其下的所有 Matches (如果需要)
    matches: Mapped[list['Match']] = relationship(back_populates='region')

    def __repr__(self) -> str:
        return f"<Region(id={self.id}, name='{self.name}', tag='{self.tag}')>"

class CompetitionType(Base):
    """
    代表一个赛事的类型或层级 (e.g., Kickoff, League Stage, Masters, Champions)。
    """
    __tablename__ = 'competition_types' # ::TABLE_NAME::

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, comment="赛事类型名称")
    tag: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True, comment="类型描述")

    # 反向关系：可以从 CompetitionType 访问该类型的所有 Matches (如果需要)
    matches: Mapped[list['Match']] = relationship(back_populates='competition_type')

    def __repr__(self) -> str:
        return f"<CompetitionType(id={self.id}, name='{self.name}', tag='{self.tag}')>"


class Match(Base):
    """
    代表一场独立的比赛。
    """
    __tablename__ = 'matches' # ::TABLE_NAME::

    id: Mapped[int] = mapped_column(primary_key=True)
    # 来自数据源（如 vlr.gg）的唯一比赛标识符
    match_source_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    match_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # 比赛相关的其他信息
    status: Mapped[str] = mapped_column(String(50), nullable=True, index=True)
    match_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    event_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    team1_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    team2_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    team1_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    team2_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # --- 新增字段 ---
    # 外键关联到赛区
    region_id: Mapped[int | None] = mapped_column(ForeignKey('regions.id'), nullable=True)
    # 外键关联到赛事类型
    competition_type_id: Mapped[int | None] = mapped_column(ForeignKey('competition_types.id'), nullable=True)

    # --- 关系 (用于 ORM 查询) ---
    # 关系到 Region 模型
    region: Mapped['Region'] = relationship(back_populates='matches')
    # 关系到 CompetitionType 模型
    competition_type: Mapped['CompetitionType'] = relationship(back_populates='matches')

    # 反向关系：允许从一个 Match 对象轻松访问该场比赛所有选手的统计数据
    player_stats: Mapped[list['PlayerMatchStats']] = relationship(back_populates='match')

    def __repr__(self):
        # 可以考虑在 repr 中包含赛区和类型信息
        return f"<Match(id={self.id}, source_id='{self.match_source_id}', url='{self.match_url}', status='{self.status}')>"
        
class Player(Base):
    """
    代表一个独立的选手。
    """
    __tablename__ = 'players' # ::TABLE_NAME::

    id: Mapped[int] = mapped_column(primary_key=True)
    # 来自数据源（如 vlr.gg）的唯一标识符，对于避免重复和关联非常重要
    player_source_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # 可以考虑添加其他相对稳定的信息，如国籍等，如果需要的话

    # 反向关系：允许从一个 Player 对象轻松访问其所有比赛的统计数据
    player_stats: Mapped[list['PlayerMatchStats']] = relationship(back_populates='player')

    def __repr__(self) -> str:
        return f"<Player(id={self.id}, source_id='{self.player_source_id}', name='{self.name}')>"


class PlayerMatchStats(Base):
    """
    存储一个选手在一场特定比赛中的详细统计数据。
    """
    __tablename__ = 'player_match_stats' # ::TABLE_NAME::

    id: Mapped[int] = mapped_column(primary_key=True)

    # --- 外键 ---
    player_id: Mapped[int] = mapped_column(ForeignKey('players.id'), nullable=False)
    match_id: Mapped[int] = mapped_column(ForeignKey('matches.id'), nullable=False)

    # --- 关系 (用于 ORM 查询) ---
    agent: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    player = relationship("Player", back_populates="player_stats")
    match = relationship("Match", back_populates="player_stats")

    # --- 比赛中的信息 ---
    # 选手在该场比赛中所属的战队 (可能与 Player 表中的 '当前' 战队不同)
    team_name = Column(String(100), nullable=True)

    # --- 核心表现指标 ---
    rating: Mapped[float | None] = mapped_column(Float, nullable=True, comment="选手本场Rating")
    acs: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="选手ACS数据 (平均战斗评分)")
    adr: Mapped[float | None] = mapped_column(Float, nullable=True, comment="选手ADR数据 (回合均伤)")
    kast_percentage: Mapped[float | None] = mapped_column(Float, nullable=True, comment="选手KAST数据 (%)") # Kills Assists Survived Traded
    headshot_percentage: Mapped[float | None] = mapped_column(Float, nullable=True, comment="选手HS%数据 (%)")

    # --- K/D/A ---
    kills: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="击杀数")
    deaths: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="死亡数")
    assists: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="助攻数")
    kill_death_difference: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="K-D差值") # Kills - Deaths

    # --- 首杀/首死 ---
    first_kills: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="首杀数")
    first_deaths: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="首死数")
    first_kill_first_death_difference: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="FK-FD差值") # First Kills - First Deaths

    # 创建复合索引以加速按比赛和选手查询统计数据的速度
    __table_args__ = (UniqueConstraint('player_id', 'match_id', name='_player_match_uc'),)

    def __repr__(self):
        return f"<PlayerMatchStats(player_id={self.player_id}, match_id={self.match_id}, agent='{self.agent}', KDA={self.kills}/{self.deaths}/{self.assists})>"




# --- 重要 ---
# 在 database.py 的 init_db() 函数被调用之前，必须确保这个文件(models.py)
# 被导入，这样 Base.metadata 才能知道这些模型。
# 我们可以在 database.py 中导入它们，或者在一个集中的地方（如 __init__.py 或 main app 文件）导入。
# 为了简单起见，我们暂时在 database.py 的 init_db 函数内部动态导入。