import re
from typing import TypeAlias

from bs4 import NavigableString, Tag

NavStr: TypeAlias = (Tag | NavigableString | None)

def extract_int(text):
	match = re.search(r'\d+', str(text))
	if match != None:
		return int(match.group())
	else:
		return None
	
def compile_tag(data: any, tag_label: str, tag_name: str | None = None) -> str:
	# Convert tag name to title case if a separate name is not given
	if tag_name == None:
		tag_name = tag_label.title()
	if data == None:
		return ""
	if isinstance(data, list):
		parsed_data: str = ";\t".join(data)
		return f'<div><span class="meta tag">{tag_name}:</span> {parsed_data}</div>'
	else:
		return f'<div><span class="meta tag">{tag_name}:</span> {str(data)}</div>'

def append(data: NavStr | str, content: NavStr | str) -> str:
	if type(content) != str:
		content = content.prettify()
	if type(data) != str:
		data = data.prettify()
	return content + data