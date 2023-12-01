# Examples
⚠️ This section is under construction

## Basics
```python
from pwiki.wiki import Wiki

# new Wiki instance, pointed to en.wikipedia.org, not logged in
wiki = Wiki()

# new Wiki instance, pointed at commons.wikimedia.org, logging in with user/pass
wiki = Wiki("commons.wikimedia.org", "MyCoolUsername", "MySuperSecretPassword")
```

## Read Page Content
```python
from pwiki.wiki import Wiki

wiki = Wiki()

# print all the titles in "Category:American 3D films"
for title in wiki.category_members("Category:American 3D films"):
    print(title)

# print all external links on the page "GitHub"
for url in wiki.external_links("GitHub"):
    print(url)
```

## Edit/Create Page Content
```python
from pwiki.wiki import Wiki

# you'll need to create a real account on Wikipedia otherwise the snippets below won't work
wiki = Wiki(username="MyCoolUsername", password="MySuperSecretPassword")

# Append "this is a test" to "Wikipedia:Sandbox"
wiki.edit("Wikipedia:Sandbox", append="this is a test")

# Replace "Wikipedia:Sandbox" with "I changed the page!" and edit summary "Hello, world!"
wiki.edit("Wikipedia:Sandbox", "I changed the page!", "Hello, world!")
```