VERSION = (0, 0, 2, 'alpha')
if VERSION[-1] != "final":
    __version__ = '.'.join(map(str, VERSION))
else:
    __version__ = '.'.join(map(str, VERSION[:-1]))
