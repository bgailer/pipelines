# -*- coding: utf-8 -*-
#! /usr/bin/python
#------------------------- pipe4.py -------------------------
# Enhancements added since pipe3:
# Stage methods: setup, finalizeSetup, initializeRun, terminate
# mechanism to call these from PipeLineSet.run:
# Stage attribute names e.g. names = ["CONSole", "TERMinal"] caps give min abbreviation
# decorator addToDict to build and return dictionary of className: class items (for stage classes)
# Message class to handle messages and errors
# Stage subclasses: Change, Console, FanInAny, Literal, RunPipe, Var
#   
# Multiple Pipelines
#   can split into two streams
#   can have 2 independent pipelines
# FO: 2 input driver stages that intermix (requires threading)
# pipeline commands:
#   added class PipeLineCommand with methods addStream and short. short is not used 

import sys
import os
import sqlite3
root = "n:/" # change this to match your OS / filesystem

def addToDict(cls=None, d={}):
  '''decorator - adds class name: class to dictionary d
     returns dictionary when called with no argument'''
  if cls:
    d[cls.__name__] = cls
    return cls
  else:
    return d

class Message:
  """mixin for classes with processes that issue messages 
  - stage
  - pipeline commands - issued by a REXX stage or the PIPCMD stage
  - scanner
  each class holds its spec / comand
  stage holdsits postiion in pipeline and the pipeline position in the pipelineset"""

  # messages are extracted from http://vm.marist.edu/~pipeline/authelp.html following label Messages:
  # a program visits each message, formats information and stores in sqlite3 database.
  
  send_msg = print  # used to send messages to console. Overridden in stage Runpipe, TestSuite and ?
  conn = None # checked in message() to set things up first time 

  def message(self, msgNo, *args):
    """Format and send a message, given a message number and a (possibly empty) tuple of args.
       Depending on msglvl add more messages.
       Route via the stage's send_msg method. console, output, stack?
       Set the pipeLineSet's RC - highest unless negative, then lowest.
       Take appropriate system action:
       - arrange for scanner to quit at end of scan.
       - stop the stage.
       - stop processing.
       - no special action."""
    if not Message.conn:
      Message.conn = sqlite3.connect(root + 'pipelines\errors.db')
      # database generated ...
      ## add description
      Message.conn.row_factory = sqlite3.Row
      Message.curs = Message.conn.cursor()    
    self.msglvl_bits = '000000' + bin(self.msglvl)[2:] # 7 -> '000000111'
    curs = Message.curs
    send_msg = self.send_msg
    curs.execute("select * from errors where id = ?", (msgNo, ))
    row = curs.fetchone()
    if not row:
      curs.execute("select * from errors where id = ?", (0, ))
      args = (msgNo, )
      row = curs.fetchone()
    severity = row['severity']
    source = self.__class__.__name__ # Stage, PipeLineSet, PipeLineCommand, ...?
    ## must add 3 char source id following FPL (DSR = dispatcher, SCA = scanner
    send_msg(('FPL%03i%s ' % (msgNo, severity)) + row['format_desc'] % args) # e.g. FPL019E No message text for message 6789
    # certain MSGLVL bits control issuing of additional messages - see 8343ff
    # bit 1 - FPL001I; bit 2 - FPL002I; bit 3 - FPL003I or FPL004I 
#   Example from User's Guide: pipe < test file j | console
#   FPLDSR119E Mode J not available or read only
#   FPLSCA003I ... Issued from stage 1 of pipeline 1
#   FPLSCA001I ... Running "< test file j"
#   Ready(119);

    if self.msglvl_bits[-3] == '1': # source is a stage.
      if self.pipeLineSet.name:
        send_msg('FPL004I ... Issued from stage %s of pipeline %s name "name"%s"' %  (self.number. self.pipeLineSet.number, self.pipeLineSet.name))
      else:    
        send_msg('FPL003I ... Issued from stage %s of pipeline %s' %  (self.number. self.pipeLineSet.number))

    if self.msglvl_bits[-2] == '1': # source is a pipeline command.
      send_msg('FPL002I ... Processing "%s"' %  self.spec[:60]) # first 60 characters of the pipeline command
      
    if self.msglvl_bits[-1] == '1': # source is scanner or a stage.
      send_msg('FPL001I ... Running "%s"' %  self.spec[:60]) #  first 60 characters of the stage specification
      if msgNo in (12, 17, 43, 44, 46, 47, 98, 99, 132, 133, 138, 139, 174, 190, 191, 193, 194, 195, 554):# caught by scanner
        send_msg('FPL192I ... Scan at position %s; previous data %s' % (self.positionInSpec, self.spec))
    self.pipeLineSet.RC = msgNo 
    
  def end(self): pass
    # issue msg 177 if msglvl bit for 8K is on

class PipeLineCommand: # (Message):
  # functions that carry out Pipeline Commands - see chapter 25 Author's Edition
  def addStream(self, sides=''): # use here and anticipate Pipeline Command AddStream
    """      ┌─BOTH───
──ADDSTREAm──┼────────┼──┬──────────┬──
             ├─INput──┤  └─streamID─┘
             └─OUTput─┘˜"""
    # FO support streamid argument
    sides = sides.lower()
    if 'input'.startswith(sides) and 2 <= len(sides) <= 5: self.inputStreams.add()
    elif 'output'.startswith(sides) and 3 <= len(sides) <= 6: self.outputStreams.add()
    elif not sides or sides == 'both': self.inputStreams.add(), self.outputStreams.add()
    else: self.message(2003, sides)

  def short(self): # not used in pipe4.
    """The currently selected input stream and the currently selected output stream
       are connected directly, bypassing the stage issuing SHORT."""
    # For now the currently selected streams are the primaries
    n = self.position - 1
    p = self.pipeLine
    left = p[n-1]
    right = p[n+1]
    left.selectedOutputStream.output = right.selectedInputStream.run
    x = 3 # for debugging breakpoint
""" To be done: List from Author's Edition Chapter 35
--- Transport Data
  OUTPUT Write the argument string to the currently selected output stream.
  SHORT Connect the currently selected input stream to the currently selected output stream. The streams are no longer connected to the program.
--- Control Pipeline Topology
  ADDPIPE Add a pipeline specification to run in parallel with your program.
  This is used, for instance, to replace the current input stream with a file to embed.
  ADDSTREAM Add an unconnected stream to the program.
  CALLPIPE Run a subroutine pipeline.
  SELECT Select an input or output stream, or both. Subsequent requests for
  data transport are directed to this stream.
  SEVER Detach a stream from the program. The other side of the connection sees end-of-file.
--- Issue Messages
  MESSAGE Write the argument string as a message.
  ISSUEMSG Issue a CMS/TSO Pipelines message. The argument specifies a
    message number; the message text is obtained from a message table.
---Query Program’s Environment
 """

class Stage(Message, PipeLineCommand):
  """superclass all stage classes"""
  # a stream may, may not, must be connected - following Defs must be overridden
  # they are compared to streams in finalizeSetup to ensure correctnexx
  inputStreamDefs = "" # 1 char per stream specifies connection: '0' = not, '=' = optional, '1' = required
  outputStreamDefs = ""
  RC = 0

  def __init__(self, pipeLineSet, name, stagePositionInPipeLine):
    self.pipeLineSet = pipeLineSet
    self.pipeLineNo = pipeLineSet.number
    ## self.pipeLine = pipeLineSet[self.pipeLineNo-1]
    self.msglvl = self.pipeLineSet.msglvl # override if local options include msglvl
    self.name = name
    self.position = stagePositionInPipeLine
    self.inputStreams = InputStreams(self)
    self.outputStreams = OutputStreams(self)
    self.addStream() # each stage starts with 1 input and 1 ouput stream; more may be added.

    # Streams are selected using thePipeline Command SELECT.
    # Selected streams are referenced by various Ppipeline Commands (e.g. SHORT)
    # Initially the primary streams are selected.
    self.selectedInputStream = self.inputStreams[0]
    self.selectedOutputStream = self.outputStreams[0]

  def checkConnection(self, streams, defs, pipeLineSet, direction):
    # def 0 may be defined; if defined must not be connected
    # def + may be defined; if defined may be connected
    # def 1 must be defined; must be connected
    ns = len(streams) - 1
    for x, y in enumerate(defs):
      if y == '1':
        if ns < x :
          self.message(2000, self, direction, x)
        if not streams[x].connected:
          self.message(2001, direction, x)
      elif y == '0':
        if ns >= x and streams[x].connected:
          self.message(2002,  direction, x)


  def setup(self, spec):
    """Stages expecting specs must override
       Return None or Error instance"""
    self.spec = spec
    if spec:
      self.message(2004, spec)

  def finalizeSetup(self):  # when all stage instances are created and connected do final check and setup
    # in IBM terms set commit level = 0 if all is OK
    # redirect special output methods to corresponing outputStreams
    self.output1 = self.outputStreams[0].run 
    if len(self.outputStreams) > 1:
      self.output2 = self.outputStreams[1].run # sufficient for now

    self.checkConnection(self.inputStreams, self.inputStreamDefs, self.pipeLineSet, 'in')
    self.checkConnection(self.outputStreams, self.outputStreamDefs, self.pipeLineSet, 'out')

  def initializeRun(self): pass # override to open files, reset counters, ...(re)connect streams, ...

  def terminate(self): pass # override to close files, other end-of-run activities

  def output2(self, record): pass # may be reassigned to outputStream[1].output

class InputDriverStage(Stage):
  """superclass of input driver stages e.g. ReadFile, Literal"""
  inputStreamDefs = '0' # may be overriddden (e.g. Literal)
  outputStreamDefs = '1' # primary outputStream must be connected
  priority = False # certain stages must be run first e.g. Literal

  def __init__(self, pipeLine, name):
    super().__init__(pipeLine, name)
    if self.priority: pipeLine.pipeLineSet.startQueue.insert(0, self)
    else: pipeLine.pipeLineSet.startQueue.append(self)

class OutputDriverStage(Stage):
  """superclass of output driver stages"""
  inputStreamDefs = '1' # primary inputStream must be connected
  outputStreamDefs = '+' # primary outputStream may be connected

class Streams(list):
  """superclass of InputStreams and OutputStreams"""
  def __init__(self, stage):
    self.stage = stage
    super().__init__()

  def add(self):
    self.append(self.cls(self.stage))

  selectedStream = None # replaced for each instance
  # initially the primary stream; changed by Pipeline Command SELECCT
  # default stream for

class Stream:
  """superclass of InputStream and OutputStream"""
  connected = False # initially it is not.
  def __init__(self, stage):
    self.stage = stage


class InputStream(Stream):
  """an instance is an input stream for a stage, stored in stage.inputStreams"""

  def run(self, record):
  # run is the input interface
  # for now it just calls output - later it will do a lot more e.g.:
  #  - blocking (DAM, FANIN, ...)
  #  - preprocessing and/or redirecting the record (CASEI etc)
   # we connect this input stream to the output stresm of the preceeding stage
  # by assigning the run method to the output "attribute" of the predecessor
    self.output(record)

  def output(self, record):
    self.stage.run(record)

class OutputStream(Stream):
  """an instance is an and output stream for a stage, stored in stage.outputStreams"""
  def run(self, record):
  # run is the input interface
  # for now it just calls output - later it will do more!
    self.output(record)

  def output(self, record=None):pass
  # usually reassigned to refer to the run method of one of the following stage's input streams

class InputStreams(Streams):
  cls = InputStream

class OutputStreams(Streams):
  cls = OutputStream

class Label:
  stage = None

class IODriverStage(Stage):
  """Base class for stages that can be first or later in a pipeline
  # e.g. Console, several disk i/o stages, stack, udp, setrc
  Such stages must define 2 classes, First and Other, each of which declares at minimum
  a setup method and a run method. See class Console for an example."""

  def __init__(self, pipeLineSet, stage, position):
    super().__init__(pipeLineSet, stage, position)

    if self.position == 0:
      self.__class__ = self.__class__.First
      if self.priority: pipeLineSet.startQueue.insert(0, self)
      else: pipeLineSet.startQueue.append(self)
    else:
      self.__class__ = self.__class__.Other

@addToDict
class Literal(InputDriverStage):
  """Simple case only spec is string"""
  names = ["LITERAL"]
  priority = True # put at front of start queue

  def setup(self, specs):
    self.string = specs
    if self.position > 1:
      self.inputStreamDefs = '1'

  def finalizeSetup(self):
    super().finalizeSetup()
    if self.position == len(self.pipeLine):
      self.message(2005)

  def start(self):
    self.output1(self.string)
    self.short() # connect downstream run to upstream output

@addToDict
class Console(IODriverStage):
  """read from terminal if first else write to terminal"""
  names = ["CONSole", "TERMinal"]

  class First(InputDriverStage): # when first in a pipeline
    prompt = 'VM READ '
    priority = False
    def setup(self, specs):
      if specs: self.prompt = specs
    def start(self):
      while True:
        record = input(self.prompt)
        if record:
          self.output1(record)
        else:
          break

  class Other(OutputDriverStage): # when not first in a pipeline
    def setup(self, specs): pass
    def run(self, record):  print(record)

@addToDict
class Change(Stage):
  """Simple version - Specs must be delimeter string delimiter string delimiter."""
  names = ["CHANGE"]
  def setup(self, specs):
    specs = specs.strip()
    delim = specs[0]
    self.findstr, *self.repStr = specs[1:-1].split(delim)
    if len(self.repStr) == 1 and specs[-1] == delim:
      self.repStr = self.repStr[0]
      return
    else:
      self.message(2006)

  def run(self, record):
    self.output1(record.replace(self.findstr, self.repStr))

@addToDict
class FanInAny(Stage):
  names = ["FANINANY"]
  inputStreamDefs = '1++++++++++'
  outputStreamDefs = '1'
  strict = False

  def setup(self, specs):
    if specs.lower() == 'strict':
      self.strict = True
      self.message(2007)
    elif specs:
      self.message(2008, specs)

  def run(self, record):
    self.output1(record)

@addToDict
class Locate(Stage):
  names = ["LOCATE"]
  inputStreamDefs = '1'
  outputStreamDefs = '1+'

  def setup(self, specs):
    # the stage specification (specs) is a "delimitedString"
    # a delimitedString starts and ends with a delimiter and has no other occurrence of the delimiter.
    # the delimiter is any non-blank character.
    # the rest of the delimitedString is its "value"
    # in our example /@/ is the delimitedString and @ is its value.

    # parse specs to ensure it is a delimitedString and get its value
    specs = specs.strip() # ignore any leading or trailing blanks
    delimiter = specs[0] # get the delimiter
    if specs[-1] != delimiter: # ensure last char == delimiter
      self.message(60, specs[:-2]) # 60E Delimiter missing after string "string"
    self.locateString = specs[1:-1] # remainder is the value
    if delimiter in self.locateString: # ensure delimiter is not in the value
      self.message(999, specs[:-2]) # I don't know the correct error for this

  def run(self, record):
    if record is None or record.find(self.locateString) >= 0:
      self.output1(record)
    else:
      self.output2(record)

@addToDict
class Var(IODriverStage):
  """Retrieve or Set (a Variable in a REXX or CLIST Variable Pool)
  Actually retrieve or set a pipelineset property"""
  names = ["VAR"]
  var = None

  def setup(self, specs):
    self.var = specs # later allow for arguments

  class First(InputDriverStage): # when first in a pipeline
     def setup(self, specs):
      self.spec = specs # later allow for arguments

     def initializeRun(self):
        if hasattr(self.pipeLineSet, self.spec):
          self.source = getattr(self.pipeLineSet, self.spec)
        else:
          self.message(99) ## not the correct number

     def start(self):
      for record in self.source:

        self.output1(record)
      self.output1(None) # final step - send EOF

  class Other(OutputDriverStage): # when not first in a pipeline
    def setup(self, specs):
      self.spec = specs # later allow for arguments

    def initializeRun(self):
      try:
        setattr(self.pipeLineSet, self.spec, [])
        self.destination = getattr(self.pipeLineSet, self.spec)
      except:
        self.message(2010)

    def run(self, record):
      if record is not None: self.destination.append(record)

@addToDict
class Readfile(InputDriverStage):
  """reads lines from a file or items from a pipelineSet attribute"""
  names = ["READFILE", "<"]
  fileName = None

  def setup(self, specs):
    self.fileName = specs

  def initializeRun(self):
    try:
      self.source = open(self.fileName)
    except IOError:
      self.message(2009, self.fileName)

  def start(self):
    for record in self.source:
      record = record.strip('\n')
      self.output1(record)
    self.output1(None) # final step - send EOF

  def terminate(self):
    if self.fileName:
      self.source.close()

@addToDict
class Runpipe(Stage):
  """Each input record is a pipelineset specification.
     Create and run the the pipelineset. Send messages to output.
  ─RUNPIPE──┬──────────────────────┬──┬───────────────────────┬──
            └─MSGLevel──┬─number─┬─┘  ├─TRACE─────────────────┤
                        └─Xhex───┘    └─EVENTS──┬───────────┬─┘
                                                └─MASK──hex─┘ """
  def setup(self, specs):
    """parse specs per above syntax diagram"""
    
  def finalizeSetup(self):
    self.send_msg = self.outputStreams[0].run

  def run(self, record):
    pipelineset = PipeLineSet(record)
    if p.RC == 0:
      pipelineset.run()
    
@addToDict
class Writefile(OutputDriverStage):
  """writes lines to a file or items to a pipelineSet list attribute"""
  names  = ["WRITEFILE", ">"]
  fileName = None
  def setup(self, specs):
    self.fileName = specs

  def run(record):
    if record is not None: self.destination.write(record + '\n')

  def initializeRun(self):
    if self.fileName:
      try:
        self.destination = open(self.fileName, "w")
      except IOError:
        self.message(2011, self.fileName)

  def terminate(self):
    if self.fileName:
      self.destination.close()

# create dictionary {stageName:stageClass, ...}
# so we can lookup a stage name from the spec and get the class object
# account for abbreviations
def updateDictFromAbbrev(stageDict, names, cls):
  for name in names:
    for n, ch in enumerate(name):
      if not ('A' <=ch <= 'Z'):
        name = name.lower()
        d = dict((name[:x], cls) for x in range(max(n,1),len(name)+1))
        stageDict.update(d)
    stageDict[name.lower()] = cls

stageDict = {}
tempDict = addToDict() # get dictionary created by addToDict decorator
for name, cls in tempDict.items():
    if hasattr(cls, "names"):
      updateDictFromAbbrev(stageDict, cls.names, cls) # e.g. CONSole

'''Escaping special characters (endchar and separator)
A pipelineset specification has 1 or 2 special characters.
endchar (optional) segments tne pipelineset specificaiton into 2 or more pipeline specifications.
separator segments a pipeline specificaiton into 2 or more stage specifications.
To override the segmenting we "escape" the special character.
We do this by either
- preceding the special character with the escape character (if defined)
or by doubling the special character.

'''

def separate(spec, sep):
  """Generator to yield  specifications separated by unescaped seperator when 
     escape character is not defined. In this case a seperator is escaped only when
     the seperator is doubled;  replace with one separator.
     yields a tuple which starts with the position of the specification in the 
     spec followed by the specification. 
""" 
  anchor = 0 # start position for finding next sep 
  pos = 1 # origin 1 start position of yielded string in spec
  chunk = '' # collector of string to be yielded
  spec += ' ' # pad end
  ps = spec.find(sep) # find first sep
  while ps >= 0: # process sep
    if spec[ps+1] == sep: # doubled seperator
      chunk += spec[anchor:ps+1]
      anchor = ps + 2      
      ps = spec.find(sep, anchor) # find next sep
    else: # unescaped sep
      yield (pos, chunk + spec[anchor:ps])
      chunk = ''
      pos = ps + 2
      anchor = ps + 1
      ps = spec.find(sep, anchor) # find next sep 
  yield (pos, chunk + spec[anchor:-1])
      
def separateWithEscape(spec, sep, esc):
  """Generator to yield stage specifications separated by unescaped seperator and remove unescaped escape
     seperator is escaped when:
     - seperator is doubled - replace with one separator 
       separator preceeded by escape - remove escape
  
     Yield start char position and result. Advance start position.
     The escape character itself is ignored and any special meaning the following 
       character might have to the pipeline specification parser is suppressed,  
      so second character becomes just a "normal" one. Use two escape characters 
      to specify a single escape character in an argument string.
      --- escape is used to override the processing of a character that has special meaning to
    the PIPE command. These special characters include the stage separator character,
    the pipeline end character (if defined), and the escape character (if defined).
    Left parenthesis, right parenthesis, asterisk (*), period and colon (:) may have a
    special meaning, depending on their placement. You must place the escape character i
    mmediately before the character that you do not want treated as a special character.
    The escape character can be specified as a single character, char, or the 2-character
    hexadecimal representation of a character, hexchar. Do not enclose the hexadecimal
    representation in quotation marks. You cannot specify left parenthesis, right parenthesis,
    asterisk (*), period, colon (:), or blank for the escape character. There is no default
    escape character. You cannot specify the ESCAPE option for an individual stage."""

  anchor = 0 # start position for finding next esc and sep 
  pos = 1 # origin 1 start position of yielded string in spec
  chunk = '' # collector of string to be yielded
  spec += ' ' # pad end
  ps = spec.find(sep) # find first sep
  pe = spec.find(esc) # find first esc
  while pe >= 0 or ps >= 0: # special char found
    if ps < 0 or 0 <= pe < ps: # drop the escape char; keep following char
      chunk += spec[anchor:pe] + spec[pe+1]
      anchor = pe + 2
      if ps - pe == 1: # escaped seperator
        ps = spec.find(sep, anchor) # find next sep
      pe = spec.find(esc, anchor)  # find next esc
    elif spec[ps+1] == sep: # doubled seperator
      chunk += spec[anchor:ps+1]
      anchor = ps + 2      
      ps = spec.find(sep, anchor) # find next sep
    else: # unescaped sep
      yield (pos, chunk + spec[anchor:ps])
      chunk = ''
      pos = ps + 2
      anchor = ps + 1
      ps = spec.find(sep, anchor) # find next sep
  yield (pos, spec[anchor:-1])
             
class PipeLineSetSpecError(Exception):
  pass

      
class PipeLine(list):
  # container of information for error repoprting
  number = 1
  def __init__(self, spec, pos):
      self.spec = spec
      self.pos = pos
      self.no = PipeLine.number
      PipeLine.number += 1

class PipeLineSet(list, Message): # list of pipeLines
  '''Initialized with a pipeLine Set Specification
     to create a runnable PipeLineSet or generate error(s)'''
  
  RC = 0
  number = 0
  # default value for global options
  seperator = '|'
  endchar = None
  escape = None
  msglvl = 3
  positionInSpec = 0

  def __init__(self, spec):
    self.spec = spec
    PipeLineSet.number += 1
    # FO: parse global options from spec
    # for now just override
    self.endchar = '?'
    self.escape = '~'
    self.startQueue = [] # stages to start when running
    self.labels = {}
    try: # presumes a call to self.message raises an exception to stop processing
      # split spec into pipeLine spec(s)
      if self.endchar:
        pipeLinespecList = [pipeLineSpec for pipeLineSpec in separate(spec, self.endchar)]
      else:
        pipeLinespecList = [pipeLineSpec]
      # process each pipeLineSpec
      for number, (posInPipeLineSetSpec, pipeLineSpec) in enumerate(pipeLinespecList): # for each pipeLine spec
        pipeLine = PipeLine(pipeLineSpec, posInPipeLineSetSpec) # create the pipeLine (stage collection)
        self.append(pipeLine)
        # split pipeLineSpec into stage spec(s)
        if self.escape:
          stageSpecList = [spec for spec in separateWithEscape(pipeLineSpec, self.seperator, self.escape)]
        else:
          stageSpecList =  separate(pipeLineSpec, seperator)
        # process each stage Spec
        for stagePositionInPipeLine, (self.positionInSpec, stageSpec) in enumerate(stageSpecList):
          #create stage or reference priorly labeled stage
          word, rest = splitter(stageSpec)
          if word[-1] == ":": # label
            # first appearance of a label in a pipeLineset is its declaration; must be followed by a stage spec.
            # any subsequent appearance is a reference; must not be followed by a stage spec.
            # when a label is referenced we add streams to its stage
            labelName = word[:-1]
            stageName, stageSpecs = splitter(rest)
            if len(labelName) == 0:
              self.message(43) # sysact continue scan then stop return RC -43
            elif len(labelName) > 8:
              labelName = labelName[:8]
              self.message(19, labelName) # truncate warning
            if labelName in self.labels: # must be reference
              if stageSpecs: # definition not allowed
                self.message(47, labelName) # sysact continue scan then stop return RC -47
              else:
                label = self.labels[labelName]
            else:
              if stageSpec:
                label = self.labels[labelName] = Label()
              else:
                self.message(46, labelName) # sysact continue scan then stop return RC -46
          else: # no label
            stageName, stageSpecs = word, rest
            label = Label()
          # end of label processing
          if label.stage: # found a referenced stage
            stageInstance = label.stage
            stageInstance.addStream()
          else:  # make stage
            stageClass = stageDict.get(stageName, None)
            if stageClass is None:
              self.message(27, stageName) # sysact continue scan then stop return RC -27
            stageInstance = stageClass(self, stageName, stagePositionInPipeLine)
            x = stageInstance.setup(stageSpecs)
            label.stage = stageInstance
            stageInstance.posInPipeLineSetSpec = posInPipeLineSetSpec # start of this stage's spec in the pipeline spec
          # stage creation/reference complete
          self.RC = min(self.RC, stageInstance.RC)
          if stageInstance.RC == 0:
            pipeLine.append(stageInstance)
            stageInstance.pipeLine = pipeLine
            if stagePositionInPipeLine > 0: # not first stage
              # connect this stage's current instream to prior stage's current outputstream
              connect(priorStage, stageInstance)
            priorStage = stageInstance
      for pipeLine in self:
        for stage in pipeLine:
          stage.finalizeSetup() # validate streams & connections; user-defined stuff
    except PipeLineSetSpecError: # error causes early termination of scanner
      pass # set flag indicating pipeline not runnable
  
  def run(self):
    for pipeLine in self:
      for stage in pipeLine:
        stage.initializeRun()
    if self.RC == 0:
      for stage in self.startQueue:
        stage.start()
      for pipeLine in self:
        for stage in pipeLine:
          stage.terminate()

def connect(left, right):
  left.outputStreams[-1].output = right.inputStreams[-1].run
  left.outputStreams[-1].connected = True
  right.inputStreams[-1].connected = True
  x=3

def splitter(st):
  st = st.strip()
  if len(st) == 0:
    return ['', '']
  st =  st.split(None, 1)
  if len(st) == 2: return st
  else: return st[0], ''

class TestSuite:
  testNo = 0
  """Base class for test suites
     Each suite has
     - a pipelineset specification (string)
     - inputs - to be accesses using var x0, x1, ..
     - expected outputs - created by var y0, y1, ...
     - each input/output is a sequence of strings; each string is treated as a pipeline record
     Example:
       TestSuite("var x0 | var y0", [["test 4 @", "not me", "@me"]], [["test 4 @", "not me", "@me"]])
       arg1 is the pipelineset specification; var tells stage to get its records from the pipelineset attribute x0
       arg2 is a sequence (length 1) of a sequence of strings which will be assigned to x0
       arg3 is a sequence (length 1) of a sequence of strings (expected results) which will be asserted == to y0
  """
  def __init__(self, specs, inputs, outputs):
    TestSuite.testNo += 1
    print(TestSuite.testNo)
    pipeLineSet = PipeLineSet(specs)
    if pipeLineSet.RC == 0: # pipeLineSet successfully created
      for x, inPut in enumerate(inputs):
        setattr(pipeLineSet, 'x'+str(x),  inPut)
      pipeLineSet.run()
      for x, output in enumerate(outputs):
        assert getattr(pipeLineSet, 'y'+str(x)) == output

if __name__ == "__main__":
  os.chdir(root) # change this to suit your file system.
  with open("file1.txt", "w") as f:
    f.write("test 4 @\n")
    f.write("not me\n")
    f.write("@me")
  if len(sys.argv) > 1: # called from command line
    specs = sys.argv[1]
    pipeLineSet = PipeLineSet(specs)
    if pipeLineSet.RC == 0:
      pipeLineSet.run()
  else:
    # various Test Suites.
    TS = TestSuite
    TS("var x0 | var y0", [["cd", "ef"]], [["cd", "ef"]]) # simple pipeline
    TS("var x0 | var y0 ? var x1 | var y1", [["cd", "ef"], ["ab"]], [["cd", "ef"], ["ab"]]) # 2 indepependent pipelines
    TS("var x0 | locate /@/ | var y0", [["test 4 @", "not me", "@me"]], [["test 4 @","@me"]]) # simple pipeline testing locate
    TS("var x0 | x: locate /@/ | var y0 ? x: | var y1", [["test 4 @", "not me", "@me"]], [["test 4 @","@me"],["not me"]]) # multi-stream pipelineset
    # add test cases for the various errors that can be caught by the scanner (19, 27, 43, 46, 47)
    # need way to ensure processing stops and correct RC is given.
    
  """ Notes on message handling
  Goal: do it as close as possible to the IBM way.
  See Author's Edition chapter 26.
  Messages are stored in sqlite3 database errors.db table errors
  Table structure:
    id integer primary key, 
    severity char,
    rc integer,
    desc text,
    explanation text,
    sysact text,
    sysactcode integer,
    useract text,
    sysprog text,
    format_desc text

  Each error has a "system action". We guessed these from reading the system action text 
  0 = processing continues
  1 - scanner continues then processing ends. 
  2 - The read or write is ignored.
  3 - Processing terminates with return code
  4 - pipeline scan or stage terminates with return code.
  5 - stage or PIPMOD) terminates with return code.
  6 - The unit of work is rolled back. The stage terminates with return code.
  7 - If the file was opened successfully, the unit of work is rolled back. The stage terminates with return code.CommandCompiler
  8 - The ABEND condition is reset. The stage terminates with return code
  9 - The PIPE command ends.
 10 - The entry point is not resolved.
 11 - Results are unpredictable.
 12 - All stages waiting on an external event (waiting on an ecb) are signalled to terminate.
 13 - If the keyword is an operand, the stage ends. If the keyword is an option, processing continues until the scanner is complete, at which time processing ends.
 14 -
 
 
 97 - The command is ignored. A subsequent attention will cause TSO Pipelines to terminate those stages that wait on an external event.
 98 - CMS abend processing takes control.
 99 - Processing continues until control returns to the dispatcher, after which results are unpredictable.
 
 sysact_text = [("The stage terminates with return code", 5, 1),
  ("Pipeline scan terminates with return code", 1, 1),
  ("Processing terminates with return code", 3, 1),
  ("Message 1022 is issued to display the parameter list. The stage terminates with return code", 0, 1),
  ("Messages 1018 are issued to display the parameter list. The stage terminates with return code", 0, 1),
  ("The PIPE command or stage terminates with return code", 0, 1),
  ("The path is severed. The stage terminates with return code", 5, 1),
  ("The unit of work is rolled back. The stage terminates with return code", 6, 1),
  ("The unit of work waw rolled back by CMS. The stage terminates with return code", 6, 1),
  ("If the file was opened successfully, the unit of work is rolled back. The stage terminates with return code", 7, 1),
  ("The ABEND condition is reset. The stage terminates with return code", 8, 1),
  ("Processing continues.", 0, 0),
  ("the keyword keyword1 is ignored. Processing continues.", 0,  0),
  ("The tokenized parameter list is translated to uppercase before the command is issued. Processing continues.", 0,  0),
  ("The indicated keyword is ignored. Processing continues.", 0,  0),
  ("The stage ends.", 5, 3, 2),
  ("The stage or PIPMOD ends.", 5, 2),
  ("The program terminates. The stage returns with code", 5, 1),
  ("The scanner ends.", 4, 2),
  ("CMS abend processing takes control.", 98,  0),
  ("A program check is caused. CMS abend processing takes control.", 98,  0),
  ("RC=rc (the return code indicated in the message,  0). The stage ends.", 4, 0),
  ("An internal error has occurred in CMS Pipelines. An unexpected return code is received on a conversion operation.", 3,  0),
  ("If the error was found by the scanner, the scanner ends. If the error was found by a stage, the stage ends.", ),
  ("Processing ends.", 4),
  ("Processing continues until the scanner has completed, at which time processing ends.", 1),
  ("Processing continues until control returns to the dispatcher, after which results are unpredictable.", 99),
  ("Processing terminates with return code", 3),
  ("The PIPE command ends.", 9), # could be preceeded by RC=
  ("The entry point is not resolved.", 10),
  ("Results are unpredictable.", 11),
  ("All stages waiting on an external event (waiting on an ecb) are signalled to terminate.", 12),
  ("The command is ignored. A subsequent attention will cause TSO Pipelines to terminate those stages that wait on an external event.", ),
  ("The code page number is ignored.", ),
  ("The interrupt is ignored.", ),
  ("The status code is set accordingly.", ),
  ("The pipeline is stalled.", ),
  ("If the keyword is an operand, the stage ends. If the keyword is an option, processing continues until the scanner is complete, at which time processing ends.", 13),
  ("The value is ignored and the default is used instead.", ),
  ("Processing continues. The message was issued from the internal message table, which is in English.", 0),
  ("Processing continues. The stage validates all input as requested.", 0),
  ("he sliding window operand is ignored. The timestamp is converted using a base year of the current century for REXX_DATE_C or the current year for REXX_DATE_D.", ),
  ("System operation continues.", 0),
  ("The read or write is ignored.", 2),
  ("The program is not executed.", ),
  ("The dispatcher stops.", ),
  ("Diagnostic information is written to the file PIPDUMP LISTnnnn A. The input and output streams of all stages that have not yet completed are severed.", ),
  ("None.", 0),
  ("The service call is ignored.", ),
  ("The stream identifier is truncated after the first four characters. Processing continues.", ),
  ("The pipeline subcommand is ignored.", ),
  ("Remaining words are ignored.", ),]

  Severity I - processing continues.
  Decide which messages must be altered or omitted and which must be added.
  """
#------------------------- end pipe4.py -------------------------
