# Document contents
0 0

### *class* outrage.contents.ContentsResult(source_key: str, metadata_key: str, headings: int, source_characters: int, source_bytes: int, characters: int)
543 543

#### source_key *: str*
1168 1168

#### metadata_key *: str*
1297 1297

#### headings *: int*
1439 1439

#### source_characters *: int*
1549 1549

#### source_bytes *: int*
1695 1695

#### characters *: int*
1907 1907

### outrage.contents.make_contents(opened: Store, key: str, \*, metadata_name: str = 'contents', strip_links: bool = True) → ContentsResult
2057 2057

### outrage.contents.render_contents(markdown: str, \*, strip_links: bool = True) → str
3265 3267

### outrage.contents.render_html_contents(html: str) → str
4325 4329
