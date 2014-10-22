#!/usr/bin/python
import re
import sys
import os
import pdb
import json
from datetime import date

from collections import deque

from optparse import OptionParser

parser = OptionParser()
parser.add_option("-f", "--frames", dest="nframes", default=3600,
    type="int", help="Number of frames in input")
parser.add_option("-t", "--template", dest="template", default=None,
    type="string", help="Report template file")
parser.add_option("-c", "--cpu-freq", dest="cpu_freq", default=1574400000,
    type="int", help="CPU cycles per second")

(options, args) = parser.parse_args()

#print "Options", options
#print "Args", args

class LineReader:
  def __init__(self, fp):
    self.fp = fp
    self.line = None

  def peek(self):
    if self.line == None:
      self.line = fp.readline()
    return self.line

  def next(self):
    self.line = None

class Symbol:
  def __init__(self, name):
    self.name = name

class CallTreeNode:
  stack_id = 0
  def __init__(self, name):
    CallTreeNode.stack_id += 1
    self.stack_id = CallTreeNode.stack_id
    self.parent_id = 0
    self.parent = None
    self.name = name
    self.self_time = 0.0
    self.tot_time = 0.0
    self.have_tot_time = False
    self.children = {}

  def getTotTime(self):
    if self.have_tot_time:
      return self.tot_time
    else:
      self.tot_time = self.self_time
      for c in self.children.values():
        self.tot_time += c.getTotTime()
      self.have_tot_time = True
      return self.tot_time

class Thread:
  def __init__(self, comm):
    self.comm = comm
    self.symbols = {}
    self.name = "???"

    self.call_tree = CallTreeNode('root')
    self.sf_map = {}
    self.sf_map[0] = self.call_tree

  def getCtree(self, sf_id, name):
    if sf_id in self.sf_map:
      return (self.sf_map[sf_id], False)
    else:
      self.getSymbol(name) # tag symbol
      newNode = CallTreeNode(name)
      self.sf_map[sf_id] = newNode
      return (newNode, True)

  def getSymbol(self, name):
    if name in self.symbols:
      sym = self.symbols[name]
    else:
      sym = Symbol(name)
      self.symbols[name] = sym
    return sym

# Derrive thread names based on existing symbols.
thread_maps = [ ("Browser Main", ["cc::SingleThreadProxy::DoCommit(scoped_ptr<cc::ResourceUpdateQueue, base::DefaultDeleter<cc::ResourceUpdateQueue> >)@Chrome"]),
                ("Renderer Main", ["blink::WebViewImpl::layout()@Chrome"]),
                ("Browser InProcGpuThread", ["gpu::GpuScheduler::PutChanged()@Chrome"]),
                ("Browser AsyncTransferThread", ["gpu::(anonymous namespace)::TransferStateInternal::PerformAsyncTexImage2D(gpu::AsyncTexImage2DParams, gpu::AsyncMemoryParams, gpu::ScopedSafeSharedMemory*, scoped_refptr<gpu::AsyncPixelTransferUploadStats>)", "gpu::(anonymous namespace)::TransferStateInternal::PerformAsyncTexSubImage2D(gpu::AsyncTexSubImage2DParams, gpu::AsyncMemoryParams, gpu::ScopedSafeSharedMemory*, scoped_refptr<gpu::AsyncPixelTransferUploadStats>)@Chrome", "gpu::(anonymous namespace)::TransferStateInternal::PerformAsyncTexSubImage2D(gpu::AsyncTexSubImage2DParams, gpu::AsyncMemoryParams, scoped_refptr<gpu::AsyncPixelTransferUploadStats>)@Chrome"]),
                ("Renderer Compositor", ["cc::Scheduler::NotifyReadyToCommit()@Chrome"]),
                ("Browser IOThread", ["content::BrowserThreadImpl::IOThreadRun(base::MessageLoop*)@Chrome"]),
                ("Browser FileThread", ["content::BrowserThreadImpl::FileThreadRun(base::MessageLoop*)@Chrome"]),
                ("Browser DBThread", ["content::BrowserThreadImpl::DBThreadRun(base::MessageLoop*)@Chrome"]),
                ("Browser ChildIOThread", ["content::GpuChannelMessageFilter::OnMessageReceived(IPC::Message const&)@Chrome"]),
                ("Renderer ChildIOThread", ["IPC::SyncMessageFilter::SendOnIOThread(IPC::Message*)@Chrome"]),
                ("Renderer RasterWorker", ["cc::Picture::Raster(SkCanvas*, SkDrawPictureCallback*, cc::Region const&, float)@Chrome", "cc::(anonymous namespace)::RasterFinishedTaskImpl::RunOnWorkerThread()@Chrome"]),
                ("DVM Compiler", ["dvmCompilerAssembleLIR(CompilationUnit*, JitTranslationInfo*)@Java"]),
                ("DVM GC", ["dvmHeapBitmapScanWalk(HeapBitmap*, void (*)(Object*, void*, void*), void*)@Java"]),
                ("Adreno Driver", ["adreno_drawctxt_wait@Kernel"]),
              ]

# Categorize DSOs by component.
dso_to_comp = {'libdvm.so': 'Java',
               'dalvik-jit-code-cache (deleted)': 'Java',
               'libjavacore.so': 'Java',
               'libandroid_runtime.so': 'Android',
               'libgui.so': 'Android',
               'libui.so': 'Android',
               'libbinder.so': 'Android',
               'libmemalloc.so': 'Android',
               'libcrypto.so': 'Android',
               'libcutils.so':'Android',
               '[kernel.kallsyms]': 'Kernel',
               'libc.so': 'Standard Lib',
               'libstdc++.so': 'Standard Lib',
               'libm.so':'Standard Lib',
               'libutils.so': 'Standard Lib',
               'libGLESv2_adreno.so': 'GPU Driver',
               'libEGL_adreno.so': 'GPU Driver',
               'libEGL.so': 'GPU Driver',
               'libgsl.so': 'GPU Driver',
               'libGLESv2.so': 'GPU Driver',
               'eglsubAndroid.so': 'GPU Driver',
               'gralloc.msm8960.so': 'GPU Driver',
               'libadreno_utils': 'GPU Driver',
               'libGLES_mali.so': 'GPU Driver',
               'libchromeview.so': 'Chrome',
               '[unknown]': '<unknown>',
               '[UNKNOWN]': '<unknown>',
               }

def filterSymbolModule(module):
  m = dso_to_comp.get(module, None)
  if m:
    return m  
  if module.find('libchrome.') == 0:
    return 'Chrome'
  return module

def filterSymbolName(module, orign_module, name):
  if module == 'Java':
    return orign_module
  elif module == 'GPU Driver':
    return orign_module
  if name == '':
    return orign_module + ':unknown'
  if name[0].isdigit() or name == '(nil)':
    return orign_module + ':unknown'
  return name

def outputPefVis(options, args):
  tot_time = 0.0
  time_recorded = 0.0
  time_scale = 1000.0 / options.nframes / options.cpu_freq

  threads = {}

  def getThread(comm):
    if comm in threads:
      thread = threads[comm]
    else:
      thread = Thread(comm)
      threads[comm] = thread
    return thread

  fp = open(args[0])
  trace = json.load(fp)
  fp.close()

  # Process samples
  stackFrames = trace['stackFrames']
  samples = trace['samples']

  for s in samples:
    samp_time = float(s['weight']) * time_scale
    tot_time += samp_time

    curr_thread = getThread(s['tid'])
    sf_id = s.get('sf')
    chain = deque()
    while sf_id != 0:
      sf = stackFrames[str(sf_id)]
      chain.appendleft(sf)
      sf_id = sf.get('parent', 0)

    seen_syms = set()
    ctree_node = curr_thread.call_tree
    for c in chain:
      base_category = os.path.basename(c['category'])
      category = filterSymbolModule(base_category)
      name = filterSymbolName(category, base_category, c['name'])
      chain_name = name + '@' + category
      if chain_name not in seen_syms: # Cull recursing methods
        seen_syms.add(chain_name)
        if chain_name in ctree_node.children:
          ctree_node = ctree_node.children[chain_name]
        else:
          new_node = CallTreeNode(chain_name)
          new_node.parent_id = ctree_node.stack_id
          ctree_node.children[chain_name] = new_node
          ctree_node = new_node
          curr_thread.getSymbol(chain_name) # tag symbol
    ctree_node.self_time += samp_time
    time_recorded += samp_time

  print "// tot_time", tot_time
  print "// time_recorded", time_recorded

  # Map thread names
  for t in threads.values():
    for m in thread_maps:
      match = False
      for s in m[1]:
        if s in t.symbols:
          match = True
          break
      if match:
        t.name = m[0]
        break

  def getNodeSiblings(node):
    if not node:
      return []
    if not node.parent:
      return []
    return node.parent.children.values()


  def fixCallTree(node, parent):
    node.parent = parent
    # Try to reduce misplaced leafs
    parent_siblings = getNodeSiblings(parent)
    for s in parent_siblings:
      if s.name == node.name and len(s.children) == 0 and s.self_time <= node.getTotTime() * 0.15:
        node.self_time += s.self_time
        s.self_time = 0
        break

    for c in node.children.values():
      fixCallTree(c, node)

  def printCallTree(node, depth):
    # Bail for smallest nodes
    if round(node.getTotTime(), 3) == 0.0:
      return
    sys.stdout.write(('+' * depth) + '%s %0.3f\n' % (node.name, node.getTotTime()))
    for c in sorted(node.children.values(), key=lambda c: -c.getTotTime()):
      printCallTree(c, depth + 1)

  def sumCallTree(node):
    ret = node.self_time
    for c in node.children.values():
      ret += sumCallTree(c)
    return ret

  def jsonCallTree(node, is_root = False):
    ret = {}
    name_comp = node.name.split('@')
    ret['name'] = name_comp[0]
    if len(name_comp) > 1:
      ret['comp'] = name_comp[1]

    if len(node.children) > 0 or is_root:
      ret['children'] = []
      for c in sorted(node.children.values(), key=lambda c: -c.getTotTime()):
        ret['children'].append(jsonCallTree(c))
      if node.self_time > 0.0:
        ret['children'].append({'name': '<self>', 'comp': ret['comp'], 'size': node.self_time})
    else:
      ret['size'] = node.self_time
    if is_root:
      return ret['children']
    else:
      return ret

  tot_thread_time = 0.0
  threads_json = {'name': '<All Threads>', 'comp': 'root', 'children':[]}
  sorted_threads = sorted(threads.values(), key=lambda thread: -thread.call_tree.getTotTime())
  for t in sorted_threads:
    thread_time = t.call_tree.getTotTime()
    tot_thread_time += thread_time
    #print "// Thread %s time %0.3f" % (t.name, thread_time)

    fixCallTree(t.call_tree, None)

    tjson = {}
    tjson['name'] = '<' + t.name + '>'
    tjson['children'] = jsonCallTree(t.call_tree, True)
    tjson['comp'] = 'Thread'
    threads_json['children'].append(tjson)
    
  if len(args) > 1:
    out_base = args[1]
  else:
    out_base = os.path.basename(args[0])
  today = date.today()
  out_base += '_%02d%02d%02d' % (today.day, today.month, today.year)

  vis_path = os.path.abspath(os.path.dirname(__file__))
  # Load template
  with open(vis_path + '/perf-vis-template.html', 'r') as template_file:
    html_temp = template_file.read()

  # Add perf data json
  html_temp = html_temp.replace('<data_json>', json.dumps(threads_json, indent=0))

  # Add jquery-1.11.0.min.js
  with open(vis_path + '/jquery-1.11.0.min.js', 'r') as js:
    html_temp = html_temp.replace('<jquery-1.11.0.min.js>', js.read())

  # Add d3.v3.min.js script
  with open(vis_path + '/sammy-latest.min.js', 'r') as js:
    html_temp = html_temp.replace('<sammy-latest.min.js>', js.read())

  # Add d3.v3.min.js script
  with open(vis_path + '/d3.v3.min.js', 'r') as js:
    html_temp = html_temp.replace('<d3.v3.min.js>', js.read())

  # Add sequences.js script
  with open(vis_path + '/sequences.js', 'r') as js:
    html_temp = html_temp.replace('<sequences.js>', js.read())

  # Write result
  print '// output:', os.path.join(os.getcwd(), out_base + '.html')
  with open(out_base + '.html', 'w') as html_file:
    html_file.write(html_temp)
  

outputPefVis(options, args)
