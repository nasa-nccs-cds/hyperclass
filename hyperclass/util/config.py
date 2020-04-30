import os, shutil, pathlib, sys
from typing import List, Union, Tuple, Optional, Dict
LOCAL_DIR = pathlib.Path(__file__).parent.absolute()

class Configuration:

    def __init__(self, config_dir = "~/.hyperclass" ):
        CONFIG_DIR = os.path.expanduser(config_dir)
        self._parms: Dict[str,Tuple[str,str]] = {}
        config_file = os.path.join( CONFIG_DIR, "config.txt" )
        if not os.path.exists( config_file ):
            os.makedirs( CONFIG_DIR, exist_ok = True )
            template_file =  os.path.join( LOCAL_DIR, "config_template.txt" )
            shutil.copyfile( template_file, config_file )
            print( f"Please edit the file {config_file} to declare local configuration options")
            sys.exit(1)
        else:
            cfile = open( config_file, "r" )
            for line in cfile.readlines( ):
                if "=" in line:
                    key, value = line.split("=")
                    names = key.split(":")
                    shortname = names[0].strip()
                    longname = names[1].strip()
                    self._parms[ longname ] = [ shortname, value.strip() ]
        self.config_dir = CONFIG_DIR
        self.src_dir = pathlib.Path(LOCAL_DIR).parent

    def get(self, key: str, default: str = None ) -> Optional[Tuple[str,str]]:
        return self._parms.get( key, default )

    def __getitem__(self, key: str ) -> Tuple[str,str]:
        return self._parms[key]

    def __contains__(self, item) -> bool:
        return item in self._parms

    def __len__(self) -> int:
        return len( self._parms )

    def getShape(self, key: str ):
        values = self._parms[key][1].split(",")
        return [ int(v) for v in values ]

    @property
    def keys(self) -> List[str]:
        skeys = list(self._parms.keys())
        skeys.sort()
        return skeys

    def __str__(self):
        fields = [ self._parms[key] for key in self.keys ]
        return "_".join( [  "-".join(field) for field in fields ] )


