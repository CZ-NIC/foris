from subprocess import check_output, STDOUT


def uci_get(path, config_directory=None):
    args = ["uci"]
    if config_directory:
        args.extend(["-c", config_directory])
    args.extend(["get", path])
    # crop newline at the end
    return check_output(args)[:-1]


def uci_is_empty(path, config_directory=None):
    args = ["uci"]
    if config_directory:
        args.extend(["-c", config_directory])
    args.extend(["get", path])
    args.append("; exit 0")
    return (check_output(" ".join(args), stderr=STDOUT, shell=True)) == "uci: Entry not found\n"


def uci_set(path, value, config_directory=None):
    args = ["uci"]
    if config_directory:
        args.extend(["-c", config_directory])
    args.extend(["set", "%s=%s" % (path, value)])
    output = check_output(args)  # CalledProcessError is raised on error
    if output != "":
        raise RuntimeWarning("uci set returned unexpected output: '%s'" % output)
    return True


def uci_commit(config_directory=None):
    args = ["uci"]
    if config_directory:
        args.extend(["-c", config_directory])
    args.append("commit")
    check_output(args)  # CalledProcessError is raised on error
    return True
