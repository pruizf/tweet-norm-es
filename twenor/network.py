
# Assumes depth-first for now...

import pdb, copy

class Node(object):
    def __init__(self, depth):
        self.targets = None    
        self.depth = depth

    def add_targets(self, targets):
        if targets != None:
            if isinstance(targets, list):
                self.targets = targets
            else:
                self.targets = [].append(targets)

    def propagate(self, proc):
        proc.process_node(self, self.depth)
        if self.targets != None:
            for t in self.targets:                
                t.propagate(proc)
            
    def erase_targets(self):        
        if self.targets != None:    
            for t in self.targets:
                t.erase_targets()
            self.targets = None
                
    def get_info(self):
        pass
        
class TweetNode(Node):
    def __init__(self, depth, orig, cand, recase, is_OOV):
        super(TweetNode, self).__init__(depth)
        self.orig = orig
        self.cand = cand
        self.recase = recase
        self.is_OOV = is_OOV
    
    def get_info(self):
        return (self.orig, self.cand, self.recase, self.is_OOV)
        
class StartNode(Node):
    def __init__(self, depth):    
        super(StartNode, self).__init__(depth)

    def propagate(self, proc):
        if self.targets != None:        
            for t in self.targets:
                t.propagate(proc)            
            
class EndNode(Node):
    def __init__(self, depth):    
        super(EndNode, self).__init__(depth)
        self.res = []

    def propagate(self, proc):
        self.res.append(proc.get_results()[:])
        
    def get_results(self):        
        return self.res

    def initialize(self):
        del self.res[:]
        
class Proc(object):
    def __init__(self):
        self.res = []
        
    def get_results(self):
        return self.res
        
    def process_node(self, n, node_depth):
        if len(self.res) >= node_depth:
            self.res = self.res[:node_depth-1]

    def fork(self):
        if len(self.res) == 0:
            self.res.append
            
    def initialize(self):
        del self.res[:]
        
class TweetCandProc(Proc):        
    def __init__(self):    
        super(TweetCandProc, self).__init__()
        self.tweet_id = 0

    def initialize(self, tid):    
        self.tweet_id = tid
        Proc.initialize(self)
        
    def process_node(self, n, node_depth):
        super(TweetCandProc, self).process_node(n, node_depth)
        self.res.append(n.get_info())
        
class Network(object):
    def __init__(self):
        self.cur_depth = 0
        self.start = StartNode(self.cur_depth)
        self.end = EndNode(self.cur_depth)
        self.leaves = []
        self.initialize()
        self.num_nodes = 0
        self.num_paths = 0
        
    def traverse(self, proc):
        if self.closed:
            self.start.propagate(proc)            
            return self.end.get_results()
        else:
            return []
        
    def get_num_nodes(self):
        return self.num_nodes

    def get_num_paths(self):
        return self.num_paths

    def get_depth(self):
        return self.cur_depth
        
    def get_results(self):
        return self.end.get_results()
        
    def add_leaves(self, leaves):
        self.cur_depth += 1
        if self.num_paths == 0:
            self.num_paths = len(leaves)
        else:
            self.num_paths *= len(leaves)        
        node_leaves = [TweetNode(self.cur_depth, l[0], l[1], l[2], l[3]) for l in leaves]
        self.num_nodes += len(node_leaves)        
        for l in self.leaves:
            l.add_targets(node_leaves)
        del self.leaves[:]
        self.leaves.extend(node_leaves)

    def initialize(self):
        self.num_nodes = 0
        self.num_paths = 0
        self.cur_depth = 0
        del self.leaves[:]
        self.start.erase_targets()
        self.leaves.append(self.start)        
        self.end.initialize()
        self.closed = False
        
    def close(self):
        self.cur_depth += 1
        self.closed = True
        #pdb.set_trace()      
        end_list = [] 
        self.end.cur_depth = self.cur_depth
        end_list.append(self.end) 
        for l in self.leaves:            
            l.add_targets(end_list)
        del self.leaves[:]
        
   
