# outrage.mounts
0 0

### outrage.mounts.MOUNT_KIND *= 'mount'*
1864 1864

### outrage.mounts.OPTIONS *= ('type',)*
2256 2256

### outrage.mounts.OPTION_ASSIGNMENT *= '='*
2575 2575

### outrage.mounts.OPTION_DELIMITER *= ','*
2838 2838

### outrage.mounts.READ_ONLY_MOUNT_KIND *= 'read-only mount'*
3614 3614

### outrage.mounts.SPEC_DELIMITER *= '='*
4469 4469

### outrage.mounts.TYPE_OPTION *= 'type'*
4782 4782

### *class* outrage.mounts.Mount(prefix: [str](https://docs.python.org/3/library/stdtypes.html#str), store: [Store](store.md#outrage.store.Store), read_only: [bool](https://docs.python.org/3/library/functions.html#bool) = False)
5480 5480

#### prefix *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
5829 5829

#### store *: [Store](store.md#outrage.store.Store)*
5978 5978

#### read_only *: [bool](https://docs.python.org/3/library/functions.html#bool)*
6032 6032

#### *property* kind *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
6325 6325

#### *property* name *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
6450 6450

#### *property* is_root *: [bool](https://docs.python.org/3/library/functions.html#bool)*
6602 6602

#### inner(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)
6693 6693

#### outer(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)
6966 6968

### *exception* outrage.mounts.MountError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
7938 7942

### *class* outrage.mounts.MountedStore(stores: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Store](store.md#outrage.store.Store)], \*, read_only: [Collection](https://docs.python.org/3/library/collections.abc.html#collections.abc.Collection)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = ())
8324 8328

#### writable *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[bool](https://docs.python.org/3/library/functions.html#bool)]* *= True*
9567 9571

#### backend_name *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[str](https://docs.python.org/3/library/stdtypes.html#str)]* *= 'mounts'*
9977 9981

#### *classmethod* single(store: [Store](store.md#outrage.store.Store)) → [MountedStore](#outrage.mounts.MountedStore)
10290 10294

#### *property* root *: [Mount](#outrage.mounts.Mount)*
10657 10663

#### *property* read_only *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Mount](#outrage.mounts.Mount)]*
11079 11085

#### *property* multiple *: [bool](https://docs.python.org/3/library/functions.html#bool)*
11249 11255

#### resolve(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), \*, allow_wildcard: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [Resolved](#outrage.mounts.Resolved)
11388 11394

#### below(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Mount](#outrage.mounts.Mount)]
12461 12469

#### directly_below(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Mount](#outrage.mounts.Mount)]
13013 13023

#### segments(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), depth: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Segment](#outrage.mounts.Segment)]
13849 13861

#### children(parent: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Entry](store.md#outrage.store.Entry)]
15281 15295

#### last_child(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)) → [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)
15949 15965

#### shadowing() → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Mount](#outrage.mounts.Mount)]
16877 16895

#### read_only_below(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]
17689 17709

#### store_document(key: [str](https://docs.python.org/3/library/stdtypes.html#str), content: [str](https://docs.python.org/3/library/stdtypes.html#str), format: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, title: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, encoding: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, updated_at: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [str](https://docs.python.org/3/library/stdtypes.html#str)
18391 18413

#### retrieve_document(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, offset: [int](https://docs.python.org/3/library/functions.html#int) = 0, byte_offset: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, length: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, pattern: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, occurrence: [int](https://docs.python.org/3/library/functions.html#int) = 0, max_chars: [int](https://docs.python.org/3/library/functions.html#int) = DEFAULT_MAX_CHARS) → [Excerpt](store.md#outrage.store.Excerpt)
21465 21489

#### exists(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [bool](https://docs.python.org/3/library/functions.html#bool)
23168 23194

#### level_entry(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [Entry](store.md#outrage.store.Entry) | [None](https://docs.python.org/3/library/constants.html#None)
23661 23689

#### descendant_count(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, whole_subtree: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [int](https://docs.python.org/3/library/functions.html#int)
24257 24287

#### latest_change(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, whole_subtree: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)
26003 26035

#### delete(key: [str](https://docs.python.org/3/library/stdtypes.html#str), recursive: [bool](https://docs.python.org/3/library/functions.html#bool) = False, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, unchanged_since: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]
26905 26939

#### list_keys(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Page](store.md#outrage.store.Page)[[Entry](store.md#outrage.store.Entry)]
29022 29058

#### get_documents(subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, max_chars: [int](https://docs.python.org/3/library/functions.html#int) = DEFAULT_BULK_MAX_CHARS, limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, max_total_chars: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Page](store.md#outrage.store.Page)[[Excerpt](store.md#outrage.store.Excerpt)]
29855 29893

#### keys_missing_meta(subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = 'title', limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Page](store.md#outrage.store.Page)[[str](https://docs.python.org/3/library/stdtypes.html#str)]
32043 32083

#### missing_meta_stats(subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, window: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = 'title', sample: [int](https://docs.python.org/3/library/functions.html#int) = 0) → [MissingMeta](store.md#outrage.store.MissingMeta)
33254 33296

#### close() → [None](https://docs.python.org/3/library/constants.html#None)
34215 34259

### *exception* outrage.mounts.ReadOnlyMountError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
34349 34395

### *class* outrage.mounts.Resolved(mount: [Mount](#outrage.mounts.Mount), key: [str](https://docs.python.org/3/library/stdtypes.html#str), outer: [str](https://docs.python.org/3/library/stdtypes.html#str))
35153 35199

#### mount *: [Mount](#outrage.mounts.Mount)*
35492 35538

#### key *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
35539 35585

#### outer *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
35647 35693

#### *property* store *: [Store](store.md#outrage.store.Store)*
35764 35810

#### *property* read_only *: [bool](https://docs.python.org/3/library/functions.html#bool)*
36213 36259

#### writable(action: [str](https://docs.python.org/3/library/stdtypes.html#str) = 'write') → [Resolved](#outrage.mounts.Resolved)
36359 36405

### *class* outrage.mounts.Segment(mount: [Mount](#outrage.mounts.Mount), subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree), key_range: [KeyRange](store.md#outrage.store.KeyRange))
37901 37949

#### mount *: [Mount](#outrage.mounts.Mount)*
38827 38875

#### subtree *: [BoundedSubtree](store.md#outrage.store.BoundedSubtree)*
38874 38922

#### key_range *: [KeyRange](store.md#outrage.store.KeyRange)*
38948 38996

#### *property* store *: [Store](store.md#outrage.store.Store)*
39012 39060

#### resume_from(after: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)) → [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), [bool](https://docs.python.org/3/library/functions.html#bool)]
39362 39410

### *class* outrage.mounts.Spec(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), type: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None)
40847 40897

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*
41693 41743

#### type *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
41776 41826

### outrage.mounts.mount_point(prefix: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, spec: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [str](https://docs.python.org/3/library/stdtypes.html#str)
41988 42038

### outrage.mounts.open_mounts(directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None), specs: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = (), read_only_specs: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = (), \*, root_mount: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [Spec](#outrage.mounts.Spec) | [None](https://docs.python.org/3/library/constants.html#None) = None, log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/library/constants.html#None) = None, attached: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Store](store.md#outrage.store.Store)] = MappingProxyType({})) → [MountedStore](#outrage.mounts.MountedStore)
42766 42818

### outrage.mounts.parse_options(value: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, spec: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Spec](#outrage.mounts.Spec)
46757 46811

### outrage.mounts.parse_spec(spec: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Spec](#outrage.mounts.Spec)]
48069 48125

### outrage.mounts.unparse(spec: [Spec](#outrage.mounts.Spec)) → [str](https://docs.python.org/3/library/stdtypes.html#str)
49360 49418
