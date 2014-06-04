from subprocess import check_output


def get_uci_value(path, config_directory=None):
    args = ["uci", "get"]
    if config_directory:
        args.extend(["-c", config_directory])
    args.append(path)
    # crop "path.to.value=" and newline at the end
    return check_output(args)[len(path)+1:-1]
