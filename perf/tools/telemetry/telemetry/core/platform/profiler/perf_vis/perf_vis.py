#!/usr/bin/python
import sys
import os
import json
from datetime import date

from collections import deque
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-f", "--frames", dest="nframes", default=3600,
    type="int", help="Number of frames in input")
parser.add_option("-s", "--start", dest="start_ts", default=0.0,
    type="float", help="Start timestamp")
parser.add_option("-e", "--end", dest="end_ts", default=1000000000000.0,
    type="float", help="End timestamp")
parser.add_option("-m", "--meta", dest="meta", default=None,
    type="string", help="Trace metadata")
parser.add_option("-o", dest="output", default=None,
    type="string", help="Output filename")
parser.add_option("-c", "--cpu-freq", dest="cpu_freq", default=1574400000,
    type="int", help="CPU cycles per second")

def Process(options, args):
  thread_names = {}

  if options.meta:
    with open(options.meta) as meta_file:
      meta = json.load(meta_file)

    options.nframes = meta.get('num_frames', 1)
    options.start_ts = meta.get('start_ts', 0.0)
    options.end_ts = meta.get('end_ts', 1000000000000.0)
    thread_names = meta.get('tid', {})

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
    def __init__(self, comm, tid):
      self.comm = comm
      self.tid = tid
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

  def filterSymbolModule(module):
    return module

  def filterSymbolName(module, orign_module, name):
    return name

  def outputPefVis(options, args):
    time_scale = 1000.0 / options.nframes / options.cpu_freq

    threads = {}

    def getThread(comm, tid):
      if tid in threads:
        thread = threads[tid]
      else:
        thread = Thread(comm, tid)
        threads[tid] = thread
      return thread

    fp = open(args[0])
    trace = json.load(fp)
    fp.close()

    # Process samples.
    stackFrames = trace['stackFrames']
    samples = trace['samples']

    for s in samples:
      samp_ts = s['ts'] / 1000.0
      if samp_ts < options.start_ts or samp_ts > options.end_ts:
        continue
      samp_time = float(s['weight']) * time_scale

      curr_thread = getThread(s['comm'], s['tid'])
      sf_id = s.get('sf')
      chain = deque()
      while sf_id != 0:
        sf = stackFrames[str(sf_id)]
        chain.appendleft((sf['name'], sf['category']))
        sf_id = sf.get('parent', 0)

      if len(chain) >= 1:
        # Add an entry with the same category, and name = base_category.
        c = chain[0]
        chain.appendleft((c[1], c[1]))

      # Add to call tree.
      ctree_node = curr_thread.call_tree
      for c in chain:
        chain_name = c
        if chain_name in ctree_node.children:
          ctree_node = ctree_node.children[chain_name]
        else:
          new_node = CallTreeNode(chain_name)
          new_node.parent_id = ctree_node.stack_id
          ctree_node.children[chain_name] = new_node
          ctree_node = new_node
          curr_thread.getSymbol(chain_name[0] + '@' + chain_name[1]) # tag symbol
      ctree_node.self_time += samp_time

    # Map thread names.
    for t in threads.values():
      if str(t.tid) in thread_names:
        t.name = thread_names[str(t.tid)]
      else:
        for m in thread_maps:
          match = False
          for s in m[1]:
            if s in t.symbols:
              match = True
              break
          if match:
            t.name = m[0]
            break

    def jsonCallTree(node, is_root = False):
      ret = {}
      name_comp = node.name
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

    threads_json = {'name': '<All Threads>', 'comp': 'root', 'children':[]}
    sorted_threads = sorted(threads.values(), key=lambda thread: -thread.call_tree.getTotTime())
    for t in sorted_threads:
      if ('chrome' in t.comm) or ('ntent_shell' in t.comm) or ('dboxed' in t.comm): 
        tjson = {}
        tjson['name'] = '<' + t.comm + ':' + t.name + '>'
        tjson['children'] = jsonCallTree(t.call_tree, True)
        tjson['comp'] = 'Thread'
        threads_json['children'].append(tjson)

    out_path = options.output
    if not out_path:
      out_base = os.path.basename(args[0])
      today = date.today()
      out_path = out_base + '_%02d%02d%02d.html' % (today.day, today.month, today.year)

    vis_path = os.path.abspath(os.path.dirname(__file__))
    # Load template
    with open(vis_path + '/perf-vis-template.html', 'r') as template_file:
      html_temp = template_file.read()

    # Add title
    html_temp = html_temp.replace('<page-title>', os.path.basename(out_path))

    # Add perf data json
    html_temp = html_temp.replace('<data_json>', json.dumps(threads_json, indent=0))

    # Add jquery-1.11.0.min.js
    with open(vis_path + '/jquery-1.11.0.min.js', 'r') as js:
      html_temp = html_temp.replace('<jquery-1.11.0.min.js>', js.read())

    # Add sammy-latest.min.js script
    with open(vis_path + '/sammy-latest.min.js', 'r') as js:
      html_temp = html_temp.replace('<sammy-latest.min.js>', js.read())

    # Add d3.v3.min.js script
    with open(vis_path + '/d3.v3.min.js', 'r') as js:
      html_temp = html_temp.replace('<d3.v3.min.js>', js.read())

    # Add jquery.dataTables.min.js
    with open(vis_path + '/jquery.dataTables.min.js', 'r') as js:
      html_temp = html_temp.replace('<jquery.dataTables.min.js>', js.read())

    # Add jquery.dataTables.min.css
    with open(vis_path + '/jquery.dataTables.css', 'r') as css:
      html_temp = html_temp.replace('<jquery.dataTables.css>', css.read())

    # Add perf-vis.js script
    with open(vis_path + '/perf-vis.js', 'r') as js:
      html_temp = html_temp.replace('<perf-vis.js>', js.read())

    # Write result
    print '### perf-vis output:', os.path.join(os.getcwd(), out_path)
    with open(out_path, 'w') as html_file:
      html_file.write(html_temp)


  outputPefVis(options, args)

if __name__ == "__main__":
  (options, arguments) = parser.parse_args()
  Process(options, arguments)
