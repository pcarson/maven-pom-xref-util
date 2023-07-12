#
# Read a directory of maven projects and process the pom.xml files.
# - cross reference all library versions used in all src ....
#
#
import argparse
import datetime
import os
from io import StringIO

import xmltodict

from PomParser import PomParser

library_details = []
repository_list = []
#
#
output_file = None
# from parameters
arg_source_directory = None
arg_repo_prefix = None
ignore_repos = []
#
output_file_name = 'results/' + datetime.datetime.now().replace(microsecond=0).isoformat() \
                   + '-maven-xref-file-system.html'
#
highest_version_colour = 'background-color:red;color:white;'
no_pom_colour = 'background-color:yellowgreen;color:white;'
# Constants
FILE_SYSTEM_CONST = 'file-system'
NAME_CONST = 'name'
VERSION_CONST = 'version'
CLIENT_CONST = 'client'
HIGHEST_CONST = 'highest'
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
        print('Missing parameters - run "python3 check-maven-pom-xref-file-system.py -h" '
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
                    repository_list.append({NAME_CONST: split_root[1],
                                            'owner': 'owner',
                                            'url': os.path.join(root, 'pom.xml')})

    process_repositories_for_branch()
    write_html_format_results()


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
            pom_parser.process_xml_content(FILE_SYSTEM_CONST, client_repo, xml_doc)
        else:
            client_repo.update({FILE_SYSTEM_CONST + '_pom_exists': False})

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


#
# produce 1 table for each branch processed
#
def process_client_libs_for_branch(branch):
    file_str = StringIO()
    repository_list.sort(key=repository_sort_key)
    num_columns = len(repository_list) + 2
    file_str.write('<tr colspan=' + str(num_columns) + '><td><b>' + branch + '</b></td></tr>')
    file_str.write('<th>Library</th>')
    file_str.write('<th>Highest version in use</th>')
    for client_repo in repository_list:
        file_str.write('<th>')
        file_str.write(client_repo[NAME_CONST])
        file_str.write('</th>')
    file_str.write('</tr>')
    print_to_output_file(file_str.getvalue())
    library_details.sort(key=library_sort_key)
    for lib in library_details:
        write_a_library_use_line(lib, repository_list, branch)


def library_sort_key(library):
    return library[NAME_CONST]


def repository_sort_key(repository):
    return repository[NAME_CONST]


def write_a_library_use_line(library, list_of_clients, branch):
    client_list_label = branch + '_client_list'
    pom_exists_label = branch + '_pom_exists'
    file_str = StringIO()
    file_str.write('<tr>')
    file_str.write('<td>' + library[NAME_CONST] + '</td>')
    file_str.write(f'<td style = {highest_version_colour}>{pom_parser.return_highest_version(library[HIGHEST_CONST])}</td>')
    # for every client of this library ......
    for client_repo in list_of_clients:
        # default empty for nulls/None
        client_list = []
        if client_list_label in library:
            client_list = library[client_list_label]
        version_in_use = get_version_for_matched_client(client_repo[NAME_CONST], client_list)
        if version_in_use is not None:
            if version_in_use == library[HIGHEST_CONST]:
                file_str.write(f'<td style = {highest_version_colour}>{version_in_use}</td>')
            else:
                file_str.write('<td>' + version_in_use + '</td>')
        else:
            # no match
            if pom_exists_label in client_repo and not client_repo[pom_exists_label]:
                # no pom exists in this branch
                file_str.write(f'<td style = {no_pom_colour}>')
            else:
                file_str.write('<td>')
            file_str.write('&nbsp;')
            file_str.write('</td>')
    file_str.write('</tr>')
    print_to_output_file(file_str.getvalue())


#
# and ... produce a tabulation of results
#
def write_html_format_results():
    global output_file, output_file_name
    if not os.path.exists(os.path.dirname(output_file_name)):
        os.makedirs(os.path.dirname(output_file_name))
    output_file = open(output_file_name, 'w')
    print_to_output_file('<html>')
    print_to_output_file('<body>')
    print_to_output_file('<p>')
    print_to_output_file('Library versions in use by projects/services in ' + arg_source_directory)
    print_to_output_file('</p>')
    print_to_output_file('<table border="1">')
    print_to_output_file('<tr>')
    print_to_output_file('<td>Key:</td>')
    print_to_output_file(
        f'<td style = {no_pom_colour}>pom.xml or project not found in the specified branch. If not present in all '
        f'branches, consider ignoring the project with the -i= runtime parameter.</td>')
    print_to_output_file('</tr>')
    print_to_output_file('<tr>')
    print_to_output_file('<td>Key:</td>')
    print_to_output_file(
        f'<td style = {highest_version_colour}>highest version in use in your code base (i.e. NOT the highest version '
        f'available in external maven repos) - NOTE that this is derived by arbitrarily stripping SNAPSHOT, RELEASE '
        f'etc. from a version number and trying to sort only on the numerical component</td>')
    print_to_output_file('</tr>')
    print_to_output_file('</table>')
    print_to_output_file('<table border="1">')
    # headers
    # data
    process_client_libs_for_branch(FILE_SYSTEM_CONST)
    print_to_output_file('</table>')
    print_to_output_file('</body>')
    print_to_output_file('</html>')


#
# see if the client name is in the library client list
#
def get_version_for_matched_client(client_name, client_list):
    for client in client_list:
        try:
            if CLIENT_CONST in client:
                if client[CLIENT_CONST] == client_name:
                    # it's a match ... return the version
                    if VERSION_CONST in client:
                        return str(client[VERSION_CONST])
        except TypeError:
            # do nothing
            print(f'TypeError looking for {client_name} in {client}')

    return None


#
# see if the client name is in the library client list
#
def get_library_from_list(artifact_name):
    for artifact in library_details:
        if artifact[NAME_CONST] == artifact_name:
            # it's a match ... return the version
            return artifact

    return None


#
# get the highest version in use
#
def find_highest_version(artifact_name):
    for artifact in library_details:
        if artifact[NAME_CONST] == artifact_name:
            # it's a match ... return the version
            return artifact

    return None


#
# utility method
#
def print_to_output_file(line):
    print(line, file=output_file)


# MAIN

# First of all
parse_command_line_arguments()
