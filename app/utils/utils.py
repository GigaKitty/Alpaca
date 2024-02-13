import json


def dumper():
    # Dump all local variables
    print(json.dumps(locals(), default=str))

    # Dump all global variables
    print(json.dumps(globals(), default=str))
