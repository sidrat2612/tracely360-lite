"""API endpoint/route extraction from AST trees.

Detects HTTP route definitions across web frameworks and emits endpoint nodes
+ exposes_endpoint edges. Called as a post-AST pass from extract.py.

Supported frameworks:
  Python:  Flask, FastAPI, Django
  JS/TS:   Express, NestJS, Next.js (file-based)
  Java:    Spring (@RequestMapping, @GetMapping, etc.)
  PHP:     Laravel (Route::get, Route::group, Route::resource)
  Ruby:    Rails (get, post, resources, namespace)
  Go:      Gin, Echo, Chi
  C#:      ASP.NET ([HttpGet], [Route], MapGet)
"""
from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from tracely360.tree_sitter_utils import read_node_text

# HTTP methods we recognize
_HTTP_METHODS = frozenset({"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"})


def _path_within_root(path: Path, root: Path) -> bool:
    """Return True if resolved path is inside the project root."""
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


# ── Helpers ──────────────────────────────────────────────────────────────────

_read_text = read_node_text


def _strip_quotes(s: str) -> str:
    if len(s) >= 2 and s[0] in ('"', "'") and s[-1] == s[0]:
        return s[1:-1]
    return s


def _normalize_path(*parts: str) -> str:
    joined = "/".join(p.strip("/") for p in parts if p)
    return "/" + joined if joined else "/"


def _find_child(node, *types: str):
    for child in node.children:
        if child.type in types:
            return child
    return None


def _iter_argument_values(node):
    for child in node.children:
        if child.type in ("(", ")", ","):
            continue
        if child.type == "argument":
            yielded = False
            for sub in child.children:
                yield sub
                yielded = True
            if not yielded:
                yield child
            continue
        yield child


def _make_endpoint_id(stem: str, method: str, path: str) -> str:
    safe = path.replace("/", "_").replace("<", "").replace(">", "").replace("{", "").replace("}", "").replace(":", "")
    return f"{stem}_endpoint_{method.lower()}_{safe}".rstrip("_")


def _make_code_id(*parts: str) -> str:
    combined = "_".join(part.strip("_.") for part in parts if part)
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", combined)
    return cleaned.strip("_").lower()


def _unique_nonempty(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result


def _singularize_name(name: str) -> str:
    if name.endswith("ies") and len(name) > 3:
        return name[:-3] + "y"
    if name.endswith("ses") and len(name) > 3:
        return name[:-2]
    if name.endswith("s") and len(name) > 1:
        return name[:-1]
    return name


def _pluralize_name(name: str) -> str:
    if name.endswith("ies") and len(name) > 3:
        return name
    if name.endswith("y") and len(name) > 1 and name[-2].lower() not in "aeiou":
        return name[:-1] + "ies"
    if name.endswith("s"):
        return name
    return name + "s"


def _camelize_name(name: str) -> str:
    parts = [part for part in re.split(r"[^a-zA-Z0-9]+", name) if part]
    return "".join(part[:1].upper() + part[1:] for part in parts)


def _last_path_segment(path: str) -> str:
    parts = [part for part in path.strip("/").split("/") if part]
    return parts[-1] if parts else ""


def _first_string_literal(node, source: bytes) -> str | None:
    if node.type in (
        "string",
        "string_literal",
        "interpreted_string_literal",
        "raw_string_literal",
        "verbatim_string_literal",
    ):
        text = _read_text(node, source)
        return _strip_quotes(text)
    if node.type in ("string_content", "string_fragment"):
        return _read_text(node, source)
    for child in node.children:
        result = _first_string_literal(child, source)
        if result is not None:
            return result
    return None


def _all_string_literals(node, source: bytes) -> list[str]:
    values: list[str] = []
    literal = _first_string_literal(node, source)
    if literal is not None and node.type in (
        "string",
        "string_literal",
        "interpreted_string_literal",
        "raw_string_literal",
        "verbatim_string_literal",
        "string_content",
        "string_fragment",
    ):
        return [literal]
    for child in node.children:
        values.extend(_all_string_literals(child, source))
    return values


def _first_string_arg(node, source: bytes) -> str | None:
    """Extract the first string literal from an argument list node."""
    for child in _iter_argument_values(node):
        result = _first_string_literal(child, source)
        if result is not None:
            return result
    return None


def _is_nextjs_route_file(path: Path) -> bool:
    parts = path.parts
    return ("pages" in parts and "api" in parts) or (path.stem == "route" and "app" in parts)


def _preferred_controller_name(controller_candidates: list[str]) -> str | None:
    candidates = _unique_nonempty(controller_candidates)
    if not candidates:
        return None
    for candidate in candidates:
        if "::" in candidate or "\\" in candidate:
            return candidate
    return candidates[0]


def _endpoint_metadata(*, controller: str | None = None, action: str | None = None) -> dict[str, str]:
    metadata: dict[str, str] = {}
    if controller:
        metadata["controller"] = controller
    if action:
        metadata["action"] = action
    return metadata


def _append_raw_endpoint_ref(raw_endpoint_refs: list[dict], endpoint_id: str,
                             controller_candidates: list[str] | None, action: str | None,
                             source_file: str, line: int, *,
                             handler_candidates: list[str] | None = None,
                             controller: str | None = None) -> None:
    cleaned_action = action.strip() if action else ""
    cleaned_controller_candidates = _unique_nonempty(controller_candidates or [])
    cleaned_handler_candidates = _unique_nonempty(handler_candidates or [])
    if not cleaned_action or (not cleaned_controller_candidates and not cleaned_handler_candidates):
        return

    ref = {
        "endpoint_id": endpoint_id,
        "action": cleaned_action,
        "source_file": source_file,
        "source_location": f"L{line}",
    }
    if cleaned_controller_candidates:
        ref["controller_candidates"] = cleaned_controller_candidates
    if cleaned_handler_candidates:
        ref["handler_candidates"] = cleaned_handler_candidates
    if controller:
        ref["controller"] = controller
    raw_endpoint_refs.append(ref)


# ── Python: Flask / FastAPI / Django ─────────────────────────────────────────

_PYTHON_ROUTE_DECORATORS = {
    "route": None,           # @app.route('/path', methods=['GET'])
    "get": "GET",
    "post": "POST",
    "put": "PUT",
    "delete": "DELETE",
    "patch": "PATCH",
    "head": "HEAD",
    "options": "OPTIONS",
    "api_route": None,       # FastAPI
    "websocket": "WEBSOCKET",
}


def _extract_methods_kwarg(decorator_call, source: bytes) -> list[str]:
    """Parse methods=['GET', 'POST'] from a decorator call's argument list."""
    args = decorator_call.child_by_field_name("arguments")
    if not args:
        return ["GET"]
    for child in args.children:
        if child.type == "keyword_argument":
            key_node = child.child_by_field_name("name")
            if key_node and _read_text(key_node, source) == "methods":
                val = child.child_by_field_name("value")
                if val and val.type == "list":
                    methods = []
                    for item in val.children:
                        if item.type == "string":
                            methods.append(_strip_quotes(_read_text(item, source)).upper())
                    return methods if methods else ["GET"]
    return ["GET"]


def _python_keyword_value(args_node, source: bytes, name: str):
    for child in _iter_argument_values(args_node):
        if child.type != "keyword_argument":
            continue
        key_node = child.child_by_field_name("name")
        if key_node and _read_text(key_node, source) == name:
            return child.child_by_field_name("value")
    return None


def _python_keyword_string(args_node, source: bytes, name: str) -> str | None:
    value = _python_keyword_value(args_node, source, name)
    if value is None:
        return None
    return _first_string_literal(value, source)


def _python_first_identifier_arg(args_node, source: bytes) -> str | None:
    for child in _iter_argument_values(args_node):
        if child.type == "keyword_argument":
            continue
        if child.type == "identifier":
            return _read_text(child, source)
    return None


def _resolve_python_module_file(current_path: Path, module_name: str, project_root: Path | None = None) -> Path | None:
    dots = len(module_name) - len(module_name.lstrip("."))
    module_parts = [part for part in module_name.lstrip(".").split(".") if part]
    if not module_parts:
        return None
    base_path = current_path.parent
    for _ in range(max(dots - 1, 0)):
        base_path = base_path.parent
    module_path = base_path.joinpath(*module_parts).with_suffix(".py")
    if module_path.exists():
        if project_root and not _path_within_root(module_path, project_root):
            return None
        return module_path
    package_init = base_path.joinpath(*module_parts, "__init__.py")
    if package_init.exists():
        if project_root and not _path_within_root(package_init, project_root):
            return None
        return package_init
    return None


def _collect_python_import_alias_paths(root, source: bytes, path: Path) -> dict[str, Path]:
    alias_paths: dict[str, Path] = {}

    def walk(node):
        if node.type == "import_from_statement":
            module_name = None
            after_import = False
            imported_aliases: list[str] = []

            for child in node.children:
                if child.type == "import":
                    after_import = True
                    continue
                if not after_import and child.type in ("relative_import", "dotted_name"):
                    module_name = _read_text(child, source)
                    continue
                if after_import:
                    if child.type == "aliased_import":
                        alias_name = None
                        original_name = None
                        for sub in child.children:
                            if sub.type == "dotted_name" and original_name is None:
                                original_name = _read_text(sub, source)
                            elif sub.type == "identifier":
                                alias_name = _read_text(sub, source)
                        imported_aliases.append(alias_name or (original_name.split(".")[-1] if original_name else ""))
                    elif child.type == "dotted_name":
                        imported_aliases.append(_read_text(child, source).split(".")[-1])

            if module_name:
                module_path = _resolve_python_module_file(path, module_name)
                if module_path:
                    for alias_name in imported_aliases:
                        if alias_name:
                            alias_paths[alias_name] = module_path

        for child in node.children:
            walk(child)

    walk(root)
    return alias_paths


def _resolve_django_include_path(include_args, source: bytes, current_path: Path,
                                 alias_paths: dict[str, Path],
                                 project_root: Path | None = None) -> Path | None:
    include_values = [child for child in _iter_argument_values(include_args)]
    if not include_values:
        return None

    target = include_values[0]
    if target.type == "tuple":
        tuple_values = [child for child in target.children if child.type not in ("(", ")", ",")]
        if not tuple_values:
            return None
        target = tuple_values[0]

    if target.type == "identifier":
        resolved = alias_paths.get(_read_text(target, source))
        if resolved and project_root and not _path_within_root(resolved, project_root):
            return None
        return resolved

    module_name = _first_string_literal(target, source)
    if module_name:
        return _resolve_python_module_file(current_path, module_name, project_root=project_root)

    return None


def _extract_python_endpoints(root, source: bytes, path: Path) -> tuple[list[dict], list[dict]]:
    """Extract endpoints from Python decorated functions (Flask, FastAPI)."""
    stem = path.stem
    str_path = str(path)
    nodes: list[dict] = []
    edges: list[dict] = []
    local_prefixes: dict[str, str] = {}
    mounted_prefixes: dict[str, list[str]] = {}

    # Also detect Django urlpatterns
    _extract_django_urls(root, source, path, nodes, edges)

    def collect_route_context(node):
        if node.type == "assignment":
            target_name = None
            value_node = None
            for child in node.children:
                if child.type == "identifier" and target_name is None:
                    target_name = _read_text(child, source)
                elif child.type == "call":
                    value_node = child
            if target_name and value_node:
                callee = value_node.child_by_field_name("function")
                args = value_node.child_by_field_name("arguments")
                if callee and callee.type == "identifier" and args:
                    callee_name = _read_text(callee, source)
                    if callee_name == "Blueprint":
                        prefix = _python_keyword_string(args, source, "url_prefix")
                        if prefix:
                            local_prefixes[target_name] = prefix
                    elif callee_name == "APIRouter":
                        prefix = _python_keyword_string(args, source, "prefix")
                        if prefix:
                            local_prefixes[target_name] = prefix
        elif node.type == "call":
            callee = node.child_by_field_name("function")
            args = node.child_by_field_name("arguments")
            if callee and callee.type == "attribute" and args:
                attr_node = callee.child_by_field_name("attribute")
                if not attr_node:
                    return
                attr_name = _read_text(attr_node, source)
                if attr_name not in ("register_blueprint", "include_router"):
                    return
                mounted_name = _python_first_identifier_arg(args, source)
                prefix_key = "url_prefix" if attr_name == "register_blueprint" else "prefix"
                prefix = _python_keyword_string(args, source, prefix_key)
                if mounted_name and prefix:
                    mounted_prefixes.setdefault(mounted_name, []).append(prefix)

        for child in node.children:
            collect_route_context(child)

    collect_route_context(root)

    def walk(node):
        if node.type == "decorated_definition":
            func_def = None
            decorators = []
            for child in node.children:
                if child.type == "decorator":
                    decorators.append(child)
                elif child.type in ("function_definition", "async_function_definition"):
                    func_def = child

            if not func_def:
                for child in node.children:
                    walk(child)
                return

            func_name_node = func_def.child_by_field_name("name")
            func_name = _read_text(func_name_node, source) if func_name_node else "unknown"
            func_nid = f"{stem}_{func_name}"

            for dec in decorators:
                # Find the call inside the decorator
                call_node = None
                for child in dec.children:
                    if child.type == "call":
                        call_node = child
                        break

                if not call_node:
                    continue

                # Get the callee — could be attribute (app.route) or identifier
                callee = call_node.child_by_field_name("function")
                if not callee:
                    continue

                method_name = None
                owner_name = ""
                if callee.type == "attribute":
                    attr_node = callee.child_by_field_name("attribute")
                    obj_node = callee.child_by_field_name("object")
                    if obj_node:
                        owner_name = _read_text(obj_node, source)
                    if attr_node:
                        method_name = _read_text(attr_node, source)
                elif callee.type == "identifier":
                    method_name = _read_text(callee, source)

                if not method_name or method_name not in _PYTHON_ROUTE_DECORATORS:
                    continue

                # Get the path from the first argument
                args = call_node.child_by_field_name("arguments")
                if not args:
                    continue
                route_path = _first_string_arg(args, source)
                if route_path is None:
                    route_path = "/"

                # Determine HTTP methods
                fixed_method = _PYTHON_ROUTE_DECORATORS[method_name]
                if fixed_method:
                    methods = [fixed_method]
                else:
                    methods = _extract_methods_kwarg(call_node, source)

                base_prefix = local_prefixes.get(owner_name, "")
                mounted = mounted_prefixes.get(owner_name)
                full_paths = [
                    _normalize_path(mount_prefix, base_prefix, route_path)
                    for mount_prefix in mounted
                ] if mounted else [_normalize_path(base_prefix, route_path)]

                line = dec.start_point[0] + 1
                for method in methods:
                    for full_path in full_paths:
                        ep_id = _make_endpoint_id(stem, method, full_path)
                        nodes.append({
                            "id": ep_id,
                            "label": f"{method} {full_path}",
                            "file_type": "endpoint",
                            "method": method,
                            "path": full_path,
                            "framework": "flask/fastapi",
                            "source_file": str_path,
                            "source_location": f"L{line}",
                        })
                        edges.append({
                            "source": func_nid,
                            "target": ep_id,
                            "relation": "exposes_endpoint",
                            "confidence": "EXTRACTED",
                            "source_file": str_path,
                            "source_location": f"L{line}",
                            "weight": 1.0,
                        })

        for child in node.children:
            walk(child)

    walk(root)
    return nodes, edges


def _extract_django_urls(root, source: bytes, path: Path,
                         nodes: list[dict], edges: list[dict],
                         base_prefix: str = "", visited: set[Path] | None = None,
                         project_root: Path | None = None, _parser=None) -> None:
    """Extract Django urlpatterns: path('route/', view_func)."""
    stem = path.stem
    str_path = str(path)
    resolved_path = path.resolve()
    visited_paths = set() if visited is None else set(visited)
    visited_paths.add(resolved_path)
    import_alias_paths = _collect_python_import_alias_paths(root, source, path)

    # Infer project root from the first call if not provided
    if project_root is None:
        project_root = path.resolve().parent

    # Reuse parser across recursive calls
    if _parser is None:
        from tree_sitter import Language, Parser
        import tree_sitter_python as tspython
        _parser = Parser(Language(tspython.language()))

    def walk(node):
        if node.type == "call":
            callee = node.child_by_field_name("function")
            if callee and callee.type == "identifier":
                name = _read_text(callee, source)
                if name in ("path", "re_path", "url"):
                    args = node.child_by_field_name("arguments")
                    if args:
                        route_path = _first_string_arg(args, source)
                        if route_path is not None:
                            arg_values = [child for child in _iter_argument_values(args)]
                            full_path = _normalize_path(base_prefix, route_path)
                            line = node.start_point[0] + 1
                            handled_include = False
                            if len(arg_values) >= 2 and arg_values[1].type == "call":
                                include_callee = arg_values[1].child_by_field_name("function")
                                if include_callee and include_callee.type == "identifier" and _read_text(include_callee, source) == "include":
                                    include_args = arg_values[1].child_by_field_name("arguments")
                                    include_path = _resolve_django_include_path(include_args, source, path, import_alias_paths, project_root=project_root) if include_args else None
                                    if include_path and include_path.resolve() not in visited_paths:
                                        include_source = include_path.read_bytes()
                                        include_root = _parser.parse(include_source).root_node
                                        _extract_django_urls(
                                            include_root,
                                            include_source,
                                            include_path,
                                            nodes,
                                            edges,
                                            base_prefix=full_path,
                                            visited=visited_paths | {include_path.resolve()},
                                            project_root=project_root,
                                            _parser=_parser,
                                        )
                                        handled_include = True

                            if not handled_include:
                                ep_id = _make_endpoint_id(stem, "ANY", full_path)
                                nodes.append({
                                    "id": ep_id,
                                    "label": f"ANY {full_path}",
                                    "file_type": "endpoint",
                                    "method": "ANY",
                                    "path": full_path,
                                    "framework": "django",
                                    "source_file": str_path,
                                    "source_location": f"L{line}",
                                })
                                # Try to get the view function name (second arg)
                                if len(arg_values) >= 2:
                                    view = arg_values[1]
                                    view_name = _read_text(view, source).split(".")[-1]
                                    view_nid = f"{stem}_{view_name}"
                                    edges.append({
                                        "source": view_nid,
                                        "target": ep_id,
                                        "relation": "exposes_endpoint",
                                        "confidence": "EXTRACTED",
                                        "source_file": str_path,
                                        "source_location": f"L{line}",
                                        "weight": 1.0,
                                    })
        for child in node.children:
            walk(child)

    walk(root)


# ── JS/TS: Express / NestJS ─────────────────────────────────────────────────

_JS_ROUTE_METHODS = {"get", "post", "put", "delete", "patch", "head", "options", "all"}

_NESTJS_DECORATORS = {
    "Get": "GET",
    "Post": "POST",
    "Put": "PUT",
    "Delete": "DELETE",
    "Patch": "PATCH",
    "Head": "HEAD",
    "Options": "OPTIONS",
    "All": "ALL",
}


def _extract_js_endpoints(root, source: bytes, path: Path) -> tuple[list[dict], list[dict]]:
    """Extract endpoints from JS/TS Express-style calls and NestJS decorators."""
    stem = path.stem
    str_path = str(path)
    nodes: list[dict] = []
    edges: list[dict] = []

    # Track router group prefixes: variable name → prefix
    group_prefixes: dict[str, str] = {}

    def _detect_router_prefix(node):
        """Detect Express Router() or route('/prefix') assignments."""
        if node.type in ("variable_declarator", "lexical_declaration"):
            for child in node.children:
                _detect_router_prefix(child)
            return
        if node.type == "call_expression":
            callee = node.child_by_field_name("function")
            if callee and callee.type == "member_expression":
                prop = callee.child_by_field_name("property")
                if prop and _read_text(prop, source) == "route":
                    args = node.child_by_field_name("arguments")
                    if args:
                        prefix = _first_string_arg(args, source)
                        if prefix:
                            obj = callee.child_by_field_name("object")
                            if obj:
                                group_prefixes[_read_text(obj, source)] = prefix

    def _get_nestjs_class_prefix(class_node, source: bytes) -> str:
        """Get @Controller('prefix') from a NestJS class."""
        for child in class_node.children:
            if child.type != "decorator":
                continue
            for sub in child.children:
                if sub.type != "call_expression":
                    continue
                callee = sub.child_by_field_name("function")
                if callee and _read_text(callee, source) == "Controller":
                    args = sub.child_by_field_name("arguments") or _find_child(sub, "arguments")
                    if args:
                        prefix = _first_string_arg(args, source)
                        if prefix:
                            return prefix

        # Look for decorators before the class
        parent = class_node.parent
        if parent and parent.type == "export_statement":
            parent = parent.parent
        if not parent:
            return ""
        prev = class_node.prev_named_sibling
        while prev:
            if prev.type == "decorator":
                for child in prev.children:
                    if child.type == "call_expression":
                        callee = child.child_by_field_name("function")
                        if callee and _read_text(callee, source) == "Controller":
                            args = child.child_by_field_name("arguments")
                            if args:
                                p = _first_string_arg(args, source)
                                if p:
                                    return p
            prev = prev.prev_named_sibling
        return ""

    def walk(node, class_prefix: str = "", class_name: str = ""):
        # Detect class with @Controller prefix (NestJS)
        if node.type == "class_declaration":
            prefix = _get_nestjs_class_prefix(node, source) or class_prefix
            name_node = node.child_by_field_name("name") or _find_child(node, "type_identifier", "identifier")
            current_class_name = _read_text(name_node, source) if name_node else class_name
            for child in node.children:
                walk(child, class_prefix=prefix, class_name=current_class_name)
            return

        # Express-style: app.get('/path', handler)
        if node.type in ("call_expression", "expression_statement"):
            actual = node
            if node.type == "expression_statement":
                actual = node.children[0] if node.children else node
            if actual.type == "call_expression":
                callee = actual.child_by_field_name("function")
                if callee and callee.type == "member_expression":
                    prop = callee.child_by_field_name("property")
                    obj = callee.child_by_field_name("object")
                    if prop:
                        method_name = _read_text(prop, source)
                        if method_name in _JS_ROUTE_METHODS:
                            args = actual.child_by_field_name("arguments")
                            if args:
                                route_path = _first_string_arg(args, source)
                                if route_path is not None:
                                    # Check if the object has a known prefix
                                    obj_name = _read_text(obj, source) if obj else ""
                                    prefix = group_prefixes.get(obj_name, "")
                                    full_path = _normalize_path(prefix, route_path)
                                    method = method_name.upper() if method_name != "all" else "ALL"
                                    line = actual.start_point[0] + 1
                                    ep_id = _make_endpoint_id(stem, method, full_path)
                                    nodes.append({
                                        "id": ep_id,
                                        "label": f"{method} {full_path}",
                                        "file_type": "endpoint",
                                        "method": method,
                                        "path": full_path,
                                        "framework": "express",
                                        "source_file": str_path,
                                        "source_location": f"L{line}",
                                    })
                                    # Try to link to the handler function
                                    non_str = [c for c in args.children
                                               if c.type not in ("(", ")", ",", "string", "template_string")]
                                    if non_str:
                                        handler = non_str[-1]
                                        if handler.type == "identifier":
                                            handler_nid = f"{stem}_{_read_text(handler, source)}"
                                            edges.append({
                                                "source": handler_nid,
                                                "target": ep_id,
                                                "relation": "exposes_endpoint",
                                                "confidence": "EXTRACTED",
                                                "source_file": str_path,
                                                "source_location": f"L{line}",
                                                "weight": 1.0,
                                            })

                        # Detect .use('/prefix', router) for prefix tracking
                        if method_name == "use":
                            args = actual.child_by_field_name("arguments")
                            if args:
                                items = [c for c in args.children if c.type not in ("(", ")", ",")]
                                if len(items) >= 2 and items[0].type == "string":
                                    prefix = _strip_quotes(_read_text(items[0], source))
                                    router_name = _read_text(items[1], source)
                                    group_prefixes[router_name] = prefix

        # NestJS decorators on methods
        if node.type == "decorator":
            for child in node.children:
                if child.type == "call_expression":
                    callee = child.child_by_field_name("function")
                    if callee:
                        dec_name = _read_text(callee, source)
                        if dec_name in _NESTJS_DECORATORS:
                            args = child.child_by_field_name("arguments")
                            route_path = ""
                            if args:
                                route_path = _first_string_arg(args, source) or ""
                            method = _NESTJS_DECORATORS[dec_name]
                            full_path = _normalize_path(class_prefix, route_path)
                            line = node.start_point[0] + 1

                            # Try to find the method this decorates
                            next_sib = node.next_named_sibling
                            func_name = "unknown"
                            if next_sib and next_sib.type in ("method_definition", "public_field_definition"):
                                name_node = next_sib.child_by_field_name("name")
                                if name_node:
                                    func_name = _read_text(name_node, source)

                            ep_id = _make_endpoint_id(stem, method, full_path)
                            nodes.append({
                                "id": ep_id,
                                "label": f"{method} {full_path}",
                                "file_type": "endpoint",
                                "method": method,
                                "path": full_path,
                                "framework": "nestjs",
                                "source_file": str_path,
                                "source_location": f"L{line}",
                            } | _endpoint_metadata(
                                controller=class_name or None,
                                action=func_name if func_name != "unknown" else None,
                            ))
                            func_nid = _make_code_id(stem, class_name, func_name) if class_name else _make_code_id(stem, func_name)
                            edges.append({
                                "source": func_nid,
                                "target": ep_id,
                                "relation": "exposes_endpoint",
                                "confidence": "EXTRACTED",
                                "source_file": str_path,
                                "source_location": f"L{line}",
                                "weight": 1.0,
                            })

        _detect_router_prefix(node)
        for child in node.children:
            walk(child, class_prefix, class_name)

    walk(root)
    return nodes, edges


# ── Next.js file-based routing ───────────────────────────────────────────────

def _extract_nextjs_route_methods(root, source: bytes) -> list[tuple[str, int]]:
    methods: list[tuple[str, int]] = []
    seen_methods: set[str] = set()

    def add_method(name: str, line: int) -> None:
        upper_name = name.upper()
        if upper_name not in _HTTP_METHODS or upper_name in seen_methods:
            return
        seen_methods.add(upper_name)
        methods.append((upper_name, line))

    for child in root.children:
        if child.type != "export_statement":
            continue
        for export_child in child.children:
            if export_child.type == "function_declaration":
                name_node = export_child.child_by_field_name("name")
                if name_node:
                    add_method(_read_text(name_node, source), export_child.start_point[0] + 1)
            elif export_child.type in ("lexical_declaration", "variable_declaration"):
                for grandchild in export_child.children:
                    if grandchild.type == "variable_declarator":
                        name_node = grandchild.child_by_field_name("name") or _find_child(grandchild, "identifier")
                        if name_node:
                            add_method(_read_text(name_node, source), grandchild.start_point[0] + 1)

    return methods


def _extract_nextjs_endpoints(root, source: bytes, path: Path) -> tuple[list[dict], list[dict]]:
    """Detect Next.js API routes from file path convention."""
    str_path = str(path)
    stem = path.stem
    parts = path.parts

    # pages/api/**/*.ts or app/**/route.ts
    nodes: list[dict] = []
    edges: list[dict] = []

    if "pages" in parts and "api" in parts:
        api_idx = parts.index("api")
        route_parts = list(parts[api_idx:])
        if route_parts[-1].startswith("index."):
            route_parts = route_parts[:-1]
        else:
            route_parts[-1] = route_parts[-1].rsplit(".", 1)[0]
        route_path = "/" + "/".join(route_parts)
        ep_id = _make_endpoint_id(stem, "ANY", route_path)
        nodes.append({
            "id": ep_id,
            "label": f"ANY {route_path}",
            "file_type": "endpoint",
            "method": "ANY",
            "path": route_path,
            "framework": "nextjs",
            "source_file": str_path,
            "source_location": "L1",
        })
    elif stem == "route" and "app" in parts:
        app_idx = parts.index("app")
        route_parts = list(parts[app_idx + 1:-1])
        route_path = "/" + "/".join(route_parts) if route_parts else "/"
        route_methods = _extract_nextjs_route_methods(root, source)
        if route_methods:
            for method, line in route_methods:
                ep_id = _make_endpoint_id(stem, method, route_path)
                nodes.append({
                    "id": ep_id,
                    "label": f"{method} {route_path}",
                    "file_type": "endpoint",
                    "method": method,
                    "path": route_path,
                    "framework": "nextjs",
                    "source_file": str_path,
                    "source_location": f"L{line}",
                })
                edges.append({
                    "source": _make_code_id(stem, method),
                    "target": ep_id,
                    "relation": "exposes_endpoint",
                    "confidence": "EXTRACTED",
                    "source_file": str_path,
                    "source_location": f"L{line}",
                    "weight": 1.0,
                })
        else:
            ep_id = _make_endpoint_id(stem, "ANY", route_path)
            nodes.append({
                "id": ep_id,
                "label": f"ANY {route_path}",
                "file_type": "endpoint",
                "method": "ANY",
                "path": route_path,
                "framework": "nextjs",
                "source_file": str_path,
                "source_location": "L1",
            })

    return nodes, edges


# ── Java: Spring ─────────────────────────────────────────────────────────────

_SPRING_METHOD_ANNOTATIONS = {
    "GetMapping": "GET",
    "PostMapping": "POST",
    "PutMapping": "PUT",
    "DeleteMapping": "DELETE",
    "PatchMapping": "PATCH",
    "RequestMapping": None,  # method from attribute
}


def _java_annotation_path(ann_node, source: bytes) -> str:
    """Get the path string from a Java annotation's argument list."""
    for child in ann_node.children:
        if child.type == "annotation_argument_list":
            for arg in child.children:
                if arg.type == "string_literal":
                    return _strip_quotes(_read_text(arg, source))
                if arg.type == "element_value_pair":
                    key = arg.child_by_field_name("key")
                    val = arg.child_by_field_name("value")
                    if key and _read_text(key, source) in ("value", "path"):
                        if val and val.type == "string_literal":
                            return _strip_quotes(_read_text(val, source))
    return ""


def _java_annotation_method(ann_node, source: bytes) -> str | None:
    """Get the HTTP method from @RequestMapping(method=RequestMethod.GET)."""
    for child in ann_node.children:
        if child.type == "annotation_argument_list":
            for arg in child.children:
                if arg.type == "element_value_pair":
                    key = arg.child_by_field_name("key")
                    if key and _read_text(key, source) == "method":
                        val = arg.child_by_field_name("value")
                        if val:
                            text = _read_text(val, source)
                            for m in _HTTP_METHODS:
                                if m in text.upper():
                                    return m
    return None


def _extract_java_endpoints(root, source: bytes, path: Path) -> tuple[list[dict], list[dict]]:
    """Extract Spring @RequestMapping/@GetMapping endpoints."""
    stem = path.stem
    str_path = str(path)
    nodes: list[dict] = []
    edges: list[dict] = []

    def walk_class(node, class_prefix: str = ""):
        if node.type == "class_declaration":
            # Check for class-level @RequestMapping
            prefix = class_prefix
            class_name = ""
            name_node = node.child_by_field_name("name")
            if name_node is not None:
                class_name = _read_text(name_node, source)
            modifiers = node.child_by_field_name("modifiers") if hasattr(node, 'child_by_field_name') else None
            if not modifiers:
                for child in node.children:
                    if child.type == "modifiers":
                        modifiers = child
                        break
            if modifiers:
                for child in modifiers.children:
                    if child.type in ("annotation", "marker_annotation"):
                        ann_name = None
                        for sub in child.children:
                            if sub.type == "identifier":
                                ann_name = _read_text(sub, source)
                                break
                        if ann_name == "RequestMapping":
                            prefix = _java_annotation_path(child, source)

            # Walk methods inside the class
            body = node.child_by_field_name("body")
            if body:
                for child in body.children:
                    if child.type == "method_declaration":
                        _process_java_method(child, prefix, class_name, stem, str_path, source, nodes, edges)
                    else:
                        walk_class(child, prefix)
        else:
            for child in node.children:
                walk_class(child, class_prefix)

    walk_class(root)
    return nodes, edges


def _process_java_method(method_node, class_prefix: str, class_name: str, stem: str,
                         str_path: str, source: bytes,
                         nodes: list[dict], edges: list[dict]) -> None:
    modifiers = None
    for child in method_node.children:
        if child.type == "modifiers":
            modifiers = child
            break

    if not modifiers:
        return

    func_name_node = method_node.child_by_field_name("name")
    func_name = _read_text(func_name_node, source) if func_name_node else "unknown"

    for child in modifiers.children:
        if child.type not in ("annotation", "marker_annotation"):
            continue
        ann_name = None
        for sub in child.children:
            if sub.type == "identifier":
                ann_name = _read_text(sub, source)
                break
        if not ann_name or ann_name not in _SPRING_METHOD_ANNOTATIONS:
            continue

        route_path = _java_annotation_path(child, source) if child.type == "annotation" else ""
        full_path = _normalize_path(class_prefix, route_path)

        fixed_method = _SPRING_METHOD_ANNOTATIONS[ann_name]
        if fixed_method:
            method = fixed_method
        elif child.type == "annotation":
            method = _java_annotation_method(child, source) or "ANY"
        else:
            method = "ANY"

        line = child.start_point[0] + 1
        ep_id = _make_endpoint_id(stem, method, full_path)
        nodes.append({
            "id": ep_id,
            "label": f"{method} {full_path}",
            "file_type": "endpoint",
            "method": method,
            "path": full_path,
            "framework": "spring",
            "source_file": str_path,
            "source_location": f"L{line}",
        } | _endpoint_metadata(controller=class_name or None, action=func_name))
        func_nid = f"{stem}_{func_name}"
        edges.append({
            "source": func_nid,
            "target": ep_id,
            "relation": "exposes_endpoint",
            "confidence": "EXTRACTED",
            "source_file": str_path,
            "source_location": f"L{line}",
            "weight": 1.0,
        })


# (Module-level _java_annotation_path / _java_annotation_method defined above)


# ── PHP: Laravel ─────────────────────────────────────────────────────────────

_LARAVEL_METHODS = {"get", "post", "put", "delete", "patch", "options", "any", "match", "resource", "apiResource"}


def _extract_string_array_values(node, source: bytes) -> list[str]:
    if node.type in (
        "string",
        "string_literal",
        "interpreted_string_literal",
        "raw_string_literal",
        "verbatim_string_literal",
    ):
        literal = _first_string_literal(node, source)
        return [literal.lstrip(":")] if literal is not None else []

    values: list[str] = []
    for child in node.children:
        values.extend(_extract_string_array_values(child, source))
    return values


def _laravel_controller_name(node, source: bytes) -> str | None:
    text = _read_text(node, source).strip()
    if not text:
        return None
    if text.endswith("::class"):
        text = text[:-7]
    text = text.lstrip("\\")
    return text or None


def _laravel_controller_candidates(controller_name: str | None) -> list[str]:
    if controller_name is None:
        return []
    full_name = controller_name.strip().rstrip("\\")
    short_name = re.split(r"\\+", full_name)[-1]
    return _unique_nonempty([short_name, full_name])


def _laravel_handler_source_id(args_node, source: bytes, stem: str) -> str | None:
    positional_args = [child for child in _iter_argument_values(args_node) if child.type != "keyword_argument"]
    if len(positional_args) < 2:
        return None

    handler_spec = _first_string_literal(positional_args[1], source)
    if handler_spec and "@" in handler_spec:
        controller_name, action = handler_spec.split("@", 1)
        controller_candidates = _laravel_controller_candidates(controller_name)
        if controller_candidates and action:
            return _make_code_id(stem, controller_candidates[0], action)
    return None


def _laravel_handler_ref(args_node, source: bytes) -> tuple[list[str], str | None]:
    positional_args = [child for child in _iter_argument_values(args_node) if child.type != "keyword_argument"]
    if len(positional_args) < 2:
        return [], None

    handler_spec = _first_string_literal(positional_args[1], source)
    if handler_spec and "@" in handler_spec:
        controller_name, action = handler_spec.split("@", 1)
        return _laravel_controller_candidates(controller_name), action

    return [], None


def _laravel_resource_controller_name(args_node, source: bytes) -> str | None:
    positional_index = 0
    for child in _iter_argument_values(args_node):
        if child.type == "keyword_argument":
            continue
        if positional_index == 1:
            return _laravel_controller_name(child, source)
        positional_index += 1
    return None


def _laravel_resource_controller_candidates(args_node, source: bytes) -> list[str]:
    return _laravel_controller_candidates(_laravel_resource_controller_name(args_node, source))


def _laravel_resource_collection_path(resource_path: str, prefix: str = "") -> str:
    segments = [segment for segment in resource_path.strip("/").split(".") if segment]
    if not segments:
        return _normalize_path(prefix)
    parts: list[str] = []
    for index, segment in enumerate(segments):
        parts.append(segment)
        if index < len(segments) - 1:
            parts.append(f"{{{_singularize_name(segment)}}}")
    return _normalize_path(prefix, *parts)


def _laravel_resource_member_base_path(resource_path: str, prefix: str = "", *, shallow: bool = False) -> str:
    if not shallow:
        return _laravel_resource_collection_path(resource_path, prefix)
    segments = [segment for segment in resource_path.strip("/").split(".") if segment]
    if not segments:
        return _normalize_path(prefix)
    return _normalize_path(prefix, segments[-1])


def _laravel_resource_routes(collection_path: str, api_only: bool,
                             only_actions: set[str] | None = None,
                             except_actions: set[str] | None = None,
                             member_base_path: str | None = None) -> list[tuple[str, str, str]]:
    member_root = member_base_path or collection_path
    resource_name = _singularize_name(_last_path_segment(member_root) or "resource")
    member_path = _normalize_path(member_root, f"{{{resource_name}}}")
    routes = [
        ("index", "GET", collection_path),
        ("store", "POST", collection_path),
        ("show", "GET", member_path),
        ("update", "PUT", member_path),
        ("update", "PATCH", member_path),
        ("destroy", "DELETE", member_path),
    ]
    if not api_only:
        routes.insert(1, ("create", "GET", _normalize_path(collection_path, "create")))
        routes.insert(4, ("edit", "GET", _normalize_path(member_path, "edit")))

    if only_actions is not None:
        routes = [route for route in routes if route[0] in only_actions]
    if except_actions is not None:
        routes = [route for route in routes if route[0] not in except_actions]

    return routes


def _resolve_laravel_resource_registration(node, source: bytes):
    current = node
    shallow = False
    only_actions: set[str] | None = None
    except_actions: set[str] | None = None

    while current and current.type == "member_call_expression":
        name = current.child_by_field_name("name")
        args = current.child_by_field_name("arguments") or _find_child(current, "arguments")
        if not name:
            return None
        chain_name = _read_text(name, source)
        if chain_name == "shallow":
            shallow = True
        elif chain_name == "only":
            only_actions = set(_extract_string_array_values(args, source)) if args else set()
        elif chain_name == "except":
            except_actions = set(_extract_string_array_values(args, source)) if args else set()
        else:
            return None
        current = current.child_by_field_name("object")

    if not current or current.type != "scoped_call_expression":
        return None

    scope = current.child_by_field_name("scope")
    base_name = current.child_by_field_name("name")
    base_args = current.child_by_field_name("arguments") or _find_child(current, "arguments")
    if not scope or not base_name or not base_args:
        return None
    if _read_text(scope, source) != "Route":
        return None

    resource_method = _read_text(base_name, source)
    if resource_method not in ("resource", "apiResource"):
        return None

    route_path = _first_string_arg(base_args, source)
    if route_path is None:
        return None

    controller_name = _laravel_resource_controller_name(base_args, source)

    return resource_method, route_path, controller_name, shallow, only_actions, except_actions


def _extract_php_endpoints(root, source: bytes, path: Path) -> tuple[list[dict], list[dict], list[dict]]:
    """Extract Laravel Route::get(), Route::group(), Route::resource() endpoints."""
    stem = path.stem
    str_path = str(path)
    nodes: list[dict] = []
    edges: list[dict] = []
    raw_endpoint_refs: list[dict] = []

    def walk(node, prefix: str = ""):
        if node.type in ("expression_statement", "return_statement"):
            for child in node.children:
                walk(child, prefix)
            return

        if node.type == "member_call_expression":
            resource_registration = _resolve_laravel_resource_registration(node, source)
            if resource_registration is not None:
                resource_method, route_path, controller_name, shallow, only_actions, except_actions = resource_registration
                collection_path = _laravel_resource_collection_path(route_path, prefix)
                member_base_path = _laravel_resource_member_base_path(route_path, prefix, shallow=shallow)
                controller_candidates = _laravel_controller_candidates(controller_name)
                controller_label = _preferred_controller_name(controller_candidates)
                routes = _laravel_resource_routes(
                    collection_path,
                    api_only=resource_method == "apiResource",
                    only_actions=only_actions,
                    except_actions=except_actions,
                    member_base_path=member_base_path,
                )
                line = node.start_point[0] + 1
                for action, method, expanded_path in routes:
                    ep_id = _make_endpoint_id(stem, method, expanded_path)
                    nodes.append({
                        "id": ep_id,
                        "label": f"{method} {expanded_path}",
                        "file_type": "endpoint",
                        "method": method,
                        "path": expanded_path,
                        "framework": "laravel",
                        "source_file": str_path,
                        "source_location": f"L{line}",
                    } | _endpoint_metadata(controller=controller_label, action=action))
                    if controller_candidates:
                        edges.append({
                            "source": _make_code_id(stem, controller_candidates[0], action),
                            "target": ep_id,
                            "relation": "exposes_endpoint",
                            "confidence": "EXTRACTED",
                            "source_file": str_path,
                            "source_location": f"L{line}",
                            "weight": 1.0,
                        })
                        _append_raw_endpoint_ref(
                            raw_endpoint_refs,
                            ep_id,
                            controller_candidates,
                            action,
                            str_path,
                            line,
                            controller=controller_label,
                        )
                return

            obj = node.child_by_field_name("object")
            name = node.child_by_field_name("name")
            args = node.child_by_field_name("arguments") or _find_child(node, "arguments")

            if obj and name and _read_text(name, source) == "group" and obj.type == "scoped_call_expression":
                scope = obj.child_by_field_name("scope")
                method = obj.child_by_field_name("name")
                if scope and method and _read_text(scope, source) == "Route" and _read_text(method, source) == "prefix":
                    prefix_args = obj.child_by_field_name("arguments") or _find_child(obj, "arguments")
                    chain_args = args
                    new_prefix = _first_string_arg(prefix_args, source) if prefix_args else ""
                    full_prefix = _normalize_path(prefix, new_prefix or "")
                    if chain_args:
                        for arg in _iter_argument_values(chain_args):
                            if arg.type in ("anonymous_function", "anonymous_function_creation_expression", "arrow_function"):
                                body = arg.child_by_field_name("body") or _find_child(arg, "compound_statement")
                                if body:
                                    for child in body.children:
                                        walk(child, full_prefix)
                    return

        # Route::get('/path', ...)
        if node.type in ("scoped_call_expression", "member_call_expression"):
            scope = node.child_by_field_name("scope") or node.child_by_field_name("object")
            name = node.child_by_field_name("name")
            if scope and name:
                scope_text = _read_text(scope, source)
                method_name = _read_text(name, source)
                if scope_text == "Route" and method_name in _LARAVEL_METHODS:
                    args = node.child_by_field_name("arguments") or _find_child(node, "arguments")
                    if args:
                        route_path = _first_string_arg(args, source)
                        if route_path is not None:
                            full_path = _normalize_path(prefix, route_path)
                            if method_name in ("resource", "apiResource"):
                                collection_path = _laravel_resource_collection_path(route_path, prefix)
                                member_base_path = _laravel_resource_member_base_path(route_path, prefix)
                                controller_candidates = _laravel_resource_controller_candidates(args, source)
                                controller_label = _preferred_controller_name(controller_candidates)
                                for action, method, expanded_path in _laravel_resource_routes(
                                    collection_path,
                                    api_only=method_name == "apiResource",
                                    member_base_path=member_base_path,
                                ):
                                    line = node.start_point[0] + 1
                                    ep_id = _make_endpoint_id(stem, method, expanded_path)
                                    nodes.append({
                                        "id": ep_id,
                                        "label": f"{method} {expanded_path}",
                                        "file_type": "endpoint",
                                        "method": method,
                                        "path": expanded_path,
                                        "framework": "laravel",
                                        "source_file": str_path,
                                        "source_location": f"L{line}",
                                    } | _endpoint_metadata(controller=controller_label, action=action))
                                    if controller_candidates:
                                        edges.append({
                                            "source": _make_code_id(stem, controller_candidates[0], action),
                                            "target": ep_id,
                                            "relation": "exposes_endpoint",
                                            "confidence": "EXTRACTED",
                                            "source_file": str_path,
                                            "source_location": f"L{line}",
                                            "weight": 1.0,
                                        })
                                        _append_raw_endpoint_ref(
                                            raw_endpoint_refs,
                                            ep_id,
                                            controller_candidates,
                                            action,
                                            str_path,
                                            line,
                                            controller=controller_label,
                                        )
                            else:
                                method = method_name.upper() if method_name != "any" else "ANY"
                                line = node.start_point[0] + 1
                                ep_id = _make_endpoint_id(stem, method, full_path)
                                controller_candidates, action = _laravel_handler_ref(args, source)
                                controller_label = _preferred_controller_name(controller_candidates)
                                nodes.append({
                                    "id": ep_id,
                                    "label": f"{method} {full_path}",
                                    "file_type": "endpoint",
                                    "method": method,
                                    "path": full_path,
                                    "framework": "laravel",
                                    "source_file": str_path,
                                    "source_location": f"L{line}",
                                } | _endpoint_metadata(controller=controller_label, action=action))
                                handler_source = _laravel_handler_source_id(args, source, stem)
                                if handler_source:
                                    edges.append({
                                        "source": handler_source,
                                        "target": ep_id,
                                        "relation": "exposes_endpoint",
                                        "confidence": "EXTRACTED",
                                        "source_file": str_path,
                                        "source_location": f"L{line}",
                                        "weight": 1.0,
                                    })
                                if controller_candidates and action:
                                    _append_raw_endpoint_ref(
                                        raw_endpoint_refs,
                                        ep_id,
                                        controller_candidates,
                                        action,
                                        str_path,
                                        line,
                                        controller=controller_label,
                                    )

                # Route::group(['prefix' => '/api'], function() { ... })
                if scope_text == "Route" and method_name == "group":
                    args = node.child_by_field_name("arguments") or _find_child(node, "arguments")
                    if args:
                        group_prefix = _extract_laravel_group_prefix(args, source) or ""
                        new_prefix = _normalize_path(prefix, group_prefix)
                        # Walk the closure body
                        for arg in _iter_argument_values(args):
                            if arg.type in ("anonymous_function", "anonymous_function_creation_expression", "arrow_function"):
                                body = arg.child_by_field_name("body") or _find_child(arg, "compound_statement")
                                if body:
                                    for child in body.children:
                                        walk(child, new_prefix)
                    return

                # Route::prefix('/api')->group(...)
                if scope_text == "Route" and method_name == "prefix":
                    args = node.child_by_field_name("arguments") or _find_child(node, "arguments")
                    if args:
                        new_prefix = _first_string_arg(args, source) or ""
                        # This returns a PendingResourceRegistration — look for chained ->group()
                        parent = node.parent
                        if parent and parent.type == "member_call_expression":
                            chain_name = parent.child_by_field_name("name")
                            if chain_name and _read_text(chain_name, source) == "group":
                                chain_args = parent.child_by_field_name("arguments") or _find_child(parent, "arguments")
                                full_prefix = _normalize_path(prefix, new_prefix)
                                if chain_args:
                                    for arg in _iter_argument_values(chain_args):
                                        if arg.type in ("anonymous_function", "anonymous_function_creation_expression", "arrow_function"):
                                            body = arg.child_by_field_name("body") or _find_child(arg, "compound_statement")
                                            if body:
                                                for child in body.children:
                                                    walk(child, full_prefix)
                    return

        for child in node.children:
            walk(child, prefix)

    walk(root)
    return nodes, edges, raw_endpoint_refs


def _extract_laravel_group_prefix(args_node, source: bytes) -> str | None:
    """Extract prefix from Route::group(['prefix' => '/api'], ...)."""
    for child in _iter_argument_values(args_node):
        array_node = child if child.type == "array_creation_expression" else _find_child(child, "array_creation_expression")
        if array_node:
            for item in array_node.children:
                if item.type == "array_element_initializer":
                    parts = [c for c in item.children if c.type not in (",", "[", "]", "=>")]
                    if len(parts) >= 2:
                        key = _strip_quotes(_read_text(parts[0], source))
                        if key == "prefix":
                            return _strip_quotes(_read_text(parts[1], source))
    return None


# ── Ruby: Rails ──────────────────────────────────────────────────────────────

_RAILS_ROUTE_METHODS = {"get", "post", "put", "patch", "delete", "match"}
_RAILS_RESOURCE_METHODS = {"resources", "resource"}


def _ruby_array_symbols(array_node, source: bytes) -> list[str]:
    values: list[str] = []
    for child in array_node.children:
        if child.type == "simple_symbol":
            values.append(_read_text(child, source).lstrip(":"))
        elif child.type in ("string", "string_content"):
            values.append(_strip_quotes(_read_text(child, source)))
    return values


def _ruby_resource_options(call_node, source: bytes) -> tuple[set[str] | None, set[str] | None, bool]:
    only_actions: set[str] | None = None
    except_actions: set[str] | None = None
    shallow = False

    for child in call_node.children:
        if child.type != "argument_list":
            continue
        for sub in child.children:
            if sub.type != "pair":
                continue
            key_node = _find_child(sub, "hash_key_symbol")
            if not key_node:
                continue
            key = _read_text(key_node, source)
            if key == "shallow":
                shallow = _find_child(sub, "true") is not None
                continue
            array_node = _find_child(sub, "array")
            if not array_node:
                continue
            values = set(_ruby_array_symbols(array_node, source))
            if key == "only":
                only_actions = values
            elif key == "except":
                except_actions = values

    return only_actions, except_actions, shallow


def _ruby_route_target(call_node, source: bytes) -> str | None:
    for child in call_node.children:
        if child.type != "argument_list":
            continue
        for sub in child.children:
            if sub.type != "pair":
                continue
            key_node = _find_child(sub, "hash_key_symbol")
            if key_node and _read_text(key_node, source) == "to":
                return _first_string_literal(sub, source)
    return None


def _ruby_controller_class_candidates(controller_spec: str, controller_scopes: tuple[str, ...] = ()) -> list[str]:
    explicit_scope = "::" in controller_spec or "/" in controller_spec
    raw_segments = [segment for segment in controller_spec.replace("::", "/").split("/") if segment]
    if not raw_segments:
        return []

    class_segments = [_camelize_name(segment) for segment in raw_segments]
    if not class_segments[-1].endswith("Controller"):
        class_segments[-1] = f"{class_segments[-1]}Controller"

    if explicit_scope:
        full_segments = tuple(class_segments)
    else:
        full_segments = controller_scopes + tuple(class_segments)

    full_name = "::".join(full_segments)
    short_name = class_segments[-1]
    return _unique_nonempty([full_name, short_name])


def _rails_resource_controller_candidates(resource_name: str, singular: bool,
                                         controller_scopes: tuple[str, ...] = ()) -> list[str]:
    controller_resource = _pluralize_name(resource_name) if singular else resource_name
    return _ruby_controller_class_candidates(controller_resource, controller_scopes)


def _rails_resource_routes(collection_path: str, singular: bool,
                           only_actions: set[str] | None = None,
                           except_actions: set[str] | None = None,
                           member_base_path: str | None = None) -> list[tuple[str, str, str]]:
    member_base = member_base_path or collection_path
    if singular:
        routes = [
            ("new", "GET", _normalize_path(collection_path, "new")),
            ("create", "POST", collection_path),
            ("show", "GET", member_base),
            ("edit", "GET", _normalize_path(member_base, "edit")),
            ("update", "PATCH", member_base),
            ("update", "PUT", member_base),
            ("destroy", "DELETE", member_base),
        ]
    else:
        member_path = _normalize_path(member_base, ":id")
        routes = [
            ("index", "GET", collection_path),
            ("new", "GET", _normalize_path(collection_path, "new")),
            ("create", "POST", collection_path),
            ("show", "GET", member_path),
            ("edit", "GET", _normalize_path(member_path, "edit")),
            ("update", "PATCH", member_path),
            ("update", "PUT", member_path),
            ("destroy", "DELETE", member_path),
        ]

    if only_actions is not None:
        routes = [route for route in routes if route[0] in only_actions]
    if except_actions is not None:
        routes = [route for route in routes if route[0] not in except_actions]

    return routes


def _rails_nested_prefix(base_path: str, resource_name: str, singular: bool) -> str:
    if singular:
        return base_path
    return _normalize_path(base_path, f":{_singularize_name(resource_name)}_id")


def _extract_ruby_endpoints(root, source: bytes, path: Path) -> tuple[list[dict], list[dict], list[dict]]:
    """Extract Rails routes from routes.rb-style files."""
    stem = path.stem
    str_path = str(path)
    nodes: list[dict] = []
    edges: list[dict] = []
    raw_endpoint_refs: list[dict] = []

    def walk(node, prefix: str = "", shallow_prefix: str = "",
             controller_scopes: tuple[str, ...] = ()):
        if node.type == "call" or node.type == "method_call":
            method_node = node.child_by_field_name("method")
            if not method_node:
                # Try first identifier child
                for child in node.children:
                    if child.type == "identifier":
                        method_node = child
                        break
            if method_node:
                method_name = _read_text(method_node, source)

                # namespace :admin do ... end
                if method_name == "namespace":
                    args = node.child_by_field_name("arguments")
                    ns_name = ""
                    if args:
                        for child in args.children:
                            if child.type in ("simple_symbol", "string", "string_content"):
                                ns_name = _read_text(child, source).lstrip(":")
                                break
                    elif node.children:
                        for child in node.children:
                            if child.type in ("simple_symbol", "argument_list"):
                                if child.type == "argument_list":
                                    for sub in child.children:
                                        if sub.type in ("simple_symbol", "string"):
                                            ns_name = _read_text(sub, source).lstrip(":")
                                            break
                                else:
                                    ns_name = _read_text(child, source).lstrip(":")
                                break
                    new_prefix = _normalize_path(prefix, ns_name)
                    new_controller_scopes = controller_scopes + ((_camelize_name(ns_name),) if ns_name else ())
                    # Walk the block
                    for child in node.children:
                        if child.type in ("do_block", "block"):
                            for sub in child.children:
                                walk(sub, new_prefix, new_prefix, new_controller_scopes)
                    return

                # resources :users
                if method_name in _RAILS_RESOURCE_METHODS:
                    resource_name = ""
                    for child in node.children:
                        if child.type in ("simple_symbol", "argument_list"):
                            if child.type == "argument_list":
                                for sub in child.children:
                                    if sub.type == "simple_symbol":
                                        resource_name = _read_text(sub, source).lstrip(":")
                                        break
                            else:
                                resource_name = _read_text(child, source).lstrip(":")
                            break
                    if resource_name:
                        full_path = _normalize_path(prefix, resource_name)
                        only_actions, except_actions, shallow = _ruby_resource_options(node, source)
                        member_base_path = _normalize_path(shallow_prefix, resource_name) if shallow else full_path
                        controller_candidates = _rails_resource_controller_candidates(
                            resource_name,
                            method_name == "resource",
                            controller_scopes,
                        )
                        controller_label = _preferred_controller_name(controller_candidates)
                        line = node.start_point[0] + 1
                        for action, method, expanded_path in _rails_resource_routes(
                            full_path,
                            singular=method_name == "resource",
                            only_actions=only_actions,
                            except_actions=except_actions,
                            member_base_path=member_base_path,
                        ):
                            ep_id = _make_endpoint_id(stem, method, expanded_path)
                            nodes.append({
                                "id": ep_id,
                                "label": f"{method} {expanded_path}",
                                "file_type": "endpoint",
                                "method": method,
                                "path": expanded_path,
                                "framework": "rails",
                                "source_file": str_path,
                                "source_location": f"L{line}",
                            } | _endpoint_metadata(controller=controller_label, action=action))
                            if controller_candidates:
                                edges.append({
                                    "source": _make_code_id(stem, controller_candidates[0], action),
                                    "target": ep_id,
                                    "relation": "exposes_endpoint",
                                    "confidence": "EXTRACTED",
                                    "source_file": str_path,
                                    "source_location": f"L{line}",
                                    "weight": 1.0,
                                })
                                _append_raw_endpoint_ref(
                                    raw_endpoint_refs,
                                    ep_id,
                                    controller_candidates,
                                    action,
                                    str_path,
                                    line,
                                    controller=controller_label,
                                )
                    # Also walk nested routes in block
                    nested_prefix = _rails_nested_prefix(member_base_path, resource_name, method_name == "resource")
                    for child in node.children:
                        if child.type in ("do_block", "block"):
                            for sub in child.children:
                                walk(sub, nested_prefix if resource_name else prefix, shallow_prefix, controller_scopes)
                    return

                # get '/users', to: 'users#index'
                if method_name in _RAILS_ROUTE_METHODS:
                    route_path = ""
                    for child in node.children:
                        if child.type in ("argument_list",):
                            for sub in child.children:
                                if sub.type == "string":
                                    route_path = _strip_quotes(_read_text(sub, source))
                                    break
                            break
                        elif child.type == "string":
                            route_path = _strip_quotes(_read_text(child, source))
                            break
                    if route_path:
                        full_path = _normalize_path(prefix, route_path)
                        method = method_name.upper() if method_name != "match" else "ANY"
                        line = node.start_point[0] + 1
                        ep_id = _make_endpoint_id(stem, method, full_path)
                        nodes.append({
                            "id": ep_id,
                            "label": f"{method} {full_path}",
                            "file_type": "endpoint",
                            "method": method,
                            "path": full_path,
                            "framework": "rails",
                            "source_file": str_path,
                            "source_location": f"L{line}",
                        })
                        target_spec = _ruby_route_target(node, source)
                        controller_candidates: list[str] = []
                        action = None
                        if target_spec and "#" in target_spec:
                            controller_spec, action = target_spec.split("#", 1)
                            controller_candidates = _ruby_controller_class_candidates(controller_spec, controller_scopes)
                        controller_label = _preferred_controller_name(controller_candidates)
                        if controller_candidates and action:
                            handler_source = _make_code_id(stem, controller_candidates[0], action)
                            edges.append({
                                "source": handler_source,
                                "target": ep_id,
                                "relation": "exposes_endpoint",
                                "confidence": "EXTRACTED",
                                "source_file": str_path,
                                "source_location": f"L{line}",
                                "weight": 1.0,
                            })
                            _append_raw_endpoint_ref(
                                raw_endpoint_refs,
                                ep_id,
                                controller_candidates,
                                action,
                                str_path,
                                line,
                                controller=controller_label,
                            )
                        nodes[-1] = nodes[-1] | _endpoint_metadata(controller=controller_label, action=action)

        for child in node.children:
            walk(child, prefix, shallow_prefix, controller_scopes)

    walk(root)
    return nodes, edges, raw_endpoint_refs


# ── Go: Gin / Echo / Chi ────────────────────────────────────────────────────

_GO_ROUTE_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS",
                     "Get", "Post", "Put", "Delete", "Patch", "Head", "Options",
                     "Handle", "Any"}

_GO_FRAMEWORK_IMPORTS: dict[str, str] = {
    "github.com/gin-gonic/gin": "gin",
    "github.com/labstack/echo": "echo",
    "github.com/go-chi/chi": "chi",
    "github.com/gorilla/mux": "gorilla",
    "github.com/julienschmidt/httprouter": "httprouter",
    "github.com/gofiber/fiber": "fiber",
}


def _detect_go_framework(root, source: bytes) -> str:
    """Detect Go HTTP framework from import declarations. Falls back to 'go-http'."""
    for child in root.children:
        if child.type != "import_declaration":
            continue
        for spec in child.children:
            if spec.type == "import_spec_list":
                for sub in spec.children:
                    if sub.type == "import_spec":
                        path_node = _find_child(sub, "interpreted_string_literal")
                        if path_node:
                            import_path = _strip_quotes(_read_text(path_node, source))
                            for prefix, framework in _GO_FRAMEWORK_IMPORTS.items():
                                if import_path == prefix or import_path.startswith(prefix + "/"):
                                    return framework
            elif spec.type == "import_spec":
                path_node = _find_child(spec, "interpreted_string_literal")
                if path_node:
                    import_path = _strip_quotes(_read_text(path_node, source))
                    for prefix, framework in _GO_FRAMEWORK_IMPORTS.items():
                        if import_path == prefix or import_path.startswith(prefix + "/"):
                            return framework
    return "go-http"


def _extract_go_endpoints(root, source: bytes, path: Path) -> tuple[list[dict], list[dict]]:
    """Extract Go HTTP route registrations (Gin, Echo, Chi)."""
    stem = path.stem
    str_path = str(path)
    nodes: list[dict] = []
    edges: list[dict] = []
    group_prefixes: dict[str, str] = {}
    framework = _detect_go_framework(root, source)

    def walk(node, prefix: str = ""):
        # r.GET("/path", handler) or e.GET("/path", handler)
        if node.type == "call_expression":
            func = node.child_by_field_name("function")
            if func and func.type == "selector_expression":
                field = func.child_by_field_name("field")
                if field:
                    method_name = _read_text(field, source)

                    # Group/Route for prefix
                    if method_name in ("Group", "Route"):
                        args = node.child_by_field_name("arguments")
                        if args:
                            group_path = _first_string_arg(args, source)
                            if group_path:
                                new_prefix = _normalize_path(prefix, group_path)
                                # Try to find the variable this is assigned to
                                parent = node.parent
                                if parent and parent.type in ("short_var_declaration", "assignment_statement"):
                                    for child in parent.children:
                                        if child.type == "expression_list":
                                            for sub in child.children:
                                                if sub.type == "identifier":
                                                    group_prefixes[_read_text(sub, source)] = new_prefix
                                                    break

                    if method_name in _GO_ROUTE_METHODS:
                        args = node.child_by_field_name("arguments")
                        if args:
                            route_path = _first_string_arg(args, source)
                            if route_path is not None:
                                obj = func.child_by_field_name("operand")
                                obj_name = _read_text(obj, source) if obj else ""
                                obj_prefix = group_prefixes.get(obj_name, prefix)
                                full_path = _normalize_path(obj_prefix, route_path)

                                method = method_name.upper()
                                if method in ("HANDLE", "ANY"):
                                    method = "ANY"
                                elif method not in _HTTP_METHODS:
                                    method = method_name.upper()
                                    if method not in _HTTP_METHODS and method not in ("ANY",):
                                        method = method  # keep as-is

                                line = node.start_point[0] + 1
                                ep_id = _make_endpoint_id(stem, method, full_path)
                                nodes.append({
                                    "id": ep_id,
                                    "label": f"{method} {full_path}",
                                    "file_type": "endpoint",
                                    "method": method,
                                    "path": full_path,
                                    "framework": framework,
                                    "source_file": str_path,
                                    "source_location": f"L{line}",
                                })
                                # Try to get handler name
                                non_str = [c for c in args.children
                                           if c.type not in ("(", ")", ",", "interpreted_string_literal", "raw_string_literal")]
                                if non_str:
                                    handler = non_str[-1]
                                    handler_text = _read_text(handler, source).split(".")[-1]
                                    handler_nid = f"{stem}_{handler_text}"
                                    edges.append({
                                        "source": handler_nid,
                                        "target": ep_id,
                                        "relation": "exposes_endpoint",
                                        "confidence": "EXTRACTED",
                                        "source_file": str_path,
                                        "source_location": f"L{line}",
                                        "weight": 1.0,
                                    })

        for child in node.children:
            walk(child, prefix)

    walk(root)
    return nodes, edges


# ── C#: ASP.NET ──────────────────────────────────────────────────────────────

_ASPNET_METHOD_ATTRS = {
    "HttpGet": "GET",
    "HttpPost": "POST",
    "HttpPut": "PUT",
    "HttpDelete": "DELETE",
    "HttpPatch": "PATCH",
    "HttpHead": "HEAD",
    "HttpOptions": "OPTIONS",
}


def _extract_csharp_accept_verbs(attr_node, source: bytes) -> tuple[list[str], str]:
    methods: list[str] = []
    route_path = ""
    arg_list = _find_child(attr_node, "attribute_argument_list", "argument_list")
    if not arg_list:
        return methods, route_path

    for child in arg_list.children:
        if child.type != "attribute_argument":
            continue
        if len(child.children) >= 3 and child.children[1].type == "=":
            key = _read_text(child.children[0], source)
            if key == "Route":
                route_path = _first_string_literal(child, source) or ""
            continue

        method = _first_string_literal(child, source)
        if method:
            upper_method = method.upper()
            if upper_method in _HTTP_METHODS and upper_method not in methods:
                methods.append(upper_method)

    return methods, route_path


def _csharp_last_identifier(node, source: bytes) -> str | None:
    if node.type == "identifier":
        return _read_text(node, source)
    if node.type == "member_access_expression":
        name_node = node.child_by_field_name("name")
        if name_node:
            return _read_text(name_node, source)
    return None


def _csharp_minimal_handler_source_id(handler_node, source: bytes, stem: str) -> str | None:
    controller_candidates, handler_candidates, _, action = _csharp_minimal_handler_ref(handler_node, source)
    if controller_candidates and action:
        return _make_code_id(stem, controller_candidates[0], action)
    if handler_candidates:
        return _make_code_id(stem, handler_candidates[0])
    return None


def _csharp_minimal_handler_ref(handler_node, source: bytes) -> tuple[list[str], list[str], str | None, str | None]:
    if handler_node.type == "identifier":
        action = _read_text(handler_node, source)
        return [], [action], None, action
    if handler_node.type == "member_access_expression":
        object_node = handler_node.child_by_field_name("expression")
        name_node = handler_node.child_by_field_name("name")
        class_name = _csharp_last_identifier(object_node, source) if object_node else None
        method_name = _read_text(name_node, source) if name_node else None
        if class_name and method_name:
            return [class_name], [], class_name, method_name
    return [], [], None, None


def _extract_csharp_endpoints(root, source: bytes, path: Path) -> tuple[list[dict], list[dict], list[dict]]:
    """Extract ASP.NET endpoints from [HttpGet], [Route], MapGet() etc."""
    stem = path.stem
    str_path = str(path)
    nodes: list[dict] = []
    edges: list[dict] = []
    raw_endpoint_refs: list[dict] = []
    group_prefixes: dict[str, str] = {}

    def _get_class_route(class_node) -> str:
        """Get [Route("api/[controller]")] from class attributes."""
        # Look for attribute_list before the class
        for child in class_node.children:
            if child.type == "attribute_list":
                for attr in child.children:
                    if attr.type == "attribute":
                        name_node = attr.child_by_field_name("name")
                        if name_node and _read_text(name_node, source) in ("Route", "ApiController"):
                            if _read_text(name_node, source) == "Route":
                                args = attr.child_by_field_name("argument_list") or attr.child_by_field_name("attribute_argument_list") or _find_child(attr, "attribute_argument_list", "argument_list")
                                if args:
                                    return _first_string_arg(args, source) or ""
        return ""

    def walk(node, class_prefix: str = "", class_name: str = ""):
        if node.type == "class_declaration":
            prefix = _get_class_route(node) or class_prefix
            name_node = node.child_by_field_name("name") or _find_child(node, "identifier")
            current_class_name = _read_text(name_node, source) if name_node else class_name
            for child in node.children:
                walk(child, prefix, current_class_name)
            return

        if node.type == "variable_declarator":
            name_node = node.child_by_field_name("name") or _find_child(node, "identifier")
            value_node = node.child_by_field_name("value") or _find_child(node, "invocation_expression")
            if name_node and value_node and value_node.type == "invocation_expression":
                callee = value_node.child_by_field_name("function")
                if callee and callee.type == "member_access_expression":
                    method_node = callee.child_by_field_name("name")
                    object_node = callee.child_by_field_name("expression")
                    if method_node and _read_text(method_node, source) == "MapGroup":
                        args = value_node.child_by_field_name("argument_list") or _find_child(value_node, "argument_list")
                        group_path = _first_string_arg(args, source) if args else None
                        object_prefix = group_prefixes.get(_read_text(object_node, source), "") if object_node else ""
                        if group_path:
                            group_prefixes[_read_text(name_node, source)] = _normalize_path(object_prefix, group_path)

        # [HttpGet("/path")] on methods
        if node.type == "method_declaration":
            func_name_node = node.child_by_field_name("name")
            func_name = _read_text(func_name_node, source) if func_name_node else "unknown"

            for child in node.children:
                if child.type == "attribute_list":
                    for attr in child.children:
                        if attr.type == "attribute":
                            name_node = attr.child_by_field_name("name")
                            if name_node:
                                attr_name = _read_text(name_node, source)
                                if attr_name in _ASPNET_METHOD_ATTRS:
                                    method = _ASPNET_METHOD_ATTRS[attr_name]
                                    args = attr.child_by_field_name("argument_list") or attr.child_by_field_name("attribute_argument_list") or _find_child(attr, "attribute_argument_list", "argument_list")
                                    route_path = ""
                                    if args:
                                        route_path = _first_string_arg(args, source) or ""
                                    full_path = _normalize_path(class_prefix, route_path)
                                    line = attr.start_point[0] + 1
                                    ep_id = _make_endpoint_id(stem, method, full_path)
                                    nodes.append({
                                        "id": ep_id,
                                        "label": f"{method} {full_path}",
                                        "file_type": "endpoint",
                                        "method": method,
                                        "path": full_path,
                                        "framework": "aspnet",
                                        "source_file": str_path,
                                        "source_location": f"L{line}",
                                    } | _endpoint_metadata(controller=class_name or None, action=func_name))
                                    func_nid = _make_code_id(stem, class_name, func_name) if class_name else _make_code_id(stem, func_name)
                                    edges.append({
                                        "source": func_nid,
                                        "target": ep_id,
                                        "relation": "exposes_endpoint",
                                        "confidence": "EXTRACTED",
                                        "source_file": str_path,
                                        "source_location": f"L{line}",
                                        "weight": 1.0,
                                    })
                                elif attr_name == "AcceptVerbs":
                                    methods, route_path = _extract_csharp_accept_verbs(attr, source)
                                    if methods:
                                        full_path = _normalize_path(class_prefix, route_path)
                                        line = attr.start_point[0] + 1
                                        func_nid = _make_code_id(stem, class_name, func_name) if class_name else _make_code_id(stem, func_name)
                                        for method in methods:
                                            ep_id = _make_endpoint_id(stem, method, full_path)
                                            nodes.append({
                                                "id": ep_id,
                                                "label": f"{method} {full_path}",
                                                "file_type": "endpoint",
                                                "method": method,
                                                "path": full_path,
                                                "framework": "aspnet",
                                                "source_file": str_path,
                                                "source_location": f"L{line}",
                                            } | _endpoint_metadata(controller=class_name or None, action=func_name))
                                            edges.append({
                                                "source": func_nid,
                                                "target": ep_id,
                                                "relation": "exposes_endpoint",
                                                "confidence": "EXTRACTED",
                                                "source_file": str_path,
                                                "source_location": f"L{line}",
                                                "weight": 1.0,
                                            })

        # Minimal API: app.MapGet("/path", handler)
        if node.type in ("invocation_expression",):
            callee = node.child_by_field_name("function")
            if callee and callee.type == "member_access_expression":
                name_node = callee.child_by_field_name("name")
                if name_node:
                    method_name = _read_text(name_node, source)
                    object_node = callee.child_by_field_name("expression")
                    object_prefix = group_prefixes.get(_read_text(object_node, source), "") if object_node else ""
                    map_methods = {"MapGet": "GET", "MapPost": "POST", "MapPut": "PUT",
                                   "MapDelete": "DELETE", "MapPatch": "PATCH"}
                    if method_name in map_methods:
                        args = node.child_by_field_name("argument_list") or _find_child(node, "argument_list")
                        if args:
                            arg_values = [child for child in _iter_argument_values(args)]
                            route_path = _first_string_literal(arg_values[0], source) if arg_values else "/"
                            controller_candidates: list[str] = []
                            handler_candidates: list[str] = []
                            controller_label = None
                            action_name = None
                            handler_source = None
                            if len(arg_values) >= 2:
                                controller_candidates, handler_candidates, controller_label, action_name = _csharp_minimal_handler_ref(arg_values[1], source)
                                handler_source = _csharp_minimal_handler_source_id(arg_values[1], source, stem)
                            method = map_methods[method_name]
                            full_path = _normalize_path(object_prefix, route_path)
                            line = node.start_point[0] + 1
                            ep_id = _make_endpoint_id(stem, method, full_path)
                            nodes.append({
                                "id": ep_id,
                                "label": f"{method} {full_path}",
                                "file_type": "endpoint",
                                "method": method,
                                "path": full_path,
                                "framework": "aspnet-minimal",
                                "source_file": str_path,
                                "source_location": f"L{line}",
                            } | _endpoint_metadata(controller=controller_label, action=action_name))
                            if handler_source:
                                edges.append({
                                    "source": handler_source,
                                    "target": ep_id,
                                    "relation": "exposes_endpoint",
                                    "confidence": "EXTRACTED",
                                    "source_file": str_path,
                                    "source_location": f"L{line}",
                                    "weight": 1.0,
                                })
                            _append_raw_endpoint_ref(
                                raw_endpoint_refs,
                                ep_id,
                                controller_candidates,
                                action_name,
                                str_path,
                                line,
                                handler_candidates=handler_candidates,
                                controller=controller_label,
                            )
                    elif method_name == "MapMethods":
                        args = node.child_by_field_name("argument_list") or _find_child(node, "argument_list")
                        if args:
                            arg_values = [child for child in _iter_argument_values(args)]
                            if len(arg_values) >= 2:
                                route_path = _first_string_literal(arg_values[0], source) or "/"
                                full_path = _normalize_path(object_prefix, route_path)
                                methods = [
                                    candidate.upper()
                                    for candidate in _all_string_literals(arg_values[1], source)
                                    if candidate.upper() in _HTTP_METHODS
                                ]
                                controller_candidates = []
                                handler_candidates = []
                                controller_label = None
                                action_name = None
                                handler_source = None
                                if len(arg_values) >= 3:
                                    controller_candidates, handler_candidates, controller_label, action_name = _csharp_minimal_handler_ref(arg_values[2], source)
                                    handler_source = _csharp_minimal_handler_source_id(arg_values[2], source, stem)
                                line = node.start_point[0] + 1
                                for method in methods:
                                    ep_id = _make_endpoint_id(stem, method, full_path)
                                    nodes.append({
                                        "id": ep_id,
                                        "label": f"{method} {full_path}",
                                        "file_type": "endpoint",
                                        "method": method,
                                        "path": full_path,
                                        "framework": "aspnet-minimal",
                                        "source_file": str_path,
                                        "source_location": f"L{line}",
                                    } | _endpoint_metadata(controller=controller_label, action=action_name))
                                    if handler_source:
                                        edges.append({
                                            "source": handler_source,
                                            "target": ep_id,
                                            "relation": "exposes_endpoint",
                                            "confidence": "EXTRACTED",
                                            "source_file": str_path,
                                            "source_location": f"L{line}",
                                            "weight": 1.0,
                                        })
                                    _append_raw_endpoint_ref(
                                        raw_endpoint_refs,
                                        ep_id,
                                        controller_candidates,
                                        action_name,
                                        str_path,
                                        line,
                                        handler_candidates=handler_candidates,
                                        controller=controller_label,
                                    )

        for child in node.children:
            walk(child, class_prefix, class_name)

    walk(root)
    return nodes, edges, raw_endpoint_refs


# ── Public API ───────────────────────────────────────────────────────────────

# Map file extension → endpoint extractor function
# Each returns (endpoint_nodes, endpoint_edges) or
# (endpoint_nodes, endpoint_edges, raw_endpoint_refs)
_ENDPOINT_EXTRACTORS: dict[str, Any] = {
    ".py": _extract_python_endpoints,
    ".js": _extract_js_endpoints,
    ".jsx": _extract_js_endpoints,
    ".mjs": _extract_js_endpoints,
    ".ts": _extract_js_endpoints,
    ".tsx": _extract_js_endpoints,
    ".java": _extract_java_endpoints,
    ".php": _extract_php_endpoints,
    ".rb": _extract_ruby_endpoints,
    ".go": _extract_go_endpoints,
    ".cs": _extract_csharp_endpoints,
}


def extract_endpoints(root, source: bytes, path: Path) -> tuple[list[dict], list[dict], list[dict]]:
    """Extract API endpoint nodes and edges from a parsed AST.

    Args:
        root: tree-sitter root node
        source: raw file bytes
        path: file path

    Returns:
        (endpoint_nodes, endpoint_edges, unresolved endpoint handler refs)
    """
    ext = path.suffix.lower()
    if ext in (".ts", ".tsx", ".js", ".jsx") and _is_nextjs_route_file(path):
        nextjs_nodes, nextjs_edges = _extract_nextjs_endpoints(root, source, path)
        return nextjs_nodes, nextjs_edges, []

    extractor = _ENDPOINT_EXTRACTORS.get(ext)
    if not extractor:
        return [], [], []
    extracted = extractor(root, source, path)
    if len(extracted) == 3:
        ep_nodes, ep_edges, raw_endpoint_refs = extracted
    else:
        ep_nodes, ep_edges = extracted
        raw_endpoint_refs = []

    return ep_nodes, ep_edges, raw_endpoint_refs
