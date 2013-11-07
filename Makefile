COMPILED_CSS = $(wildcard static/css/*)

COMPILED_L10N = $(wildcard locale/*/LC_MESSAGES/*.mo)

JS_FILES = $(filter-out %.min.js $(wildcard static/js/contrib/*),$(wildcard \
	static/js/*.js \
	static/js/**/*.js \
))

JS_MINIFIER = slimit -m

SASS_COMPILER = compass compile

JS_MINIFIED = $(JS_FILES:.js=.min.js)

all: compile-sass minify-js localization

# target: minify-js - Create minified JS files using slimit JS compressor.
minify-js: $(JS_FILES) $(JS_MINIFIED)

# target: compile-sass - Compile SASS files to CSS files using SASS/Compass compiler.
compile-sass:
	@cd static/; \
	echo `pwd`; \
	echo '-- Running compass $<';\
	$(SASS_COMPILER)
	@echo

# target: localization - Create .mo files from .po fiels in locale directory
localization:
	@echo "-- Compiling localization files"
	@tools/compilemessages.sh
	@echo "Done."
	@echo

%.min.js: %.js
	@echo '-- Minifying $<'
	$(JS_MINIFIER) $< > $@
	@echo

# target: clean - Remove all compiled CSS, JS and localization files.
clean:
	rm -rf $(COMPILED_CSS) $(COMPILED_L10N) $(JS_MINIFIED)

# target: help - Show this help.
help:
	@egrep "^# target:" Makefile