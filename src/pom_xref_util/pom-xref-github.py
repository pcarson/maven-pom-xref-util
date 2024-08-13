#
# Read GitHub repos for projects.
# - cross-reference all library versions used in all src ....
#
# see https://docs.github.com/en/rest/reference/repos#contents
#
#
import argparse
import base64
import datetime
import json
import tempfile
import os

import requests
import xmltodict

from pom_xref_util.modules.output_handler import htmlwriter
from pom_xref_util.modules.pom_parser.pomparser import PomParser
from pom_xref_util.utils.constants import Constants

# from https://github.com/user/settings/tokens
# it seems max page size at gitHub is 100 by default!!!!
# watch out here i ...
page_size = 100
library_details = []
repository_list = []
#
gh_session = None
#
# from parameters
git_username = None
git_token = None
arg_repo_prefix = None
git_branches = ['master', 'release']
ignore_repos = []
ignore_archived_projects = False
ignore_private_projects = False
# we assume the script is run from the src directory, so 'one up' is to the root
output_file_name = os.path.join('..', 'results',
                                datetime.datetime.now().replace(microsecond=0).isoformat()
                                + '-maven-xref-github.html')
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
        print('Missing parameters - in the ''src'' directory run "python3 -m pom_xref_util.pom-xref-github -h" '
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

    # it seems max page size at gitHub is 100 by default!!!!
    # watch out here i ...
    while len(repos) >= page_size:
        # go again, try the next page
        page_number += 1
        repos = do_github_repo_query(page_number)
        process_repo_names(repos)

    for branch in git_branches:
        process_repositories_for_branch(branch)

    htmlwriter.write_html_format_results(library_details,
                                         repository_list,
                                         pom_parser,
                                         output_file_name,
                                         False,
                                         git_branches)


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
        if we_do_process_this_repo(repo[Constants.NAME_CONST]):
            # if 'language' in repo:
            # if repo['language'] is not None and (repo['language'] == 'Java'):
            # OK, also get owner  ...
            owner = None
            if 'owner' in repo:
                owner_object = repo['owner']
                owner = owner_object['login']
            if private_or_archived(archived, private):
                print('Ignoring ' + repo[Constants.NAME_CONST] + ' as it is archived or private')
            else:
                repository_list.append(
                    {Constants.NAME_CONST: repo[Constants.NAME_CONST], 'owner': owner, 'url': repo['url']})


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
    # retrieve the pom.xml from gitHub
    pom_metadata_as_json = json.loads(
        retrieve_pom_file_for(lib_repo['owner'], lib_repo[Constants.NAME_CONST], 'pom.xml', branch))
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
                print('exception - xmltodict problem with ' + lib_repo[Constants.NAME_CONST])
    return xml_doc


#
# retrieve the pom.xml file from gitHub
#
def retrieve_pom_file_for(repo_owner, repo_name, path, branch):
    repos_url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{path}?ref={branch}'
    response = gh_session.get(repos_url)
    return response.text


# MAIN

# First of all
parse_command_line_arguments()
