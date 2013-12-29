#------------------------- pipe.py -------------------------

# Define the stage classes

class ReadFile():
  
  def __init__(self, sourceFileName):
'''
   Stage instances are initialized by passing the stage
   specification (spec) to the __init__ method.
   __init__ may do nothing, save the spec, or process in
   some meaningful manner.
'''   
    self.sourceFileName = sourceFileName

  def run(self):
'''
 each stage class has a run method.The run method of the
 input driver is called once to start that stage.
'''
    with open(self.sourceFileName, "r") as f:
      for record in f:
        self.output(record) # each stage class has an output method
      self.output()

class Locate:

  def __init__(self, locateStr):
    self.locateStr = locateStr

  def run(self,record=None):
    if record is None or record.find(self.locateStr) >= 0:
      self.output(record)

class WriteFile:
  
  def __init__(self, destFileName):
    self. destFile = open(destFileName, "w")
  def run(self, record):    
    if record is None:
      self. destFile.close()
    else:
      self.destFile.write(record)

# Create stage instances passing the stage specification to __init__.
# This is the pipeline specification we are applying:
# "readfile c:\file1.txt | locate /apple/ | writefile c:\file2.txt"

stage1 = ReadFile("c:/file1.txt")
stage2 = Locate("apple")
stage3 = WriteFile("c:/file2.txt")

# connect the output method  of each stage to the run method of the next.

stage1.output = stage2.run
stage2.output = stage3.run

# start the pipeline

stage1.run()

#------------------------- end pipe.py -------------------------
