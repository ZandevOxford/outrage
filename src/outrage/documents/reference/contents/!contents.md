# Document contents
0 0 1

### *class* outrage.contents.ContentsResult(source_key: str, metadata_key: str, headings: int, source_characters: int, source_bytes: int, characters: int)
550 550 12

#### source_key *: str*
1182 1182 18

#### metadata_key *: str*
1312 1312 22

#### headings *: int*
1455 1455 26

#### source_characters *: int*
1566 1566 30

#### source_bytes *: int*
1713 1713 34

#### characters *: int*
1926 1926 39

### outrage.contents.make_contents(opened: Store, key: str, \*, metadata_name: str = 'contents', strip_links: bool = True) → ContentsResult
2077 2077 43

### outrage.contents.render_contents(markdown: str, \*, strip_links: bool = True) → str
3312 3314 61

### outrage.contents.render_html_contents(html: str) → str
4404 4408 78
