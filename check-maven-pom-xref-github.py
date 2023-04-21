#
# Read GitHub repos for projects ..
# - cross reference all library versions used in all code ....
#
# see https://docs.github.com/en/rest/reference/repos#contents
#
#
import argparse
import base64
import datetime
import json
import os
import tempfile
from io import StringIO

import requests
import xmltodict

from PomParser import PomParser

# from https://github.com/user/settings/tokens
# it seems max page size at github is 100 by default!!!!
# watch out here i ...
page_size = 100
library_details = []
repository_list = []
#
gh_session = None
#
output_file = None
# from parameters
git_username = None
git_token = None
arg_repo_prefix = None
git_branches = ['master', 'release']
ignore_repos = []
ignore_archived_projects = False
ignore_private_projects = False
#
output_file_name = 'results/' + datetime.datetime.now().replace(microsecond=0).isoformat() + '-maven-xref-github.html'
#
highest_version_colour = "background-color:red;color:white;"
no_pom_colour = "background-color:yellowgreen;color:white;"
#
pom_parser = PomParser()


def parse_command_line_arguments():
    global git_username, git_token, arg_repo_prefix, git_branches
    global ignore_repos, ignore_archived_projects, ignore_private_projects
    # create parser
    parser = argparse.ArgumentParser()
    # add arguments to the parser
    parser.add_argument('--git_username', '-u', help='username at GitHub')
    parser.add_argument('--git_token', '-t', help='Personal Access Token from GitHub')
    parser.add_argument('--git_repo_prefix', '-p',
                        help='process all/any repositories with this prefix, e.g. company-name-')
    parser.add_argument('--git_branches', '-b', help='comma separated list of branches to process, e.g. master,release')
    parser.add_argument('--git_repo_list_to_ignore', '-i',
                        help='comma separated list of repositories to be ignored, e.g. repo-one,repo-three')
    parser.add_argument('--git_ignore_archived', '-ia',
                        help='ignore archived projects Y|N')
    parser.add_argument('--git_ignore_private', '-ip',
                        help='ignore private projects Y|N')

    # parse the arguments
    args = parser.parse_args()

    # get the arguments value
    if args.git_username is not None:
        git_username = args.git_username
    if args.git_token is not None:
        git_token = args.git_token
    if args.git_repo_prefix is not None:
        git_repo_prefix = args.git_repo_prefix
    if args.git_branches is not None:
        # should be comma delimited list
        git_branches = args.git_branches.split(",")
    if args.git_repo_list_to_ignore is not None:
        # should be comma delimited list
        ignore_repos = args.git_repo_list_to_ignore.split(",")
    if args.git_ignore_archived is not None and args.git_ignore_archived == 'Y':
        ignore_archived_projects = True
    if args.git_ignore_private is not None and args.git_ignore_private == 'Y':
        ignore_private_projects = True

    if git_username is None or git_token is None:
        print('Missing parameters - run "python3 check-maven-pom-library-version-use.py -h" '
              'for parameter information')
    else:
        print(
            f'Executing for git repository prefix {git_repo_prefix}, '
            f'branches {git_branches} '
            f'see {output_file_name} for output')
        print(f'-> ignoring {ignore_repos}')
        start()


def start():
    global gh_session

    # create a re-usable session object with the user creds in-built
    gh_session = requests.Session()
    gh_session.auth = (git_username, git_token)

    # get the list of repos belonging to me - default query first page

    # pagination ....
    page_number = 1
    repos = do_github_repo_query(page_number)
    process_repo_names(repos)

    # it seems max page size at github is 100 by default!!!!
    # watch out here i ...
    while len(repos) >= page_size:
        # go again, try the next page
        page_number += 1
        repos = do_github_repo_query(page_number)
        process_repo_names(repos)

    for branch in git_branches:
        process_repositories_for_branch(branch)

    write_html_format_results()


#
# retrieve repository details
#
def do_github_repo_query(page_number):
    repos_url = f'https://api.github.com/user/repos?per_page={page_size}&page={page_number}'
    response = gh_session.get(repos_url)
    repos = json.loads(response.text)
    return repos


#
# build lists of library projects and non-library projects
#
def process_repo_names(repos):
    global repository_list
    # process the repo names
    for repo in repos:
        private = False
        archived = False
        if 'private' in repo:
            private = repo['private']
        if 'archived' in repo:
            archived = repo['archived']
        if we_do_process_this_repo(repo['name']):
            # if 'language' in repo:
            # if repo['language'] is not None and (repo['language'] == 'Java'):
            # OK, also get owner  ...
            owner = None
            if 'owner' in repo:
                owner_object = repo['owner']
                owner = owner_object['login']
            if private_or_archived(archived, private):
                print('Ignoring ' + repo['name'] + ' as it is archived or private')
            else:
                repository_list.append({'name': repo['name'], 'owner': owner, 'url': repo['url']})


def private_or_archived(archived, private):
    if ignore_archived_projects is True and archived is True:
        return True
    if ignore_private_projects is True and private is True:
        return True
    return False


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
def process_repositories_for_branch(branch):
    global library_details
    for client_repo in repository_list:
        xml_doc = handle_xml_content(client_repo, branch)
        if xml_doc is not None:
            pom_parser.process_xml_content(branch, client_repo, xml_doc)
        else:
            client_repo.update({branch + '_pom_exists': False})

    library_details = pom_parser.get_library_details()


#
# return an XML dictionary representation of the related pom file - or None
#
def handle_xml_content(lib_repo, branch):
    xml_doc = None
    # retrieve the pom.xml from github
    pom_metadata_as_json = json.loads(retrieve_pom_file_for(lib_repo['owner'], lib_repo['name'], 'pom.xml', branch))
    # process the base64 content (i.e. XML in base64)
    if 'content' in pom_metadata_as_json:
        xml_content = base64.b64decode(pom_metadata_as_json['content'])
        fp = tempfile.NamedTemporaryFile()
        # NB write requires binary format - it is already in binary
        fp.write(xml_content)
        fp = tempfile.NamedTemporaryFile()
        # NB write requires binary format - it is already in binary
        fp.write(xml_content)
        with open(fp.name) as fd:
            try:
                xml_doc = xmltodict.parse(fd.read())
            except Exception:
                print('exception - xmltodict problem with ' + lib_repo['name'])
    return xml_doc


#
# retrieve the pom.xml file from github
#
def retrieve_pom_file_for(repo_owner, repo_name, path, branch):
    repos_url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{path}?ref={branch}'
    response = gh_session.get(repos_url)
    return response.text


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
        file_str.write(client_repo['name'])
        file_str.write('</th>')
    file_str.write('</tr>')
    print_to_output_file(file_str.getvalue())
    library_details.sort(key=library_sort_key)
    for lib in library_details:
        write_a_library_use_line(lib, repository_list, branch)


def library_sort_key(library):
    return library['name']


def repository_sort_key(repository):
    return repository['name']


def write_a_library_use_line(library, list_of_clients, branch):
    client_list_label = branch + '_client_list'
    pom_exists_label = branch + '_pom_exists'
    file_str = StringIO()
    file_str.write('<tr>')
    file_str.write('<td>' + library['name'] + '</td>')
    file_str.write(f'<td style = {highest_version_colour}>{pom_parser.return_highest_version(library["highest"])}</td>')
    # for every client of this library ......
    for client_repo in list_of_clients:
        # default empty for nulls/None
        client_list = []
        if client_list_label in library:
            client_list = library[client_list_label]
        version_in_use = get_version_for_matched_client(client_repo['name'], client_list)
        if version_in_use is not None:
            if version_in_use == library['highest']:
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
    print_to_output_file('Library versions in use by projects/services')
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
    # do master first, release next ....
    for branch in git_branches:
        process_client_libs_for_branch(branch)
    print_to_output_file('</table>')
    print_to_output_file('</body>')
    print_to_output_file('</html>')


#
# see if the client name is in the library client list
#
def get_version_for_matched_client(client_name, client_list):
    for client in client_list:
        try:
            if 'client' in client:
                if client['client'] == client_name:
                    # it's a match ... return the version
                    if 'version' in client:
                        return str(client['version'])
        except TypeError:
            # do nothing
            print(f'TypeError looking for {client_name} in {client}')

    return None


#
# see if the client name is in the library client list
#
def get_library_from_list(artifact_name):
    for artifact in library_details:
        if artifact['name'] == artifact_name:
            # it's a match ... return the version
            return artifact

    return None


#
# get the highest version in use
#
def find_highest_version(artifact_name):
    for artifact in library_details:
        if artifact['name'] == artifact_name:
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
