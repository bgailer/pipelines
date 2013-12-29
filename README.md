pipelines
=========
pipe.py can be used to easily automate data manipulation tasks. A very simple example: you want to get the lines in a file (file1.txt) that contain the character string apple and put them in file2.txt

So you enter on a command line:

pipe.py "readfile c:\file1.txt | locate /apple/ | writefile c:\file2.txt"

And viola the job is done.

Well you say I can do that using grep apple file1.txt > file2.txt. But the order of operations is counter-intuitive, and what if you are running Windows?

Pipelines is more intuitive, consistent and powerful than *nix utilities and pipes.

The concept was originally developed by John Hartmann of IBM Denmark. See http://en.wikipedia.org/wiki/Hartmann_pipeline. John created a mainframe-specific version, but nothing cross-platform.
How it works

pipe.py invokes the pipe program passing rest of the command line as argument (hereinafter known as a pipeline specification, or spec for short). The quotes are essential - otherwise the arguments will be parsed by the command (shell) processor.

The vertical bar (|) separates the pipeline specification into stages.

The first word of each stage is the stage name; the rest is the stage specification

"readfile c:\file1.txt | locate /apple/ | writefile c:\file2.txt"

stage stage name stage specification

"readfile c:\file1.txt " "readfile" " c:\file1.txt"
" locate / apple/ " "locate" "/apple/"
" writefile c:\file2.txt" "writefile" " c:\file2.txt"

Observations:

readfile reads a record from c:\file1.txt and sends it to locate.
if the record contains apple, locate sends it to writefile.
writefile writes the record to c:\file2.txt
repeat above until readfile reaches EOF 

Author
======
Bob Gailer (bgailer@gmail.com)
