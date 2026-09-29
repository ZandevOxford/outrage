# outrage.systemone

A judge for [`outrage.smartsearch`](smartsearch.md#module-outrage.smartsearch) that speaks the System One protocol.

Direct HTTP rather than a vendor SDK, deliberately. The protocol is one POST
with a JSON body, and more than one server speaks it: TypeSafe's hosted Jev
and a local `laya-serve` differ in their base URL and nothing else, so a
client written against the wire rather than against one vendor's library is
one client for both.

**The three settings are read in one place**, [`Settings.read()`](#outrage.systemone.Settings.read), because
they are expected to change shape once a second provider needs configuring.
Each comes from TypeSafe's own environment variable if it is set, else from
the `[smart_search]` table of the user's configuration file
([`outrage.home.read_config()`](home.md#outrage.home.read_config)), else from a default. The variables are the
ones TypeSafe's SDK reads, and they mean what they mean there: in particular
`TYPESAFE_BASE_URL` is the API root, with the protocol's path appended, so a
value set for the SDK or for a gateway in front of it works here unchanged.

Retrying follows the policy TypeSafe's own SDK defaults to -- two retries,
backoff from half a second doubling to five with a quarter jitter, over 408,
429 and every 5xx, honouring `Retry-After` -- so a failure that reaches the
cascade has already had the chances an SDK user's would.

### outrage.systemone.BASE_URL_VARIABLE *= 'TYPESAFE_BASE_URL'*

The environment variable holding the base URL, as TypeSafe's SDK names it.

### outrage.systemone.CONFIG_NAMES *= ('key', 'base_url', 'model')*

The settings that table may hold. Any other name is refused rather than
ignored, so a misspelt setting is reported instead of silently not applying.

### outrage.systemone.CONFIG_TABLE *= 'smart_search'*

The configuration file's table for these settings.

### outrage.systemone.DEFAULT_BASE_URL *= 'https://api.typesafe.ai'*

The root of TypeSafe's hosted API.

### outrage.systemone.DEFAULT_MODEL *= 'jev-latest'*

TypeSafe's alias for its current flagship model.

### outrage.systemone.DETAIL_CHARS *= 300*

Longest stretch of an error response carried into a message. A validation
failure names its field in the first line or two, and a proxy's HTML error
page is not worth more.

### outrage.systemone.ENDPOINT_PATH *= '/v1/systemone'*

Where the protocol answers, below any base URL.

### outrage.systemone.KEY_VARIABLE *= 'TYPESAFE_API_KEY'*

The environment variable holding the API key, as TypeSafe's SDK names it.

### outrage.systemone.MODEL_VARIABLE *= 'TYPESAFE_DEFAULT_MODEL'*

The environment variable naming the model, as TypeSafe's SDK names it.

### *class* outrage.systemone.RetryPolicy(max_retries: [int](https://docs.python.org/3/builtins/functions.html#int) = 2, backoff_initial: [float](https://docs.python.org/3/builtins/functions.html#float) = 0.5, backoff_max: [float](https://docs.python.org/3/builtins/functions.html#float) = 5.0, backoff_jitter: [float](https://docs.python.org/3/builtins/functions.html#float) = 0.25, statuses: [frozenset](https://docs.python.org/3/builtins/stdtypes.html#frozenset)[[int](https://docs.python.org/3/builtins/functions.html#int)] = <factory>, timeout: [float](https://docs.python.org/3/builtins/functions.html#float) = 30.0)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

When a failed request is sent again, and how long to wait first.

#### max_retries *: [int](https://docs.python.org/3/builtins/functions.html#int)*

#### backoff_initial *: [float](https://docs.python.org/3/builtins/functions.html#float)*

#### backoff_max *: [float](https://docs.python.org/3/builtins/functions.html#float)*

#### backoff_jitter *: [float](https://docs.python.org/3/builtins/functions.html#float)*

#### statuses *: [frozenset](https://docs.python.org/3/builtins/stdtypes.html#frozenset)[[int](https://docs.python.org/3/builtins/functions.html#int)]*

#### timeout *: [float](https://docs.python.org/3/builtins/functions.html#float)*

#### delay(attempt: [int](https://docs.python.org/3/builtins/functions.html#int), retry_after: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None) → [float](https://docs.python.org/3/builtins/functions.html#float)

Seconds to wait before retry number `attempt`, counted from zero.

### *class* outrage.systemone.Settings(base_url: [str](https://docs.python.org/3/builtins/stdtypes.html#str) = 'https://api.typesafe.ai', model: [str](https://docs.python.org/3/builtins/stdtypes.html#str) = 'jev-latest', key: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, key_source: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Where to send questions, which model answers them, and the key if any.

#### base_url *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

The API root, as `TYPESAFE_BASE_URL` means it; [`url`](#outrage.systemone.Settings.url) is below it.

#### model *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

#### key *: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None)*

None sends no `Authorization` header, which is what a local server
wants; TypeSafe's refuses the request. Kept out of `repr` so a settings
object in a log or a traceback does not carry it.

#### key_source *: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None)*

Where the key came from, a variable name or a file path, so a refused
key can be looked for in the right place.

#### *property* url *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

Where requests are posted.

#### *classmethod* read(environ: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [str](https://docs.python.org/3/builtins/stdtypes.html#str)] | [None](https://docs.python.org/3/builtins/constants.html#None) = None, path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [None](https://docs.python.org/3/builtins/constants.html#None) = None) → [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Self](https://docs.python.org/3/library/typing.html#typing.Self), [list](https://docs.python.org/3/builtins/stdtypes.html#list)[[Refusal](errors.md#outrage.errors.Refusal)]]

The settings this process is configured with, and every problem with them.

`path` is the configuration file, [`outrage.home.config_path()`](home.md#outrage.home.config_path)
by default. The settings come back even when there are refusals, built
from whatever was usable, but a caller should not search with them: a
file that other users can open, in particular, refuses the search even
where the environment supplies everything, since the key in it has to be
treated as out either way.

An empty variable counts as unset, as a shell's `VAR=` usually means.

#### *classmethod* load(environ: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [str](https://docs.python.org/3/builtins/stdtypes.html#str)] | [None](https://docs.python.org/3/builtins/constants.html#None) = None, path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [None](https://docs.python.org/3/builtins/constants.html#None) = None) → [Self](https://docs.python.org/3/library/typing.html#typing.Self)

[`read()`](#outrage.systemone.Settings.read), raising the first refusal as its error.

#### *property* configured *: [bool](https://docs.python.org/3/builtins/functions.html#bool)*

Whether a search can be sent anywhere with these settings.

A key, or a base URL of its own: TypeSafe's hosted API refuses a
request without a key, while a local server usually wants none, and
is only reached by setting its URL. A gateway that wants a key and has
none says so on the first request.

### *class* outrage.systemone.SystemOne(settings: [Settings](#outrage.systemone.Settings), \*, retry: [RetryPolicy](#outrage.systemone.RetryPolicy) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, transport: BaseTransport | [None](https://docs.python.org/3/builtins/constants.html#None) = None, sleep: [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[float](https://docs.python.org/3/builtins/functions.html#float)], [None](https://docs.python.org/3/builtins/constants.html#None)] = time.sleep)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A [`Judge`](smartsearch.md#outrage.smartsearch.Judge) over HTTP.

Holds one connection pool for its lifetime, so a search that sends a few
hundred requests opens a handful of connections rather than a few hundred.
Close it, or use it as a context manager.

#### close() → [None](https://docs.python.org/3/builtins/constants.html#None)

#### judge(state: [str](https://docs.python.org/3/builtins/stdtypes.html#str), questions: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Question](smartsearch.md#outrage.smartsearch.Question)]) → [Judgement](smartsearch.md#outrage.smartsearch.Judgement)
