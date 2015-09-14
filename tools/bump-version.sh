#!/bin/sh
PREV=$(git tag | grep "package-v" | sed 's/package-v//' | sort -n | tail -1)

NEXT=$(( ${PREV} + 1 ))

( grep -q "^__version__ = ${PREV}$" foris/__init__.py ) || {
    echo "ERROR: version in last tag (package-v${PREV}) does not match version in __init__.py"
    exit 1
}

sed -i "s/^__version__ = ${PREV}$/__version__ = ${NEXT}/" foris/__init__.py
git commit -m "version: bumped to ${NEXT}" foris/__init__.py
git tag "package-v${NEXT}"
echo "\nVersion bumped to ${NEXT}. Check the commit and push the code and tags to server using:"\
"\n\n\tgit push\n\tgit push --tags\n"
