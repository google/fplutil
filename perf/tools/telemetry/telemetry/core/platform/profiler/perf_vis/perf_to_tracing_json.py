#!/usr/bin/python
# Copyright (c) 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import sys
from collections import deque
from optparse import OptionParser

# Line reading helper.
class LineReader:
  def __init__(self, fp):
    self.fp = fp
    self.line = None

  def peek(self):
    if self.line == None:
      self.line = self.fp.readline()
    return self.line

  def next(self):
    self.line = None

class StackFrameNode:
  def __init__(self, stack_id, name, dso):
    self.stack_id = stack_id
    self.parent_id = 0
    self.name = name
    self.dso = dso
    self.children = {}

  def ToDict(self, out_dict):
    if self.stack_id:
      node_dict = {}
      node_dict['name'] = self.name
      node_dict['category'] = self.dso
      if self.parent_id:
        node_dict['parent'] = self.parent_id

      out_dict[self.stack_id] = node_dict

    for child in self.children.values():
      child.ToDict(out_dict)
    return out_dict

class PerfSample:
  def __init__(self, stack_id, ts, cpu, tid, weight, type, comm):
    self.stack_id = stack_id
    self.ts = ts
    self.cpu = cpu
    self.tid = tid
    self.weight = weight
    self.type = type
    self.comm = comm

  def ToDict(self):
    ret = {}
    ret['ts'] = self.ts * 1000000.0  # Timestamp in us
    ret['tid'] = self.tid  # Thread id
    ret['cpu'] = self.cpu  # Sampled CPU
    ret['weight'] = self.weight  # Sample weight
    ret['name'] = self.type  # Sample type
    ret['comm'] = self.comm  # Command
    assert self.stack_id != 0
    if self.stack_id:
      ret['sf'] = self.stack_id  # Stack frame id
    return ret

def Main(args): 
  parser = OptionParser()
  parser.add_option("-l", "--limit-samples", dest="limit_samples", default=0,
      type="int", help="Limit number of samples processed")
  (options, args) = parser.parse_args()

  fp = open(args[0])
  reader = LineReader(fp)

  samples = []
  root_chain = StackFrameNode(0, 'root', '[unknown]')
  next_stack_id = 1
  tot_period = 0
  saved_period = 0

  # Parse samples header.
  while True:
    l = reader.peek()
    reader.next() # Eat line
    if not l:
      break

    # Skip comments
    if len(l) >= 1 and l[0] == '#':
      continue

    # TODO(vmiura): Parse these in a more readable way.
    l = l.strip()
    toks = l.split('\t')
    samp_command = toks[0]
    samp_tid = int(toks[1])
    samp_cpu = int(toks[2][1:-1])
    samp_ts = float(toks[3][0:-1])
    samp_period = int(toks[5])
    samp_type = toks[4][0:-1]
    tot_period += samp_period

    # Parse call chain.
    chain = deque()
    while True:
      l = reader.peek()
      reader.next() # Eat line
      if l and l.strip() != '':
        # TODO(vmiura): Parse these in a more readable way.
        toks1 = l.strip().split(' ', 1)
        toks2 = toks1[1].rsplit(' ', 1)
        cs_name = toks2[0]
        cs_dso = toks2[1][1:-1]
        chain.appendleft((cs_name, cs_dso))
      else:
        # Done reading call chain.  Add to stack frame tree.
        seen_syms = set()
        stack_frame = root_chain
        for call in chain:
          if call not in seen_syms: # Cull recursing methods.
            seen_syms.add(call)
            if call in stack_frame.children:
              stack_frame = stack_frame.children[call]
            else:
              new_node = StackFrameNode(next_stack_id, call[0], call[1])
              next_stack_id += 1
              new_node.parent_id = stack_frame.stack_id
              stack_frame.children[call] = new_node
              stack_frame = new_node

        # Save sample.
        sample = PerfSample(stack_frame.stack_id,
                        samp_ts,
                        samp_cpu,
                        samp_tid,
                        samp_period,
                        samp_type,
                        samp_command)
        samples.append(sample)
        saved_period += samp_period
        break
    if options.limit_samples and len(samples) >= options.limit_samples:
      break

  #print "// Num Samples:", len(samples)
  #print "// Tot period:", tot_period
  #print "// Saved period:", saved_period

  trace_dict = {}
  trace_dict['samples'] = [s.ToDict() for s in samples]
  trace_dict['stackFrames'] = root_chain.ToDict({})
  trace_dict['traceEvents'] = []

  json.dump(trace_dict, sys.stdout, indent=1)

if __name__ == '__main__':
  sys.exit(Main(sys.argv[1:]))
