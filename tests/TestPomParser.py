import os
import unittest

import xmltodict

from pom_xref_util.modules.pom_parser.pomparser import PomParser

#
# see https://docs.python.org/3/library/unittest.html
#

TESTDATA_FILENAME = os.path.join(os.path.dirname(__file__), 'sample.xml')


class TestPomParser(unittest.TestCase):
    """ Tests for PomParser """

    def setUp(self):
        self.testfile = open(TESTDATA_FILENAME)
        # parse the raw xml to a dictionary
        self.testdata = xmltodict.parse(self.testfile.read())
        self.testfile.close()
        # default
        self.target_client_repo = {'name': 'spring-boot-rest-jpa-metrics-demo', 'owner': 'pcarson',
                                   'url': 'https://api.github.com/repos/pcarson/spring-boot-rest-jpa-metrics-demo'}
        self.parser = PomParser()

    def test_xml_file_is_parsed_to_expose_library_details(self):
        # initially dependency list is empty
        self.assertEqual(0, len(PomParser.library_details))

        # parse/process the testdata
        self.parser.process_xml_content('master', self.target_client_repo, self.testdata)

        # processing XML content prepares 10 dependencies
        self.assertEqual(10, len(PomParser.library_details))

        # in this case, we expect the lombok version to match that in sample.xml
        self.assertEqual('1.18.26', self.parser.return_highest('', 'lombok'), 'Expected result 1.18.26 :tick')

    @unittest.skip("demonstrating skipping")
    def test_nothing(self):
        self.fail("shouldn't happen")
