from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Optional

_log = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 300


@dataclass
class ClassifierRules:
    ext_map:          dict[str, tuple[str, str]]        = field(default_factory=dict)
    named_map:        dict[str, tuple[str, str]]        = field(default_factory=dict)
    fingerprints:     list[tuple[re.Pattern, str, str]] = field(default_factory=list)
    path_patterns:    list[tuple[re.Pattern, str, str]] = field(default_factory=list)
    category_colors:  dict[str, str]                    = field(default_factory=dict)
    edge_colors:      dict[tuple[str, str], str]        = field(default_factory=dict)
    unambiguous_exts: frozenset                         = field(default_factory=frozenset)
    loaded_at:        float                             = field(default_factory=time.time)

    def is_stale(self) -> bool:
        return (time.time() - self.loaded_at) > CACHE_TTL_SECONDS


_cached_rules: Optional[ClassifierRules] = None


async def get_rules() -> ClassifierRules:
    global _cached_rules

    if _cached_rules is not None and not _cached_rules.is_stale():
        return _cached_rules

    try:
        rules = await _load_from_db()
        _cached_rules = rules
        _log.debug(
            "Classifier rules loaded from MongoDB — "
            "%d extensions, %d fingerprints, %d path patterns",
            len(rules.ext_map), len(rules.fingerprints), len(rules.path_patterns),
        )
        return rules
    except Exception as e:
        _log.warning("Failed to load classifier rules from MongoDB: %s — using defaults", e)
        if _cached_rules is not None:
            return _cached_rules  
        rules = _load_defaults()
        _cached_rules = rules
        return rules


async def invalidate_cache() -> None:
    global _cached_rules
    _cached_rules = None
    _log.info("Classifier rule cache invalidated")


async def _load_from_db() -> ClassifierRules:
    from database import get_db
    db = get_db()

    rules = ClassifierRules()
    unambiguous = set()
    
    async for doc in db.classifier_extensions.find({}):
        rules.ext_map[doc["ext"]] = (doc["category"], doc["sub"])
        if doc.get("unambiguous"):
            unambiguous.add(doc["ext"])
    rules.unambiguous_exts = frozenset(unambiguous)

    async for doc in db.classifier_named_files.find({}):
        rules.named_map[doc["name"].lower()] = (doc["category"], doc["sub"])

    async for doc in db.classifier_fingerprints.find({}, sort=[("priority", 1)]):
        flags = 0
        for flag_name in doc.get("flags", "").split(","):
            flag_name = flag_name.strip().upper()
            if flag_name == "IGNORECASE": flags |= re.IGNORECASE
            if flag_name == "MULTILINE":  flags |= re.MULTILINE
        try:
            pattern = re.compile(doc["pattern"], flags)
            rules.fingerprints.append((pattern, doc["category"], doc["sub"]))
        except re.error as e:
            _log.warning("Invalid fingerprint regex (priority %s): %s", doc.get("priority"), e)

    async for doc in db.classifier_path_patterns.find({}, sort=[("priority", 1)]):
        try:
            pattern = re.compile(doc["pattern"])
            rules.path_patterns.append((pattern, doc["category"], doc["sub"]))
        except re.error as e:
            _log.warning("Invalid path pattern regex (priority %s): %s", doc.get("priority"), e)

    async for doc in db.classifier_categories.find({}):
        rules.category_colors[doc["category"]] = doc["color"]

    async for doc in db.classifier_edge_colors.find({}):
        rules.edge_colors[(doc["src"], doc["tgt"])] = doc["color"]

    return rules


def _load_defaults() -> ClassifierRules:
    from services.classifier_seed import (
        EXTENSIONS, NAMED_FILES, FINGERPRINTS,
        PATH_PATTERNS, CATEGORY_COLORS, EDGE_COLORS,
    )

    rules = ClassifierRules()
    unambiguous = set()

    for doc in EXTENSIONS:
        rules.ext_map[doc["ext"]] = (doc["category"], doc["sub"])
        if doc.get("unambiguous"):
            unambiguous.add(doc["ext"])
    rules.unambiguous_exts = frozenset(unambiguous)

    for doc in NAMED_FILES:
        rules.named_map[doc["name"].lower()] = (doc["category"], doc["sub"])

    for doc in sorted(FINGERPRINTS, key=lambda d: d["priority"]):
        flags = 0
        for flag_name in doc.get("flags", "").split(","):
            flag_name = flag_name.strip().upper()
            if flag_name == "IGNORECASE": flags |= re.IGNORECASE
            if flag_name == "MULTILINE":  flags |= re.MULTILINE
        try:
            rules.fingerprints.append(
                (re.compile(doc["pattern"], flags), doc["category"], doc["sub"])
            )
        except re.error:
            pass

    for doc in sorted(PATH_PATTERNS, key=lambda d: d["priority"]):
        try:
            rules.path_patterns.append(
                (re.compile(doc["pattern"]), doc["category"], doc["sub"])
            )
        except re.error:
            pass

    for doc in CATEGORY_COLORS:
        rules.category_colors[doc["category"]] = doc["color"]

    for doc in EDGE_COLORS:
        rules.edge_colors[(doc["src"], doc["tgt"])] = doc["color"]

    _log.warning("Using hardcoded classifier defaults (MongoDB unavailable)")
    return rules
