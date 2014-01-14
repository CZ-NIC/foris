class NuciError(Exception):
    """
    Raised when something fails during communication with Nuci.
    """
    pass


class ConfigRestoreError(NuciError):
    """
    Raised when config-restore RPC command fails.
    """
    pass