#!/usr/bin/python
# -*- coding: latin-1 -*-
## This is a class I pulled off of stackoverflow--- may be useful for reference
import calendar
import Bio
 
from Bio import Entrez

def format_ddate(ddate):
    """Turn a date dictionary into an ISO-type string (YYYY-MM-DD)."""
    year = ddate['Year']
    month = ddate['Month']
    day = ddate['Day']
    if not month.isdigit():
        month = months_rdict.get(month, None)
        if not month:
            return None
    return "%s-%s-%s" % (year, month.zfill(2), day.zfill(2))


 
# This is for translating abbreviated month names to numbers.
months_rdict = {v: str(k) for k,v in enumerate(calendar.month_abbr)}
 
# Returns a list or its value if there is only one.
list_or_single = lambda l: l*(len(l)>1) or l[0]
 
class PubmedSearcher:
    """Fetches data from Pubmed using the Entrez module from Biopython."""
 
    # There are the fields that we want to fetch, and all of them are single
    # values except grantlist, which is a dictionary (as per Entrez).
    # More fields can easily be added, and all that needs to be done is
    # to add the appropriate extract_ and fetch_ methods below.
    fields = [
        'pmid', 'doi', 'vol', 'pages',
        'year', 'pub_month', 'pub_day',
        'date_pubmed_created', 'date_pubmed_updated',
        'date_accepted', 'date_aheadofprint', 'date_pubmed_history',
        'grantlist' # this is a dict!
    ]
 
    # Entrez normally limits the number of queries to 200, so work with block of 100.
    nblock = 100
 
    def __init__(self, email):
        """Entrez requires and email address."""
        Entrez.email = email
 
    def fetch_xml_round(self, pmid):
        """Tries to fetch and parse the XML for a list of PMIDs, no questions asked."""
        return Entrez.read(Entrez.efetch(db="pubmed", id=pmid, retmode="xml"))
 
    def fetch_xml(self, pmid):
        """This breaks the process up into blocks."""
        self.nrounds = len(pmid) / self.nblock + (len(pmid) % self.nblock > 0)
        if self.nrounds > 1:
            print "Will query in %i rounds with %i articles per round." % (self.nrounds, self.nblock)
            xml_data = []
            for i in range(self.nrounds):
                istart = i * self.nblock
                ifinish = (i+1) * self.nblock
                print "Fetching round %i..." % (i+1)
                xml_data += self.fetch_xml_round(pmid[istart:ifinish])
        else:
            xml_data = fetch_xml_round(pmid)
        return xml_data
 
    def extract_id_factory(idtype):
        def extract_id(self, xml_data):
            """Extract the %s ID from Entrez XML output.""" % idtype
            for id in xml_data['PubmedData']['ArticleIdList']:
                if id.attributes['IdType'].lower() == idtype:
                    return str(id)
        return extract_id
    extract_pmid = extract_id_factory('pubmed')
    extract_doi = extract_id_factory('doi')
 
    def extract_date_factory(datetype):
        def extract_date(self, xml_data):
            """Extract %s date from Entrez XML output.""" % datetype
            for date in xml_data['PubmedData']['History']:
                if date.attributes['PubStatus'].lower() == datetype:
                    return format_ddate(date)
        return extract_date
    extract_date_accepted = extract_date_factory('accepted')
    extract_date_aheadofprint = extract_date_factory('aheadofprint')
    extract_date_pubmed_history = extract_date_factory('pubmed')
 
    # Many fields can be pointed to via an Xpath directly, although we still want
    # to mangle the result in many cases, so the factory needs some tweaking.
    # To make names shorter, the field 'type' argument passed to the factory
    # is prefixed by "xpath_" to get the xpath variable name. Watch out for that!
    xpath_year = ['MedlineCitation', 'Article', 'Journal', 'JournalIssue', 'PubDate', 'Year']
    xpath_pub_month = ['MedlineCitation', 'Article', 'Journal', 'JournalIssue', 'PubDate', 'Month']
    xpath_pub_day = ['MedlineCitation', 'Article', 'Journal', 'JournalIssue', 'PubDate', 'Day']
    xpath_vol = ['MedlineCitation', 'Article', 'Journal', 'JournalIssue', 'Volume']
    xpath_pages = ['MedlineCitation', 'Article', 'Pagination', 'MedlinePgn']
    xpath_date_pubmed_created = ['MedlineCitation', 'DateCreated']
    xpath_date_pubmed_updated = ['MedlineCitation', 'DateRevised']
    def extract_xpath_factory(type, rdict=None, format=None):
        def extract_xpath(self, xml_data):
            try:
                data = xml_data
                for node in getattr(self, 'xpath_'+type):
                    data = data[node]
                if rdict != None:
                    data = rdict[data]
                if format != None:
                    data = format(data)
                return data
            except (KeyError, TypeError):
                return None
        return extract_xpath
    extract_year = extract_xpath_factory('year')
    extract_pub_month = extract_xpath_factory('pub_month', rdict=months_rdict)
    extract_pub_day = extract_xpath_factory('pub_day')
    extract_vol = extract_xpath_factory('vol')
    extract_pages = extract_xpath_factory('pages')
    extract_date_pubmed_created = extract_xpath_factory('date_pubmed_created', format=format_ddate)
    extract_date_pubmed_updated = extract_xpath_factory('date_pubmed_updated', format=format_ddate)
 
    # The grantlist is a bit mroe convoluted, because it is itself a dictionary with several
    # fields, which normally need to go together to by of use.
    xpath_grantlist = ['MedlineCitation', 'Article', 'GrantList']
    def extract_grantlist(self, xml_data):
        try:
            data = xml_data
            for node in self.xpath_grantlist:
                data = data[node]
            fields = {'acronym':'Acronym', 'agency':'Agency', 'country':'Country', 'number':'GrantID'}
            return [{k:d.get(v,None) for k,v in fields.items()} for d in data]
        except (KeyError, TypeError):
            return None
 
    # These are convenience functions that fetch single fields for many PMIDs.
    def fetch_field_factory(type):
        def fetch_field(self, pmid):
            targets = [getattr(self, 'extract_'+type)(parsed) for parsed in self.fetch_xml(pmid)]
            return list_or_single(targets)
        return fetch_field
    fetch_pmid = fetch_field_factory('pmid')
    fetch_doi = fetch_field_factory('doi')
    fetch_year = fetch_field_factory('year')
    fetch_pub_month = fetch_field_factory('pub_month')
    fetch_pub_day = fetch_field_factory('pub_day')
    fetch_vol = fetch_field_factory('vol')
    fetch_pages = fetch_field_factory('pages')
 
    # And this one extracts fetches all the fields defined above for many PMIDs.
    def fetch_all(self, pmid):
        xml_data = self.fetch_xml(pmid)
        all = []
        for parsed in xml_data:
            x = {}
            for f in self.fields:
                x[f] = getattr(self, "extract_"+f)(parsed)
            all.append(x)
        return all

