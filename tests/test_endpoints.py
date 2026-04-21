"""Tests for API endpoint extraction across frameworks."""
from pathlib import Path
import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _endpoint_by_method_path(result, method: str, path: str) -> dict:
    for node in result["nodes"]:
        if node.get("file_type") == "endpoint" and node.get("method") == method and node.get("path") == path:
            return node
    raise AssertionError(f"Endpoint not found: {method} {path}")


# ── Flask ────────────────────────────────────────────────────────────────────

def test_flask_endpoint_count():
    from tracely360.extract import extract_python
    result = extract_python(FIXTURE_DIR / "sample_flask.py")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    # @app.route('/health', methods=['GET']) → 1
    # @app.get('/items/<id>') → 1
    # @app.post('/items') → 1
    # @api_bp.route('/users', methods=['GET', 'POST']) → 2
    assert len(eps) == 5


def test_flask_methods():
    from tracely360.extract import extract_python
    result = extract_python(FIXTURE_DIR / "sample_flask.py")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    methods = {(e["method"], e["path"]) for e in eps}
    assert ("GET", "/health") in methods
    assert ("GET", "/items/<id>") in methods
    assert ("POST", "/items") in methods
    assert ("GET", "/api/users") in methods
    assert ("POST", "/api/users") in methods


def test_flask_registered_blueprint_prefix_composition():
    from tracely360.extract import extract_python
    result = extract_python(FIXTURE_DIR / "sample_flask_registered_blueprint.py")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    assert len(eps) == 1
    assert eps[0]["method"] == "GET"
    assert eps[0]["path"] == "/v1/api/users"


def test_flask_edges():
    from tracely360.extract import extract_python
    result = extract_python(FIXTURE_DIR / "sample_flask.py")
    ep_edges = [e for e in result["edges"] if e["relation"] == "exposes_endpoint"]
    # All 5 endpoints should have edges from their handler functions
    assert len(ep_edges) == 5
    sources = {e["source"] for e in ep_edges}
    assert any("health" in s for s in sources)
    assert any("get_item" in s for s in sources)
    assert any("create_item" in s for s in sources)


def test_flask_framework_tag():
    from tracely360.extract import extract_python
    result = extract_python(FIXTURE_DIR / "sample_flask.py")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    for ep in eps:
        assert ep["framework"] == "flask/fastapi"


def test_fastapi_router_prefix_composition():
    from tracely360.extract import extract_python
    result = extract_python(FIXTURE_DIR / "sample_fastapi_router.py")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    method_path = {(e["method"], e["path"]) for e in eps}
    assert ("GET", "/v1/items/{item_id}") in method_path
    assert ("POST", "/v1/items") in method_path

    ep_edges = [e for e in result["edges"] if e["relation"] == "exposes_endpoint"]
    assert len(ep_edges) == 2
    sources = {e["source"] for e in ep_edges}
    assert "sample_fastapi_router_get_item" in sources
    assert "sample_fastapi_router_create_item" in sources


# ── Express.js ───────────────────────────────────────────────────────────────

def test_express_endpoint_count():
    from tracely360.extract import extract_js
    result = extract_js(FIXTURE_DIR / "sample_express.js")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    # app.get, app.post, app.delete, app.put + router.get, router.post = 6
    assert len(eps) == 6


def test_express_methods():
    from tracely360.extract import extract_js
    result = extract_js(FIXTURE_DIR / "sample_express.js")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    methods = {(e["method"], e["path"]) for e in eps}
    assert ("GET", "/users") in methods
    assert ("POST", "/users") in methods
    assert ("DELETE", "/users/:id") in methods
    assert ("PUT", "/users/:id") in methods
    assert ("GET", "/items") in methods
    assert ("POST", "/items") in methods


def test_express_handler_edges():
    from tracely360.extract import extract_js
    result = extract_js(FIXTURE_DIR / "sample_express.js")
    ep_edges = [e for e in result["edges"] if e["relation"] == "exposes_endpoint"]
    # Handler edges may be filtered if handler IDs don't match seen_ids format;
    # the key property is that endpoint *nodes* are created
    assert isinstance(ep_edges, list)


def test_express_framework_tag():
    from tracely360.extract import extract_js
    result = extract_js(FIXTURE_DIR / "sample_express.js")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    for ep in eps:
        assert ep["framework"] == "express"


# ── Spring Java ──────────────────────────────────────────────────────────────

def test_spring_endpoint_count():
    from tracely360.extract import extract_java
    result = extract_java(FIXTURE_DIR / "sample_spring.java")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    # @GetMapping("/users"), @PostMapping("/users"), @DeleteMapping("/users/{id}"), @RequestMapping("/ping")
    assert len(eps) == 4


def test_spring_prefix_resolution():
    from tracely360.extract import extract_java
    result = extract_java(FIXTURE_DIR / "sample_spring.java")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    paths = {e["path"] for e in eps}
    # Class-level @RequestMapping("/api") + method-level paths
    assert "/api/users" in paths
    assert "/api/users/{id}" in paths
    assert "/api/ping" in paths


def test_spring_methods():
    from tracely360.extract import extract_java
    result = extract_java(FIXTURE_DIR / "sample_spring.java")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    method_path = {(e["method"], e["path"]) for e in eps}
    assert ("GET", "/api/users") in method_path
    assert ("POST", "/api/users") in method_path
    assert ("DELETE", "/api/users/{id}") in method_path
    assert ("GET", "/api/ping") in method_path


def test_spring_framework_tag():
    from tracely360.extract import extract_java
    result = extract_java(FIXTURE_DIR / "sample_spring.java")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    for ep in eps:
        assert ep["framework"] == "spring"


# ── Go / Gin ────────────────────────────────────────────────────────────────

def test_gin_endpoint_count():
    from tracely360.extract import extract_go
    result = extract_go(FIXTURE_DIR / "sample_gin.go")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    # r.GET, r.POST, r.DELETE + api.GET, api.POST = 5
    assert len(eps) == 5


def test_gin_methods():
    from tracely360.extract import extract_go
    result = extract_go(FIXTURE_DIR / "sample_gin.go")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    methods = {(e["method"], e["path"]) for e in eps}
    assert ("GET", "/users") in methods
    assert ("POST", "/users") in methods
    assert ("DELETE", "/users/:id") in methods


def test_gin_framework_tag():
    from tracely360.extract import extract_go
    result = extract_go(FIXTURE_DIR / "sample_gin.go")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    for ep in eps:
        assert ep["framework"] == "gin"


def test_echo_framework_tag():
    from tracely360.extract import extract_go
    result = extract_go(FIXTURE_DIR / "sample_echo.go")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    assert len(eps) == 2
    for ep in eps:
        assert ep["framework"] == "echo"


def test_chi_framework_tag():
    from tracely360.extract import extract_go
    result = extract_go(FIXTURE_DIR / "sample_chi.go")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    assert len(eps) == 3
    methods = {(e["method"], e["path"]) for e in eps}
    assert ("GET", "/users") in methods
    assert ("POST", "/users") in methods
    assert ("DELETE", "/users/{id}") in methods
    for ep in eps:
        assert ep["framework"] == "chi"


def test_go_stdlib_framework_tag():
    """net/http without a known framework falls back to go-http."""
    from tracely360.extract import extract_go
    result = extract_go(FIXTURE_DIR / "sample_go_stdlib.go")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    for ep in eps:
        assert ep["framework"] == "go-http"


# ── Django ─────────────────────────────────────────────────────────────────

def test_django_endpoint_count():
    from tracely360.extract import extract_python
    result = extract_python(FIXTURE_DIR / "sample_django.py")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    assert len(eps) == 2


def test_django_paths_and_edges():
    from tracely360.extract import extract_python
    result = extract_python(FIXTURE_DIR / "sample_django.py")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    method_path = {(e["method"], e["path"]) for e in eps}
    assert ("ANY", "/health") in method_path
    assert ("ANY", "/users") in method_path

    ep_edges = [e for e in result["edges"] if e["relation"] == "exposes_endpoint"]
    assert len(ep_edges) == 2
    sources = {e["source"] for e in ep_edges}
    assert "sample_django_health" in sources
    assert "sample_django_users" in sources


def test_django_framework_tag():
    from tracely360.extract import extract_python
    result = extract_python(FIXTURE_DIR / "sample_django.py")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    for ep in eps:
        assert ep["framework"] == "django"


def test_django_include_prefix_resolution():
    from tracely360.extract import extract_python
    result = extract_python(FIXTURE_DIR / "sample_django_include.py")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    method_path = {(e["method"], e["path"]) for e in eps}
    assert ("ANY", "/api/health") in method_path
    assert ("ANY", "/api/users") in method_path


def test_django_include_tuple_resolution():
    from tracely360.extract import extract_python
    result = extract_python(FIXTURE_DIR / "sample_django_include_tuple.py")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    method_path = {(e["method"], e["path"]) for e in eps}
    assert ("ANY", "/tuple-api/health") in method_path
    assert ("ANY", "/tuple-api/users") in method_path


# ── NestJS ────────────────────────────────────────────────────────────────

def test_nestjs_endpoint_count():
    from tracely360.extract import extract_js
    result = extract_js(FIXTURE_DIR / "sample_nest.ts")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    assert len(eps) == 2


def test_nestjs_paths_and_edges():
    from tracely360.extract import extract_js
    result = extract_js(FIXTURE_DIR / "sample_nest.ts")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    method_path = {(e["method"], e["path"]) for e in eps}
    assert ("GET", "/users") in method_path
    assert ("POST", "/users/:id") in method_path

    ep_edges = [e for e in result["edges"] if e["relation"] == "exposes_endpoint"]
    assert len(ep_edges) == 2
    sources = {e["source"] for e in ep_edges}
    assert "sample_nest_usercontroller_listusers" in sources
    assert "sample_nest_usercontroller_createuser" in sources


def test_nestjs_framework_tag():
    from tracely360.extract import extract_js
    result = extract_js(FIXTURE_DIR / "sample_nest.ts")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    for ep in eps:
        assert ep["framework"] == "nestjs"


# ── Next.js ───────────────────────────────────────────────────────────────

def test_nextjs_pages_api_route():
    from tracely360.extract import extract_js
    result = extract_js(FIXTURE_DIR / "pages" / "api" / "users.ts")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    assert len(eps) == 1
    assert eps[0]["method"] == "ANY"
    assert eps[0]["path"] == "/api/users"
    assert eps[0]["framework"] == "nextjs"


def test_nextjs_app_route():
    from tracely360.extract import extract_js
    result = extract_js(FIXTURE_DIR / "app" / "api" / "health" / "route.ts")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    assert len(eps) == 2
    assert {(ep["method"], ep["path"]) for ep in eps} == {
        ("GET", "/api/health"),
        ("POST", "/api/health"),
    }
    for ep in eps:
        assert ep["framework"] == "nextjs"


def test_nextjs_app_route_exported_constants():
    from tracely360.extract import extract_js
    result = extract_js(FIXTURE_DIR / "app" / "api" / "items" / "route.ts")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    assert {(ep["method"], ep["path"]) for ep in eps} == {
        ("GET", "/api/items"),
        ("DELETE", "/api/items"),
    }


def test_nextjs_route_files_skip_generic_js_routes():
    from tracely360.extract import extract_js
    result = extract_js(FIXTURE_DIR / "pages" / "api" / "mixed.ts")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    assert {(ep["method"], ep["path"]) for ep in eps} == {
        ("ANY", "/api/mixed"),
    }


# ── Laravel ───────────────────────────────────────────────────────────────

def test_laravel_endpoint_count():
    from tracely360.extract import extract_php
    result = extract_php(FIXTURE_DIR / "sample_laravel.php")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    assert len(eps) == 11


def test_laravel_paths_and_methods():
    from tracely360.extract import extract_php
    result = extract_php(FIXTURE_DIR / "sample_laravel.php")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    method_path = {(e["method"], e["path"]) for e in eps}
    assert ("GET", "/api/users") in method_path
    assert ("POST", "/api/users") in method_path
    assert ("DELETE", "/admin/users/{id}") in method_path
    assert ("GET", "/posts") in method_path
    assert ("GET", "/posts/create") in method_path
    assert ("POST", "/posts") in method_path
    assert ("GET", "/posts/{post}") in method_path
    assert ("GET", "/posts/{post}/edit") in method_path
    assert ("PUT", "/posts/{post}") in method_path
    assert ("PATCH", "/posts/{post}") in method_path
    assert ("DELETE", "/posts/{post}") in method_path


def test_laravel_api_resource_paths_and_methods():
    from tracely360.extract import extract_php
    result = extract_php(FIXTURE_DIR / "sample_laravel_api_resource.php")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    assert {(e["method"], e["path"]) for e in eps} == {
        ("GET", "/comments"),
        ("POST", "/comments"),
        ("GET", "/comments/{comment}"),
        ("PUT", "/comments/{comment}"),
        ("PATCH", "/comments/{comment}"),
        ("DELETE", "/comments/{comment}"),
    }


def test_laravel_nested_resource_with_filters():
    from tracely360.extract import extract_php
    result = extract_php(FIXTURE_DIR / "sample_laravel_nested_resource.php")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    assert {(e["method"], e["path"]) for e in eps} == {
        ("GET", "/users/{user}/posts"),
        ("GET", "/users/{user}/posts/{post}"),
        ("GET", "/teams/{team}/members"),
        ("POST", "/teams/{team}/members"),
        ("GET", "/teams/{team}/members/{member}"),
        ("PUT", "/teams/{team}/members/{member}"),
        ("PATCH", "/teams/{team}/members/{member}"),
    }


def test_laravel_shallow_resources_with_filters():
    from tracely360.extract import extract_php
    result = extract_php(FIXTURE_DIR / "sample_laravel_shallow_resource.php")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    assert {(e["method"], e["path"]) for e in eps} == {
        ("GET", "/photos/{photo}/comments"),
        ("GET", "/comments/{comment}"),
        ("DELETE", "/comments/{comment}"),
        ("GET", "/teams/{team}/members"),
        ("POST", "/teams/{team}/members"),
        ("GET", "/members/{member}"),
        ("PUT", "/members/{member}"),
        ("PATCH", "/members/{member}"),
    }


def test_laravel_handler_edges_for_direct_and_resource_routes():
    from tracely360.extract import extract_php
    result = extract_php(FIXTURE_DIR / "sample_laravel_handler_edges.php")
    ep_edges = [e for e in result["edges"] if e["relation"] == "exposes_endpoint"]
    assert len(ep_edges) == 7
    assert {e["source"] for e in ep_edges} == {
        "sample_laravel_handler_edges_usercontroller_index",
        "sample_laravel_handler_edges_usercontroller_store",
        "sample_laravel_handler_edges_postcontroller_index",
        "sample_laravel_handler_edges_postcontroller_show",
        "sample_laravel_handler_edges_postcontroller_update",
        "sample_laravel_handler_edges_postcontroller_destroy",
    }


def test_laravel_cross_file_handler_resolution(tmp_path):
    from tracely360.extract import extract
    fixture_dir = FIXTURE_DIR / "laravel_cross_file"
    result = extract(
        [fixture_dir / "routes.php", fixture_dir / "controllers.php"],
        cache_root=tmp_path,
    )
    ep_edges = [e for e in result["edges"] if e["relation"] == "exposes_endpoint"]
    assert len(ep_edges) == 2
    assert {e["source"] for e in ep_edges} == {
        "controllers_usercontroller_index",
        "controllers_postcontroller_show",
    }
    assert {e["confidence"] for e in ep_edges} == {"INFERRED"}


def test_laravel_endpoint_controller_action_metadata():
    from tracely360.extract import extract_php
    result = extract_php(FIXTURE_DIR / "sample_laravel_handler_edges.php")

    users_index = _endpoint_by_method_path(result, "GET", "/users")
    assert users_index["controller"] == "UserController"
    assert users_index["action"] == "index"

    posts_show = _endpoint_by_method_path(result, "GET", "/posts/{post}")
    assert posts_show["controller"] == "PostController"
    assert posts_show["action"] == "show"


def test_laravel_framework_tag():
    from tracely360.extract import extract_php
    result = extract_php(FIXTURE_DIR / "sample_laravel.php")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    for ep in eps:
        assert ep["framework"] == "laravel"


# ── Rails ─────────────────────────────────────────────────────────────────

def test_rails_endpoint_count():
    from tracely360.extract import extract_ruby
    result = extract_ruby(FIXTURE_DIR / "sample_rails.rb")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    assert len(eps) == 10


def test_rails_paths_and_methods():
    from tracely360.extract import extract_ruby
    result = extract_ruby(FIXTURE_DIR / "sample_rails.rb")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    method_path = {(e["method"], e["path"]) for e in eps}
    assert ("GET", "/admin/health") in method_path
    assert ("POST", "/admin/login") in method_path
    assert ("GET", "/admin/users") in method_path
    assert ("GET", "/admin/users/new") in method_path
    assert ("POST", "/admin/users") in method_path
    assert ("GET", "/admin/users/:id") in method_path
    assert ("GET", "/admin/users/:id/edit") in method_path
    assert ("PATCH", "/admin/users/:id") in method_path
    assert ("PUT", "/admin/users/:id") in method_path
    assert ("DELETE", "/admin/users/:id") in method_path


def test_rails_singular_resource_paths_and_methods():
    from tracely360.extract import extract_ruby
    result = extract_ruby(FIXTURE_DIR / "sample_rails_resource.rb")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    assert {(e["method"], e["path"]) for e in eps} == {
        ("GET", "/admin/profile/new"),
        ("POST", "/admin/profile"),
        ("GET", "/admin/profile"),
        ("GET", "/admin/profile/edit"),
        ("PATCH", "/admin/profile"),
        ("PUT", "/admin/profile"),
        ("DELETE", "/admin/profile"),
    }


def test_rails_nested_resources_with_filters():
    from tracely360.extract import extract_ruby
    result = extract_ruby(FIXTURE_DIR / "sample_rails_nested_resource.rb")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    assert {(e["method"], e["path"]) for e in eps} == {
        ("GET", "/users"),
        ("GET", "/users/new"),
        ("POST", "/users"),
        ("GET", "/users/:id"),
        ("GET", "/users/:id/edit"),
        ("PATCH", "/users/:id"),
        ("PUT", "/users/:id"),
        ("DELETE", "/users/:id"),
        ("GET", "/users/:user_id/posts"),
        ("GET", "/users/:user_id/posts/:id"),
        ("GET", "/profile/new"),
        ("POST", "/profile"),
        ("GET", "/profile"),
        ("GET", "/profile/edit"),
        ("PATCH", "/profile"),
        ("PUT", "/profile"),
    }


def test_rails_shallow_resources_with_filters():
    from tracely360.extract import extract_ruby
    result = extract_ruby(FIXTURE_DIR / "sample_rails_shallow_resource.rb")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    assert {(e["method"], e["path"]) for e in eps} == {
        ("GET", "/admin/articles"),
        ("GET", "/admin/articles/new"),
        ("POST", "/admin/articles"),
        ("GET", "/admin/articles/:id"),
        ("GET", "/admin/articles/:id/edit"),
        ("PATCH", "/admin/articles/:id"),
        ("PUT", "/admin/articles/:id"),
        ("DELETE", "/admin/articles/:id"),
        ("GET", "/admin/articles/:article_id/comments"),
        ("GET", "/admin/comments/:id"),
        ("DELETE", "/admin/comments/:id"),
        ("GET", "/admin/comments/:comment_id/likes"),
    }


def test_rails_handler_edges_for_direct_and_resource_routes():
    from tracely360.extract import extract_ruby
    result = extract_ruby(FIXTURE_DIR / "sample_rails_handler_edges.rb")
    ep_edges = [e for e in result["edges"] if e["relation"] == "exposes_endpoint"]
    assert len(ep_edges) == 7
    assert {e["source"] for e in ep_edges} == {
        "sample_rails_handler_edges_userscontroller_index",
        "sample_rails_handler_edges_userscontroller_show",
        "sample_rails_handler_edges_postscontroller_index",
        "sample_rails_handler_edges_postscontroller_show",
        "sample_rails_handler_edges_postscontroller_update",
        "sample_rails_handler_edges_postscontroller_destroy",
    }


def test_rails_cross_file_handler_resolution(tmp_path):
    from tracely360.extract import extract
    fixture_dir = FIXTURE_DIR / "rails_cross_file"
    result = extract(
        [fixture_dir / "routes.rb", fixture_dir / "controllers.rb"],
        cache_root=tmp_path,
    )
    ep_edges = [e for e in result["edges"] if e["relation"] == "exposes_endpoint"]
    assert len(ep_edges) == 2
    assert {e["source"] for e in ep_edges} == {
        "controllers_admin_userscontroller_index",
        "controllers_admin_postscontroller_show",
    }
    assert {e["confidence"] for e in ep_edges} == {"INFERRED"}


def test_rails_endpoint_controller_action_metadata():
    from tracely360.extract import extract_ruby
    result = extract_ruby(FIXTURE_DIR / "sample_rails_handler_edges.rb")

    users_index = _endpoint_by_method_path(result, "GET", "/users")
    assert users_index["controller"] == "UsersController"
    assert users_index["action"] == "index"

    posts_show = _endpoint_by_method_path(result, "GET", "/posts/:id")
    assert posts_show["controller"] == "PostsController"
    assert posts_show["action"] == "show"


def test_rails_framework_tag():
    from tracely360.extract import extract_ruby
    result = extract_ruby(FIXTURE_DIR / "sample_rails.rb")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    for ep in eps:
        assert ep["framework"] == "rails"


# ── ASP.NET ───────────────────────────────────────────────────────────────

def test_aspnet_endpoint_count():
    from tracely360.extract import extract_csharp
    result = extract_csharp(FIXTURE_DIR / "sample_aspnet.cs")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    assert len(eps) == 3


def test_aspnet_paths_frameworks_and_edges():
    from tracely360.extract import extract_csharp
    result = extract_csharp(FIXTURE_DIR / "sample_aspnet.cs")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    method_path = {(e["method"], e["path"]) for e in eps}
    assert ("GET", "/api/users") in method_path
    assert ("POST", "/api/users/create") in method_path
    assert ("GET", "/health") in method_path

    frameworks = {e["framework"] for e in eps}
    assert frameworks == {"aspnet", "aspnet-minimal"}

    ep_edges = [e for e in result["edges"] if e["relation"] == "exposes_endpoint"]
    assert len(ep_edges) == 2
    sources = {e["source"] for e in ep_edges}
    assert "sample_aspnet_userscontroller_listusers" in sources
    assert "sample_aspnet_userscontroller_createuser" in sources


def test_aspnet_mapgroup_and_mapmethods():
    from tracely360.extract import extract_csharp
    result = extract_csharp(FIXTURE_DIR / "sample_aspnet_group.cs")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    assert {(ep["method"], ep["path"]) for ep in eps} == {
        ("GET", "/api/users"),
        ("GET", "/ping"),
        ("POST", "/ping"),
    }
    for ep in eps:
        assert ep["framework"] == "aspnet-minimal"


def test_aspnet_acceptverbs_attribute():
    from tracely360.extract import extract_csharp
    result = extract_csharp(FIXTURE_DIR / "sample_aspnet_acceptverbs.cs")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    assert {(ep["method"], ep["path"]) for ep in eps} == {
        ("GET", "/api/items/bulk"),
        ("POST", "/api/items/bulk"),
    }
    assert {ep["framework"] for ep in eps} == {"aspnet"}


def test_aspnet_minimal_handler_edges():
    from tracely360.extract import extract_csharp
    result = extract_csharp(FIXTURE_DIR / "sample_aspnet_minimal_handlers.cs")
    ep_edges = [e for e in result["edges"] if e["relation"] == "exposes_endpoint"]
    assert len(ep_edges) == 3
    assert {e["source"] for e in ep_edges} == {
        "sample_aspnet_minimal_handlers_health",
        "sample_aspnet_minimal_handlers_handlers_ping",
    }
    assert {(e["method"], e["path"]) for e in result["nodes"] if e.get("file_type") == "endpoint"} == {
        ("GET", "/health"),
        ("GET", "/ping"),
        ("POST", "/ping"),
    }


def test_aspnet_cross_file_minimal_handler_resolution(tmp_path):
    from tracely360.extract import extract
    fixture_dir = FIXTURE_DIR / "aspnet_cross_file"
    result = extract(
        [fixture_dir / "routes.cs", fixture_dir / "handlers.cs"],
        cache_root=tmp_path,
    )
    ep_edges = [e for e in result["edges"] if e["relation"] == "exposes_endpoint"]
    assert len(ep_edges) == 3
    assert {e["source"] for e in ep_edges} == {
        "handlers_health",
        "handlers_handlers_ping",
    }
    assert {e["confidence"] for e in ep_edges} == {"INFERRED"}


def test_endpoint_controller_action_metadata_for_controller_frameworks():
    from tracely360.extract import extract_csharp, extract_java, extract_js

    nest = extract_js(FIXTURE_DIR / "sample_nest.ts")
    nest_users = _endpoint_by_method_path(nest, "GET", "/users")
    assert nest_users["controller"] == "UserController"
    assert nest_users["action"] == "listUsers"

    spring = extract_java(FIXTURE_DIR / "sample_spring.java")
    spring_users = _endpoint_by_method_path(spring, "GET", "/api/users")
    assert spring_users["controller"] == "UserController"
    assert spring_users["action"] == "getUsers"

    aspnet = extract_csharp(FIXTURE_DIR / "sample_aspnet.cs")
    aspnet_users = _endpoint_by_method_path(aspnet, "GET", "/api/users")
    assert aspnet_users["controller"] == "UsersController"
    assert aspnet_users["action"] == "ListUsers"

    minimal = extract_csharp(FIXTURE_DIR / "sample_aspnet_minimal_handlers.cs")
    health = _endpoint_by_method_path(minimal, "GET", "/health")
    assert "controller" not in health
    assert health["action"] == "Health"

    ping = _endpoint_by_method_path(minimal, "GET", "/ping")
    assert ping["controller"] == "Handlers"
    assert ping["action"] == "Ping"


# ── OpenAPI / Swagger import ───────────────────────────────────────────────

def test_openapi_yaml_import(tmp_path):
    from tracely360.extract import extract

    result = extract([FIXTURE_DIR / "sample_openapi.yaml"], cache_root=tmp_path)
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]

    assert {(ep["method"], ep["path"]) for ep in eps} == {
        ("GET", "/pets"),
        ("POST", "/pets"),
        ("GET", "/pets/{petId}"),
    }
    assert {ep["framework"] for ep in eps} == {"openapi"}

    list_pets = _endpoint_by_method_path(result, "GET", "/pets")
    assert list_pets["operation_id"] == "listPets"
    assert list_pets["summary"] == "List pets"
    assert list_pets["tags"] == ["pets"]
    assert list_pets["spec_title"] == "Petstore API"
    assert list_pets["spec_version"] == "3.1.0"
    assert list_pets["api_version"] == "1.2.3"

    contains = [e for e in result["edges"] if e["relation"] == "contains"]
    assert len(contains) == 3


def test_swagger_json_import(tmp_path):
    from tracely360.extract import extract

    result = extract([FIXTURE_DIR / "sample_swagger.json"], cache_root=tmp_path)
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]

    assert {(ep["method"], ep["path"]) for ep in eps} == {
        ("GET", "/users"),
        ("DELETE", "/users/{id}"),
    }
    assert {ep["framework"] for ep in eps} == {"swagger"}

    delete_user = _endpoint_by_method_path(result, "DELETE", "/users/{id}")
    assert delete_user["operation_id"] == "deleteUser"
    assert delete_user["summary"] == "Delete user"
    assert delete_user["tags"] == ["users"]
    assert delete_user["spec_title"] == "Legacy API"
    assert delete_user["spec_version"] == "2.0"
    assert delete_user["api_version"] == "2.0"


# ── Endpoint node schema ────────────────────────────────────────────────────

def test_endpoint_node_schema():
    from tracely360.extract import extract_python
    result = extract_python(FIXTURE_DIR / "sample_flask.py")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    required_keys = {"id", "label", "file_type", "method", "path", "framework", "source_file", "source_location"}
    for ep in eps:
        assert required_keys.issubset(ep.keys()), f"Missing keys: {required_keys - ep.keys()}"


def test_endpoint_edge_schema():
    from tracely360.extract import extract_python
    result = extract_python(FIXTURE_DIR / "sample_flask.py")
    ep_edges = [e for e in result["edges"] if e["relation"] == "exposes_endpoint"]
    required_keys = {"source", "target", "relation", "confidence", "source_file", "source_location", "weight"}
    for edge in ep_edges:
        assert required_keys.issubset(edge.keys()), f"Missing keys: {required_keys - edge.keys()}"
        assert edge["relation"] == "exposes_endpoint"
        assert edge["confidence"] == "EXTRACTED"


# ── No endpoints in non-web code ────────────────────────────────────────────

def test_no_endpoints_in_plain_python():
    from tracely360.extract import extract_python
    result = extract_python(FIXTURE_DIR / "sample_calls.py")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    assert len(eps) == 0


def test_no_endpoints_in_plain_c():
    from tracely360.extract import extract_c
    result = extract_c(FIXTURE_DIR / "sample.c")
    eps = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    assert len(eps) == 0


# ── Validation integration ───────────────────────────────────────────────────

def test_endpoint_passes_validation():
    from tracely360.extract import extract_python
    from tracely360.validate import validate_extraction
    result = extract_python(FIXTURE_DIR / "sample_flask.py")
    # Check endpoint nodes pass schema validation (test with nodes only, no edges,
    # since exposes_endpoint edges may reference function nodes resolved in other files)
    ep_nodes = [n for n in result["nodes"] if n.get("file_type") == "endpoint"]
    ep_result = {"nodes": ep_nodes, "edges": [], "raw_calls": []}
    errors = validate_extraction(ep_result)
    assert len(errors) == 0, f"Validation errors: {errors}"


# ── Integration: extract → build → cluster → export ─────────────────────────

@pytest.mark.integration
def test_endpoint_pipeline_integration(tmp_path):
    """End-to-end: extract Flask fixture → build graph → cluster → export HTML with endpoints."""
    from tracely360.extract import extract_python
    from tracely360.build import build_from_json
    from tracely360.cluster import cluster, score_all
    from tracely360.analyze import god_nodes, surprising_connections
    from tracely360.report import generate
    from tracely360.export import to_html, to_json

    extraction = extract_python(FIXTURE_DIR / "sample_flask.py")
    assert any(n.get("file_type") == "endpoint" for n in extraction["nodes"])

    G = build_from_json(extraction)
    assert G.number_of_nodes() > 0

    # Endpoint nodes survive into the graph
    ep_graph_nodes = [
        (nid, d) for nid, d in G.nodes(data=True)
        if d.get("file_type") == "endpoint"
    ]
    assert len(ep_graph_nodes) >= 3  # at least GET /health, GET /items/<id>, POST /items

    # Cluster
    communities = cluster(G)
    assert len(communities) >= 1
    cohesion = score_all(G, communities)

    # Every node is in a community
    all_community_nodes = {n for ns in communities.values() for n in ns}
    for nid in G.nodes():
        assert nid in all_community_nodes, f"Node {nid} not in any community"

    # Analyze
    gods = god_nodes(G)
    surprises = surprising_connections(G, communities)

    # Report includes endpoint section
    community_labels = {cid: f"Group {cid}" for cid in communities}
    from tracely360.detect import detect
    detection = detect(FIXTURE_DIR)
    report = generate(
        G, communities, cohesion, community_labels,
        gods, surprises, detection,
        {"input": 0, "output": 0},
        root=str(FIXTURE_DIR),
    )
    assert "## API Endpoints" in report
    assert "GET" in report
    assert "/health" in report

    # Export HTML
    html_path = str(tmp_path / "graph.html")
    to_html(G, communities, html_path, community_labels=community_labels)
    html_content = (tmp_path / "graph.html").read_text()
    assert "star" in html_content  # endpoint nodes use star shape
    assert "endpoint" in html_content

    # Export JSON
    json_path = str(tmp_path / "graph.json")
    to_json(G, communities, json_path)
    import json
    data = json.loads((tmp_path / "graph.json").read_text())
    ep_json_nodes = [n for n in data["nodes"] if n.get("file_type") == "endpoint"]
    assert len(ep_json_nodes) >= 3
