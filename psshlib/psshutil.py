# Copyright (c) 2009-2012, Andrew McNabb
# Copyright (c) 2003-2008, Brent N. Chun

import fcntl
import string
import sys

HOST_FORMAT = 'Host format is [user@]host[:port] [user]'


def get_exit_code_index(statuses, exitcodes_file):
    exitcodes = read_exit_codes(exitcodes_file)
    exitcode_status_base = 201
    exit_code_index = -1
    exitcode_index = 0
    for status in statuses:
        for gt_lt, exit_code, lt_ceiling, ceiling in exitcodes:
            int_exit_code = int(exit_code)
            if (ceiling != ''):
                int_ceiling = int(ceiling)
            if gt_lt != '' and lt_ceiling != '':
                if (gt_lt == '>' and status > int_exit_code) or (gt_lt == '>=' and status >= int_exit_code):
                    if (lt_ceiling == '<' and status < int_ceiling) or (lt_ceiling == '<=' and status <= int_ceiling):
                        exit_code_index = exitcode_index
                        break
            elif gt_lt != '' and lt_ceiling == '':
                if (gt_lt == '>' and status > int_exit_code) or (gt_lt == '>=' and status >= int_exit_code):
                    exit_code_index = exitcode_index
                    break
                elif (gt_lt == '<' and status < int_exit_code) or (gt_lt == '<=' and status <= int_exit_code):
                    exit_code_index = exitcode_index
                    break
            elif status == int_exit_code:
                exit_code_index = exitcode_index
                break

            exitcode_index += 1

        if exit_code_index > -1:
            return exitcode_status_base + exit_code_index
        else:
            return exit_code_index


def read_exit_codes(paths):
    exitcodes = []

    if paths:
        for path in paths:
            exitcodes.extend(read_exit_code(path))

    return exitcodes

def read_exit_code(path):
    """Reads the given exit codes to check for file.

    Lines are of the form: [ > | < | >= | <= ]<exit code>.
    Returns a list of (lessthengreaterthan, equals, exitcode) triples.
    """
    lines = []
    f = open(path)
    for line in f:
        lines.append(line.strip())
    f.close()

    exitcodes = []
    for line in lines:
        # Skip blank lines or lines starting with #
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        gt_lt, exit_code, lt_ceiling, ceiling = parse_exit_code_entry(line)
        exitcodes.append((gt_lt, exit_code, lt_ceiling, ceiling))
    return exitcodes

def parse_exit_code_entry(line):
    """Parses an exit code entry.

    This takes the form [>= | <=] <exit code>

    Returns a (gt+lt, exit_code) double.
    """
    gt_lt = ''
    exit_code = ''
    lt_ceiling = ''
    ceiling = ''
    fields = line.split()
    if len(fields) == 3 or len(fields) > 4:
        sys.stderr.write('Bad line: "%s". Format should be'
                '{<exit code> | <> | >= | < | <=> <exit code> | <> | >=> <celining exit code> << | <=>}\n' % line)
        return None, None, None, None
    if len(fields) == 1:
        exit_code = fields[0]
    elif len(fields) == 2:
        gt_lt = fields[0]
        exit_code = fields[1]
    else:
        gt_lt = fields[0]
        exit_code = fields[1]
        lt_ceiling = fields[2]
        ceiling = fields[3]
    if not exit_code.decode('utf-8').isnumeric():
        sys.stderr.write('Exit code must be numeric: "%s"\n' % line)
        return None, None, None, None
    elif len(fields) == 2:
        if gt_lt != '>=' and gt_lt != '<=' and gt_lt != '>' and gt_lt != '<':
            sys.stderr.write('Bad comparison (must be >, <, >=, or <=):  "%s"\n' % line)
            return None, None, None, None
    elif len(fields) == 4:
        if not ceiling.decode('utf-8').isnumeric():
            sys.stderr.write('Celining must be numeric: "%s"\n' % line)
            return None, None, None, None
        if gt_lt != '>=' and gt_lt != '>':
            sys.stderr.write('Bad floor comparison (must be > or >=): "%s"\n' % line)
            return None, None, None, None
        if lt_ceiling != '<=' and lt_ceiling != '<':
            sys.stderr.write('Bad ceiling comparison (must be < or <=): "%s"\n' % line)
            return None, None, None, None
    return gt_lt, exit_code, lt_ceiling, ceiling


def read_host_files(paths, default_user=None, default_port=None):
    """Reads the given host files.

    Returns a list of (host, port, user) triples.
    """
    hosts = []
    if paths:
        for path in paths:
            hosts.extend(read_host_file(path, default_user=default_user))
    return hosts


def read_host_file(path, default_user=None, default_port=None):
    """Reads the given host file.

    Lines are of the form: host[:port] [login].
    Returns a list of (host, port, user) triples.
    """
    lines = []
    f = open(path)
    for line in f:
        lines.append(line.strip())
    f.close()

    hosts = []
    for line in lines:
        # Skip blank lines or lines starting with #
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        host, port, user = parse_host_entry(line, default_user, default_port)
        if host:
            hosts.append((host, port, user))
    return hosts


# TODO: deprecate the second host field and standardize on the
# [user@]host[:port] format.
def parse_host_entry(line, default_user, default_port):
    """Parses a single host entry.

    This may take either the of the form [user@]host[:port] or
    host[:port][ user].

    Returns a (host, port, user) triple.
    """
    fields = line.split()
    if len(fields) > 2:
        sys.stderr.write('Bad line: "%s". Format should be'
                ' [user@]host[:port] [user]\n' % line)
        return None, None, None
    host_field = fields[0]
    host, port, user = parse_host(host_field, default_port=default_port)
    if len(fields) == 2:
        if user is None:
            user = fields[1]
        else:
            sys.stderr.write('User specified twice in line: "%s"\n' % line)
            return None, None, None
    if user is None:
        user = default_user
    return host, port, user


def parse_host_string(host_string, default_user=None, default_port=None):
    """Parses a whitespace-delimited string of "[user@]host[:port]" entries.

    Returns a list of (host, port, user) triples.
    """
    hosts = []
    entries = host_string.split()
    for entry in entries:
        hosts.append(parse_host(entry, default_user, default_port))
    return hosts


def parse_host(host, default_user=None, default_port=None):
    """Parses host entries of the form "[user@]host[:port]".

    Returns a (host, port, user) triple.
    """
    # TODO: when we stop supporting Python 2.4, switch to using str.partition.
    user = default_user
    port = default_port
    if '@' in host:
        user, host = host.split('@', 1)
    if ':' in host:
        host, port = host.rsplit(':', 1)
    return (host, port, user)


def set_cloexec(filelike):
    """Sets the underlying filedescriptor to automatically close on exec.

    If set_cloexec is called for all open files, then subprocess.Popen does
    not require the close_fds option.
    """
    fcntl.fcntl(filelike.fileno(), fcntl.FD_CLOEXEC, 1)
