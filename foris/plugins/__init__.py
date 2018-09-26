# Foris - web administration interface for OpenWrt based on NETCONF
# Copyright (C) 2015 CZ.NIC, z. s. p. o. <https://www.nic.cz>
#
# Foris is distributed under the terms of GNU General Public License v3.
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import gettext
import inspect
import importlib
import logging
import os
import pkgutil
import pkg_resources

import bottle

from foris.utils.translators import translations


logger = logging.getLogger(__name__)


class ForisPlugin(object):
    """Simple class that all Foris plugins should inherit from."""

    DIRNAME = None
    LOAD_ORDER = 100  # smaller number means that the plugin will be loaded sooner
    plugin_translations = None

    def __init__(self, app):
        self.app = app
        if not self.DIRNAME:
            raise NameError("DIRNAME attribute must be set by ForisPlugin subclass.")
        # initialize templates
        template_dir = os.path.join(self.DIRNAME, "templates")
        bottle.TEMPLATE_PATH.append(template_dir)
        # initialize translations
        self.add_translations()

    def add_translations(self):
        """Add translations in current plugin.

        This approach has one design flaw - messages in the plugin apply to
        the whole app. This is not an issue now, but it should be examined
        later and replaced by a better solution.
        """
        for lang, default_translation in translations.items():
            local_translation = gettext.translation(
                "messages", os.path.join(self.DIRNAME, "locale"),
                languages=[lang], fallback=True
            )
            default_translation.add_fallback(local_translation)


class ForisPluginLoader(object):
    """Class for loading plugins and holding references to them in runtime."""

    def __init__(self, app):
        self.app = app
        self.app.foris_plugin_loader = self
        self.plugins = []

    def autoload_plugins(self):
        """Find and load plugins in foris_plugins.*"""

        plugin_classes = []

        modules = importlib.import_module("foris_plugins")
        for _, mod_name, _ in pkgutil.iter_modules(modules.__path__):
            plugin_module_name = "foris_plugins.%s" % mod_name
            # try to determine version
            try:
                version = pkg_resources.get_distribution("foris_%s_plugin" % mod_name).version
            except pkg_resources.DistributionNotFound:
                version = "?"
            logger.debug("Found foris plugin '%s (%s)'.", mod_name, version)
            plugin_classes += self._get_plugin_classes(plugin_module_name)

        # sort plugin classes
        plugin_classes.sort(key=lambda x: (x.LOAD_ORDER, x.PLUGIN_NAME))

        # load the plugin
        for plugin_class in plugin_classes:
            self.load_plugin(plugin_class)

    @staticmethod
    def is_foris_plugin(klass):
        """Check that argument klass is a valid Foris plugin.

        Check is True for all classes that have class named ForisPlugin
        in their inheritance chain.
        """
        if not inspect.isclass(klass):
            return False
        # first element is basically klass.__name__ - throw it away
        mro_names = [c.__name__ for c in inspect.getmro(klass)][1:]
        return ForisPlugin.__name__ in mro_names

    def _get_plugin_classes(self, package_name):
        """Reads all plugin classes in package """
        try:
            logger.info("Looking for plugins in package '%s'", package_name)
            package = importlib.import_module(package_name)
            classes = inspect.getmembers(package, self.is_foris_plugin)
            classes = [klass for _, klass in classes]
            for klass in classes:
                logger.debug("Plugin found %s", klass)
            return classes
        except ImportError:
            logger.exception("Unable to import package '%s'.", package_name)
        except Exception:
            # catching all errors - plugins should not kill Foris
            logger.exception("Error when loading plugin '%s': " % package_name)

    def load_plugin(self, plugin_class):
        """Load a single plugin class."""
        logger.info("Loading plugin: %s", plugin_class)
        instance = plugin_class(self.app)
        self.plugins.append(instance)
