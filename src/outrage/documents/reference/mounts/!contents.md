# outrage.mounts
0 0

### outrage.mounts.EXTENSIONS_OPTION *= 'extensions'*
2172 2172

### outrage.mounts.MOUNT_KIND *= 'mount'*
3169 3169

### outrage.mounts.OPTIONS *= ('type', 'extensions')*
3561 3561

### outrage.mounts.OPTION_ASSIGNMENT *= '='*
3893 3893

### outrage.mounts.OPTION_DELIMITER *= ','*
4156 4156

### outrage.mounts.READ_ONLY_MOUNT_KIND *= 'read-only mount'*
4932 4932

### outrage.mounts.ROOT_KIND *= 'root'*
5738 5738

### outrage.mounts.SPEC_DELIMITER *= '='*
6140 6140

### outrage.mounts.TYPE_OPTION *= 'type'*
6453 6453

### *class* outrage.mounts.Mount(prefix: [str](https://docs.python.org/3/library/stdtypes.html#str), store: [Store](store.md#outrage.store.Store), read_only: [bool](https://docs.python.org/3/library/functions.html#bool) = False)
7151 7151

#### prefix *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
7500 7500

#### store *: [Store](store.md#outrage.store.Store)*
7649 7649

#### read_only *: [bool](https://docs.python.org/3/library/functions.html#bool)*
7703 7703

#### *property* kind *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
7996 7996

#### *property* name *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
8121 8121

#### *property* is_root *: [bool](https://docs.python.org/3/library/functions.html#bool)*
8273 8273

#### inner(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)
8364 8364

#### outer(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)
8637 8639

### *exception* outrage.mounts.MountError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
9562 9566

### *class* outrage.mounts.MountedStore(stores: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Store](store.md#outrage.store.Store)], \*, read_only: [Collection](https://docs.python.org/3/library/collections.abc.html#collections.abc.Collection)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = ())
9948 9952

#### writable *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[bool](https://docs.python.org/3/library/functions.html#bool)]* *= True*
11191 11195

#### backend_name *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[str](https://docs.python.org/3/library/stdtypes.html#str)]* *= 'mounts'*
11601 11605

#### *classmethod* single(store: [Store](store.md#outrage.store.Store)) → [MountedStore](#outrage.mounts.MountedStore)
11914 11918

#### remounted(\*, mount: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Store](store.md#outrage.store.Store)] = MappingProxyType({}), read_only: [Collection](https://docs.python.org/3/library/collections.abc.html#collections.abc.Collection)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = (), unmount: [Collection](https://docs.python.org/3/library/collections.abc.html#collections.abc.Collection)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = ()) → [MountedStore](#outrage.mounts.MountedStore)
12281 12287

#### *property* root *: [Mount](#outrage.mounts.Mount)*
14589 14597

#### *property* read_only *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Mount](#outrage.mounts.Mount)]*
15011 15019

#### *property* multiple *: [bool](https://docs.python.org/3/library/functions.html#bool)*
15181 15189

#### resolve(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), \*, allow_wildcard: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [Resolved](#outrage.mounts.Resolved)
15320 15328

#### below(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Mount](#outrage.mounts.Mount)]
16393 16403

#### directly_below(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Mount](#outrage.mounts.Mount)]
16945 16957

#### segments(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), depth: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Segment](#outrage.mounts.Segment)]
17781 17795

#### children(parent: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Entry](store.md#outrage.store.Entry)]
19207 19223

#### last_child(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)) → [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)
19875 19893

#### shadowing() → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Mount](#outrage.mounts.Mount)]
20803 20823

#### read_only_below(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]
21615 21637

#### read_only_at_or_below(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]
22317 22341

#### store_document(key: [str](https://docs.python.org/3/library/stdtypes.html#str), content: [str](https://docs.python.org/3/library/stdtypes.html#str), format: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, title: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, encoding: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, updated_at: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [str](https://docs.python.org/3/library/stdtypes.html#str)
23461 23487

#### retrieve_document(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, offset: [int](https://docs.python.org/3/library/functions.html#int) = 0, byte_offset: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, length: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, pattern: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, occurrence: [int](https://docs.python.org/3/library/functions.html#int) = 0, max_chars: [int](https://docs.python.org/3/library/functions.html#int) = DEFAULT_MAX_CHARS) → [Excerpt](store.md#outrage.store.Excerpt)
26535 26563

#### exists(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [bool](https://docs.python.org/3/library/functions.html#bool)
28238 28268

#### level_entry(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [Entry](store.md#outrage.store.Entry) | [None](https://docs.python.org/3/library/constants.html#None)
28731 28763

#### descendant_count(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, whole_subtree: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [int](https://docs.python.org/3/library/functions.html#int)
29327 29361

#### latest_change(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, whole_subtree: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)
31073 31109

#### delete(key: [str](https://docs.python.org/3/library/stdtypes.html#str), recursive: [bool](https://docs.python.org/3/library/functions.html#bool) = False, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, unchanged_since: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]
31975 32013

#### list_keys(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Page](store.md#outrage.store.Page)[[Entry](store.md#outrage.store.Entry)]
34030 34070

#### get_documents(subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, max_chars: [int](https://docs.python.org/3/library/functions.html#int) = DEFAULT_BULK_MAX_CHARS, limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, max_total_chars: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Page](store.md#outrage.store.Page)[[Excerpt](store.md#outrage.store.Excerpt)]
34863 34905

#### keys_missing_meta(subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = 'title', limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Page](store.md#outrage.store.Page)[[str](https://docs.python.org/3/library/stdtypes.html#str)]
37051 37095

#### missing_meta_stats(subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, window: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = 'title', sample: [int](https://docs.python.org/3/library/functions.html#int) = 0) → [MissingMeta](store.md#outrage.store.MissingMeta)
38262 38308

#### close() → [None](https://docs.python.org/3/library/constants.html#None)
39223 39271

### *exception* outrage.mounts.ReadOnlyMountError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
39357 39407

### *class* outrage.mounts.Resolved(mount: [Mount](#outrage.mounts.Mount), key: [str](https://docs.python.org/3/library/stdtypes.html#str), outer: [str](https://docs.python.org/3/library/stdtypes.html#str))
40161 40211

#### mount *: [Mount](#outrage.mounts.Mount)*
40500 40550

#### key *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
40547 40597

#### outer *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
40655 40705

#### *property* store *: [Store](store.md#outrage.store.Store)*
40772 40822

#### *property* read_only *: [bool](https://docs.python.org/3/library/functions.html#bool)*
41221 41271

#### writable(action: [str](https://docs.python.org/3/library/stdtypes.html#str) = 'write') → [Resolved](#outrage.mounts.Resolved)
41367 41417

### *class* outrage.mounts.Segment(mount: [Mount](#outrage.mounts.Mount), subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree), key_range: [KeyRange](store.md#outrage.store.KeyRange))
42909 42961

#### mount *: [Mount](#outrage.mounts.Mount)*
43835 43887

#### subtree *: [BoundedSubtree](store.md#outrage.store.BoundedSubtree)*
43882 43934

#### key_range *: [KeyRange](store.md#outrage.store.KeyRange)*
43956 44008

#### *property* store *: [Store](store.md#outrage.store.Store)*
44020 44072

#### resume_from(after: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)) → [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), [bool](https://docs.python.org/3/library/functions.html#bool)]
44370 44422

### *class* outrage.mounts.Spec(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), type: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, extensions: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None)
45855 45909

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*
46844 46898

#### type *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
46927 46981

#### extensions *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
47139 47193

#### opened(directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/library/constants.html#None) = None, mount_point: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [FileStore](store.md#outrage.store.FileStore)
47465 47519

### outrage.mounts.mount_point(prefix: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, spec: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [str](https://docs.python.org/3/library/stdtypes.html#str)
48646 48702

### outrage.mounts.open_mounts(directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None), specs: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = (), read_only_specs: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = (), \*, root_mount: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [Spec](#outrage.mounts.Spec) | [None](https://docs.python.org/3/library/constants.html#None) = None, log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/library/constants.html#None) = None, attached: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Store](store.md#outrage.store.Store)] = MappingProxyType({})) → [MountedStore](#outrage.mounts.MountedStore)
49424 49482

### outrage.mounts.parse_options(value: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, spec: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Spec](#outrage.mounts.Spec)
53415 53475

### outrage.mounts.parse_spec(spec: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Spec](#outrage.mounts.Spec)]
54727 54789

### outrage.mounts.unparse(spec: [Spec](#outrage.mounts.Spec)) → [str](https://docs.python.org/3/library/stdtypes.html#str)
56018 56082
