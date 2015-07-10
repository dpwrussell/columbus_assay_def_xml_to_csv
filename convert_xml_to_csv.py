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
        """Columbus:Registration/Columbus:Content[@GroupName='Drug'
                                                  or @GroupName='drug']""",
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

    drug_names_not = ' and '.join(["not(@ContentID='%s')" % drug.get('ID')
                                  for drug in drugs])

    data = {}
    other_headers = set([])

    # Get the drug in any well which has a drug value
    for drug_value in drug_values:
        content = drug_value.getparent()
        # Get the well that this drug is in
        well = content.getparent()

        # Some basic tests of data integrity
        if well.get('WellID') is None:
            print 'WellID can not be None'
            exit(1)
        if drug_value.text is None:
            print 'Value can not be None'
            exit(1)
        if content.get('ContentID') is None:
            print 'Drug can not be None'
            exit(1)

        # Lookup drug name for alias
        try:
            drug_alias = drug_aliases[content.get('ContentID')]
        except KeyError as e:
            print 'Drug must be present in the registration data'
            exit(1)

        # Create a store of all the data which has been parsed
        data[well.get('WellID')] = {
            'drug': drug_alias,
            'value': drug_value.text,
            # Note: Unit can be None
            'unit': drug_value.get('Unit', ''),
            'other': {}
        }

        # Determine what other Content columns there are which
        # are not drugs
        other_columns = well.xpath(
            "Columbus:Content[%s]" % drug_names_not,
            namespaces=namespaces)

        for other_column in other_columns:
            other_column_name = other_column.get('ContentID').split('_')[0]
            other_headers.add(other_column_name)
            value = other_column.xpath("Columbus:Value/text()[1]",
                                       namespaces=namespaces)[0]
            data[well.get('WellID')]['other'][other_column_name] = value



    # Write the CSV File
    with open('%s.csv' % filename, 'wb') as csvfile:
        row_writer = UnicodeWriter(csvfile, quoting=csv.QUOTE_NONE)

        header = ['Well', 'Drug', 'Value', 'Unit']
        header.extend(other_headers)
        row_writer.writerow(header)

        for well, well_data in data.iteritems():
            row = [well, well_data['drug'],
                   well_data['value'],
                   well_data['unit']]

            for other_header in other_headers:
                row.append(well_data['other'].get(other_header, ''))

            # write row
            row_writer.writerow(row)

def main():
    args = parser.parse_args()
    for f in args.files:
        convert_file(f)

if __name__ == "__main__":
    main()