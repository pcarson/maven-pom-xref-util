# check-maven-pom-xref-all.py

A simple python utility (Disclaimer: I'm a Java with maven developer not a Python developer) to read 
* GitHub repos for all MAVEN projects with a given prefix 
OR
* A nominated local directory containing maven based projects and 
  - get the relevant pom.xml for repo/branch
  - cross-reference all library dependencies ...
  - produce in the 'results' sub-directory (which you may have to create)
    - an html xref of all selected repos to show which version of which library is used in which project

# dependencies

```commandline

```

# to run

## option 1 - GitHub
### dependencies
```commandline
import argparse
import base64
import datetime
import json
import os
import tempfile
from io import StringIO
import requests
import xmltodict
```
### GitHub security
The script expects to be supplied with a git username and a git PAT 'personal access token' which has access to all relevant repositories to be queried.
See Github https://github.com/settings/tokens

### command line parameters
e.g.:
```
python3 check-maven-pom-xref-github.py -u=<git username> -t=<github PAT> -p=<repo prefix to select, empty for all> -b=<comma separated list of branches to include> -i=<comma-separated list of repositories to IGNORE - no spaces between the repo names, just a comma>
```
for more parameter information:
```
python3 check-maven-pom-xref-github.py --help
```

## option 2 - File System
### dependencies
```commandline
import argparse
import datetime
import os
from io import StringIO
import xmltodict
```
### Requirements
The script expects to be supplied with a local directory name containing all relevant repositories to be queried.

It will process only the top level projects within that directory, e.g.
```commandline
source-directory
->  maven-project-one
    .....
    pom.xml
->  maven-project-two
    .....
    pom.xml
```

### command line parameters
e.g.:
```
python3 check-maven-pom-xref-file-system.py -d=/home/maven-projects/source-directory -p=<repo prefix to select, empty for all> -i=<comma-separated list of repositories to IGNORE - no spaces between the repo names, just a comma>
```
for more parameter information:
```
python3 check-maven-pom-xref-file-system.py --help
```
