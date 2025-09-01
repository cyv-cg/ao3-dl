
import traceback
import argparse
import json
import re
import os
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Union, Any

from bs4 import BeautifulSoup, Tag
from weasyprint import HTML # type: ignore
import ebookmeta # type: ignore
from ebooklib import epub # type: ignore
import fitz # type: ignore

from models import Series, Work, User
from helpers import NavStr
import helpers

LOCAL_DIR: Path = Path(__file__).resolve().parent

@dataclass
class Options:
	url: str
	pdf: Optional[bool]
	epub: Optional[bool]
	html: Optional[bool]

def _get_thumbnail(directory: str, file_name: str) -> str:
	pdf_path: str = f"{directory}/{file_name}.pdf"
	pdf_document: fitz.Document = fitz.open(pdf_path)

	# Select the first page (page numbering starts from 0)
	page: fitz.Page = pdf_document.load_page(0)

	# Save the page as a thumbnail image
	pix = page.get_pixmap(dpi=100)
	thumbnail_path = f"{directory}/thumbnail.jpg"
	pix.save(thumbnail_path)

	return thumbnail_path

def _prep_for_print(content: NavStr, soup: BeautifulSoup, work: Work, cover_data: str) -> str:
	chapters: NavStr = soup.find("div", id="chapters")

	new_content: Optional[str] = chapters.prettify() if isinstance(chapters, Tag) else None
	new_content = helpers.append(
		content,
		cover_data
	)
	if work.is_single_chapter:
		new_content = helpers.append('<div style="page-break-after: always"></div>', new_content)

	return f'<head><meta charset="utf-8"><link rel="stylesheet" type="text/css" href="{LOCAL_DIR}/style.css"></head><body class="wrapper">{new_content}</body>'

def _print_series(data: Optional[list[Work.SeriesMetadata]]) -> str:
	if data is None:
		return ""

	ret_val: str = '<div class="series"><ul>'
	for series in data:
		length: str = f' of {series.length}' if series.length is not None else ""
		ret_val += f'<li class="entry"><span class="name">{series.title}</span> - Part {series.part}{length}</li>'

	return ret_val + '</ul></div><hr>'

def ao3_dl(work: Work, args: Options, series: Optional[Series]) -> None:
	soup: BeautifulSoup = BeautifulSoup(work.content, "html.parser")

	header: str = f"""
		{'<hr>' if work.author is not None or work.title is not None else ''}
		{f'<div class="title">{work.title}</div>' if work.title is not None else ''}
		{f'<div class="author">{work.author}</div>' if work.author is not None else ''}
		{'<hr><hr>' if work.author is not None or work.title is not None else ''}
	"""
	meta_tags: str = f"""
		<div class="meta">
			{f'<title>{work.meta_title()}</title>'}
			{f'<meta name="author" content="{work.author}">'}
			{f'<meta name="description" content="{";".join(work.fandoms) if work.fandoms is not None else ""}">'}
			{f'<meta name="keywords" content="{";".join(work.tags) if work.tags is not None else ""}">'}
			{_print_series(work.series)}
			{helpers.compile_tag(work.rating, "rating")}
			{helpers.compile_tag(work.warning, "warning", "Archive Warning")}
			{helpers.compile_tag(work.category, "category")}
			{helpers.compile_tag(work.fandoms, "fandoms")}
			{helpers.compile_tag(work.characters, "characters")}
			{helpers.compile_tag(work.relationships, "relationships")}
			{helpers.compile_tag(work.language, "language")}
			{helpers.compile_tag(work.published.strftime("%d %b %Y"), "published")}
			{helpers.compile_tag(work.updated.strftime("%d %b %Y"), "updated") if work.updated is not None else ""}
			{helpers.compile_tag(work.words, "words")}
			{helpers.compile_tag(work.tags, "tags")}
			{helpers.compile_tag(work.chapters, "chapters")}
		</div>
	"""
	summary_element: NavStr = soup.find("div", class_="summary module")
	summary: str = ""
	if isinstance(summary_element, Tag):
		summary = f"""
			<hr>
			{summary_element.prettify()}
		"""
	cover_info = header + meta_tags + summary


	# Building output file name
	active_series: Optional[Work.SeriesMetadata] = work.get_series_data(series.title) if series is not None else None
	series_prefix: str = ""
	if active_series is not None:
		index: str = str(active_series.part)
		length: str = str(active_series.length)
		series_prefix = f"({index.zfill(len(length))} of {length}) " if (series.title if series is not None else None) is not None else ""

	file_name: str = series_prefix + work.author + " - " + work.title.replace("/", "-")

	directory = series.title.replace("/", "-") if series is not None else work.title.replace("/", "-")
	os.makedirs(directory, exist_ok=True)

	# Printing

	# Always start by printing a pdf to get a thumbnail for the epub
	print_pdf(soup, work, cover_info, directory, file_name)

	if args.html:
		print_html(soup, work, cover_info, directory, file_name)
	if args.epub:
		thumbnail = _get_thumbnail(directory, file_name)
		# Print the epub
		print_epub(cover_info, work, series, directory, file_name, thumbnail)
		# Delete the used thumbnail
		os.remove(thumbnail)
	if not args.pdf:
		# Delete the pdf if it's not wanted
		os.remove(f"{directory}/{file_name}.pdf")

def print_pdf(soup: BeautifulSoup, work: Work, cover_data: str, out_dir: str, out_file: str) -> None:
	content: str = _prep_for_print(soup.find("div", id="chapters"), soup, work, cover_data)
	result_file = open(f"{out_dir}/{out_file}.pdf", "w+b")
	HTML(string=content).write_pdf(result_file, stylesheets=[f"{Path(__file__).resolve().parent}/style.css"])

def print_html(soup: BeautifulSoup, work: Work, cover_data: str, out_dir: str, out_file: str) -> None:
	content: str = _prep_for_print(soup.find("div", id="chapters"), soup, work, cover_data)
	with open(f"{out_dir}/{out_file}.html", "w", encoding="utf-8") as file:
		file.write(content)

def print_epub(cover_data: str, work: Work, series: Optional[Series], out_dir: str, out_file: str, thumbnail: str) -> None:
	# Initialize with metadata
	book: epub.EpubBook = epub.EpubBook()
	book.set_identifier(str(work.id))
	book.set_title(work.title)
	book.set_language(work.language)
	book.add_author(work.author)
	book.add_metadata("DC", "date", work.published.isoformat())

	with open(thumbnail, "rb") as f:
		book.set_cover("thumbnail.jpg", f.read(), create_page=False)

	# Define css style
	style = ""
	with open(f"{LOCAL_DIR}/style.css", "r", encoding="utf-8") as file:
		style = file.read()
		file.close()

	# Add css file
	nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style)
	book.add_item(nav_css)

	# Custom cover
	cover = epub.EpubHtml(file_name="cover_meta.xhtml", uid="cover_meta", content=cover_data)
	cover.add_item(nav_css)
	book.add_item(cover)

	chapters = []
	# Create chapters
	# for i in range(len(work.chapter_list)):
	for i, _ in enumerate(work.chapter_list):
		# Get the title from the work
		title: str | None = work.chapter_list[i].title
		# Create and fetch content
		chapter: epub.EpubHtml = epub.EpubHtml(title=title, uid=f"chap_{str(i + 1).zfill(3)}", file_name=f"chap_{str(i + 1).zfill(3)}.xhtml", lang=work.language)
		chapter.set_content(work.chapter_list[i].content)
		# Include the css in the chapter
		chapter.add_item(nav_css)
		# Set title
		chapter.title = title
		# Add to the book
		book.add_item(chapter)
		chapters.append(chapter)

	# Add all content to the spine
	book.spine = [cover]
	for chapter in chapters:
		book.spine.append(chapter)

	book.add_item(epub.EpubNcx())
	book.add_item(epub.EpubNav())

	epub_title: str = f"{out_dir}/{out_file}.epub"
	epub.write_epub(epub_title, book)

	# Set additional metadata for parsing in Calibre.
	meta: ebookmeta.Metadata = ebookmeta.get_metadata(epub_title)
	if series is not None:
		meta.series = series.title
		if work.series is not None:
			for entry in work.series:
				if entry.id == series.id:
					meta.series_index = entry.part
					break
	if work.fandoms is not None:
		meta.tag_list.extend(work.fandoms)
	if work.tags is not None:
		meta.tag_list.extend(work.tags)

	ebookmeta.set_metadata(epub_title, meta)

def _parse_works(url: str) -> Optional[Union[Work, Series, User]]:
	content_id: Optional[int] = helpers.extract_int(url)
	if content_id is None:
		return None

	if "works/" in url or url.isdigit():
		return Work(content_id)
	if "series/" in url:
		return Series(content_id)
	if "users/" in url:
		username: str = url.split("/")[1]
		return User(username)

	return None

def _dl_work(work: Work, args: Options, series: Optional[Series] = None) -> None:
	try:
		if work.restricted:
			raise PermissionError(f"{args.url} is restricted, you'll need to log in and download manually :(")
		print(f"""Downloading '{work.title}'""")
		ao3_dl(work=work, series=series, args=args)
	except Exception as ex: # pylint: disable=broad-exception-caught
		print(f"Error: {ex}")
		traceback.print_exc()

def _has_output_formats(args: Options) -> bool:
	if args.pdf is not None and args.epub is not None and args.html is not None:
		return args.pdf or args.epub or args.html
	return False

def main(passed_args: argparse.Namespace) -> None:
	args: Options = Options(**vars(passed_args))

	config: Optional[dict[str, Any]] = None
	with open("config.json", "r", encoding="utf-8") as file:
		config = json.load(file)

	if args.url is None:
		print("No work given")
		sys.exit(1)

	match: Optional[re.Match[str]] = re.search(helpers.MATCH_REGEX, args.url)

	if match is None:
		print(f"Invalid link: {args.url}")
		sys.exit(1)

	# Try to get default formats if none are given and the config is defined
	if not _has_output_formats(args) and config is not None:
		print("No output formats given, using defaults")
		args.pdf = config["default_formats"]["pdf"]
		args.html = config["default_formats"]["html"]
		args.epub = config["default_formats"]["epub"]
	# If there are still no output formats, error out
	if not _has_output_formats(args):
		print("Select at least 1 output format: --pdf --epub --html")
		sys.exit(1)

	result: Optional[Union[Series | Work | User]] = _parse_works(match.group(0))
	if isinstance(result, Series):
		series: Series = result
		print(f"""Downloading '{series.title}'""")
		for entry in series.works:
			_dl_work(work=entry, series=series, args=args)
	elif isinstance(result, Work):
		work: Work = result
		_dl_work(work=work, args=args)
	elif isinstance(result, User):
		user: User = result
		print(f"""Downloading all works from {user.username}""")
		for entry in user.works:
			_dl_work(work=entry, args=args)

	print("Finished")


if __name__ == "__main__":
	parser: argparse.ArgumentParser = argparse.ArgumentParser(description='Utility for downloading a work or series from archiveofourown.org.')

	parser.add_argument('url', type=str, help='The URL of the work or series to download. Also accepts an ID and parses it as a work.')

	parser.add_argument('--pdf', action='store_true', help='Will export the parsed work as a pdf.')
	parser.add_argument('--epub', action='store_true', help='Will export the parsed work as an epub.')
	parser.add_argument('--html', action='store_true', help='Will export the parsed work as raw html.')

	main(parser.parse_args())
