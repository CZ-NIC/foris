from base import YinElement
from xml.etree import cElementTree as ET


class Updater(YinElement):
    tag = "updater"
    NS_URI = "http://www.nic.cz/ns/router/updater"

    def __init__(self, running, failed, last_activity):
        super(Updater, self).__init__()
        self.running = running
        self.failed = failed
        self.last_activity = last_activity

    @staticmethod
    def from_element(element):
        running = element.find(Updater.qual_tag("running"))
        running = running.text if running is not None else False
        failed = element.find(Updater.qual_tag("failed"))
        failed = failed.text if failed is not None else False
        activities_elem = element.find(Updater.qual_tag("last_activity"))
        last_activity = []
        if activities_elem is not None:
            for activity_elem in activities_elem.iter():
                if activity_elem.tag == Updater.qual_tag("install"):
                    last_activity.append(('install', activity_elem.text))
                elif activity_elem.tag == Updater.qual_tag("remove"):
                    last_activity.append(('remove', activity_elem.text))
        return Updater(running, failed, last_activity)

    @property
    def key(self):
        return "updater"

####################################################################################################
ET.register_namespace("updater", Updater.NS_URI)
