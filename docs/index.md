# Introduction
[![Python 3.9+](https://upload.wikimedia.org/wikipedia/commons/4/4f/Blue_Python_3.9%2B_Shield_Badge.svg)](https://www.python.org)
[![MediaWiki 1.35+](https://upload.wikimedia.org/wikipedia/commons/b/b3/Blue_MediaWiki_1.35%2B_Shield_Badge.svg)](https://www.mediawiki.org/wiki/MediaWiki)
[![License: GPL v3](https://upload.wikimedia.org/wikipedia/commons/8/86/GPL_v3_Blue_Badge.svg)](https://www.gnu.org/licenses/gpl-3.0.en.html)

**pwiki** is a Python library which makes interacting with the MediaWiki API simple and easy.  It can be used with sites such as Wikipedia, or virtually any other website that runs on MediaWiki.

## Installation
```bash
pip install pwiki
```

## Overview
I created `pwiki` with the goal of being simple and powerful, all while being mindful of DX (developer experience).  This means that every interaction with the API is simple, easy, and usually just one line of code.

`pwiki` is split into four main modules:

1. [wiki](API/wiki-reference.md) - The main API and entry point.  This module ecompasses most of the functionality for reading from/writing to MediaWiki.
2. [mquery](API/mquery-reference.md) - The batch query API.  This module makes it easy to efficiently query against many titles/articles on the MediaWiki instance in fewer round-trips.
3. [gquery](API/gquery-reference.md) - A batch query API that uses python generators to efficiently query for results.  This is useful for sampling large quantities of data from MediaWiki in a piecemeal fashion.
4. [wparser](API/wparser-reference.md) - Contains methods for parsing wikitext into higher level object-based models that are easy to work with.
