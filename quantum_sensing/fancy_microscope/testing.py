import os
import sys
srcpath = os.path.realpath('SourceFiles')
sys.path.append(srcpath)
print(srcpath)

'''from teproteus import TEProteusAdmin as TepAdmin

admin = TepAdmin() #required to control PXI module
sid = 12 #PXI slot WDS found
inst = admin.open_instrument(slot_id=sid)
resp = inst.send_scpi_query("*IDN?")
print('connected to: ' + resp) # Print *IDN'''