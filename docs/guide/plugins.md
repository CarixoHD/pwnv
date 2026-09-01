# Plugins and Templates

A plugin decides what happens when a challenge of a given category is created:
which template files get written, and what code runs afterwards.

## Where they live

```
<config dir>/
├── plugins/
│   ├── selection.json      # category -> plugin name
│   └── pwn_example.py
└── templates/
    └── pwn/
        └── rop.py
```

`pwnv init` seeds both directories with the bundled examples. Files that already
exist are never overwritten, so an edited plugin survives a re-init.

## Writing one

```bash
pwnv plugin add my_pwn
```

That scaffolds a plugin file you can fill in:

```python
from pwnv.core import register_plugin
from pwnv.models.challenge import Category
from pwnv.plugins.plugin import ChallengePlugin


@register_plugin
class MyPwnPlugin(ChallengePlugin):
    templates_to_copy = {
        "rop.py": "solve.py",  # source in templates/pwn/ -> name on disk
    }

    def category(self) -> Category:
        return Category.pwn

    def logic(self, challenge):
        (challenge.path / "notes.md").touch()
```

| Member | Purpose |
| :--- | :--- |
| `category()` | Which category this plugin serves |
| `templates_to_copy` | `{source: destination}`; `None` keeps the source name |
| `logic(challenge)` | Anything else — chmod the binary, fetch a libc, write notes |
| `create_template()` | Override only if the default copy loop is not enough |

`logic` receives the full `Challenge` model, so services, points, tags and
attachments are all available.

## Selecting

One plugin per category is active at a time:

```bash
pwnv plugin select     # interactive
pwnv plugin info       # what is registered and what is selected
pwnv plugin info --json
pwnv plugin remove
```

## Templates

Templates are plain text with `{{placeholder}}` tokens, filled in when the file
is written:

```python
from pwn import *

p = remote("{{service.host}}", {{service.port}})
```

| Token | Value |
| :--- | :--- |
| `{{challenge.name}}`, `{{challenge.points}}`, `{{challenge.category}}` | Challenge fields |
| `{{challenge.description}}`, `{{challenge.slug}}`, `{{challenge.tags}}` | Synced metadata |
| `{{host}}`, `{{port}}`, `{{url}}` | The first service |
| `{{service.host}}`, `{{services.1.port}}` | Any service, by index |

An unknown token is left in place rather than replaced with an empty string, so
a typo shows up in the file instead of silently vanishing.

!!! tip "Templates fill in once; the object does not"

    A rendered template captures the host as it was when the file was written.
    If the service changes after a sync, the file is stale. Reading
    `challenge.service.host` from [the challenge object](../api/challenge.md)
    instead means the value is always current, and the same script works for the
    next challenge you copy it into.

## Re-running a plugin

```bash
pwnv challenge scaffold --category pwn --suffix _pwn
```

Useful when a challenge turns out to need a different category's setup, or when
you have improved a template and want it applied to an existing challenge.
Nothing is overwritten without `--force`.
