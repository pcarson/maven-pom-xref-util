#!/bin/sh
#
# Example script to generate effective pom files for all maven projects in the current directory/folder.
#
for i in */pom.xml; do (echo $i; mvn -f $i help:effective-pom -Doutput=effective-pom.xml;); done
