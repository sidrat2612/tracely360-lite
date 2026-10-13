"""tracely360 - extract · build · cluster · analyze · report."""


def __getattr__(name):
    # Lazy imports so `tracely360 install` works before heavy deps are in place.
    _map = {
        "extract": ("tracely360.extract", "extract"),
        "collect_files": ("tracely360.extract", "collect_files"),
        "build_from_json": ("tracely360.build", "build_from_json"),
        "cluster": ("tracely360.cluster", "cluster"),
        "score_all": ("tracely360.cluster", "score_all"),
        "cohesion_score": ("tracely360.cluster", "cohesion_score"),
        "god_nodes": ("tracely360.analyze", "god_nodes"),
        "surprising_connections": ("tracely360.analyze", "surprising_connections"),
        "suggest_questions": ("tracely360.analyze", "suggest_questions"),
        "graph_diff": ("tracely360.analyze", "graph_diff"),
        "query_graph": ("tracely360.query", "query_graph"),
        "get_node": ("tracely360.query", "get_node"),
        "get_neighbors": ("tracely360.query", "get_neighbors"),
        "get_community": ("tracely360.query", "get_community"),
        "graph_stats": ("tracely360.query", "graph_stats"),
        "shortest_path": ("tracely360.query", "shortest_path"),
        "generate": ("tracely360.report", "generate"),
        "to_json": ("tracely360.export", "to_json"),
        "to_html": ("tracely360.export", "to_html"),
        "to_svg": ("tracely360.export", "to_svg"),
        "to_canvas": ("tracely360.export", "to_canvas"),
        "to_wiki": ("tracely360.wiki", "to_wiki"),
    }
    if name in _map:
        import importlib
        mod_name, attr = _map[name]
        mod = importlib.import_module(mod_name)
        return getattr(mod, attr)
    raise AttributeError(f"module 'tracely360' has no attribute {name!r}")
