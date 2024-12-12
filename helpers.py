import re

from models import Work

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
		return f'<div><span class="meta tag">{tag_name}:</span> {", ".join(data)}</div>'
	else:
		return f'<div><span class="meta tag">{tag_name}:</span> {str(data)}</div>'
def compile_series(data: list[Work.SeriesMetadata] | None) -> str:
	if data == None:
		return ""
	
	ret_val: str = '<div class="series"><ul>'
	for series in data:
		length: str = f' of {series.length}' if series.length != None else ""
		ret_val += f'<li class="entry"><span class="name">{series.title}</span> - Part {series.part}{length}</li>'
	
	return ret_val + '</ul></div><hr>'
def build_meta_title(title: str, series_list: list[Work.SeriesMetadata] | None) -> str:
	if series_list == None or len(series_list) == 0:
		return title
	
	meta_title: str = f'{title.replace("|", "_")}'
	for series in series_list:
		meta_title += f"|{series.title}({series.part}/{series.length})"
	
	return meta_title