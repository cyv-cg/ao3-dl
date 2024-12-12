from bs4 import BeautifulSoup
from weasyprint import HTML
from pathlib import Path
import traceback
import requests
import argparse
import re
import os

from models import NavStr, Series, Work
import helpers

def prepend(data: NavStr, content: NavStr) -> NavStr:
	if type(content) != str:
		content = content.prettify()
	if type(data) != str:
		data = data.prettify()
	return data + content

def prep_for_print(content):
	return f'<head><meta charset="utf-8"><link rel="stylesheet" type="text/css" href="{Path(__file__).resolve().parent}/style.css"></head><body class="wrapper">{content}</body>'

def ao3_dl(response: requests.Response, work: Work, exp_html: bool = False, series: Series = None) -> None:
	soup: BeautifulSoup = BeautifulSoup(response.text, "html.parser")

	content: NavStr = soup.find("div", id="chapters")
	
	if work.is_single_chapter:
		content = prepend('<div style="page-break-after: always"></div>', content)

	summary: NavStr = soup.find("div", class_="summary module")
	content = prepend(summary, content)
	content = prepend('<hr>', content)

	content = prepend(
		(
			f'<div class="meta">'
			+ f'<title>{helpers.build_meta_title(work.title, work.series)}</title>'
			+ f'<meta name="author" content="{work.author}">'
			+ f'<meta name="description" content="{";".join(work.fandoms) if work.fandoms != None else ""}">'
			+ f'<meta name="keywords" content="{";".join(work.tags) if work.tags != None else ""}">'
			+ f'<meta name="dcterms.created" content="{work.published}">'
			+ f'<meta name="dcterms.modified" content="{work.updated}">'
			+ helpers.compile_series(work.series)
			+ helpers.compile_tag(work.rating, "rating")
			+ helpers.compile_tag(work.warning, "warning", "Archive Warning")
			+ helpers.compile_tag(work.category, "category")
			+ helpers.compile_tag(work.fandoms, "fandoms")
			+ helpers.compile_tag(work.characters, "characters")
			+ helpers.compile_tag(work.relationships, "relationships")
			+ helpers.compile_tag(work.language, "language")
			+ helpers.compile_tag(work.published, "published")
			+ helpers.compile_tag(work.updated, "updated")
			+ helpers.compile_tag(work.words, "words")
			+ helpers.compile_tag(work.tags, "tags")
			+ helpers.compile_tag(work.chapters, "chapters")
			+ '</div>'
		), 
		content
	)

	if work.author != None or work.title != None:
		content = prepend('<hr>', content)
		content = prepend('<hr>', content)
	content = prepend(f'<div class="author">{work.author}</div>' if work.author != None else "", content)
	content = prepend(f'<div class="title">{work.title}</div>' if work.title != None else "", content)
	if work.author != None or work.title != None:
		content = prepend('<hr>', content)
	
	
	active_series: Work.SeriesMetadata = work.get_series_data(series.title) if series != None else None
	series_prefix: str = ""
	if active_series != None:
		index: str = str(active_series.part)
		length: str = str(active_series.length)
		series_prefix = f"({index.zfill(len(length))} of {length}) " if series.title != None else ""

	file_name: str = series_prefix + work.author + " - " + work.title.replace("/", "-")

	directory = series.title if series != None else work.title.replace("/", "-")
	os.makedirs(directory, exist_ok=True)

	result_file = open(f"{directory}/{file_name}.pdf", "w+b")
	content = prep_for_print(content)
	HTML(string=content).write_pdf(result_file, stylesheets=[f"{Path(__file__).resolve().parent}/style.css"])

	if exp_html:
		with open(f"{directory}/{file_name}.html", "w") as file:
			file.write(content)
			file.close()

	print(f"Finished downloading '{work.title}' by {work.author}")

def parse_works(url: str) -> tuple[Work | None, Series | None] | None:
	id = helpers.extract_int(url)

	if "works/" in url or url.isdigit():
		return Work(id), None
	elif "series/" in url:
		return None, Series(id)

	return None

def dl_work(work: Work, series: Series = None, exp_html: bool = False) -> None:
	try:
		response = requests.get(work.url())
		if response.status_code == 200:
			if "restricted=true" in response.url:
				raise Exception(f"{args.url} is restricted, you'll need to log in and download manually :(")
			ao3_dl(response=response, work=work, series=series, exp_html=exp_html)
		else:
			print(response.status_code)
	except Exception as ex:
		print(f"Error: {ex}\n{traceback.print_exc()}")

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Utility for downloading a work or series from archiveofourown.org.')

	parser.add_argument('url', type=str, help='The URL of the work or series to download. Also accepts an ID and parses it as a work.')
	parser.add_argument('--export-as-html', action='store_true', help='Will export the parsed work as raw html as well as a pdf.')

	args = parser.parse_args()

	if args.url == None:
		print("No work given")
		exit()

	match: re.Match[str] = re.search(r"((?:https:\/\/)?archiveofourown\.org\/(?:works|series)\/\d+|\d+)", args.url)

	if match == None:
		print("Invalid link")
		exit()

	work, series = parse_works(match.group(0))
	if series != None:
		print(f"""Downloading '{series.title}':""")
		for work in series.works:
			dl_work(work=work, series=series, exp_html=args.export_as_html)
	elif work != None:
		print(f"""Downloading '{work.title}':""")
		dl_work(work=work, exp_html=args.export_as_html)