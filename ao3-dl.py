from weasyprint import HTML
from bs4 import BeautifulSoup
import requests
import sys
import re

def extract_int(text):
	match = re.search(r'\d+', str(text))
	if match != None:
		return int(match.group())
	else:
		return None

def get_series_length(id):
	response = requests.get(f"https://archiveofourown.org/series/{id}")
	if response.status_code != 200:
		raise Exception(response.status_code)

	soup = BeautifulSoup(response.text, "html.parser")
	return soup.find("dd", class_="works").text

def prepend(data, content):
	if type(content) != str:
		content = content.prettify()
	if type(data) != str:
		data = data.prettify()
	return data + content

def prep_for_print(content):
	return f'<head><meta charset="utf-8"><link rel="stylesheet" type="text/css" href="style.css"></head><body class="wrapper">{content}</body>'

def get_single_tag(meta, class_):
	return meta.find("dd", class_=class_).text.strip() if meta.find("dd", class_=class_) != None else None
def get_meta_tags(meta, class_):
	tags = []
	element = meta.find("dd", class_=class_)
	if element != None:
		for x in element.find_all("a"):
			tags.append(x.text.strip())
		return tags
	else:
		return None
def get_series(meta):
	element = meta.find("dd", class_="series")
	if element == None:
		return None
	
	series = []
	for tag in element.find_all("span", class_="series"):
		part = extract_int(tag.find("span", class_="position"))
		name = tag.find_all("a")[0 if part == 1 else 1].text
		try:
			length = get_series_length(extract_int(tag.find_all("a")[0 if part == 1 else 1].get("href")))
		except:
			length = None
		series.append(
			{
				"part": part,
				"name": name,
				"length": length
			}
		)

	return series

def get_meta(meta):
	metadata = {
		"series": get_series(meta),
		"rating": get_single_tag(meta, "rating tags"),
		"warning": get_single_tag(meta, "warning tags"),
		"category": get_meta_tags(meta, "category tags"),
		"fandoms": get_meta_tags(meta, "fandom tags"),
		"language": get_single_tag(meta, "language"),
		"published": get_single_tag(meta, "published"),
		"updated": get_single_tag(meta, "status"),
		"words": get_single_tag(meta, "words"),
		"chapters": get_single_tag(meta, "chapters"),
		"fandoms": get_meta_tags(meta, "fandom tags"),
		"relationships": get_meta_tags(meta, "relationship tags"),
		"characters": get_meta_tags(meta, "character tags"),
		"tags": get_meta_tags(meta, "freeform tags")
	}
	return metadata
def compile_tag(meta, tag, tag_name=None):
	if tag_name == None:
		tag_name = tag.title()
	data = meta[tag]
	if data == None:
		return ""
	if isinstance(data, list):
		return f'<div><span class="meta tag">{tag_name}:</span> {", ".join(data)}</div>'
	else:
		return f'<div><span class="meta tag">{tag_name}:</span> {data}</div>'
def compile_series(meta):
	if meta["series"] == None:
		return ""
	
	ret_val = '<div class="series"><ul>'
	for series in meta["series"]:
		length = f' of {series["length"]}' if series["length"] != None else ""
		ret_val += f'<li class="entry"><span class="name">{series["name"]}</span> - Part {series["part"]}{length}</li>'
	
	return ret_val + '</ul></div><hr>'
def build_meta_title(title, series_list):
	if series_list == None or len(series_list) == 0:
		return title
	
	meta_title = f'{title.replace("|", "_")}'
	for series in series_list:
		length = f'/{series["length"]}' if series["length"] != None else ""
		meta_title += f'|{series["name"]}({series["part"]}{length})'
	
	return meta_title

def series_data(list, name):
	for series in list:
		if name == series["name"]:
			return series
	return None

def ao3_dl(response, exp_html=False, series_name=None):
	soup = BeautifulSoup(response.text, "html.parser")

	content = soup.find("div", id="chapters")
	title = soup.find("h2", class_="title heading")
	author = soup.find("h3", class_="byline heading")

	meta = soup.find("dl", class_="work meta group")
	data = get_meta(meta)

	if data["chapters"] == "1/1":
		content = prepend('<div style="page-break-after: always"></div>', content)

	summary = soup.find("div", class_="summary module")
	content = prepend(summary, content)
	content = prepend('<hr>', content)

	content = prepend(
		(
			f'<div class="meta">'
			+ f'<title>{build_meta_title(title.text.strip(), data["series"])}</title>'
			+ f'<meta name="author" content="{author.text.strip()}">'
			+ f'<meta name="description" content="{";".join(data["fandoms"]) if data["fandoms"] != None else ""}">'
			+ f'<meta name="keywords" content="{";".join(data["tags"]) if data["tags"] != None else ""}">'
			+ f'<meta name="dcterms.created" content="{data["published"]}">'
			+ f'<meta name="dcterms.modified" content="{data["updated"]}">'
			+ compile_series(data)
			+ compile_tag(data, "rating")
			+ compile_tag(data, "warning", "Archive Warning")
			+ compile_tag(data, "category")
			+ compile_tag(data, "fandoms")
			+ compile_tag(data, "characters")
			+ compile_tag(data, "relationships")
			+ compile_tag(data, "language")
			+ compile_tag(data, "published")
			+ compile_tag(data, "updated")
			+ compile_tag(data, "words")
			+ compile_tag(data, "tags")
			+ compile_tag(data, "chapters")
			+ '</div>'
		), 
		content
	)

	if author != None or title != None:
		content = prepend('<hr>', content)
		content = prepend('<hr>', content)
	content = prepend(f'<div class="author">{author}</div>' if author != None else "", content)
	content = prepend(f'<div class="title">{title}</div>' if title != None else "", content)
	if author != None or title != None:
		content = prepend('<hr>', content)
	
	active_series = series_data(data["series"], series_name)
	index = str(active_series["part"])
	length = str(active_series["length"])
	series_name = f"{series_name} ({index.zfill(len(length))} of {length}): " if series_name != None else ""

	file_name = series_name + author.text.strip() + " - " + title.text.strip().replace("/", "-")
	result_file = open(f"{file_name}.pdf", "w+b")
	content = prep_for_print(content)
	HTML(string=content).write_pdf(result_file, stylesheets=["style.css"])

	if exp_html:
		with open("out.html", "w") as file:
			file.write(content)
			file.close()

	print(f"Finished downloading '{title.text.strip()}' by {author.text.strip()}")

def get_series_works(url):
	response = requests.get(url)
	if response.status_code != 200:
		raise Exception(response.status_code)
	
	works = []
	
	soup = BeautifulSoup(response.text, "html.parser")
	for li in soup.find("ul", class_="series work index group").find_all(recursive=False):
		id = li.get("id").replace("work_", "")
		works.append(f"https://archiveofourown.org/works/{id}?view_full_work=true")
	
	return (works, soup.find("h2", class_="heading").text.strip())

def get_dl_loc(url):
	id = extract_int(url)

	if "works/" in url or url.isdigit():
		return {
			"works": [ f"https://archiveofourown.org/works/{id}?view_full_work=true" ],
			"series": None
		}
	elif "series/" in url:
		works = get_series_works(url)
		return {
			"works": works[0],
			"series": works[1]
		}

	return None

if __name__ == "__main__":
	if len(sys.argv) < 2:
		print("No work given")
		exit()

	id = sys.argv[1]
	match = re.search(r"((?:https:\/\/)?archiveofourown\.org\/(?:works|series)\/\d+|\d+)", id)

	if match == None:
		print("Invalid link")
		exit()

	src = get_dl_loc(match.group(0))

	for work in src["works"]:
		try:
			response = requests.get(work)
			if response.status_code == 200:
				if src["series"] != None:
					print(f"""Downloading '{src["series"]}':""")
				ao3_dl(response, series_name=src["series"])
			else:
				print(response.status_code)
		except Exception as ex:
			print(f"Error: {ex}")
