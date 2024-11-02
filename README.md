# ao3-dl

Utility for downloading a work or series from archiveofourown.org.

## Usage

python ao3-dl.py [-h] [--export-as-html] url

### positional arguments:
<pre>
	url				The URL of the work or series to download. Also accepts an ID and parses  
					it as a work.
</pre>

### options:  

<pre>
	--export-as-html		Will export the parsed work as raw html as well as a pdf.
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
