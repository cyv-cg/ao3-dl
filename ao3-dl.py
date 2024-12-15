from bs4 import BeautifulSoup
from weasyprint import HTML
from ebooklib import epub
from pathlib import Path
import traceback
import argparse
import fitz
import re
import os

from models import Series, Work, User
from helpers import NavStr
import helpers

LOCAL_DIR = Path(__file__).resolve().parent

def get_thumbnail(directory: str, file_name: str) -> str:
	pdf_path: str = f"{directory}/{file_name}.pdf"
	pdf_document: fitz.Document = fitz.open(pdf_path)

	# Select the first page (page numbering starts from 0)
	page: fitz.Page = pdf_document.load_page(0)

	# Save the page as a thumbnail image
	pix = page.get_pixmap(dpi=100)
	thumbnail_path = f"{directory}/thumbnail.jpg"
	pix.save(thumbnail_path)

	return thumbnail_path

def prep_for_print(content: NavStr, soup: BeautifulSoup, work: Work, cover_data: str) -> str:
	content: NavStr = soup.find("div", id="chapters")
	content = helpers.append(
		content,
		cover_data
	)
	if work.is_single_chapter:
		content = helpers.append('<div style="page-break-after: always"></div>', content)

	return f'<head><meta charset="utf-8"><link rel="stylesheet" type="text/css" href="{LOCAL_DIR}/style.css"></head><body class="wrapper">{content}</body>'

def print_series(data: list[Work.SeriesMetadata] | None) -> str:
	if data == None:
		return ""
	
	ret_val: str = '<div class="series"><ul>'
	for series in data:
		length: str = f' of {series.length}' if series.length != None else ""
		ret_val += f'<li class="entry"><span class="name">{series.title}</span> - Part {series.part}{length}</li>'
	
	return ret_val + '</ul></div><hr>'

def ao3_dl(work: Work, args: argparse.Namespace, series: Series = None) -> None:
	soup: BeautifulSoup = BeautifulSoup(work.content, "html.parser")

	header: str = f"""
		{'<hr>' if work.author != None or work.title != None else ''}
		{f'<div class="title">{work.title}</div>' if work.title != None else ''}
		{f'<div class="author">{work.author}</div>' if work.author != None else ''}
		{'<hr><hr>' if work.author != None or work.title != None else ''}
	"""
	meta_tags: str = f"""
		<div class="meta"">
			{f'<title>{work.meta_title()}</title>'}
			{f'<meta name="author" content="{work.author}">'}
			{f'<meta name="description" content="{";".join(work.fandoms) if work.fandoms != None else ""}">'}
			{f'<meta name="keywords" content="{";".join(work.tags) if work.tags != None else ""}">'}
			{f'<meta name="dcterms.created" content="{work.published}">'}
			{f'<meta name="dcterms.modified" content="{work.updated}">'}
			{print_series(work.series)}
			{helpers.compile_tag(work.rating, "rating")}
			{helpers.compile_tag(work.warning, "warning", "Archive Warning")}
			{helpers.compile_tag(work.category, "category")}
			{helpers.compile_tag(work.fandoms, "fandoms")}
			{helpers.compile_tag(work.characters, "characters")}
			{helpers.compile_tag(work.relationships, "relationships")}
			{helpers.compile_tag(work.language, "language")}
			{helpers.compile_tag(work.published, "published")}
			{helpers.compile_tag(work.updated, "updated")}
			{helpers.compile_tag(work.words, "words")}
			{helpers.compile_tag(work.tags, "tags")}
			{helpers.compile_tag(work.chapters, "chapters")}
		</div>
	"""
	summary: str = f"""
		<hr>
		{soup.find("div", class_="summary module").prettify()}
	"""
	cover_info = header + meta_tags + summary
	

	# Building output file name
	active_series: Work.SeriesMetadata = work.get_series_data(series.title) if series != None else None
	series_prefix: str = ""
	if active_series != None:
		index: str = str(active_series.part)
		length: str = str(active_series.length)
		series_prefix = f"({index.zfill(len(length))} of {length}) " if series.title != None else ""

	file_name: str = series_prefix + work.author + " - " + work.title.replace("/", "-")

	directory = series.title if series != None else work.title.replace("/", "-")
	os.makedirs(directory, exist_ok=True)

	# Printing

	# Always start by printing a pdf to get a thumbnail for the epub
	print_pdf(soup, work, cover_info, directory, file_name)

	if args.html:
		print_html(soup, work, cover_info, directory, file_name)
	if args.epub:
		thumbnail = get_thumbnail(directory, file_name)
		# Print the epub
		print_epub(cover_info, work, series, directory, file_name, thumbnail)
		# Delete the used thumbnail
		os.remove(thumbnail)
	if not args.pdf:
		# Delete the pdf if it's not wanted
		os.remove(f"{directory}/{file_name}.pdf")

def print_pdf(soup: BeautifulSoup, work: Work, cover_data: str, out_dir: str, out_file: str) -> None:
	content: str = prep_for_print(soup.find("div", id="chapters"), soup, work, cover_data)
	result_file = open(f"{out_dir}/{out_file}.pdf", "w+b")
	HTML(string=content).write_pdf(result_file, stylesheets=[f"{Path(__file__).resolve().parent}/style.css"])

def print_html(soup: BeautifulSoup, work: Work, cover_data: str, out_dir: str, out_file: str) -> None:
	content: str = prep_for_print(soup.find("div", id="chapters"), soup, work, cover_data)
	file = open(f"{out_dir}/{out_file}.html", "w")
	file.write(content)
	file.close()

def print_epub(cover_data: str, work: Work, series: Series, out_dir: str, out_file: str, thumbnail: str) -> None:
	# Initialize with metadata
	book: epub.EpubBook = epub.EpubBook()
	book.set_identifier(str(work.id))
	book.set_title(work.title)
	book.set_language(work.language)
	book.add_author(work.author)

	book.set_cover("thumbnail.jpg", open(thumbnail, "rb").read())

	# Define css style
	style = ""
	with open(f"{LOCAL_DIR}/style.css", "r") as file:
		style = file.read()
		file.close()

	# Add css file
	nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style)
	book.add_item(nav_css)

	# Custom cover
	cover = epub.EpubHtml(file_name="cover_meta.xhtml", content=cover_data)
	cover.add_item(nav_css)
	book.add_item(cover)

	chapters = []
	# Create chapters
	for i in range(len(work.chapter_list)):
		# Get the title from the work
		title: str | None = work.chapter_list[i].title
		# Create and fetch content
		chapter: epub.EpubHtml = epub.EpubHtml(title=title, file_name=f"chap_{str(i + 1).zfill(3)}.xhtml", lang=work.language)
		chapter.set_content(work.chapter_list[i].content)
		# Include the css in the chapter
		chapter.add_item(nav_css)
		# Set title
		chapter.title = title
		# Add to the book
		book.add_item(chapter)
		chapters.append(chapter)

	# Add all content to the spine
	book.spine = ["cover", cover]
	for chapter in chapters:
		book.spine.append(chapter)
	
	book.add_item(epub.EpubNcx())
	book.add_item(epub.EpubNav())

	epub.write_epub(f"{out_dir}/{out_file}.epub", book)

def parse_works(url: str) -> Work | Series | User | None:
	id = helpers.extract_int(url)

	if "works/" in url or url.isdigit():
		return Work(id)
	elif "series/" in url:
		return Series(id)
	elif "users/" in url:
		username: str = url.split("/")[1]
		return User(username)

	return None

def dl_work(work: Work, args: argparse.Namespace, series: Series = None) -> None:
	try:
		if work.restricted:
			raise Exception(f"{args.url} is restricted, you'll need to log in and download manually :(")
		print(f"""Downloading '{work.title}'""")
		ao3_dl(work=work, series=series, args=args)
	except Exception as ex:
		print(f"Error: {ex}\n{traceback.print_exc()}")

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Utility for downloading a work or series from archiveofourown.org.')

	parser.add_argument('url', type=str, help='The URL of the work or series to download. Also accepts an ID and parses it as a work.')

	parser.add_argument('--pdf', action='store_true', help='Will export the parsed work as a pdf.')
	parser.add_argument('--epub', action='store_true', help='Will export the parsed work as an epub.')
	parser.add_argument('--html', action='store_true', help='Will export the parsed work as raw html.')

	args = parser.parse_args()

	if args.url == None:
		print("No work given")
		exit()
	
	if not (args.pdf or args.epub or args.html):
		print("Select at least 1 output format: --pdf --epub --html")
		exit()

	match: re.Match[str] = re.search(helpers.MATCH_REGEX, args.url)

	if match == None:
		print(f"Invalid link: {args.url}")
		exit()

	result: Series | Work | User | None = parse_works(match.group(0))
	if isinstance(result, Series):
		series: Series = result
		print(f"""Downloading '{series.title}'""")
		for work in series.works:
			dl_work(work=work, series=series, args=args)
	elif isinstance(result, Work):
		work: Work = result
		dl_work(work=work, args=args)
	elif isinstance(result, User):
		user: User = result
		print(f"""Downloading all works from {user.username}""")
		for work in user.works:
			dl_work(work=work, args=args)
	
	print("Finished")
