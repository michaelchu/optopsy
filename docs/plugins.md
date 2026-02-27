# Plugins

Optopsy supports extending its functionality through Python [entry points](https://packaging.python.org/en/latest/specifications/entry-points/). Plugins are discovered automatically at runtime — install a plugin package and it is available immediately.

## Entry Point Groups

There are five plugin groups:

| Group | Purpose |
|-------|---------|
| `optopsy.strategies` | Add custom strategy functions |
| `optopsy.signals` | Add custom entry/exit signal factories |
| `optopsy.providers` | Add data provider backends |
| `optopsy.tools` | Add Chat UI tools |
| `optopsy.auth` | Add Chat UI authentication |

All discovery is lazy and cached. A broken plugin is logged and skipped — it cannot crash the host application.

## Registering Plugins

Plugins are registered via `[project.entry-points]` in your package's `pyproject.toml`:

```toml
[project.entry-points."optopsy.strategies"]
my_strategy = "my_package:register_strategies"

[project.entry-points."optopsy.signals"]
my_signals = "my_package:register_signals"

[project.entry-points."optopsy.providers"]
my_provider = "my_package:MyProvider"

[project.entry-points."optopsy.tools"]
my_tools = "my_package:register_tools"

[project.entry-points."optopsy.auth"]
my_auth = "my_package:register_auth"
```

## Strategy Plugins

Each entry point must resolve to a callable (registrar) that returns a dict:

```python
def register_strategies():
    return {
        "my_custom_spread": (
            my_custom_spread_func,   # The strategy function
            "My custom spread strategy",  # Description
            False,                    # is_calendar (True for calendar/diagonal)
            None,                     # option_type: "call", "put", or None
        ),
    }
```

The strategy function should follow the same signature as built-in strategies (accept a DataFrame and `**kwargs`).

## Signal Plugins

Each entry point must resolve to a callable returning a dict of signal factory lambdas:

```python
def register_signals():
    return {
        "my_custom_signal": lambda period, threshold: ...,
    }
```

The shape matches the internal `SIGNAL_REGISTRY` used by the Chat UI.

## Provider Plugins

Each entry point must resolve to a `DataProvider` subclass (the class itself, not an instance):

```python
from optopsy.data.providers.base import DataProvider

class MyProvider(DataProvider):
    name = "my_provider"
    env_key = "MY_PROVIDER_API_KEY"

    def get_tool_schemas(self): ...
    def get_tool_names(self): ...
    async def execute(self, tool_name, arguments): ...
```

The provider is auto-detected if its `env_key` environment variable is set.

## Tool Plugins

Each entry point must resolve to a callable returning:

```python
def register_tools():
    return {
        "schemas": [
            # OpenAI-compatible tool schema dicts
            {"type": "function", "function": {"name": "my_tool", ...}},
        ],
        "handlers": {"my_tool": handler_callable},
        "models": {"my_tool": PydanticModel},
        "descriptions": {"my_tool": "Description of my tool"},
    }
```

## Auth Plugins

Each entry point must resolve to a callable returning an auth configuration dict:

```python
def register_auth():
    return {
        "type": "password",  # "password", "oauth", or "header"
        "callback": my_auth_callback,
    }
```

Only the first discovered auth plugin is used.

### Auth Types

| Type | Callback Signature |
|------|-------------------|
| `password` | `(username: str, password: str) -> cl.User \| None` |
| `oauth` | `(provider_id, token, raw_user_data, default_user, id_token) -> cl.User \| None` |
| `header` | `(headers) -> cl.User \| None` |

When no auth plugin is installed, the Chat UI defaults to local header-based auto-auth for single-user access.
