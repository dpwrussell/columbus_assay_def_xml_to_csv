#!/usr/bin/env python

from lxml import etree
from argparse import ArgumentParser
import csv, codecs, cStringIO

# Configure argument parsing
parser = ArgumentParser(description='Convert Columbus XML to CSV')
parser.add_argument("files", nargs="*")

class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

# Define the namespace
namespaces = {'Columbus': 'http://www.perkinelmer.com/Columbus'}

def convert_file(filename):
    # Parse the input file
    tree = etree.parse(filename)

    # Use the registration to get the drug names

    drugs = tree.xpath(
        "Columbus:Registration/Columbus:Content[@GroupName='Drug']",
        namespaces=namespaces)

    # Look for each of the drugs and create a list of rows

    drug_aliases = {}

    # Map drug "names" to the aliases (the real names)
    for drug in drugs:
        drug_aliases[drug.get('ID')] = drug[0].text

    drug_names = ' or '.join(["@ContentID='%s'" % drug.get('ID')
                             for drug in drugs])

    drug_values = tree.xpath(
        "//Columbus:Well/Columbus:Content[%s]/Columbus:Value" % drug_names,
        namespaces=namespaces)

    # Write the CSV File
    with open('%s.csv' % filename, 'wb') as csvfile:
        row_writer = UnicodeWriter(csvfile, quoting=csv.QUOTE_NONE)
        row_writer.writerow(['Well', 'Sample Type', 'Cell Type',
                             'Drug', 'Value', 'Unit'])

        for drug_value in drug_values:
            content = drug_value.getparent()
            well = content.getparent()
            control = well.xpath(
                "Columbus:Content[@ContentID='Control_2']/Columbus:Value",
                namespaces=namespaces)[0]
            celltype = well.xpath(
                "Columbus:Content[@ContentID='Celltype_3']/Columbus:Value",
                namespaces=namespaces)[0]

            # Require that none of these fields are None
            if well.get('WellID') is None:
                print 'WellID can not be None'
                exit(1)
            if control.text is None:
                print 'Sample Type can not be None'
                exit(1)
            if celltype.text is None:
                print 'Cell Type can not be None'
                exit(1)
            if content.get('ContentID') is None:
                print 'Drug can not be None'
                exit(1)
            if drug_value.text is None:
                print 'Value can not be None'
                exit(1)

            # Lookup drug name for alias
            drug_alias = drug_aliases[content.get('ContentID')]

            # Note: Unit can be None and is simply replaced with 'N/A'
            row = [well.get('WellID').upper(), control.text, celltype.text,
                   drug_alias, drug_value.text,
                   drug_value.get('Unit', 'N/A')]

            # write row
            row_writer.writerow(row)

def main():
    args = parser.parse_args()
    for f in args.files:
        convert_file(f)

if __name__ == "__main__":
    main()