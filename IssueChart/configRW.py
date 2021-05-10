import configparser
import ast


def write_config(dicts, file):
    config = configparser.ConfigParser()
    for c_dict in dicts:
        config[c_dict] = dicts[c_dict]
    with open(file, 'w') as configfile:
        config.write(configfile)


def read_config(file):
    config = configparser.ConfigParser()
    config.read(file)
    dicts = {}
    for section in config.sections():
        dicts[section] = dict(config[section])
    # print(dicts)
    if len(dict(config["DEFAULT"])) > 0:
        dicts["DEFAULT"] = dict(config["DEFAULT"])

    for k in dicts:
        for key, value in dicts[k].items():
            try:
                dicts[k][key] = int(dicts[k][key])
                continue
            except ValueError:
                try:
                    dicts[k][key] = float(dicts[k][key])
                    continue
                except ValueError:
                    pass
            try:
                if value[0] == "[" and value[-1] == "]":
                    dicts[k][key] = ast.literal_eval(value)
            except Exception as e:
                print(e)
    return dicts
