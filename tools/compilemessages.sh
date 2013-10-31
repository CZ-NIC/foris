#!/bin/bash
for lang_dir in locale/*; do
	locale_dir=$lang_dir/LC_MESSAGES/
	for file in $locale_dir/*.po; do
		msgfmt $file -o ${file%.*}.mo
	done
done
