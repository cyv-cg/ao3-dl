from bs4 import NavigableString, Tag
from bs4 import BeautifulSoup
from typing import TypeAlias
import requests

from helpers import extract_int

NavStr: TypeAlias = (Tag | NavigableString | None)

class Work:
	class SeriesMetadata:
		title: str
		length: int
		part: int

		def __init__(self, series_length: int, part_in_series: int, series_name: str):
			self.title = series_name
			self.length = series_length
			self.part = part_in_series
	
	id: int

	title: str
	author: str

	series: list[SeriesMetadata]
	rating: str
	warning: str
	category: list[str] | None
	fandoms: list[str] | None
	language: str
	published: str
	updated: str
	words: int
	chapters: str
	released_chapters: int
	completed: bool
	is_single_chapter: bool
	relationships: list[str] | None
	characters: list[str] | None
	tags: list[str] | None

	def __init__(self, id: int):
		self.id = id

		response = requests.get(self.url())
		if response.status_code != 200:
			raise Exception(response.status_code)
		soup = BeautifulSoup(response.text, "html.parser")

		self.title = self._get_title(soup)
		self.author = self._get_author(soup)

		self._get_meta(soup)

	def url(self) -> str:
		return f"https://archiveofourown.org/works/{self.id}?view_full_work=true"
	
	def _get_title(self, soup: BeautifulSoup) -> str:
		return soup.find("h2", class_="heading").text.strip()
	def _get_author(self, soup: BeautifulSoup) -> str:
		return soup.find("h3", class_="byline heading").text.strip()
		
	def get_series_data(self, series_title: str) -> SeriesMetadata | None:
		if self.series == None:
			return None
		for series in self.series:
			if series_title == series.title:
				return series

	# Gets the number of entries in a given series
	def _get_series_length(series_id: int) -> int:
		response = requests.get(f"https://archiveofourown.org/series/{series_id}")
		if response.status_code != 200:
			raise Exception(response.status_code)
		soup = BeautifulSoup(response.text, "html.parser")
		return int(soup.find("dd", class_="works").text)
	# Retreive metadata about the series (plural) that this work is attached to
	def _get_attached_series(self, meta: NavStr) -> list[SeriesMetadata]:
		element: NavStr = meta.find("dd", class_="series")
		if element == None:
			return None
		
		series: list[Work.SeriesMetadata] = []
		for tag in element.find_all("span", class_="series"):
			part = extract_int(tag.find("span", class_="position"))
			name = tag.find_all("a")[0 if part == 1 else 1].text
			try:
				length = self._get_series_length(extract_int(tag.find_all("a")[0 if part == 1 else 1].get("href")))
			except:
				length = None
			series.append(Work.SeriesMetadata(length, part, name))

		return series

	# Gets single-response metadata information
	def _get_single_tag(self, meta: NavStr, class_: str) -> str | None:
		return meta.find("dd", class_=class_).text.strip() if meta.find("dd", class_=class_) != None else None
	# Gets multiple-response metadata information
	def _get_multiple_tags(self, meta: NavStr, class_: str) -> list[str] | None:
		tags: list[str] = []
		element: NavStr = meta.find("dd", class_=class_)
		if element != None:
			for x in element.find_all("a"):
				tags.append(x.text.strip())
			return tags
		else:
			return None

	def _get_meta(self, soup: BeautifulSoup) -> None:
		meta: NavStr = soup.find("dl", class_="work meta group")
		self.series = self._get_attached_series(meta)
		self.rating = self._get_single_tag(meta, "rating tags")
		self.warning = self._get_single_tag(meta, "warning tags")
		self.category = self._get_multiple_tags(meta, "category tags")
		self.fandoms = self._get_multiple_tags(meta, "fandom tags")
		self.language = self._get_single_tag(meta, "language")
		self.published = self._get_single_tag(meta, "published")
		self.updated = self._get_single_tag(meta, "status")
		self.words = self._get_single_tag(meta, "words")
		self.relationships = self._get_multiple_tags(meta, "relationship tags")
		self.characters = self._get_multiple_tags(meta, "character tags")
		self.tags = self._get_multiple_tags(meta, "freeform tags")

		chapters: str = self._get_single_tag(meta, "chapters")
		latest_chapter: int = int(chapters.split("/")[0])
		num_chapters: str = chapters.split("/")[1]

		# If a work is incomplete, its chapter count appears as 'x/?'
		# If it *is* complete, it shows as 'x/x'
		self.completed = num_chapters.isdigit() and latest_chapter == int(num_chapters)
		self.chapters = chapters
		self.released_chapters = latest_chapter
		self.is_single_chapter = chapters == "1/1"

class Series:
	works: list[Work]
	id: int

	title: str

	length: int

	def __init__(self, id: int):
		self.id = id

		response = requests.get(self.url)
		if response.status_code != 200:
			raise Exception(response.status_code)
		soup = BeautifulSoup(response.text, "html.parser")

		self._get_works(soup)
		self.length = self._length(soup)
		self.title = self._get_title(soup)

	def url(self) -> str:
		return f"https://archiveofourown.org/series/{self.id}"
	
	def _get_works(self, soup: BeautifulSoup) -> None:
		for li in soup.find("ul", class_="series work index group").find_all(recursive=False):
			id = li.get("id").replace("work_", "")
			self.works.append(Work(id))
	
	def _get_title(self, soup: BeautifulSoup) -> str:
		return soup.find("h2", class_="heading").text.strip()
	
	def _length(self, soup: BeautifulSoup) -> int:
		return int(soup.find("dd", class_="works").text)
