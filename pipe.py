#------------------------- pipe.py -------------------------
class Stage():
  """superclass all stage classes"""

  def output(self, record): raise NotImplementedError 
    # must be replaced by the next stage's run method

  def run(self): raise NotImplementedError 
    # must be overridden in subclasses of Stage 
  
class Readfile(Stage):
  
  def __init__(self, specs):
    self.fileName = specs
  
  def run(self):
    with open(self.fileName) as f:
      for record in f:
        record = record.strip('\n')
        self.output(record)
      self.output()

class Locate(Stage):

  def __init__(self, specs):
    # the stage specification (specs) is a "delimitedString"
    # a delimitedString starts and ends with a delimiter and has no other occurrence 
    # of the delimiter.
    # the delimiter is any non-blank character.
    # the rest of the delimitedString is its value.
    # in our example /apple/ is the delimitedString; apple is its value.
    
    # parse specs to ensure it is a delimitedString and get its value
    specs = specs.strip() # ignore any leading or trailing blanks
    delimiter = specs[0] # get the delimiter
    if specs[-1] != delimiter: # ensure last char == delimiter
      raise "invalid delimited string"
    self.locateString = specs[1:-1] # remainder is the value
    if delimiter in self.locateString: # ensure delimiter is not in the value
      raise "invalid delimited string"

  def run(self, record=None):
    if record is None or record.find(self.locateString) >= 0:
      self.output(record) 

class Writefile(Stage):

  def __init__(self, destFileName ):
    self.destFile = open(destFileName, "w")

  def run(self, record):
    if record is None:
      self.destFile.close()
    else:
      self.destFile .write(record + '\n')
    
# create dictionary {stageName:stageClass, ...} so we can lookup a stage name from the spec and get the class object
stageDict = dict(readfile = Readfile,
                 locate = Locate,
                 writefile = Writefile)

class PipeLine(list): # instance is a list of stage instances
  seperator = '|' 
  def __init__(self, specs):
    specList = specs.split(self.seperator) 
    # ["readfile c:/file1.txt ", "locate /apple/ ", "writefile c:/file2.txt"]
    for stage in specList:
      stageName, stageSpecs = stage.split(None, 1) # "["readfile", "c:/file1.txt "]
      StageClass = stageDict[stageName]
      stageInstance = StageClass(stageSpecs)
      self.append(stageInstance)
      if len(self) > 1: # connect to prior stage
        priorStage.output = stageInstance.run
      priorStage = stageInstance
  def run(self):
    self[0].run() # start the input driver stage
    
def main():
  import sys
  if len(sys.argv) > 1: # called from command line
    specs = sys.argv[1]
  else:
    specs = "readfile c:/file1.txt | locate /apple/ | writefile c:/file2.txt"
  pipeLine = PipeLine(specs)
  pipeLine.run()

main()
#------------------------- end pipe.py -------------------------
