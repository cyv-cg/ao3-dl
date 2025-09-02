# ao3-dl

Utility for downloading a work or series from Archive of Our Own.

Currently accepts inputs in the following forms:
- `https://archiveofourown.org/works/123456`
- `123456		(interprets as https://archiveofourown.org/works/123456)`
- `archiveofourown.org/series/123456`
- `archiveofourown.org/user/abcdef`

## Usage

Utility for downloading a work or series from archiveofourown.org.

usage: ao3-dl.py [-h] [--pdf] [--epub] [--html] [--cookies COOKIES] url

A bash script is included that will automaticaly handle crating a virtual environment and installing dependencies.
Use it with `sh ao3-dl.sh [arguments]`.

If no format arguments are specified, it will default to outputting in EPUB. This can be changed by editing `config.json`.

### positional arguments:
<pre>
	url				The URL of the work/series to download. Also accepts an ID and parses it as a work.
</pre>

### options:  

<pre>
	--pdf				Will export the parsed work as a pdf.
	--epub				Will export the parsed work as an epub.
	--html		  		Will export the parsed work as raw html.
	--cookies COOKIES 	File containing browser cookies - used to access restricted content.
</pre>

### Restricted works & cookies
Some authors choose to restrict works so they can only be accessed by logged in users. For these, you'll need to pass in browser cookies so the utility can access the work.
To get the cookies, you can use an extension such as [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc).
Save the cookies to a file and pass it in using `python ao3-dl.py --cookies /path/to/cookies.txt [url]`.

## Installation

### Install python dependencies:
	pip install -r requirements.txt


### ~~Install npm:~~
	sudo apt update
	sudo apt install nodejs npm  
	sudo npm install -g sass

### ~~Build the css:~~
	sass style.scss style.css
Compiled css is now included directly.
