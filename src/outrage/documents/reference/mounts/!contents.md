# outrage.mounts
0 0

### outrage.mounts.MOUNT_KIND *= 'mount'*
2172 2172

### outrage.mounts.OPTIONS *= ('type',)*
2564 2564

### outrage.mounts.OPTION_ASSIGNMENT *= '='*
2883 2883

### outrage.mounts.OPTION_DELIMITER *= ','*
3146 3146

### outrage.mounts.READ_ONLY_MOUNT_KIND *= 'read-only mount'*
3922 3922

### outrage.mounts.ROOT_KIND *= 'root'*
4728 4728

### outrage.mounts.SPEC_DELIMITER *= '='*
5130 5130

### outrage.mounts.TYPE_OPTION *= 'type'*
5443 5443

### *class* outrage.mounts.Mount(prefix: [str](https://docs.python.org/3/library/stdtypes.html#str), store: [Store](store.md#outrage.store.Store), read_only: [bool](https://docs.python.org/3/library/functions.html#bool) = False)
6141 6141

#### prefix *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
6490 6490

#### store *: [Store](store.md#outrage.store.Store)*
6639 6639

#### read_only *: [bool](https://docs.python.org/3/library/functions.html#bool)*
6693 6693

#### *property* kind *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
6986 6986

#### *property* name *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
7111 7111

#### *property* is_root *: [bool](https://docs.python.org/3/library/functions.html#bool)*
7263 7263

#### inner(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)
7354 7354

#### outer(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)
7627 7629

### *exception* outrage.mounts.MountError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
8552 8556

### *class* outrage.mounts.MountedStore(stores: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Store](store.md#outrage.store.Store)], \*, read_only: [Collection](https://docs.python.org/3/library/collections.abc.html#collections.abc.Collection)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = ())
8938 8942

#### writable *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[bool](https://docs.python.org/3/library/functions.html#bool)]* *= True*
10181 10185

#### backend_name *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[str](https://docs.python.org/3/library/stdtypes.html#str)]* *= 'mounts'*
10591 10595

#### *classmethod* single(store: [Store](store.md#outrage.store.Store)) → [MountedStore](#outrage.mounts.MountedStore)
10904 10908

#### remounted(\*, mount: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Store](store.md#outrage.store.Store)] = MappingProxyType({}), read_only: [Collection](https://docs.python.org/3/library/collections.abc.html#collections.abc.Collection)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = (), unmount: [Collection](https://docs.python.org/3/library/collections.abc.html#collections.abc.Collection)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = ()) → [MountedStore](#outrage.mounts.MountedStore)
11271 11277

#### *property* root *: [Mount](#outrage.mounts.Mount)*
13579 13587

#### *property* read_only *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Mount](#outrage.mounts.Mount)]*
14001 14009

#### *property* multiple *: [bool](https://docs.python.org/3/library/functions.html#bool)*
14171 14179

#### resolve(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), \*, allow_wildcard: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [Resolved](#outrage.mounts.Resolved)
14310 14318

#### below(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Mount](#outrage.mounts.Mount)]
15383 15393

#### directly_below(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Mount](#outrage.mounts.Mount)]
15935 15947

#### segments(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), depth: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Segment](#outrage.mounts.Segment)]
16771 16785

#### children(parent: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Entry](store.md#outrage.store.Entry)]
18197 18213

#### last_child(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)) → [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)
18865 18883

#### shadowing() → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Mount](#outrage.mounts.Mount)]
19793 19813

#### read_only_below(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]
20605 20627

#### store_document(key: [str](https://docs.python.org/3/library/stdtypes.html#str), content: [str](https://docs.python.org/3/library/stdtypes.html#str), format: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, title: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, encoding: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, updated_at: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [str](https://docs.python.org/3/library/stdtypes.html#str)
21307 21331

#### retrieve_document(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, offset: [int](https://docs.python.org/3/library/functions.html#int) = 0, byte_offset: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, length: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, pattern: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, occurrence: [int](https://docs.python.org/3/library/functions.html#int) = 0, max_chars: [int](https://docs.python.org/3/library/functions.html#int) = DEFAULT_MAX_CHARS) → [Excerpt](store.md#outrage.store.Excerpt)
24381 24407

#### exists(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [bool](https://docs.python.org/3/library/functions.html#bool)
26084 26112

#### level_entry(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [Entry](store.md#outrage.store.Entry) | [None](https://docs.python.org/3/library/constants.html#None)
26577 26607

#### descendant_count(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, whole_subtree: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [int](https://docs.python.org/3/library/functions.html#int)
27173 27205

#### latest_change(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, whole_subtree: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)
28919 28953

#### delete(key: [str](https://docs.python.org/3/library/stdtypes.html#str), recursive: [bool](https://docs.python.org/3/library/functions.html#bool) = False, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, unchanged_since: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]
29821 29857

#### list_keys(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Page](store.md#outrage.store.Page)[[Entry](store.md#outrage.store.Entry)]
31876 31914

#### get_documents(subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, max_chars: [int](https://docs.python.org/3/library/functions.html#int) = DEFAULT_BULK_MAX_CHARS, limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, max_total_chars: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Page](store.md#outrage.store.Page)[[Excerpt](store.md#outrage.store.Excerpt)]
32709 32749

#### keys_missing_meta(subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = 'title', limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Page](store.md#outrage.store.Page)[[str](https://docs.python.org/3/library/stdtypes.html#str)]
34897 34939

#### missing_meta_stats(subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, window: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = 'title', sample: [int](https://docs.python.org/3/library/functions.html#int) = 0) → [MissingMeta](store.md#outrage.store.MissingMeta)
36108 36152

#### close() → [None](https://docs.python.org/3/library/constants.html#None)
37069 37115

### *exception* outrage.mounts.ReadOnlyMountError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
37203 37251

### *class* outrage.mounts.Resolved(mount: [Mount](#outrage.mounts.Mount), key: [str](https://docs.python.org/3/library/stdtypes.html#str), outer: [str](https://docs.python.org/3/library/stdtypes.html#str))
38007 38055

#### mount *: [Mount](#outrage.mounts.Mount)*
38346 38394

#### key *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
38393 38441

#### outer *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
38501 38549

#### *property* store *: [Store](store.md#outrage.store.Store)*
38618 38666

#### *property* read_only *: [bool](https://docs.python.org/3/library/functions.html#bool)*
39067 39115

#### writable(action: [str](https://docs.python.org/3/library/stdtypes.html#str) = 'write') → [Resolved](#outrage.mounts.Resolved)
39213 39261

### *class* outrage.mounts.Segment(mount: [Mount](#outrage.mounts.Mount), subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree), key_range: [KeyRange](store.md#outrage.store.KeyRange))
40755 40805

#### mount *: [Mount](#outrage.mounts.Mount)*
41681 41731

#### subtree *: [BoundedSubtree](store.md#outrage.store.BoundedSubtree)*
41728 41778

#### key_range *: [KeyRange](store.md#outrage.store.KeyRange)*
41802 41852

#### *property* store *: [Store](store.md#outrage.store.Store)*
41866 41916

#### resume_from(after: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)) → [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), [bool](https://docs.python.org/3/library/functions.html#bool)]
42216 42266

### *class* outrage.mounts.Spec(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), type: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None)
43701 43753

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*
44547 44599

#### type *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
44630 44682

### outrage.mounts.mount_point(prefix: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, spec: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [str](https://docs.python.org/3/library/stdtypes.html#str)
44842 44894

### outrage.mounts.open_mounts(directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None), specs: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = (), read_only_specs: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = (), \*, root_mount: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [Spec](#outrage.mounts.Spec) | [None](https://docs.python.org/3/library/constants.html#None) = None, log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/library/constants.html#None) = None, attached: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Store](store.md#outrage.store.Store)] = MappingProxyType({})) → [MountedStore](#outrage.mounts.MountedStore)
45620 45674

### outrage.mounts.parse_options(value: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, spec: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Spec](#outrage.mounts.Spec)
49611 49667

### outrage.mounts.parse_spec(spec: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Spec](#outrage.mounts.Spec)]
50923 50981

### outrage.mounts.unparse(spec: [Spec](#outrage.mounts.Spec)) → [str](https://docs.python.org/3/library/stdtypes.html#str)
52214 52274
