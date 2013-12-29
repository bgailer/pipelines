#------------------------- pipe.py -------------------------
'''
   A simple Python implementation of pipe
  "readfile c:\file1.txt | locate /apple/ | writefile c:\file2.txt"
   The output of each stage is connected to the input of the next,
   forming form a pipeline. This is a static configuration. Our
   subsequent goal is a dynamic configuration constructed automatically
   from the pipeline specification. 
'''
def readFile():
'''
   This method is the first stage and acts as an input driver.
   An input driver repeatedly obtain a record from some source
   and passes it to the next stage.
   It is responsible for opening and closing its source.
'''
  with open("c:/file1.txt", "r") as f: #If on Linux, substitute a Linux path for c:\ 
    for record in f:
      locate(record)
    locate() # pass EOF indicator

def locate(record=None):
'''
   locate is a filter stage or filter.
   A filter selects records for output based on some criteria.
'''   
  if record is None or 'apple' in record:
    writeFile(record)

def writeFile(record, destFile=open("c:/file2.txt", "w")): #If on Linux, substitute a Linux path for c:\ 
'''
   The final stage is an output driver. An output driver
   sends records to an external destination e.g. file, terminal,
   database, tcp/ip connection. It is responsible for opening
   and closing its destination.
'''   
  if record is None: # EOF
    destFile.close()
  else:
    destFile.write(record)

readFile()
#------------------------- end pipe.py -------------------------
