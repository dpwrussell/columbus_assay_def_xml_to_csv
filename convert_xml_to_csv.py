#!/usr/bin/env python

import xml.etree.ElementTree as ET
import csv, codecs, cStringIO

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

# Parse the input file
tree = ET.parse('2015-01-18 plate map_2-2.xml')

# Get the root of the tree
assay_definition = tree.getroot()

# Find the wells
wells = assay_definition.find('Wells')

# Write the CSV File
with open('outfile.csv', 'wb') as csvfile:
    row_writer = UnicodeWriter(csvfile, quoting=csv.QUOTE_NONE)
    row_writer.writerow(['WellID', 'Content', 'Value',
                         'Type (if exists for Content)',
                         'Unit (if exists for Content)'])

    for well in wells.iter('Well'):
        # Get all the Content elements for this well
        for content in well.iter("Content"):
            for content_value in content.iter("Value"):
                row = [ well.get('WellID'),
                        content.get('ContentID'),
                        content_value.text ]

                # If the content has Type and Units, add those (or None)
                row.append(content_value.get('Type', ''))
                row.append(content_value.get('Unit', ''))

                row_writer.writerow(row)
