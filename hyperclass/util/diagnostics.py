
line = "-"*50

def emphasize( *args, **kwargs  ):
    print( "\n" + line )
    for arg in args: print( arg )
    for k,v in kwargs.items(): print( f"{k} = {v}" )
    print( line + "\n" )
