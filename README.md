# ao3-dl

Utility for downloading a work or series from Archive of Our Own.

Currently accepts inputs in the following forms:
- `https://archiveofourown.org/works/123456`
- `123456		(interprets as https://archiveofourown.org/works/123456)`
- `archiveofourown.org/series/123456`
- `archiveofourown.org/user/abcdef`

## Usage

Utility for downloading a work or series from archiveofourown.org.

usage: ao3-dl.py [-h] [--pdf] [--epub] [--html] url

### positional arguments:
<pre>
	url				The URL of the work/series to download. Also accepts an ID and parses it as a work.
</pre>

### options:  

<pre>
	--pdf			Will export the parsed work as a pdf.
	--epub			Will export the parsed work as an epub.
	--html			Will export the parsed work as raw html.
</pre>


## Installation

### Install python dependencies:
	pip install -r requirements.txt

### Install npm:
	sudo apt update  
	sudo apt install nodejs npm  
	sudo npm install -g sass  

### Build the css:
	sass style.scss style.css
