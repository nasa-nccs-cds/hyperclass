import os, shutil, pathlib, sys
from typing import List, Union, Tuple, Optional, Dict
LOCAL_DIR = pathlib.Path(__file__).parent.absolute()

class Section:

    def __init__(self, name: str ):
        self.name = name
        self._parms:  Dict[str,Tuple[str]] = {}

    def addItem(self, id: str, name: str, value: str ):
        self._parms[name] = ( id, value )

    def toDict(self) -> Dict[str,str]:
        return { name:self.toNum(name) for name in self._parms.keys() }

    def get(self, key: str, default: str = None ) -> Optional[Tuple[str]]:
        return self._parms.get( key, default )

    def __getitem__(self, key: str ) -> Tuple[str]:
        return self._parms[key]

    def __contains__(self, item) -> bool:
        return item in self._parms

    def __len__(self) -> int:
        return len( self._parms )

    def getShape(self, key: str ):
        values = self._parms[key][1].split(",")
        return [ int(v) for v in values ]

    def toNum(self, key: str ):
        value = self._parms[key][1]
        if "," in value:
            return [ self.v2num( x.strip() ) for x in value.split(",") ]
        else: return self.v2num( value.strip() )

    def v2num(self, value: str ):
        try: return int(value)
        except ValueError:
            try: return float(value)
            except ValueError:
                return value

    @classmethod
    def _2cfg( cls, id: str, value: str ) -> str :
        if "," in value:
            toks = value.split(",")
            return "-".join( [id] + [tok.strip() for tok in toks] )
        else: return f"{id}-{value}"

    @property
    def keys(self) -> List[str]:
        skeys = list(self._parms.keys())
        skeys.sort()
        return skeys

    def __str__(self):
        fields = [ self._parms[key] for key in self.keys ]
        cfg_fields =  [ self._2cfg(*field) for field in fields ]
        return "_".join( cfg_fields )

class Configuration:

    def __init__(self, config_dir = "~/.hyperclass", **kwargs ):
        CONFIG_DIR = os.path.expanduser(config_dir)
        self._sections: Dict[str,Section] = {}
        self._pindex = {}
        config_file = os.path.join( CONFIG_DIR, "config.txt" )
        if not os.path.exists( config_file ):
            os.makedirs( CONFIG_DIR, exist_ok = True )
            template_file =  os.path.join( LOCAL_DIR, "config_template.txt" )
            shutil.copyfile( template_file, config_file )
            print( f"Please edit the file {config_file} to declare local configuration options")
            sys.exit(1)
        else:
            current_section = None
            cfile = open( config_file, "r" )
            for line in cfile.readlines( ):
                line = line.strip()
                if line:
                    if line.startswith("*"):
                        current_section = Section( line[1:] )
                        self._sections[ current_section.name ] = current_section
                    elif "=" in line:
                        key, value = line.split("=")
                        names = key.split(":")
                        id = names[0].strip()
                        name = names[1].strip()
                        current_section.addItem( id, name, value.strip() )
                        self._pindex[ name ] = current_section
                    else:
                        print( f"WARNING: Unrecognozed line in config file: {line}")
        self.config_dir = CONFIG_DIR
        self.src_dir = pathlib.Path(LOCAL_DIR).parent

    def __getitem__(self, key: str ) -> str:
        section = self._pindex[key]
        return section[key][1]

    def section(self, key: str) -> Section:
        return self._sections[key]

    def getShape(self, key: str ):
        section = self._pindex[key]
        return section.getShape( key )

    def toNum(self, key: str ):
        section = self._pindex[key]
        return section.toNum( key )

    def getCfg(self, key: str):
        section = self._pindex[key]
        return section._2cfg( *section[key] )

    @property
    def sections(self) -> List[str]:
        skeys = list(self._sections.keys())
        skeys.sort()
        return skeys

    def toStr( self, section_names: List[str] ) -> str:
        return "_".join( [  str(self._sections[name]) for name in section_names ] )


