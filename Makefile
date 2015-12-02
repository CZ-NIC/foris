# Foris - web administration interface for OpenWrt based on NETCONF
# Copyright (C) 2013 CZ.NIC, z.s.p.o. <http://www.nic.cz>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

COMPILED_CSS = $(wildcard foris/static/css/*)

COMPILED_L10N = $(wildcard foris/locale/*/LC_MESSAGES/*.mo)

JS_FILES = $(filter-out %.min.js $(wildcard foris/static/js/contrib/*),$(wildcard \
	foris/static/js/*.js \
	foris/static/js/**/*.js \
))

JS_MINIFIED = $(JS_FILES:.js=.min.js)


PRE_TPL_FILES = $(wildcard \
	foris/templates/*.pre.tpl \
	foris/templates/**/*.pre.tpl \
)

TPL_FILES = $(PRE_TPL_FILES:.pre.tpl=.tpl)

JS_MINIFIER = slimit -m

SASS_COMPILER = compass compile -s compressed -e production


all: compile-sass minify-js localization preprocess-tpl

# target: minify-js - Create minified JS files using slimit JS compressor.
minify-js: $(JS_FILES) $(JS_MINIFIED)

# target: preprocess-tpl - Do preprocessing of .pre.tpl files.
preprocess-tpl: $(PRE_TPL_FILES) $(TPL_FILES)

# target: compile-sass - Compile SASS files to CSS files using SASS/Compass compiler.
compile-sass:
	@cd foris/static/; \
	echo '-- Running compass $<';\
	$(SASS_COMPILER)
	@echo

# target: localization - Create .mo files from .po fiels in locale directory
localization:
	@echo "-- Compiling localization files"
	@tools/compilemessages.sh foris
	@echo "Done."
	@echo

%.tpl: %.pre.tpl
	@echo '-- Preprocessing template $<'
	tools/preprocess_template.sh $< > $@
	@echo

%.min.js: %.js
	@echo '-- Minifying $<'
	$(JS_MINIFIER) $< > $@
	@echo

# target: clean - Remove all compiled CSS, JS and localization files.
clean:
	rm -rf $(COMPILED_CSS) $(COMPILED_L10N) $(JS_MINIFIED) $(TPL_FILES)

# target: help - Show this help.
help:
	@egrep "^# target:" Makefile
