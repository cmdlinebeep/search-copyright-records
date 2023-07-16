# Search Copyright Records

Determining if a book is in the Public Domain in the United States can be an arduous task.  A few years back, some great folks at the New York Public Library (NYPL) made a heroic effort to digitize and standardize records from the U.S. Catalog of Copyright Entries (CCE).  However, searching if a book is in the CCE is not the whole picture, as author's had a certain time window to choose to optionally renew the Copyrights as well.  The NYPL also helped digitize those CCE Renewals records.

However, the entries exist as a huge collection of XML and TSV files, and (at least at the time I wrote this code), there was no simple way to search through it all.  

This library searches both the CCE records and the CCE Renewals records for a given book and title.  If you don't give it any idea when the book was published, a linear search through all the entries could take around 10 days to finish running.  If you give it a hint around when you think the book was originally published (usually easily searchable on the internet), the script will only need to search a few years around that date, speeding the search up considerably.  The original records are about 1.5GB of text at the time of writing.

One other issue this library solves is that the original scans of the books (done by Archive.org) contains occasional OCR errors.  Pair that with not knowing how an author's name or the title might be listed, and you could end up with an unreliable search.  For example, you might search `A.A. Milne` but the CCE might have the entry as `Milne, Alan Alexander`.  Or a speck of dust in the book might have led to an OCR error, like `Milne, Alan Aléxander` and an unforgiving literal search may come up empty.  

For these reasons, I used both a library called `unidecode` which matches accent characters to their closest ASCII characters (e.g. unidecode('kožušček') ==> 'kozuscek').  This is performed on both the search terms and the target words in the database.  Secondly, I use a fuzzy search library `fuzzywuzzy` which uses Levenshtein distances to allow a close match, up to a specified tolerance.  I experimented with the right tolerances until performance was good, but you are free to change it.

I highly recommend reading the [NYPL's original blog post](https://www.nypl.org/blog/2019/05/31/us-copyright-history-1923-1964) about this topic first.

To read more about U.S. Copyright Law, read Title 17 [here](https://www.copyright.gov/title17/).

# About the Code

The main functions operate as follows:

`check_one_book.py`             This is a simple wrapper most likely what you want -- to check the status of a single book

`copyright_status()`            This function performs the main control logic.  There is a sortof complicated logical branching that determines if a book is still under Copyright or not (see the NYPL blog post).  This function performs that logic, calling the next two functions to do its job.

`fuzzy_search_registration()`   Searches the CCE records and returns if a book was found to be registered for Copyright.

`check_if_renewed()`            Searches the CCE Renewal records to see if a book was renewed.

## Important!
**Please note that it is impossible to prove a negative.  That is, just because the script comes back saying it was not found in the registration or renewal records, CANNOT guarantee that the book is not still Copyrighted!  For example, excessive OCR errors could have led to it being missed.  But it gives you a likely answer.  However, finding a positive match (that an entry was found and its renewal) can be banked on (and manually verified yourself).**

# Installation and Running the Code

## Download the NYPL databases
You'll need to download the [CCE database](https://github.com/NYPL/catalog_of_copyright_entries_project) and the [CCE Renewal](https://github.com/NYPL/cce-renewals) databases first.  I recommend using GitHub's "Download as .zip" option in this case.  

I've already created empty folders in this repository which shows you where to populate the downloaded data.  There are extra files in the NYPL downloads that you can safely ignore or include, they're benign.  Once the data is in the right place, your directory tree structure should look like:

  ```sh
  ├── README.md
  ├── book_utils.py
  ├── check_one_book.py
  ├── requirements.txt
  ├── __init.py__
  ├── cce_renewals
  │   └── data
  │       ├── 1950-14A.tsv
  │       ├── ... 
  │       └── 2001-from-db.tsv
  └── copyright_entries
      └── xml
          ├── 1923
          |   └── 1923_v20_n1-125.xml
          ├── ... 
          └── 1977
              └── 1977_v31_1.xml
  ```

## Usage

At the base repo directory, set up a virtual environment and install the Python libraries in `requirements.txt`, then:

```sh
python check_one_book.py
```