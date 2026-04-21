from tracely360.naming import safe_note_name, safe_wiki_filename, strip_diacritics


def test_safe_note_name_strips_invalid_chars_and_markdown_suffix():
    assert safe_note_name("  CLAUDE.md\n") == "CLAUDE"
    assert safe_note_name("foo/bar:baz") == "foobarbaz"


def test_safe_wiki_filename_preserves_existing_transform_rules():
    assert safe_wiki_filename("Parsing Layer/Render:Phase") == "Parsing_Layer-Render-Phase"


def test_strip_diacritics_normalizes_labels():
    assert strip_diacritics("caf\u00e9") == "cafe"