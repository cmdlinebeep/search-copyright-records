"""Check the copyright status of a single book."""

from book_utils import copyright_status

#read multiple strings from user
author = input('Enter Author name: ')
title = input('Enter Book title: ')
year = input('Enter year of book, if known [or blank]: ')

if year == '':
    year = None
else:
    year = int(year)

# Meat of the work done here
status = copyright_status(author=author, title=title, year=year, verbose=True)

print(status)