import importlib.resources
from dataclasses import dataclass
from functools import lru_cache

import yaml
 
 
@dataclass(frozen=True)
class EmbeddingConfig:
    collection_name: str
    model_name: str
    normalize: bool = True
    show_progress: bool = False

# AI Assessment:
@dataclass(frozen=True)
class AIAssessmentConfig:
    data_dir: str
    indexes_dir: str
    llm: str
    embedding: EmbeddingConfig   # ✅ add this


# -----------------------------
# Root config
# -----------------------------

@dataclass(frozen=True)
class AppConfig:
    ai_assessment: AIAssessmentConfig




# -----------------------------
# Loader (cached singleton)
# -----------------------------

@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    path = importlib.resources.files("app") / "config.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    ai_cfg = raw["ai_assessment"]

    return AppConfig(
        ai_assessment=AIAssessmentConfig(
            data_dir=ai_cfg["data_dir"],
            indexes_dir=ai_cfg["indexes_dir"],
            llm=ai_cfg["llm"],
            embedding=EmbeddingConfig(**ai_cfg["embedding"])  
        ),
    )

"""

How to use?

from chat_server.config import get_config

cfg = get_config()

cfg.firmographic.data_dir
cfg.firmographic.llm

cfg.services.serpapi.key
cfg.services.tavily.key


"""

# -------------------------------------------------------------------------
#  This takes RUnnableConfig (of LangGraph) and returns a simple config
# -------------------------------------------------------------------------
def get_cfg_from_runnable(rconfig):
    if isinstance(rconfig, dict):
        return rconfig.get("configurable", {}) or {}
    return getattr(rconfig, "configurable", {}) or {}
