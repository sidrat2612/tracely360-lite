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
from typing import Any

# HTTP methods we recognize
_HTTP_METHODS = frozenset({"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"})

# ── Helpers ──────────────────────────────────────────────────────────────────

def _read_text(node, source: bytes) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _strip_quotes(s: str) -> str:
    if len(s) >= 2 and s[0] in ('"', "'") and s[-1] == s[0]:
        return s[1:-1]
    return s


def _normalize_path(*parts: str) -> str:
    joined = "/".join(p.strip("/") for p in parts if p)
    return "/" + joined if joined else "/"


def _make_endpoint_id(stem: str, method: str, path: str) -> str:
    safe = path.replace("/", "_").replace("<", "").replace(">", "").replace("{", "").replace("}", "").replace(":", "")
    return f"{stem}_endpoint_{method.lower()}_{safe}".rstrip("_")


def _first_string_arg(node, source: bytes) -> str | None:
    """Extract the first string literal from an argument list node."""
    for child in node.children:
        if child.type in ("string", "string_literal", "interpreted_string_literal"):
            text = _read_text(child, source)
            return _strip_quotes(text)
        if child.type == "string_content" or child.type == "string_fragment":
            return _read_text(child, source)
        # Python string with start/content/end children
        if child.child_count > 0:
            for sub in child.children:
                if sub.type in ("string_content", "string_fragment"):
                    return _read_text(sub, source)
    return None


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


def _extract_python_endpoints(root, source: bytes, path: Path) -> tuple[list[dict], list[dict]]:
    """Extract endpoints from Python decorated functions (Flask, FastAPI)."""
    stem = path.stem
    str_path = str(path)
    nodes: list[dict] = []
    edges: list[dict] = []

    # Also detect Django urlpatterns
    _extract_django_urls(root, source, path, nodes, edges)

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
                if callee.type == "attribute":
                    attr_node = callee.child_by_field_name("attribute")
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
                route_path = _first_string_arg(args, source) or "/"

                # Determine HTTP methods
                fixed_method = _PYTHON_ROUTE_DECORATORS[method_name]
                if fixed_method:
                    methods = [fixed_method]
                else:
                    methods = _extract_methods_kwarg(call_node, source)

                line = dec.start_point[0] + 1
                for method in methods:
                    ep_id = _make_endpoint_id(stem, method, route_path)
                    nodes.append({
                        "id": ep_id,
                        "label": f"{method} {route_path}",
                        "file_type": "endpoint",
                        "method": method,
                        "path": route_path,
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
                         nodes: list[dict], edges: list[dict]) -> None:
    """Extract Django urlpatterns: path('route/', view_func)."""
    stem = path.stem
    str_path = str(path)

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
                            line = node.start_point[0] + 1
                            ep_id = _make_endpoint_id(stem, "ANY", route_path)
                            nodes.append({
                                "id": ep_id,
                                "label": f"ANY {route_path}",
                                "file_type": "endpoint",
                                "method": "ANY",
                                "path": route_path,
                                "framework": "django",
                                "source_file": str_path,
                                "source_location": f"L{line}",
                            })
                            # Try to get the view function name (second arg)
                            non_paren = [c for c in args.children if c.type not in ("(", ")", ",")]
                            if len(non_paren) >= 2:
                                view = non_paren[1]
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

    def walk(node, class_prefix: str = ""):
        # Detect class with @Controller prefix (NestJS)
        if node.type == "class_declaration":
            prefix = _get_nestjs_class_prefix(node, source) or class_prefix
            for child in node.children:
                walk(child, class_prefix=prefix)
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
                            })
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

        _detect_router_prefix(node)
        for child in node.children:
            walk(child, class_prefix)

    walk(root)
    return nodes, edges


# ── Next.js file-based routing ───────────────────────────────────────────────

def _extract_nextjs_endpoints(path: Path) -> tuple[list[dict], list[dict]]:
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
                        _process_java_method(child, prefix, stem, str_path, source, nodes, edges)
                    else:
                        walk_class(child, prefix)
        else:
            for child in node.children:
                walk_class(child, class_prefix)

    walk_class(root)
    return nodes, edges


def _process_java_method(method_node, class_prefix: str, stem: str,
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
        })
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


def _extract_php_endpoints(root, source: bytes, path: Path) -> tuple[list[dict], list[dict]]:
    """Extract Laravel Route::get(), Route::group(), Route::resource() endpoints."""
    stem = path.stem
    str_path = str(path)
    nodes: list[dict] = []
    edges: list[dict] = []

    def walk(node, prefix: str = ""):
        if node.type in ("expression_statement", "return_statement"):
            for child in node.children:
                walk(child, prefix)
            return

        # Route::get('/path', ...)
        if node.type in ("scoped_call_expression", "member_call_expression"):
            scope = node.child_by_field_name("scope") or node.child_by_field_name("object")
            name = node.child_by_field_name("name")
            if scope and name:
                scope_text = _read_text(scope, source)
                method_name = _read_text(name, source)
                if scope_text == "Route" and method_name in _LARAVEL_METHODS:
                    args = node.child_by_field_name("arguments")
                    if args:
                        route_path = _first_string_arg(args, source)
                        if route_path is not None:
                            full_path = _normalize_path(prefix, route_path)
                            if method_name in ("resource", "apiResource"):
                                # Resource routes generate multiple endpoints
                                for m in ("GET", "POST", "PUT", "DELETE"):
                                    line = node.start_point[0] + 1
                                    ep_id = _make_endpoint_id(stem, m, full_path)
                                    nodes.append({
                                        "id": ep_id,
                                        "label": f"{m} {full_path}",
                                        "file_type": "endpoint",
                                        "method": m,
                                        "path": full_path,
                                        "framework": "laravel",
                                        "source_file": str_path,
                                        "source_location": f"L{line}",
                                    })
                            else:
                                method = method_name.upper() if method_name != "any" else "ANY"
                                line = node.start_point[0] + 1
                                ep_id = _make_endpoint_id(stem, method, full_path)
                                nodes.append({
                                    "id": ep_id,
                                    "label": f"{method} {full_path}",
                                    "file_type": "endpoint",
                                    "method": method,
                                    "path": full_path,
                                    "framework": "laravel",
                                    "source_file": str_path,
                                    "source_location": f"L{line}",
                                })

                # Route::group(['prefix' => '/api'], function() { ... })
                if scope_text == "Route" and method_name == "group":
                    args = node.child_by_field_name("arguments")
                    if args:
                        group_prefix = _extract_laravel_group_prefix(args, source) or ""
                        new_prefix = _normalize_path(prefix, group_prefix)
                        # Walk the closure body
                        for arg in args.children:
                            if arg.type in ("anonymous_function_creation_expression", "arrow_function"):
                                body = arg.child_by_field_name("body")
                                if body:
                                    for child in body.children:
                                        walk(child, new_prefix)
                    return

                # Route::prefix('/api')->group(...)
                if scope_text == "Route" and method_name == "prefix":
                    args = node.child_by_field_name("arguments")
                    if args:
                        new_prefix = _first_string_arg(args, source) or ""
                        # This returns a PendingResourceRegistration — look for chained ->group()
                        parent = node.parent
                        if parent and parent.type == "member_call_expression":
                            chain_name = parent.child_by_field_name("name")
                            if chain_name and _read_text(chain_name, source) == "group":
                                chain_args = parent.child_by_field_name("arguments")
                                full_prefix = _normalize_path(prefix, new_prefix)
                                if chain_args:
                                    for arg in chain_args.children:
                                        if arg.type in ("anonymous_function_creation_expression", "arrow_function"):
                                            body = arg.child_by_field_name("body")
                                            if body:
                                                for child in body.children:
                                                    walk(child, full_prefix)
                    return

        for child in node.children:
            walk(child, prefix)

    walk(root)
    return nodes, edges


def _extract_laravel_group_prefix(args_node, source: bytes) -> str | None:
    """Extract prefix from Route::group(['prefix' => '/api'], ...)."""
    for child in args_node.children:
        if child.type == "array_creation_expression":
            for item in child.children:
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


def _extract_ruby_endpoints(root, source: bytes, path: Path) -> tuple[list[dict], list[dict]]:
    """Extract Rails routes from routes.rb-style files."""
    stem = path.stem
    str_path = str(path)
    nodes: list[dict] = []
    edges: list[dict] = []

    def walk(node, prefix: str = ""):
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
                    # Walk the block
                    for child in node.children:
                        if child.type in ("do_block", "block"):
                            for sub in child.children:
                                walk(sub, new_prefix)
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
                        line = node.start_point[0] + 1
                        for m in ("GET", "POST", "PUT", "DELETE"):
                            ep_id = _make_endpoint_id(stem, m, full_path)
                            nodes.append({
                                "id": ep_id,
                                "label": f"{m} {full_path}",
                                "file_type": "endpoint",
                                "method": m,
                                "path": full_path,
                                "framework": "rails",
                                "source_file": str_path,
                                "source_location": f"L{line}",
                            })
                    # Also walk nested routes in block
                    for child in node.children:
                        if child.type in ("do_block", "block"):
                            for sub in child.children:
                                walk(sub, _normalize_path(prefix, resource_name) if resource_name else prefix)
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

        for child in node.children:
            walk(child, prefix)

    walk(root)
    return nodes, edges


# ── Go: Gin / Echo / Chi ────────────────────────────────────────────────────

_GO_ROUTE_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS",
                     "Get", "Post", "Put", "Delete", "Patch", "Head", "Options",
                     "Handle", "Any"}


def _extract_go_endpoints(root, source: bytes, path: Path) -> tuple[list[dict], list[dict]]:
    """Extract Go HTTP route registrations (Gin, Echo, Chi)."""
    stem = path.stem
    str_path = str(path)
    nodes: list[dict] = []
    edges: list[dict] = []
    group_prefixes: dict[str, str] = {}

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
                                    "framework": "go-http",
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


def _extract_csharp_endpoints(root, source: bytes, path: Path) -> tuple[list[dict], list[dict]]:
    """Extract ASP.NET endpoints from [HttpGet], [Route], MapGet() etc."""
    stem = path.stem
    str_path = str(path)
    nodes: list[dict] = []
    edges: list[dict] = []

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
                                args = attr.child_by_field_name("argument_list")
                                if args:
                                    return _first_string_arg(args, source) or ""
        return ""

    def walk(node, class_prefix: str = ""):
        if node.type == "class_declaration":
            prefix = _get_class_route(node) or class_prefix
            for child in node.children:
                walk(child, prefix)
            return

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
                                    args = attr.child_by_field_name("argument_list")
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
                                    })
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

        # Minimal API: app.MapGet("/path", handler)
        if node.type in ("invocation_expression",):
            callee = node.child_by_field_name("function")
            if callee and callee.type == "member_access_expression":
                name_node = callee.child_by_field_name("name")
                if name_node:
                    method_name = _read_text(name_node, source)
                    map_methods = {"MapGet": "GET", "MapPost": "POST", "MapPut": "PUT",
                                   "MapDelete": "DELETE", "MapPatch": "PATCH"}
                    if method_name in map_methods:
                        args = node.child_by_field_name("argument_list")
                        if args:
                            route_path = _first_string_arg(args, source) or "/"
                            method = map_methods[method_name]
                            line = node.start_point[0] + 1
                            ep_id = _make_endpoint_id(stem, method, route_path)
                            nodes.append({
                                "id": ep_id,
                                "label": f"{method} {route_path}",
                                "file_type": "endpoint",
                                "method": method,
                                "path": route_path,
                                "framework": "aspnet-minimal",
                                "source_file": str_path,
                                "source_location": f"L{line}",
                            })

        for child in node.children:
            walk(child, class_prefix)

    walk(root)
    return nodes, edges


# ── Public API ───────────────────────────────────────────────────────────────

# Map file extension → endpoint extractor function
# Each returns (endpoint_nodes, endpoint_edges)
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


def extract_endpoints(root, source: bytes, path: Path) -> tuple[list[dict], list[dict]]:
    """Extract API endpoint nodes and edges from a parsed AST.

    Args:
        root: tree-sitter root node
        source: raw file bytes
        path: file path

    Returns:
        (endpoint_nodes, endpoint_edges)
    """
    ext = path.suffix.lower()
    extractor = _ENDPOINT_EXTRACTORS.get(ext)
    if not extractor:
        return [], []
    ep_nodes, ep_edges = extractor(root, source, path)

    # Also check for Next.js file-based routing
    if ext in (".ts", ".tsx", ".js", ".jsx"):
        nextjs_nodes, nextjs_edges = _extract_nextjs_endpoints(path)
        ep_nodes.extend(nextjs_nodes)
        ep_edges.extend(nextjs_edges)

    return ep_nodes, ep_edges
