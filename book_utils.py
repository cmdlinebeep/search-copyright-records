import glob
from fuzzywuzzy import fuzz
import xml.etree.ElementTree as ET
from tqdm import tqdm   # progress bar
from datetime import datetime
import re
from unidecode import unidecode


def fuzzy_search_registration(author, title, year_guess=None):
    '''Searches the copyright registration entries for the work.
    Does a fuzzy search on author and title, uses largest product of
    both as the most likely result.  Use minimum threshold.
    Returns tuple of (year, reg_num) if found, or (None, None)
    Also returns ratios and detected author and title, for debug.'''

    # Experimental code in scratch.py

    print(f"Searching records for {year_guess}: {title} by {author}...")

    # Searching ALL .xml files takes about 3 minutes per book, so times 5000 books is 15,000 minutes, 
    # or 250 hours, or 10.5 days!  Need to speed this up.
    # Instead of searching EVERY .xml file, only search the suspected publication
    # year, +/- 5 years (11 year window).  So if 1927, search 1922 to 1932.  Should dramatically speed
    # up search.  Didn't necessarily register copyright in same publication year.
    # If input year not given, search ALL records (so try to give year).

    # Actually, if we *think* the publication year was in a year, more likely that the copyright
    # didn't get filed for a while (no limit?) but less likely it was filed *before* the date we think
    # so only go a few years earlier and more lears later.
    
    # TO DEBUG THE COPYRIGHT SEARCH, example command:
    # grep -ir --color "kon-tiki" ./copyright_entries/xml/*

    # https://www.geeksforgeeks.org/how-to-use-glob-function-to-find-files-recursively-in-python/
    if year_guess is None:
        # Search all files :(
        xml_files = glob.glob('./copyright_entries/xml/**/*.xml', recursive=True)
    else:
        xml_files = []
        for i in range(-2, 7+1):
            # Glob returns a list, we don't want to append or we get lists of lists
            # Instead just use the + operator which joins them
            xml_files += glob.glob(f'./copyright_entries/xml/{year_guess + i}/*.xml', recursive=True)

    # These are the best OVERALL so best out of all xml files!  Search them all.
    best_overall_ratio = 0
    best_overall_match = ''
    best_child = None

    # Search all relevant .xml files (hopefully not full set)
    for xml_file in tqdm(xml_files):

        # https://www.datacamp.com/community/tutorials/python-xml-elementtree
        tree = ET.parse(xml_file)
        root = tree.getroot()

        # Iterate over copyright entries
        for child in root.findall('./copyrightEntry'):

            # Make sure first that copyrightEntry has a regnum!  Rare, but some entries don't.
            # If it doesn't, we can't use it later, so skip it and hope there's a better entry yet.
            try:
                regnum_key_test = child.attrib['regnum']    # We grab this again later in the code, throwaway
            # If we have a KeyError here, then entry didn't have a regnum
            # e.g. <copyrightEntry id="D178B20E-6D99-1014-A5EA-BAD7E825951E">
            #        <author>
            #            <authorName>GILBRETH, FRANK BUNKER.</authorName>
            #        </author> 
            #        <title>Cheaper by the dozen</title>
            except KeyError:
                continue        # skip entry

            # Find best Author match for this entry
            # Iterate over all authors for this book (can have multiple authors for a book)
            best_author_ratio = 0
            best_author_match = ''
            for author_node in child.findall('author/authorName'):

                # Many ways to list the author name, keep the best match, as it's likely
                # the right one (e.g. A.A. Milne versus Milne, Alan Alexander)

                # https://www.datacamp.com/community/tutorials/fuzzy-string-python
                # Find the fuzzy string match of the author we're looking for

                # Replace accent characters with closest ASCII
                # unidecode('kožušček') ==> 'kozuscek'
                cce_author_text = author_node.text
                try:
                    cce_author_text = unidecode(cce_author_text)
                except AttributeError:
                    # In rare cases, the XML is malformatted where a author/authorName child is found,
                    # but it's literally empty in between, like here.  This returns None as the author string.
                    # And we'd get error: AttributeError: 'NoneType' object has no attribute 'encode'
                    # <copyrightEntry id="35F72E23-6DD5-1014-B757-AF09C522E301" regnum="A869349">
                    #     <author>
                    #         <authorName></authorName>Emma Earlenbaugh Davis
                    #     </author>
                    continue    # just skip this author node

                author_token_set_ratio = fuzz.token_set_ratio(cce_author_text, author)

                # Find best author match out of all authors
                if author_token_set_ratio > best_author_ratio:
                    best_author_ratio = author_token_set_ratio
                    best_author_match = cce_author_text
                
            # Title match
            # Only one title of a work
            try:
                title_node = child.findall('title')[0]
            except IndexError:
                # Some works don't have titles (believe it or not).  Just skip these
                continue
            
            # Again, clean up to closest ASCII
            cce_title_text = title_node.text
            try:
                cce_title_text = unidecode(cce_title_text)
            except AttributeError:
                # Similar to Authors, in rare cases there is a Title node, but it's literally empty (returns None).
                continue    # just skip this title node
            
            # Find the fuzzy string match of the title we're looking for
            title_token_set_ratio = fuzz.token_set_ratio(cce_title_text, title)

            # Take the product of both match ratios to find the best overall match
            overall_ratio = best_author_ratio * title_token_set_ratio

            # Find best overall match out of all titles and potentially multiple authors
            if overall_ratio > best_overall_ratio:
                best_overall_match = best_author_match + ' ' + cce_title_text
                best_overall_ratio = overall_ratio
                best_child = child      # store whole object
                # print(f"BEST MATCH: {best_overall_ratio} {best_overall_match}")

    # Set minimum confidence of 9000 required.  Best possible is 100x100=10000
    # This was found experimentally looking at results for about 300 books.
    # 9000 is about a 95% match on the author and 95% match on title.
    if best_overall_ratio < 9000:
        # No good-enough matches
        return (None, None, best_overall_ratio, best_overall_match)

    # Else, we have good enough match, return the best match's Year and Reg Number
    reg_num = best_child.attrib['regnum']   # e.g. 'A1010229'

    # Try to get the registration date
    try:
        reg_date = best_child.findall('regDate')[0]
    except IndexError:
        # Will get list index out of range if [0] doesn't exist, means was no registration date
        # Try to get the copyDate instead
        try:
            reg_date = best_child.findall('copyDate')[0]
        except IndexError:
            # Don't want to quit, lose all progress!
            # If we get to this point, we actually found a good match (> threshold) so we 
            # want to maintain as much info as we can.  We also have a registration number!
            # So return what we know.
            print("ERROR: Could not find regDate or copyDate for entry.")
            print(f"Was searching for: {year_guess} {author} {title} when error occurred.")
            print(f"Best overall match was: {best_overall_ratio} {best_overall_match}")
            return (None, reg_num, best_overall_ratio, best_overall_match)

    # print(reg_date)                             # = <regDate date="1927-10-14">Oct. 14, 1927</regDate>
    # print(reg_date.attrib['date'])              # = "1927-10-14"
    # print(reg_date.attrib['date'].split('-'))   # = ['1927', '10', '14']
    reg_year = int(reg_date.attrib['date'].split('-')[0])   # e.g. 1927
    
    # Also return useful information for debugging (unused)
    return (reg_year, reg_num, best_overall_ratio, best_overall_match)


def check_if_renewed(reg_num, reg_year):
    '''Returns True if registration number found in the renewal files'''

    # Search again only in 28 years from now, +/- 2 years (5 year span)
    # to save search time, since you can renew after 28 years

    # Similarly, they can't file late, so only search more heavily for early renewals,
    # and only add like one year at the end due to corner cases.

    # TO DEBUG THE RENEWAL SEARCH, example command:
    # grep -i --color "A653819" ./cce_renewals/data/*.tsv
    tsv_files = []
    for i in range(-3, 1+1):
        # Glob returns a list, we don't want to append or we get lists of lists
        # Instead just use the + operator which joins them
        # Remember that we're searching renewal records 28 years in the future!
        tsv_files += glob.glob(f'./cce_renewals/data/{reg_year + 28 + i}*.tsv')

    # Search for registration number in renewal records
    for tsv_file in tsv_files:
        with open(tsv_file, 'r', encoding='utf8') as tsv_file_handle:
            for line in tsv_file_handle:
                if re.search(reg_num, line):
                    # If it's found, then it's been renewed
                    return True
    
    # if we get to here, it wasn't found
    return False


def copyright_status(author, title, year=None, verbose=False):
    '''Highest level function that takes in book info and
    returns the likely copyright status.'''

    # Replace accent characters with closest ASCII
    # unidecode('kožušček') ==> 'kozuscek'
    author = unidecode(author)
    title = unidecode(title)

    author = author.strip()
    title = title.strip()

    # year is already interpreted as an int
    # if year is not None:
    #     year = int(year.strip())

    if author == '' or title == '':
        # empty row
        return ""

    # Do fuzzy search of author and title to find most likely match
    (reg_year, reg_num, best_overall_ratio, best_overall_match) = fuzzy_search_registration(author=author, title=title, year_guess=year)

    if verbose:
        print(f"Best overall match: {best_overall_match}")
        print(f"Reg. year: {reg_year}")
        print(f"Reg. number: {reg_num}")

    # Trying to find best min_threshold to set these to on a large dataset.
    # return f"{best_overall_ratio} {best_overall_match}"

    current_year = int(datetime.now().year)
    public_domain_year = current_year - 95  # e.g. if script ran in 2018 - 95 = 1923 (protected til end of 2018)

    # Flowchart logic.  Every branch must return something.
    if reg_num is None:
        # No copyright entry record found
        if year is None:
            # If no guessed year is even given
            return "Unknown. No registration record found. No publication date given."
        elif year < public_domain_year:
            return "Likely public domain. No registration record found, so verify."
        else:
            return "Potentially public domain. No registration record found."

    else:
        # Copyright entry record found
        if reg_year is None:
            # Rare case where we found a registration but no registration date or copyright date
            return "Manually check. Rare case of registration record found, but no registration or copyright date found."
        elif reg_year < public_domain_year:
            return "Public domain. Registration record found. Published over 95 years ago."
        elif reg_year >= 1964:
            return "Copyrighted. Registration record found. Published after 1964."
        else:
            # If get to here, it was registered in the "Renewal Era" 
            # as defined by this helpful New York Public Library blog post:
            # https://www.nypl.org/blog/2019/05/31/us-copyright-history-1923-1964

            # We need to check if the copyright was renewed or not.
            renewed = check_if_renewed(reg_num=reg_num, reg_year=reg_year)

            if renewed:
                return "Copyrighted. Registration record found and renewed."
            else:
                return "Public domain. Registration record found but not renewed."

    # default case
    return 'Error. Should not have arrived here in code!'



# Testing code:

# # guess the wrong year, 1926 instead of 1927
# (reg_year, reg_num) = fuzzy_search_registration(author="A.A. Milne", title="Now We Are Six", year_guess=1928)

# print(reg_year)
# print(reg_num)

# test = copyright_status(author="A.A. Milne", title="Now We Are Six", year='1927')
# print(test)