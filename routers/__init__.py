from importlib import import_module

# Explicitly import router submodules so they are available for `from routers import ...` syntax
for _submod in [
    'avatar_routes',
    'auth_routes',
    'animation_routes',
    'progress_ws',
    'story_routes',
]:
    try:
        import_module(f'{__name__}.{_submod}')
    except ModuleNotFoundError:
        pass 