
import re
from typing import Any, Optional, Union, TypeAlias

from bs4 import NavigableString, Tag

NavStr: TypeAlias = Union[Tag, NavigableString, None]

MATCH_REGEX: str = r"((?:https:\/\/)?archiveofourown\.org\/((?:works|series)\/\d+|\d+)|users\/(.+))|(\d+)"

def extract_int(text: str) -> Optional[int]:
	match = re.search(r'\d+', str(text))
	if match is not None:
		return int(match.group())
	return None

def compile_tag(data: Any, tag_label: str, tag_name: Optional[str] = None) -> str:
	# Convert tag name to title case if a separate name is not given
	if tag_name is None:
		tag_name = tag_label.title()
	if data is None:
		return ""
	if isinstance(data, list):
		parsed_data: str = ";\t".join(data)
		return f'<div><span class="meta tag">{tag_name}:</span> {parsed_data}</div>'

	return f'<div><span class="meta tag">{tag_name}:</span> {str(data)}</div>'

def append(data: Union[NavStr, str], content: Union[NavStr, str]) -> Optional[str]:
	if content is None and data is not None:
		return data if isinstance(data, str) else data.prettify()
	if data is None and content is not None:
		return content if isinstance(content, str) else content.prettify()

	if content is not None and data is not None:
		if not isinstance(content, str):
			content = content.prettify()
		if not isinstance(data, str):
			data = data.prettify()

		return content + data

	return None
