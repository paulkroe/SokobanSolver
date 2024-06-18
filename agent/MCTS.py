import numpy as np
from graphviz import Digraph
from queue import Queue
import random
from copy import deepcopy

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import game.Sokoban as Sokoban

C_PUT = 32 # 8
D_PUT = 8  # 100
LOOKAHEAD = 7

class Node():
    def __init__(self, parent, state, move, depth):
        self.depth = depth
        self.move = move
        self.state = state
        self.parent = parent
        self.children = {}
        self.q = 0
        self.n = 0
        self.reward = self.state.reward()
        self.max_value = self.reward
        self.sum_of_squares = self.reward.get_value()**2
        
    @property
    def u(self):
        if self.parent is None:
            return 0
        return C_PUT * np.sqrt(2*np.log(self.parent.n)) / (self.n) + np.sqrt(self.sum_of_squares / (self.n) - self.q**2 + D_PUT)
    
    @property
    def score(self):
        return self.q + self.u
    
    def update(self, value, max_value):
        self.q = (self.q * self.n + value) / (self.n + 1)
        self.n += 1
        self.sum_of_squares = self.sum_of_squares + value**2
        if self.max_value.get_value() < max_value.get_value():
            self.max_value = max_value
        if self.parent:
            self.parent.update(value, max_value) 
       
    def expand_node(self, valid_moves, mcts):
        added = 0
        for move in valid_moves:
            new_state = self.state.move(*move)
            new_hash = new_state.hash
            if not (new_hash in mcts.del_nodes or new_hash in mcts.nodes):
                child_node = Node(state=new_state, parent=self, move=move, depth=self.depth+1)
                added += 1
                self.children[move] = child_node
                mcts.nodes[new_hash] = child_node
                            
        # important that this is not done in one loop
        for move in valid_moves:
            if move in self.children: # could be that child caused cycle and thus was not added
                if self.children[move].reward.get_type() == "LOSS" or self.children[move] in mcts.del_nodes:
                    assert self.children[move].should_remove()
                    self.children[move].remove(mcts)
        
        if added == 0:
            assert self.should_remove() and (not self in mcts.del_nodes) #TODO: fix 
            self.remove(mcts)
        
         
    def select_child(self):
        if len(self.children) == 0:
            return None
        
        # if there is a unvisited node, visit that node first
        unvisited = [child for child in self.children.values() if child.n == 0]
        if len(unvisited) > 0:
            return random.choice(unvisited)
        
        best_score = max(child.score for child in self.children.values())
        best_children = [child for child in self.children.values() if child.score == best_score] 
        return random.choice(best_children) # break ties randomly

    def select_move(self):
        if len(self.children) == 0:
            return None
        else:
            best_value = max(child.max_value.get_value() for child in self.children.values())
            best_children = [child for child in self.children.values() if child.max_value.get_value() == best_value]
            return random.choice(best_children).move # break ties randomly
    
    def rollout(self):
        # perform bfs starting from current state until a depth of LOOKAHEAD and return maximal achieved reward
        state = self.state.copy()
        max_reward = state.reward()
        visited = set(state.hash)
        q = Queue()
        q.put((state, 0))
        while not q.empty():
            state, depth = q.get()
            if depth == LOOKAHEAD:
                break
            for move in state.valid_moves():
                new_state = state.move(*move)
                if new_state.reward().get_type() == "WIN":
                    return new_state.reward()
                if new_state.reward().get_type() == "STEP":
                    if new_state.hash not in visited:
                        visited.add(new_state.hash)
                        reward = new_state.reward()
                        if reward.get_value() > max_reward.get_value():
                            max_reward = reward
                        q.put((new_state, depth+1))
        return max_reward
    
    def should_remove(self):
        return len(self.children) == 0 and not (self.max_value.get_type() == "WIN")
        
    def remove(self, mcts):
        mcts.del_nodes.add(self.state.hash)
        del mcts.nodes[self.state.hash]
        assert len(self.children) == 0
        parent = self.parent
        if not parent is None:
            del parent.children[self.move]
            if parent.should_remove() or parent in mcts.del_nodes:
                parent.remove(mcts) 
        
    
    
class MCTS():
    def __init__(self, sokobanboard):
        self.root = Node(parent=None, state=sokobanboard, move=None, depth=0)
        self.del_nodes = set()
        self.nodes = {self.root.state.hash: self.root}
         
    def select_leaf(self, node):
        # if no node can be returned, return None
        while len(node.children) != 0 and node.reward.get_type() == "STEP":
            node = node.select_child()
            if node is None:
                break
        return node
    
    def expand(self, node):
        node.expand_node(node.state.valid_moves(), self)
                
    def run(self, simulations, visualize=False):
        for i in range(simulations):
            if i == 2000:
                self.visualize()
                assert 0
            # print(f"Simulation {i+1}, {len(self.nodes)} nodes, {len(self.del_nodes)} deleted nodes", end="\r")
            # selection phase
            node = self.select_leaf(self.root)
            # if all states have been explored and there is no solution, None will be returned during the selection phase
            if node is None:
                return None
            # rollout
            if node.n == 0:
                # random rollout
                reward = node.rollout()
                # backpropagate rollout value
                node.update(reward.get_value(), reward)
            # expansion phase
            else:
                # expand node
                self.expand(node)
                # it might be that all children have already been removed from the tree again and the node removed, for example if the child was a loss
                
                if len(node.children):
                # pick on chlid at random for simulation
                    node = random.choice(list(node.children.values()))
                    # rollout
                    reward = node.rollout()
                    # backpropagate rollout value
                    node.update(reward.get_value(), reward)
            if self.root.max_value.get_type() == "WIN":
                break
                
        if visualize:
            self.visualize()
            
        if self.root.max_value.get_type() == "WIN":
            moves = []
            node = self.root
            # if might be that after this loop node.state.reward().get_type() != "WIN" if the solution was discovered during rollout
            while len(node.children) != 0:
                move = node.select_move()
                moves.append(move)
                node = node.children[move]
            # find win with bfs
            if node.state.reward().get_type() != "WIN":
                moves.extend(self.find(node.state))           
        else:
            best_move = self.best_move
            if best_move is None:
                moves =  []
            else:
                moves = [self.best_move]
        return moves
    
    @property
    def best_move(self):
        return self.root.select_move()
    
    def visualize(self):
        visualize(self.root)

    def find(self, state):
        q = Queue()
        q.put((state, []))
        visited = set(state.hash)
        while not q.empty():
            state, moves = q.get()
            if state.reward().get_type() == "WIN":
                return moves
            for move in state.valid_moves():
                new_state = state.move(*move)
                if new_state.hash not in visited:
                    visited.add(new_state.hash)
                    q.put((new_state, moves + [move]))
        return []
    
def visualize(node):
    dot = Digraph()
    q = Queue()
    
    q.put(node)
    
    while not q.empty():
        node = q.get()
        node_label = node.state.__repr__()+f"\nscore: {round(node.score, 3)},\n max_value: {node.max_value},\n n: {node.n},\n steps: {node.state.steps}\nreward: {node.reward}\nmove: {node.move}, depth: {node.depth}, children: {node.children.keys()}"
        shape = 'oval'
        color = 'black'
        if node.reward.get_type() == "WIN":
            node_label += f"\noutcome: {node.reward.get_type()}"
            shape = 'octagon'
            color = 'green'
        elif node.reward.get_type() == "LOSS":
            node_label += f",\noutcome: {node.reward.get_type()}"
            shape = 'rectangle'
            color = 'red'
        dot.node(str(node), label=node_label, shape=shape, color=color)
        
        for child in node.children.values():
            q.put(child)
            dot.edge(str(node), str(child), label=str(child.move))
    
    dot.render('mcts', format='pdf', cleanup=True)