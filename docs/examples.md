# Examples
This is a non-exhaustive collection of snippets exhibiting some of the functionality `pwiki` is capable of.

## Basics
```python
from pwiki.wiki import Wiki

# new Wiki instance, pointed to en.wikipedia.org, not logged in
wiki = Wiki()

# new Wiki instance, pointed at commons.wikimedia.org, logging in with user/pass
wiki = Wiki("commons.wikimedia.org", "MyCoolUsername", "MySuperSecretPassword")

# login on en.wikipedia.org as MyCoolUsername.  Password will be read from environment variable "MyCoolUsername_PW"
wiki = Wiki(username="MyCoolUsername")

# save cookies so they can automatically be reused for next time
wiki.save_cookies()
```

## Read Page Content
```python
from pwiki.wiki import Wiki

wiki = Wiki()

# get all the titles in "Category:American 3D films"
print(wiki.category_members("Category:American 3D films"))

# get all external links on the page "GitHub"
print(wiki.external_links("GitHub")):
```

## Edit/Create Content
```python
from pwiki.wiki import Wiki

# you'll need to create a real account on Wikipedia otherwise the snippets below won't work
wiki = Wiki(username="MyCoolUsername", password="MySuperSecretPassword")

# Append "this is a test" to "Wikipedia:Sandbox"
wiki.edit("Wikipedia:Sandbox", append="this is a test")

# Replace "Wikipedia:Sandbox" with "I changed the page!" and edit summary "Hello, world!"
wiki.edit("Wikipedia:Sandbox", "I changed the page!", "Hello, world!")

# Upload a file
from pathlib import Path
wiki.upload(Path("/path/to/file.jpg"), "My awesome new file on Wikipedia.jpg", "my file description", "test edit summary")
```

## Categories
```python
from pwiki.ns import NS
from pwiki.wiki import Wiki

wiki = Wiki()

# get all category members of "Category:Some Cool Category"
print(wiki.category_members("Category:Some Cool Category"))

# get all category members of "Category:Some Cool Category" in the File namespace
print(wiki.category_members("Category:Some Cool Category", NS.FILE))
```