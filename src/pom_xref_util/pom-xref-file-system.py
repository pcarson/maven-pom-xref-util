#
# Read a directory of maven projects and process the pom.xml files.
# - cross-reference all library versions used in all src ....
#
#
import argparse
import datetime
import os

import xmltodict

from pom_xref_util.modules.output_handler import htmlwriter
from pom_xref_util.modules.pom_parser.pomparser import PomParser
from pom_xref_util.utils.constants import Constants

library_details = []
repository_list = []
#
# from parameters
arg_source_directory = None
arg_repo_prefix = None
ignore_repos = []
# we assume the script is run from the src directory, so 'one up' is to the root
output_file_name = os.path.join('..', 'results',
                                datetime.datetime.now().replace(microsecond=0).isoformat()
                                + '-maven-xref-file-system.html')
#
pom_parser = PomParser()


def parse_command_line_arguments():
    global arg_source_directory, arg_repo_prefix, ignore_repos
    # create parser
    parser = argparse.ArgumentParser()
    # add arguments to the parser
    parser.add_argument('--source_directory', '-d', help='directory containing maven projects')
    parser.add_argument('--repo_prefix', '-p',
                        help='process all/any repositories with this prefix, e.g. company-name-')
    parser.add_argument('--repo_list_to_ignore', '-i',
                        help='comma separated list of repositories to be ignored, e.g. repo-one,repo-three')

    # parse the arguments
    args = parser.parse_args()

    # get the arguments value
    if args.source_directory is not None:
        arg_source_directory = args.source_directory
    if args.repo_prefix is not None:
        arg_repo_prefix = args.repo_prefix
    if args.repo_list_to_ignore is not None:
        # should be comma delimited list
        ignore_repos = args.repo_list_to_ignore.split(",")

    if arg_source_directory is None:
        print('Missing parameters - in the ''src'' directory run "python3 -m pom_xref_util.pom-xref-file-system -h" '
              'for parameter information')
    else:
        print(
            f'Executing for git repository prefix {arg_repo_prefix}, '
            f'see {output_file_name} for output')
        print(f'-> ignoring {ignore_repos}')
        start()


def start():
    global repository_list
    for root, dirs, files in os.walk(arg_source_directory):
        for file in files:
            if file == 'pom.xml':
                split_root = os.path.split(root)
                if split_root is not None and split_root[0] == arg_source_directory:
                    # source_directory == split_root if we're just 1 level down from root ....
                    repository_list.append({Constants.NAME_CONST: split_root[1],
                                            'owner': 'owner',
                                            'url': os.path.join(root, 'pom.xml')})

    process_repositories_for_branch()
    htmlwriter.write_html_format_results(library_details,
                                         repository_list,
                                         pom_parser,
                                         output_file_name,
                                         True,
                                         [])


def we_do_process_this_repo(repo_name):
    if arg_repo_prefix is not None:
        if arg_repo_prefix in repo_name:
            if repo_name not in ignore_repos:
                return True
    else:
        if repo_name not in ignore_repos:
            return True

    return False


#
# Look at all services to analyse their use of libs
#
def process_repositories_for_branch():
    global library_details
    for client_repo in repository_list:
        xml_doc = handle_xml_content(client_repo['url'])
        if xml_doc is not None:
            pom_parser.process_xml_content(Constants.FILE_SYSTEM_CONST, client_repo, xml_doc)
        else:
            client_repo.update({Constants.FILE_SYSTEM_CONST + '_pom_exists': False})

    library_details = pom_parser.get_library_details()


#
# return an XML dictionary representation of the related pom file - or None
#
def handle_xml_content(pom_url):
    xml_doc = None
    # retrieve the pom.xml from file system
    with open(pom_url) as fd:
        try:
            xml_doc = xmltodict.parse(fd.read())
        except Exception:
            print(f'exception - xmltodict problem with {pom_url}')

    return xml_doc


# MAIN

# First of all
parse_command_line_arguments()
