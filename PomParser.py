#
# Analyse and collate POM library details
#


class PomParser:
    # class variable as only 1 possible user
    library_details = []

    # Constants
    NAME_CONST = 'name'
    VERSION_CONST = 'version'
    CLIENT_CONST = 'client'
    HIGHEST_CONST = 'highest'
    DEPENDENCY_MANAGEMENT_CONST = 'dependencyManagement'
    DEPENDENCIES_CONST = 'dependencies'
    DEPENDENCY_CONST = 'dependency'
    PLUGINS_CONST = 'plugins'
    PLUGIN_CONST = 'plugin'
    PROJECT_CONST = 'project'
    PARENT_CONST = 'parent'
    BUILD_CONST = 'build'

    def __init__(self):
        PomParser.library_details = []

    #
    # Look at all services to analyse their use of libs
    #
    def process_xml_content(self, branch, client_repo, xml_doc):

        if xml_doc is not None:
            # look for each of the lib libraries being used here ....
            # if xml_doc['project']['artifactId']} ...
            client_repo.update({branch + '_pom_exists': True})
            dependency_list = xml_doc[PomParser.PROJECT_CONST][PomParser.DEPENDENCIES_CONST][PomParser.DEPENDENCY_CONST]
            self.process_dependency_list_for(client_repo[PomParser.NAME_CONST],
                                             dependency_list,
                                             branch,
                                             xml_doc)
            if PomParser.PLUGINS_CONST in xml_doc[PomParser.PROJECT_CONST][PomParser.BUILD_CONST]:
                plugin_list = xml_doc[PomParser.PROJECT_CONST][PomParser.BUILD_CONST][PomParser.PLUGINS_CONST][PomParser.PLUGIN_CONST]
                self.process_dependency_list_for(client_repo[PomParser.NAME_CONST],
                                                 plugin_list,
                                                 branch,
                                                 xml_doc)
            # also check the 'parent' structure
            if PomParser.PARENT_CONST in xml_doc[PomParser.PROJECT_CONST]:
                parent_list = xml_doc[PomParser.PROJECT_CONST][PomParser.PARENT_CONST]
                self.process_dependency_list_for(client_repo[PomParser.NAME_CONST],
                                                 parent_list,
                                                 branch,
                                                 xml_doc)
            # and the 'dependencyManagement' structure
            if PomParser.DEPENDENCY_MANAGEMENT_CONST in xml_doc[PomParser.PROJECT_CONST]:
                if PomParser.DEPENDENCIES_CONST in xml_doc[PomParser.PROJECT_CONST][PomParser.DEPENDENCY_MANAGEMENT_CONST]:
                    dependency_management_list = xml_doc[PomParser.PROJECT_CONST][PomParser.DEPENDENCY_MANAGEMENT_CONST][PomParser.DEPENDENCIES_CONST][PomParser.DEPENDENCY_CONST]
                    self.process_dependency_list_for(client_repo[PomParser.NAME_CONST],
                                                     dependency_management_list,
                                                     branch,
                                                     xml_doc)
        else:
            # no XML pom file - remove the repo (NO)?
            client_repo.update({branch + '_pom_exists': False})
            print('Ignoring ' + client_repo[PomParser.NAME_CONST]
                  + ' for branch '
                  + branch
                  + ' as either '
                  + '1) the branch does not exist or '
                  + '2) it does not seem to be a maven repo - no pom.xml file found.'
                  )
            # DO NOT REMOVE - some lib repos may only exist as master
            # repository_list.remove(client_repo)

        return client_repo

    @staticmethod
    def get_library_details():
        return PomParser.library_details

    #
    # iterate through the dependencies listed in the pom
    # if we find the one we're looking for, return the version
    #
    def process_dependency_list_for(self, client_name, dependency_list, branch, xml_doc):

        client_list_name = branch + '_client_list'
        list_of_dependencies = []
        if type(dependency_list) != list:
            # i.e. only 1 item ... method expects a list, so make it a list
            list_of_dependencies.append(dependency_list)
        else:
            list_of_dependencies = dependency_list
        for dependency in list_of_dependencies:
            client_list = []
            if 'artifactId' in dependency:
                artifact_name = dependency['artifactId']
                if PomParser.VERSION_CONST in dependency:
                    # it's the one that we want, return it
                    updated_version = dependency[PomParser.VERSION_CONST]
                    if updated_version.startswith('$'):
                        # it's a variable - so get the value from the properties section of the pom
                        updated_version = updated_version.replace('${', '').replace('}', '')
                        try:
                            updated_version = xml_doc[PomParser.PROJECT_CONST]['properties'][updated_version]
                        except KeyError:
                            # do nothing
                            print(f'Error trying to find {updated_version} in pom.xml for project {client_name}')
                    client_detail = {PomParser.CLIENT_CONST: client_name, PomParser.VERSION_CONST: updated_version}
                    client_list.append(client_detail)
                    # update library detail with client list

                    # update library details with this library_detail
                    check_library_detail = get_library_from_list(artifact_name)
                    if check_library_detail is None:
                        # then it needs to be added
                        library_detail = {PomParser.NAME_CONST: artifact_name,
                                          PomParser.HIGHEST_CONST: updated_version,
                                          client_list_name: client_list}
                        PomParser.library_details.append(library_detail)
                    else:
                        # We need to update the existing library detail in place with the updated client list
                        try:
                            updated_client_list = check_library_detail[client_list_name]
                        except KeyError:
                            # default empty list
                            updated_client_list = []
                        updated_client_list.append(client_detail)
                        highest_version = self.return_highest(updated_version, artifact_name)
                        check_library_detail.update({PomParser.NAME_CONST: artifact_name,
                                                     PomParser.HIGHEST_CONST: highest_version,
                                                     client_list_name: updated_client_list})

    def return_highest(self, first, library_name):
        for library in PomParser.library_details:
            if library[PomParser.NAME_CONST] == library_name:
                # check if it is a list or string ...
                this_version = self.return_highest_version(library[PomParser.HIGHEST_CONST])
                updated_version = self.return_highest_version(first)
                this_array = [updated_version, this_version]
                try:
                    tuple_list = self.convert_version_list_to_tuple_list_if_numeric(this_array)
                    try:
                        re_stringed = self.tuple_version_to_string(sorted(tuple_list, reverse=True)[0])
                        if re_stringed in this_version:
                            # prefer the original which may have contained SNAPSHOT | RELEASE etc.
                            return this_version
                        if re_stringed in updated_version:
                            # prefer the original which may have contained SNAPSHOT | RELEASE etc.
                            return updated_version
                        return re_stringed
                    except IndexError:
                        print(f'IndexError trying to sort {this_array} for {library_name}')
                except TypeError | IndexError:
                    # do nothing
                    print(f'TypeError trying to sort {this_array} for {library_name}')

        return first

    def return_highest_version(self, test_version):
        this_type = type(test_version).__name__
        if this_type == 'list':
            try:
                tuple_list = self.convert_version_list_to_tuple_list_if_numeric(test_version)
                self.tuple_version_to_string(sorted(tuple_list, reverse=True)[0])
            except TypeError:
                # do nothing
                print(f'TypeError trying to sort {test_version}')

        # otherwise
        return test_version

    @staticmethod
    def convert_version_list_to_tuple_list_if_numeric(version_list):
        tuple_list = []
        try:
            for item in version_list:
                first_item = item.split('-')[0]  # remove any SNAPSHOT | RELEASE | Final .....
                first_item = first_item.split('_')[0]
                filled = []
                for point in first_item.split('.'):
                    try:
                        filled.append(int(point))
                    except ValueError:
                        print(f'Could not cast {point} to an int - ignoring')
                tuple_list.append(tuple(filled))
        except AttributeError:
            print(f'Could not cast {version_list} to a tuple - ignoring')
        return tuple_list

    @staticmethod
    def tuple_version_to_string(tuple_version):
        reconstituted_version = ''
        for component in tuple_version:
            reconstituted_version = reconstituted_version + str(component) + "."
        return reconstituted_version[:-1]


#
# see if the client name is in the library client list
#
def get_library_from_list(artifact_name):
    for artifact in PomParser.library_details:
        if artifact[PomParser.NAME_CONST] == artifact_name:
            # it's a match ... return the version
            return artifact

    return None


#
# get the highest version in use
#
def find_highest_version(artifact_name):
    for artifact in PomParser.library_details:
        if artifact[PomParser.NAME_CONST] == artifact_name:
            # it's a match ... return the version
            return artifact

    return None
