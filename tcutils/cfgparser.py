'''Parse config files which are ConfigParser complaint'''

from ConfigParser import SafeConfigParser


def string_to_list(tstr, force=False):
    '''Split a string with comma, If no comma is present
       and if force=True, return a list with str element
    '''

    tstr = tstr.replace('\n', '')
    tstr = tstr.split(' #')[0].strip()
    tstr = tstr.split(' ;')[0].strip()
    sstr = [sstr.strip() for sstr in tstr.split(',')]
    if force:
        return sstr
    else:
        return tstr if tstr.rfind(',') < 0 else sstr


def parse_cfg_file(cfg_files):
    ''' parse given config files and return a dictionary
        with sections as keys and its items as dictionary items
    '''
    parsed_dict = {}
    sections = []
    cfg_files = [cfg_files] if type(cfg_files) is str else cfg_files
    for cfg_file in cfg_files:
        parser = SafeConfigParser()
        parsed_files = parser.read(cfg_file)
        if cfg_file not in parsed_files:
            raise RuntimeError('Unable to parse (%s), '
                               'No such file or invalid format' % cfg_file)
        common_sections = list(set(parser.sections()) & set(sections))
        if len(common_sections) != 0:
            raise RuntimeError('Duplication Section Error while parsing '
                               '(%s): %s' % (cfg_file, "\n".join(common_sections)))
        for sect in parser.sections():
            parsed_dict[sect] = dict((iname, string_to_list(ival))
                                     for iname, ival in parser.items(sect))
        sections.extend(parser.sections())
        del parser
    return parsed_dict
