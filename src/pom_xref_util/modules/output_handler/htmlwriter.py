#
# Write the output file
#
import os
from io import StringIO

from pom_xref_util.utils.constants import Constants

#
output_file = None


#
# and ... produce a tabulation of results
#
def write_html_format_results(library_details,
                              repository_list,
                              pom_parser,
                              output_file_name,
                              file_system_source,
                              git_branches):
    global output_file
    if not os.path.exists(os.path.dirname(output_file_name)):
        os.makedirs(os.path.dirname(output_file_name))
    output_file = open(output_file_name, 'w')
    _print_to_output_file('<html>')
    _print_to_output_file('<body>')
    _print_to_output_file('<p>')
    _print_to_output_file('Library versions in use by projects/services')
    _print_to_output_file('</p>')
    _print_to_output_file('<table border="1">')
    _print_to_output_file('<tr>')
    _print_to_output_file('<td>Key:</td>')
    _print_to_output_file(
        f'<td style = {Constants.NO_POM_COLOUR}>pom.xml or project not found in the specified branch. '
        f'If not present in all branches, consider ignoring the project with the -i= runtime parameter.</td>')
    _print_to_output_file('</tr>')
    _print_to_output_file('<tr>')
    _print_to_output_file('<td>Key:</td>')
    _print_to_output_file(
        f'<td style = {Constants.HIGHEST_VERSION_COLOUR}>highest version in use in your code base (i.e. NOT the '
        f'highest version available in external maven repos) - NOTE that this is derived by arbitrarily stripping '
        f'SNAPSHOT, RELEASE etc. from a version number and trying to sort only on the numerical component</td>')
    _print_to_output_file('</tr>')
    _print_to_output_file('</table>')
    _print_to_output_file('<table border="1">')
    # headers
    # data
    # do master first, release next ....
    if file_system_source is True:
        _process_client_libs_for_branch(library_details, repository_list, Constants.FILE_SYSTEM_CONST, pom_parser)
    else:  # GitHub
        for branch in git_branches:
            _process_client_libs_for_branch(library_details, repository_list, branch, pom_parser)
    _print_to_output_file('</table>')
    _print_to_output_file('</body>')
    _print_to_output_file('</html>')


#
# produce 1 table for each branch processed
#
def _process_client_libs_for_branch(library_details, repository_list, branch, pom_parser):
    file_str = StringIO()
    repository_list.sort(key=_repository_sort_key)
    num_columns = len(repository_list) + 2
    file_str.write('<tr colspan=' + str(num_columns) + '><td><b>' + branch + '</b></td></tr>')
    file_str.write('<th>Library</th>')
    file_str.write('<th>Highest version in use</th>')
    for client_repo in repository_list:
        file_str.write('<th>')
        file_str.write(client_repo[Constants.NAME_CONST])
        file_str.write('</th>')
    file_str.write('</tr>')
    _print_to_output_file(file_str.getvalue())
    library_details.sort(key=_library_sort_key)
    for lib in library_details:
        _write_a_library_use_line(lib, repository_list, branch, pom_parser)


def _write_a_library_use_line(library, list_of_clients, branch, pom_parser):
    client_list_label = branch + '_client_list'
    pom_exists_label = branch + '_pom_exists'
    file_str = StringIO()
    file_str.write('<tr>')
    file_str.write('<td>' + library[Constants.NAME_CONST] + '</td>')
    file_str.write(
        f'<td style = {Constants.HIGHEST_VERSION_COLOUR}>{pom_parser.return_highest_version(library["highest"])}</td>')
    # for every client of this library ......
    for client_repo in list_of_clients:
        # default empty for nulls/None
        client_list = []
        if client_list_label in library:
            client_list = library[client_list_label]
        version_in_use = _get_version_for_matched_client(client_repo[Constants.NAME_CONST], client_list)
        if version_in_use is not None:
            if version_in_use == library[Constants.HIGHEST_CONST]:
                file_str.write(f'<td style = {Constants.HIGHEST_VERSION_COLOUR}>{version_in_use}</td>')
            else:
                file_str.write('<td>' + version_in_use + '</td>')
        else:
            # no match
            if pom_exists_label in client_repo and not client_repo[pom_exists_label]:
                # no pom exists in this branch
                file_str.write(f'<td style = {Constants.NO_POM_COLOUR}>')
            else:
                file_str.write('<td>')
            file_str.write('&nbsp;')
            file_str.write('</td>')
    file_str.write('</tr>')
    _print_to_output_file(file_str.getvalue())


#
# see if the client name is in the library client list
#
def _get_version_for_matched_client(client_name, client_list):
    for client in client_list:
        try:
            if Constants.CLIENT_CONST in client:
                if client[Constants.CLIENT_CONST] == client_name:
                    # it's a match ... return the version
                    if Constants.VERSION_CONST in client:
                        return str(client[Constants.VERSION_CONST])
        except TypeError:
            # do nothing
            print(f'TypeError looking for {client_name} in {client}')

    return None


def _library_sort_key(library):
    return library[Constants.NAME_CONST]


def _repository_sort_key(repository):
    return repository[Constants.NAME_CONST]


#
# utility method
#
def _print_to_output_file(line):
    print(line, file=output_file)
