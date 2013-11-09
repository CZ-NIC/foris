#!/bin/bash
if [ $# -eq 1 ]
then
	lang=$1
	locale_dir="locale/$lang/LC_MESSAGES"
	if [ ! -d $locale_dir ]
	then
		mkdir -p $locale_dir
	fi
	find \( -iname "*.py" -o -iname "*.tpl" \) -exec cat {} \; | sed 's/"*{{ _\(("[^"]*")\) }}"*/\n_\1\n/g' | \
		xgettext -d messages --no-location --language=Python --from-code=UTF-8 --output=$locale_dir/tmp_messages.pot -
	if [ -f $locale_dir/messages.po ]
	then
		echo "Making messages in $locale_dir."
		msgmerge -q -U $locale_dir/messages.po $locale_dir/tmp_messages.pot
		rm $locale_dir/tmp_messages.pot
	else
		mv $locale_dir/tmp_messages.pot $locale_dir/messages.po
	fi
	echo "Message making completed."
else
	echo "No language specified - use '$0 LANGUAGE'"
fi
