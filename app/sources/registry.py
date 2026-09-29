from typing import Dict, Type, List, Optional, Tuple, Any
import logging
from sqlalchemy.orm import Session
from app.sources.base import SourceAdapter
from app.sources.tathva import TathvaSourceAdapter
from app.sources.devfolio import DevfolioSourceAdapter
from app.sources.unstop import UnstopSourceAdapter
from app.sources.devpost import DevpostSourceAdapter
from app.sources.mlh import MLHSourceAdapter
from app.sources.hack2skill import Hack2SkillSourceAdapter
from app.sources.kaggle import KaggleSourceAdapter
from app.sources.generic import GenericSourceAdapter
from app.database.schema import Source, utc_now

logger = logging.getLogger("hackradar.sources.registry")

class SourceRegistry:
    def __init__(self):
        self._registry: Dict[str, Type[SourceAdapter]] = {}
        # Register core source adapters
        self.register("tathva", TathvaSourceAdapter)
        self.register("devfolio", DevfolioSourceAdapter)
        self.register("unstop", UnstopSourceAdapter)
        self.register("devpost", DevpostSourceAdapter)
        self.register("mlh", MLHSourceAdapter)
        self.register("hack2skill", Hack2SkillSourceAdapter)
        self.register("kaggle", KaggleSourceAdapter)
        self.register("generic", GenericSourceAdapter)

    def register(self, name: str, adapter_cls: Type[SourceAdapter]):
        self._registry[name.lower()] = adapter_cls
        logger.debug(f"Registered source adapter: {name} -> {adapter_cls.__name__}")

    def get_adapter_class(self, name: str) -> Optional[Type[SourceAdapter]]:
        return self._registry.get(name.lower())

    def get_adapter(self, name: str, **kwargs) -> Optional[SourceAdapter]:
        cls = self.get_adapter_class(name)
        if cls:
            return cls(**kwargs)
        return None

    def list_registered_names(self) -> List[str]:
        return list(self._registry.keys())

    def get_enabled_adapters(self, db: Session) -> List[Tuple[Source, SourceAdapter]]:
        """Return (db_source, adapter_instance) for all enabled sources in DB"""
        db_sources = db.query(Source).filter(Source.enabled == True).all()
        result = []
        for src in db_sources:
            adapter = self.get_adapter(src.name)
            if adapter:
                # If custom URL configured in DB, pass it
                if src.base_url:
                    adapter.base_url = src.base_url
                result.append((src, adapter))
            else:
                logger.warning(f"No adapter registered for enabled source '{src.name}'")
        return result

    def run_health_checks(self, db: Session) -> Dict[str, Dict[str, Any]]:
        """Run health checks on all registered sources and update DB"""
        results = {}
        db_sources = db.query(Source).all()
        for src in db_sources:
            adapter = self.get_adapter(src.name)
            if not adapter:
                results[src.name] = {"healthy": False, "message": "No adapter found"}
                continue

            try:
                healthy, msg = adapter.health_check()
                src.last_checked_at = utc_now()
                if healthy:
                    src.last_success_at = utc_now()
                    src.last_error = None
                else:
                    src.last_error = msg
                results[src.name] = {"healthy": healthy, "message": msg}
            except Exception as e:
                src.last_checked_at = utc_now()
                src.last_error = str(e)
                results[src.name] = {"healthy": False, "message": str(e)}

        db.commit()
        return results

# Global singleton
source_registry = SourceRegistry()
