import os
import pickle


# Load directory of countries country_code: country_name
countries = pickle.load(open(os.path.join(os.path.dirname(__file__), "countries.pickle2"), "rb"))

# Load TZ data tuple of tuples: (luci_tz, country, city, zoneinfo)
tz_data = pickle.load(open(os.path.join(os.path.dirname(__file__), "tzdata.pickle2"), "rb"))


# Set of existing regions
regions = set(x[0].split("/")[0] for x in tz_data)


def timezones_in_region(region):
    """List timezones in a region. Returns filtered tz_data items."""
    result = filter(lambda x: x[0].startswith(region), tz_data)
    return result


def timezones_in_region_and_country(region, country):
    """List timezones in a region and country. Returns filtered tz_data items."""
    result = filter(lambda x: x[0].startswith(region) and x[1] == country, tz_data)
    return result


def countries_in_region(region):
    """List countries in a region. Returns set of country codes."""
    filtered = filter(lambda x: x[0].startswith(region), tz_data)
    result = set(x[1] for x in filtered)
    return result


def get_country_for_tz(tz):
    """Get country code for a timezone identifier."""
    filtered = filter(lambda x: x[0] == tz, tz_data)
    return filtered[0][1] if filtered else None


def get_zoneinfo_for_tz(tz):
    """Get zoneinfo record for a timezone identifier."""
    filtered = filter(lambda x: x[0] == tz, tz_data)
    return filtered[0][3] if filtered else None
