import ConfigParser


class ReadConfigIni():

    def __init__(self):
        self.Config = ConfigParser.ConfigParser()
        self.config = self.Config.read("tor_params.ini")

    def config_section_map(self, section):

        dict1 = {}
        options = self.Config.options(section)
        for option in options:
            try:
                dict1[option] = self.Config.get(section, option)
                if dict1[option] == -1:
                    DebugPrint("skip: %s" % option)
            except:
                print("exception on %s!" % option)
                dict1[option] = None
        return dict1

    def create_config_dict(self):
        self.tor_scale_dict = {}
        sections_list = self.Config.sections()
        for section in sections_list:
            self.tor_scale_dict[section] = self.config_section_map(section)

if __name__ == "__main__":

    config = ReadConfigIni()
    config.create_config_dict()
