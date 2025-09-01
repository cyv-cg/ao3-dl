
from typing import Optional, Union

import requests
from bs4 import BeautifulSoup, ResultSet, Tag, PageElement

from helpers import extract_int, NavStr

class Work:
	class SeriesMetadata:
		title: str
		length: int
		part: int

		def __init__(self, series_length: int, part_in_series: int, series_name: str):
			self.title = series_name
			self.length = series_length
			self.part = part_in_series

	class Chapter:
		title: str
		content: str

		def __init__(self, title: str, content: str):
			self.title = title
			self.content = content

	id: int
	content: str
	restricted: bool

	title: str
	author: str

	chapter_list: list[Chapter]

	series: list[SeriesMetadata]
	rating: str
	warning: str
	category: Optional[list[str]]
	fandoms: Optional[list[str]]
	language: str
	published: str
	updated: str
	words: str
	chapters: str
	released_chapters: int
	completed: bool
	is_single_chapter: bool
	relationships: Optional[list[str]]
	characters: Optional[list[str]]
	tags: Optional[list[str]]

	def __init__(self, work_id: int):
		self.id = work_id

		response = requests.get(self.url(), timeout=10)
		if response.status_code != 200:
			raise SystemError(response.status_code)

		self.restricted = "restricted=true" in response.url

		if not self.restricted:
			soup = BeautifulSoup(response.text, "html.parser")

			self.title = self._get_title(soup)
			self.author = self._get_author(soup)

			self._get_meta(soup)
			self._get_attached_series(soup)

			# Remove "chapter text" heading
			for heading in soup.find_all("h3", class_="landmark heading", id="work"):
				heading.string = ""

			self.chapter_list = []
			if not self.is_single_chapter:
				for i in range(self.released_chapters):
					title: str | None = self._chapter_title(soup, i + 1)

					content: NavStr = self._get_chapter_content(soup, i + 1)
					if not isinstance(content, Tag):
						continue

					title_tag: Union[NavStr, int] = content.find("h3", class_="title")

					if title is not None:
						title = f"Chapter {i + 1}: {title}"
					else:
						title = f"Chapter {i + 1}"

					if isinstance(title_tag, Tag):
						title_tag.string = title

					self.chapter_list.append(Work.Chapter(title, content.prettify()))
			else:
				full_content: NavStr = soup.find("div", id="chapters")
				if isinstance(full_content, Tag):
					self.chapter_list.append(Work.Chapter(self.title, full_content.prettify()))

			self.content = soup.prettify()


	def url(self) -> str:
		return f"https://archiveofourown.org/works/{self.id}?view_full_work=true"

	def meta_title(self) -> str:
		if self.series is None or len(self.series) == 0:
			return self.title

		meta_title: str = f'{self.title.replace("|", "_")}'
		for series in self.series:
			meta_title += f"|{series.title}({series.part}/{series.length})"

		return meta_title

	def _chapter_title(self, soup: BeautifulSoup, chapter: int) -> str | None:
		if self.is_single_chapter:
			return None

		index: int = chapter - 1
		chapters: ResultSet[PageElement] = soup.find_all("h3", class_="title")
		title: str = chapters[index].text.strip()

		if title == "":
			return None

		title = title.replace(f"Chapter {chapter}:", "").strip()

		return title
	def _get_chapter_content(self, soup: BeautifulSoup, chapter: int) -> NavStr:
		tag: NavStr = None

		if self.is_single_chapter:
			tag = soup.find("div", class_="userstuff")
		else:
			tag = soup.find(class_="chapter", id=f"chapter-{chapter}")

		return tag

	def _get_title(self, soup: BeautifulSoup) -> str:
		element: NavStr = soup.find("h2", class_="heading")
		if element is not None:
			return element.text.strip()
		return "Unknown"
	def _get_author(self, soup: BeautifulSoup) -> str:
		element: NavStr = soup.find("h3", class_="byline heading")
		if element is not None:
			return element.text.strip()
		return "Unknown"

	def get_series_data(self, series_title: str) -> Optional[SeriesMetadata]:
		if self.series is None:
			return None
		for series in self.series:
			if series_title == series.title:
				return series
		return None

	# Gets the number of entries in a given series
	def _get_series_length(self, series_id: int) -> int:
		response = requests.get(f"https://archiveofourown.org/series/{series_id}", timeout=10)
		if response.status_code != 200:
			raise SystemError(response.status_code)
		soup = BeautifulSoup(response.text, "html.parser")
		works_list: NavStr = soup.find("dd", class_="works")
		if works_list is None:
			return 0
		return int(works_list.text)
	# Retreive metadata about the series (plural) that this work is attached to
	def _get_attached_series(self, soup: BeautifulSoup) -> Optional[list[SeriesMetadata]]:
		element: NavStr = soup.find("dd", class_="series")
		if not isinstance(element, Tag):
			return None

		series: list[Work.SeriesMetadata] = []
		for tag in element.find_all("span", class_="series"):
			part: Optional[int] = extract_int(tag.find("span", class_="position"))
			name: str = tag.find_all("a")[0 if part == 1 else 1].text
			series_id: Optional[int] = extract_int(tag.find_all("a")[0 if part == 1 else 1].get("href"))
			if series_id is None:
				continue
			length: int = self._get_series_length(series_id)
			series.append(Work.SeriesMetadata(length, part if part is not None else 0, name))

		return series

	# Gets single-response metadata information
	def _get_single_tag(self, meta: NavStr, class_: str) -> Optional[str]:
		if not isinstance(meta, Tag):
			return None
		element: NavStr = meta.find("dd", class_=class_)
		return element.text.strip() if element is not None else None
	# Gets multiple-response metadata information
	def _get_multiple_tags(self, meta: NavStr, class_: str) -> Optional[list[str]]:
		if not isinstance(meta, Tag):
			return None
		tags: list[str] = []
		element: NavStr = meta.find("dd", class_=class_)
		if isinstance(element, Tag):
			for x in element.find_all("a"):
				tags.append(x.text.strip())
			return tags
		return None

	def _get_meta(self, soup: BeautifulSoup) -> None:
		meta: NavStr = soup.find("dl", class_="work meta group")
		self.series = self._get_attached_series(soup) or []
		self.rating = self._get_single_tag(meta, "rating tags") or ""
		self.warning = self._get_single_tag(meta, "warning tags") or ""
		self.category = self._get_multiple_tags(meta, "category tags")
		self.fandoms = self._get_multiple_tags(meta, "fandom tags")
		self.language = self._get_single_tag(meta, "language") or ""
		self.published = self._get_single_tag(meta, "published") or ""
		self.updated = self._get_single_tag(meta, "status") or ""
		self.words = self._get_single_tag(meta, "words") or ""
		self.relationships = self._get_multiple_tags(meta, "relationship tags")
		self.characters = self._get_multiple_tags(meta, "character tags")
		self.tags = self._get_multiple_tags(meta, "freeform tags")

		chapters: str = self._get_single_tag(meta, "chapters") or ""
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

	def __init__(self, series_id: int):
		self.id = series_id

		response = requests.get(self.url(), timeout=10)
		if response.status_code != 200:
			raise SystemError(response.status_code)
		soup = BeautifulSoup(response.text, "html.parser")

		self.length = self._length(soup)
		self.title = self._get_title(soup)
		self._get_works(soup)

	def url(self) -> str:
		"""
		The url to access the series.
		Returns:
			str: "https://archiveofourown.org/series/{Series ID}"
		"""
		return f"https://archiveofourown.org/series/{self.id}"

	def _get_works(self, soup: BeautifulSoup) -> None:
		self.works = []
		work_list: NavStr = soup.find("ul", class_="series work index group")
		if not isinstance(work_list, Tag):
			raise LookupError()
		for li in work_list.find_all(recursive=False):
			work_id: Optional[int] = extract_int(li.get("id").replace("work_", ""))
			if work_id is None:
				raise LookupError()
			self.works.append(Work(work_id))

	def _get_title(self, soup: BeautifulSoup) -> str:
		title_element: NavStr = soup.find("h2", class_="heading")
		if title_element is None:
			raise LookupError()
		return title_element.text.strip()

	def _length(self, soup: BeautifulSoup) -> int:
		work_list: NavStr = soup.find("dd", class_="works")
		if work_list is None:
			return 0
		return int(work_list.text)

class User:
	works: list[Work]
	username: str

	def __init__(self, username: str):
		self.username = username
		self.works = []

		response = requests.get(self.url(), timeout=10)
		if response.status_code != 200:
			raise SystemError(response.status_code)
		soup = BeautifulSoup(response.text, "html.parser")

		work_list: NavStr = soup.find("ol", class_="work index group")
		if work_list is None:
			raise LookupError("'work index group' element not found")
		if isinstance(work_list, Tag):
			for li in work_list.find_all("li"):
				user_id: Optional[int] = extract_int(li.get("id"))
				if user_id is None:
					continue
				self.works.append(Work(user_id))

	def url(self) -> str:
		"""
		The url to access the user's page.
		Returns:
			str: "https://archiveofourown.org/users/{Username}/works"
		"""
		return f"https://archiveofourown.org/users/{self.username}/works"
