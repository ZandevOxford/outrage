# outrage.systemone

A judge for [`outrage.smartsearch`](smartsearch.md#module-outrage.smartsearch) that speaks the System One protocol.

Direct HTTP rather than a vendor SDK, deliberately. The protocol is one POST
with a JSON body, and more than one server speaks it: TypeSafe's hosted Jev
and a local `laya-serve` differ in their base URL and nothing else, so a
client written against the wire rather than against one vendor's library is
one client for both.

**The three settings are read in one place**, [`Settings.from_environment()`](#outrage.systemone.Settings.from_environment),
because they are expected to change shape once a second provider needs
configuring. Until then a key in `TYPESAFE_API_KEY` is the whole of it, with
TypeSafe's URL and `jev-latest` as defaults.

Retrying follows the policy TypeSafe's own SDK defaults to -- two retries,
backoff from half a second doubling to five with a quarter jitter, over 408,
429 and every 5xx, honouring `Retry-After` -- so a failure that reaches the
cascade has already had the chances an SDK user's would.

### outrage.systemone.DEFAULT_MODEL *= 'jev-latest'*

TypeSafe's alias for its current flagship model.

### outrage.systemone.DEFAULT_URL *= 'https://api.typesafe.ai/v1/systemone'*

Where TypeSafe's hosted models answer.

### outrage.systemone.DETAIL_CHARS *= 300*

Longest stretch of an error response carried into a message. A validation
failure names its field in the first line or two, and a proxy's HTML error
page is not worth more.

### outrage.systemone.KEY_VARIABLE *= 'TYPESAFE_API_KEY'*

The environment variable holding the API key.

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

### *class* outrage.systemone.Settings(url: [str](https://docs.python.org/3/builtins/stdtypes.html#str) = 'https://api.typesafe.ai/v1/systemone', model: [str](https://docs.python.org/3/builtins/stdtypes.html#str) = 'jev-latest', key: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Where to send questions, which model answers them, and the key if any.

#### url *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

#### model *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

#### key *: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None)*

None sends no `Authorization` header, which is what a local server
wants; TypeSafe's refuses the request.

#### *classmethod* from_environment(environ: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [str](https://docs.python.org/3/builtins/stdtypes.html#str)] | [None](https://docs.python.org/3/builtins/constants.html#None) = None) → [Self](https://docs.python.org/3/library/typing.html#typing.Self)

The settings this process is configured with.

#### *property* configured *: [bool](https://docs.python.org/3/builtins/functions.html#bool)*

Whether a search can be sent anywhere with these settings.

A key, for now: the URL and model always have defaults, and the only
server that needs no key is a local one, which has no configuration
of its own yet.

### *class* outrage.systemone.SystemOne(settings: [Settings](#outrage.systemone.Settings), \*, retry: [RetryPolicy](#outrage.systemone.RetryPolicy) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, transport: BaseTransport | [None](https://docs.python.org/3/builtins/constants.html#None) = None, sleep: [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[float](https://docs.python.org/3/builtins/functions.html#float)], [None](https://docs.python.org/3/builtins/constants.html#None)] = time.sleep)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A [`Judge`](smartsearch.md#outrage.smartsearch.Judge) over HTTP.

Holds one connection pool for its lifetime, so a search that sends a few
hundred requests opens a handful of connections rather than a few hundred.
Close it, or use it as a context manager.

#### close() → [None](https://docs.python.org/3/builtins/constants.html#None)

#### judge(state: [str](https://docs.python.org/3/builtins/stdtypes.html#str), questions: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Question](smartsearch.md#outrage.smartsearch.Question)]) → [Judgement](smartsearch.md#outrage.smartsearch.Judgement)
