import pytest
from services.classifier_registry import _load_defaults, ClassifierRules

def test_load_defaults():
    rules = _load_defaults()
    assert isinstance(rules, ClassifierRules)
    assert len(rules.ext_map) > 0
    assert len(rules.category_colors) > 0
    
    # Check for some common extensions
    assert ".js" in rules.ext_map
    assert ".py" in rules.ext_map
    assert ".ts" in rules.ext_map

def test_is_stale():
    import time
    rules = ClassifierRules(loaded_at=time.time() - 400) # 400s > TTL 300s
    assert rules.is_stale() is True
    
    rules_new = ClassifierRules(loaded_at=time.time())
    assert rules_new.is_stale() is False
