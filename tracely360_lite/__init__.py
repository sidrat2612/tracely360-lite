"""tracely360-lite - extract · build · cluster · analyze · report."""


def __getattr__(name):
    # Lazy imports so `tracely360-lite install` works before heavy deps are in place.
    _map = {
        "extract": ("tracely360_lite.extract", "extract"),
        "collect_files": ("tracely360_lite.extract", "collect_files"),
        "build_from_json": ("tracely360_lite.build", "build_from_json"),
        "cluster": ("tracely360_lite.cluster", "cluster"),
        "score_all": ("tracely360_lite.cluster", "score_all"),
        "cohesion_score": ("tracely360_lite.cluster", "cohesion_score"),
        "god_nodes": ("tracely360_lite.analyze", "god_nodes"),
        "surprising_connections": ("tracely360_lite.analyze", "surprising_connections"),
        "suggest_questions": ("tracely360_lite.analyze", "suggest_questions"),
        "generate": ("tracely360_lite.report", "generate"),
        "to_json": ("tracely360_lite.export", "to_json"),
        "to_html": ("tracely360_lite.export", "to_html"),
        "to_svg": ("tracely360_lite.export", "to_svg"),
        "to_canvas": ("tracely360_lite.export", "to_canvas"),
        "to_wiki": ("tracely360_lite.wiki", "to_wiki"),
    }
    if name in _map:
        import importlib
        mod_name, attr = _map[name]
        mod = importlib.import_module(mod_name)
        return getattr(mod, attr)
    raise AttributeError(f"module 'tracely360-lite' has no attribute {name!r}")
