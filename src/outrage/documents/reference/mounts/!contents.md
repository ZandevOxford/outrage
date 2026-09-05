# outrage.mounts
0 0

### outrage.mounts.MOUNT_KIND *= 'mount'*
1773 1773

### outrage.mounts.OPTIONS *= ('type',)*
2165 2165

### outrage.mounts.OPTION_ASSIGNMENT *= '='*
2484 2484

### outrage.mounts.OPTION_DELIMITER *= ','*
2747 2747

### outrage.mounts.READ_ONLY_MOUNT_KIND *= 'read-only mount'*
3523 3523

### outrage.mounts.SPEC_DELIMITER *= '='*
4329 4329

### outrage.mounts.TYPE_OPTION *= 'type'*
4642 4642

### *class* outrage.mounts.Mount(prefix: [str](https://docs.python.org/3/library/stdtypes.html#str), store: [Store](store.md#outrage.store.Store), read_only: [bool](https://docs.python.org/3/library/functions.html#bool) = False)
5340 5340

#### prefix *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
5689 5689

#### store *: [Store](store.md#outrage.store.Store)*
5838 5838

#### read_only *: [bool](https://docs.python.org/3/library/functions.html#bool)*
5892 5892

#### *property* kind *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
6185 6185

#### *property* name *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
6310 6310

#### *property* is_root *: [bool](https://docs.python.org/3/library/functions.html#bool)*
6462 6462

#### inner(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)
6553 6553

#### outer(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)
6826 6828

### *exception* outrage.mounts.MountError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
7751 7755

### *class* outrage.mounts.MountedStore(stores: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Store](store.md#outrage.store.Store)], \*, read_only: [Collection](https://docs.python.org/3/library/collections.abc.html#collections.abc.Collection)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = ())
8137 8141

#### writable *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[bool](https://docs.python.org/3/library/functions.html#bool)]* *= True*
9380 9384

#### backend_name *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[str](https://docs.python.org/3/library/stdtypes.html#str)]* *= 'mounts'*
9790 9794

#### *classmethod* single(store: [Store](store.md#outrage.store.Store)) → [MountedStore](#outrage.mounts.MountedStore)
10103 10107

#### *property* root *: [Mount](#outrage.mounts.Mount)*
10470 10476

#### *property* read_only *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Mount](#outrage.mounts.Mount)]*
10892 10898

#### *property* multiple *: [bool](https://docs.python.org/3/library/functions.html#bool)*
11062 11068

#### resolve(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), \*, allow_wildcard: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [Resolved](#outrage.mounts.Resolved)
11201 11207

#### below(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Mount](#outrage.mounts.Mount)]
12274 12282

#### directly_below(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Mount](#outrage.mounts.Mount)]
12826 12836

#### segments(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), depth: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Segment](#outrage.mounts.Segment)]
13662 13674

#### children(parent: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Entry](store.md#outrage.store.Entry)]
15088 15102

#### last_child(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)) → [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)
15756 15772

#### shadowing() → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Mount](#outrage.mounts.Mount)]
16684 16702

#### read_only_below(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]
17496 17516

#### store_document(key: [str](https://docs.python.org/3/library/stdtypes.html#str), content: [str](https://docs.python.org/3/library/stdtypes.html#str), format: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, title: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, encoding: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, updated_at: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [str](https://docs.python.org/3/library/stdtypes.html#str)
18198 18220

#### retrieve_document(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, offset: [int](https://docs.python.org/3/library/functions.html#int) = 0, byte_offset: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, length: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, pattern: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, occurrence: [int](https://docs.python.org/3/library/functions.html#int) = 0, max_chars: [int](https://docs.python.org/3/library/functions.html#int) = DEFAULT_MAX_CHARS) → [Excerpt](store.md#outrage.store.Excerpt)
21272 21296

#### exists(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [bool](https://docs.python.org/3/library/functions.html#bool)
22975 23001

#### level_entry(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [Entry](store.md#outrage.store.Entry) | [None](https://docs.python.org/3/library/constants.html#None)
23468 23496

#### descendant_count(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, whole_subtree: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [int](https://docs.python.org/3/library/functions.html#int)
24064 24094

#### latest_change(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, whole_subtree: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)
25810 25842

#### delete(key: [str](https://docs.python.org/3/library/stdtypes.html#str), recursive: [bool](https://docs.python.org/3/library/functions.html#bool) = False, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, unchanged_since: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]
26712 26746

#### list_keys(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Page](store.md#outrage.store.Page)[[Entry](store.md#outrage.store.Entry)]
28767 28803

#### get_documents(subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, max_chars: [int](https://docs.python.org/3/library/functions.html#int) = DEFAULT_BULK_MAX_CHARS, limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, max_total_chars: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Page](store.md#outrage.store.Page)[[Excerpt](store.md#outrage.store.Excerpt)]
29600 29638

#### keys_missing_meta(subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = 'title', limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Page](store.md#outrage.store.Page)[[str](https://docs.python.org/3/library/stdtypes.html#str)]
31788 31828

#### missing_meta_stats(subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, window: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = 'title', sample: [int](https://docs.python.org/3/library/functions.html#int) = 0) → [MissingMeta](store.md#outrage.store.MissingMeta)
32999 33041

#### close() → [None](https://docs.python.org/3/library/constants.html#None)
33960 34004

### *exception* outrage.mounts.ReadOnlyMountError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
34094 34140

### *class* outrage.mounts.Resolved(mount: [Mount](#outrage.mounts.Mount), key: [str](https://docs.python.org/3/library/stdtypes.html#str), outer: [str](https://docs.python.org/3/library/stdtypes.html#str))
34898 34944

#### mount *: [Mount](#outrage.mounts.Mount)*
35237 35283

#### key *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
35284 35330

#### outer *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
35392 35438

#### *property* store *: [Store](store.md#outrage.store.Store)*
35509 35555

#### *property* read_only *: [bool](https://docs.python.org/3/library/functions.html#bool)*
35958 36004

#### writable(action: [str](https://docs.python.org/3/library/stdtypes.html#str) = 'write') → [Resolved](#outrage.mounts.Resolved)
36104 36150

### *class* outrage.mounts.Segment(mount: [Mount](#outrage.mounts.Mount), subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree), key_range: [KeyRange](store.md#outrage.store.KeyRange))
37646 37694

#### mount *: [Mount](#outrage.mounts.Mount)*
38572 38620

#### subtree *: [BoundedSubtree](store.md#outrage.store.BoundedSubtree)*
38619 38667

#### key_range *: [KeyRange](store.md#outrage.store.KeyRange)*
38693 38741

#### *property* store *: [Store](store.md#outrage.store.Store)*
38757 38805

#### resume_from(after: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)) → [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), [bool](https://docs.python.org/3/library/functions.html#bool)]
39107 39155

### *class* outrage.mounts.Spec(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), type: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None)
40592 40642

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*
41438 41488

#### type *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
41521 41571

### outrage.mounts.mount_point(prefix: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, spec: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [str](https://docs.python.org/3/library/stdtypes.html#str)
41733 41783

### outrage.mounts.open_mounts(directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None), specs: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = (), read_only_specs: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = (), \*, root_mount: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [Spec](#outrage.mounts.Spec) | [None](https://docs.python.org/3/library/constants.html#None) = None, log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/library/constants.html#None) = None, attached: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Store](store.md#outrage.store.Store)] = MappingProxyType({})) → [MountedStore](#outrage.mounts.MountedStore)
42511 42563

### outrage.mounts.parse_options(value: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, spec: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Spec](#outrage.mounts.Spec)
46502 46556

### outrage.mounts.parse_spec(spec: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Spec](#outrage.mounts.Spec)]
47814 47870

### outrage.mounts.unparse(spec: [Spec](#outrage.mounts.Spec)) → [str](https://docs.python.org/3/library/stdtypes.html#str)
49105 49163
