from weasyprint import HTML
from bs4 import BeautifulSoup
import requests
import sys


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

def get_meta(meta):
	metadata = {
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

def ao3_dl(response):
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
			+ f'<title>{title.text.strip()}</title>'
			+ f'<meta name="author" content="{author.text.strip()}">'
			+ f'<meta name="description" content="{";".join(data["fandoms"])}">'
			+ f'<meta name="keywords" content="{";".join(data["tags"])}">'
			+ f'<meta name="dcterms.created" content="{data["published"]}">'
			+ f'<meta name="dcterms.modified" content="{data["updated"]}">'
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
	
	file_name = f"{author.text.strip()} - {title.text.strip()}"
	result_file = open(f"{file_name}.pdf", "w+b")
	content = prep_for_print(content)
	HTML(string=content).write_pdf(result_file, stylesheets=["style.css"], custom_metadata=True)

	with open("out.html", "w") as file:
		file.write(content)
		file.close()

	print(f"Finished downloading '{title.text.strip()}' by {author.text.strip()}")


if __name__ == "__main__":
	if len(sys.argv) < 2:
		print("No work ID given")
		exit()

	id = sys.argv[1]

	if id.isdigit():
		src = f"https://archiveofourown.org/works/{id}?view_full_work=true"
	else:
		print("Input must be the ID of the work")
		exit()

	try:
		response = requests.get(src)
		if response.status_code == 200:
			ao3_dl(response)
		else:
			print(response.status_code)
	except Exception as ex:
		print(f"Error: {ex}")
