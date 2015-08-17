# Require any additional compass plugins here.
require 'breakpoint'

# use development environment by default
environment = :development

# Set this to the root of your project when deployed:
http_path = "/"
css_dir = "css"
sass_dir = "sass"
images_dir = "img"
javascripts_dir = "js"

# You can select your preferred output style here (can be overridden via the command line):
# output_style = (environment == :production) ? :compressed : :nested

line_comments = (environment == :production) ? false : true

preferred_syntax = :sass

sourcemap = (environment == :production) ? false : true