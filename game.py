from copy import deepcopy
from collections import deque
import random
import torch
from enum import Enum

class GameElements(Enum):
    WALL = 0
    PLAYER = 1
    GOAL = 2
    BOX = 3
    FLOOR = 4
    BOX_ON_GOAL = 5
    PLAYER_ON_GOAL = 6
    BEDROCK = 7

class Game:

    def __init__(self, level_id=None, disable_prints=True):

        # Initialize the game board as a list of lists (2D array)
        self.level_id = level_id
        self.board = Game.load_microban_level(0) if self.level_id is None else Game.load_microban_level(self.level_id)
        
        # Initialize the game elements
        self.player_position = self.find_elements([GameElements.PLAYER.value, GameElements.PLAYER_ON_GOAL.value])[0]
        self.box_positions = sorted(self.find_elements([GameElements.BOX.value, GameElements.BOX_ON_GOAL.value]))
        self.box_dict = {} # TODO: simplify
        for i, box in enumerate(self.box_positions):
            self.box_dict[tuple(box)] = i # list no hashable
        self.goal_positions = sorted(self.find_elements([GameElements.PLAYER_ON_GOAL.value, GameElements.BOX_ON_GOAL.value, GameElements.GOAL.value]))
        self.edge_list = self.construct_edge_list(self.board)
        
        # Status of the game:
        self.disable_prints = disable_prints
        self.end = 0
        self.turn = 0
        self.max_number_of_turns = 100
        self.current_move = None
        
        
    # POST: Returns the board of the Microban level with the given level_id. level_id == 0 corresponds to a dummy training level used for testing.
    def load_microban_level(level_id):

        if level_id < 0 or level_id > 155:
            raise ValueError("Level ID must be between 1 and 155 for Microban levels.")
        
        with open(f"levels/microban.txt", "r") as file:
            lines = file.readlines()
            for i, line in enumerate(lines):
                if line.startswith(f"; {level_id}"):
                    j = i + 1
                    while not lines[j].startswith(";"):
                        j += 1
                    level = [list(lines[k][:-1]) for k in range(i+2,j-1)]
                    for row in range(len(level)):
                        for col in range(len(level[row])):
                            char = level[row][col]
                            if char == "#":
                                level[row][col] = GameElements.WALL.value
                            elif char == " ":
                                level[row][col] = GameElements.FLOOR.value
                            elif char == "$":
                                level[row][col] = GameElements.BOX.value
                            elif char == ".":
                                level[row][col] = GameElements.GOAL.value
                            elif char == "@":
                                level[row][col] = GameElements.PLAYER.value
                            elif char == "*":
                                level[row][col] = GameElements.BOX_ON_GOAL.value
                            elif char == "+":
                                level[row][col] = GameElements.PLAYER_ON_GOAL.value
                            elif char == ":":
                                level[row][col] = GameElements.BEDROCK.value
                    return level
    
    # Main loop of the game. If the game is played via the command line interface no moves need to be passed as arguments.
    # If the game is played step by step by an agent for example, the moves need to be passed as arguments.
    def play(self, moves=None):
        self.print_board()
        if moves is None:
            while(True):
                    self.turn+=1
                    self.input()
                    self.update_positions()
                    self.update_game_status()
                    self.print_board()
        else:
            for move in moves:
                self.turn+=1                   
                self.current_move = move
                self.update_positions()
                self.update_game_status()
                self.print_board()
            return self.state()
        
    # POST: Returns a move in ['w', 'a', 's', 'd']
    def input(self):
        while(True):
            user_input = input().strip().lower()
            if user_input in ["w", "a", "s", "d"]:
                self.current_move = user_input
                return
            else:
                print("Invalid input. Please enter 'w', 'a', 's', 'd'")
                return

    # Prints the current state of the game board
    def print_board(self, board=None):
        if self.disable_prints:
            return
        if board is None:
            board = self.board
            
        char_mapping = {
            str(GameElements.WALL.value): '#',
            str(GameElements.FLOOR.value): " ",
            str(GameElements.BOX.value): "$",
            str(GameElements.GOAL.value): ".",
            str(GameElements.PLAYER.value): "@",
            str(GameElements.BOX_ON_GOAL.value): "*",
            str(GameElements.PLAYER_ON_GOAL.value): "+",
            str(GameElements.BEDROCK.value): ":"
        }
        for row in board:
            
            row  = ''.join(str(element) for element in row)
            print("".join(char_mapping[char] for char in row))
       
    # POST: Returns the positions of all occurrences of element on the board
    # Search starts from the top left corner of the board
    # If a list of elements is passed, the function returns the positions of all occurrences of all the elements
    def find_elements(self, element, board=None):

        if board is None:
            board = self.board
        positions = [
            [x, y]
            for x, row in enumerate(board)
            for y, char in enumerate(row)
            if (isinstance(element, list) and char in element) or char == element
        ]
        return positions
    
    # POST: uses bfs to return the interior of a given board.
    # For example, the interior of the following board:
    # #####..
    # #   ###
    # #.$@$.#
    # #######
    # is:
    # #####::
    # #   ###
    # #     #
    # #######
    def find_interior(self, board=None):
        if board is None:
            board = self.board
        board = deepcopy(board)
        height = len(board)
        width = max([len(board[i]) for i in range(height)])
        interior = [[GameElements.WALL.value for _ in range(width)] for _ in range(height)]
        
        # use breadth first search to find the interior
        queue = deque([self.player_position])
        while queue:
            x, y = queue.popleft()
            if interior[x][y] == GameElements.WALL.value:
                interior[x][y] = GameElements.FLOOR.value
                for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                    new_x, new_y = x + dx, y + dy
                    if 0 <= new_x < height and 0 <= new_y < width and board[new_x][new_y] in [GameElements.FLOOR.value, GameElements.GOAL.value, GameElements.BOX.value, GameElements.BOX_ON_GOAL.value, GameElements.PLAYER.value, GameElements.PLAYER_ON_GOAL.value]:
                        if interior[new_x][new_y] == GameElements.WALL.value:
                            queue.append((new_x, new_y))
                            board[new_x][new_y] = ';' # mark as visited
                            
        for x in range(height):
            for y in range(width):
                if board[x][y] == GameElements.BEDROCK.value:
                    interior[x][y] = GameElements.BEDROCK.value
        return interior

    # POST: Draws the current Player and Box positions on the board
    def redraw_board(self, player_position=None, box_positions=None, board=None):
        if board is None:
            board = self.board
        if player_position is None:
            player_position = self.player_position
        if box_positions is None:
            box_positions = self.box_positions
            
        for goal_position in self.goal_positions:
            board[goal_position[0]][goal_position[1]] = GameElements.GOAL.value
    
        board[player_position[0]][player_position[1]] = GameElements.PLAYER_ON_GOAL.value if player_position in self.goal_positions else GameElements.PLAYER.value
        
        for box_position in box_positions:
            board[box_position[0]][box_position[1]] = GameElements.BOX_ON_GOAL.value if box_position in self.goal_positions else GameElements.BOX.value
        
    def update_positions(self):
        next_player_position = self.adjacent_position(self.player_position)
        next_player_obstacle = self.board[next_player_position[0]][next_player_position[1]]
        
        # Player runs into a wall
        if next_player_obstacle == GameElements.WALL.value:
            return
        # Player runs into a box
        elif next_player_obstacle in [GameElements.BOX.value, GameElements.BOX_ON_GOAL.value]:
            next_box_position = self.adjacent_position(next_player_position)
            next_box_obstacle = self.board[next_box_position[0]][next_box_position[1]]

            # Box can be pushed if there is floor or goal behind it
            if next_box_obstacle in [GameElements.FLOOR.value, GameElements.GOAL.value]:
                box_index = self.box_positions.index(next_player_position)
                self.box_dict[tuple(next_box_position)] = self.box_dict[(tuple(self.box_positions[box_index]))]
                self.box_dict.pop(tuple(self.box_positions[box_index]))
                self.box_positions[box_index] = next_box_position
                self.board[self.player_position[0]][self.player_position[1]] = GameElements.FLOOR.value
                self.player_position = next_player_position
                
            # There is a wall or another box behind the box, so it cannot be pushed    
            else:
                return
        # Next position is floor or goal
        elif next_player_obstacle in [GameElements.FLOOR.value, GameElements.GOAL.value]:
            self.board[self.player_position[0]][self.player_position[1]] = GameElements.FLOOR.value 
            self.player_position = next_player_position

        else:
            print("ERROR")
            assert(0)
        self.redraw_board()

    # POST: Returns the position of the player after a move
    def adjacent_position(self, position, move=None):
        if move is None:
            move = self.current_move
        move_dict = {"w": (-1, 0), "a": (0, -1), "s": (1, 0), "d": (0, 1)}
        delta_x, delta_y = move_dict.get(move, (0, 0))
        new_position = [position[0] + delta_x, position[1] + delta_y]
        return new_position

    # POST: Updates the game status:
    # Game is won if all boxes are on goals and the number of turns is less than the maximum number of turns
    # otherwise game is lost if the number of turns is greater than the maximum number of turns
    def update_game_status(self):
        if(sorted(self.box_positions) == sorted(self.goal_positions) and self.turn <= self.max_number_of_turns):
                self.end = 1
                if not self.disable_prints:
                    print("WIN!")
        elif self.turn > self.max_number_of_turns:
            self.end = 1
            if not self.disable_prints:
                print("LOSE!")

    # POST: Returns the features of the state if action were taken, without actually changing the state of the game
    # is used for the RL agent to compute the value of the next state
    def step(self, action):
        board = deepcopy(self.board)
        player_position = deepcopy(self.player_position)
        box_positions = deepcopy(self.box_positions)
        box_dict = deepcopy(self.box_dict)
        
        next_player_position = self.adjacent_position(player_position, move=action)
        next_player_obstacle = board[next_player_position[0]][next_player_position[1]]
        
        # Player runs into a wall
        if next_player_obstacle == GameElements.WALL.value:
            return
        # Player runs into a box
        elif next_player_obstacle in [GameElements.BOX.value, GameElements.BOX_ON_GOAL.value]:
            next_box_position = self.adjacent_position(next_player_position, move=action)
            next_box_obstacle = board[next_box_position[0]][next_box_position[1]]

            # Box can be pushed if there is floor or goal behind it
            if next_box_obstacle in [GameElements.FLOOR.value, GameElements.GOAL.value]:
                box_index = box_positions.index(next_player_position)
                box_dict[tuple(next_box_position)] = box_dict[(tuple(box_positions[box_index]))]
                box_dict.pop(tuple(box_positions[box_index]))
                box_positions[box_index] = next_box_position
                board[player_position[0]][player_position[1]] = GameElements.FLOOR.value
                player_position = next_player_position
                
            # There is a wall or another box behind the box, so it cannot be pushed    
            else:
                return

        elif next_player_obstacle in [GameElements.FLOOR.value, GameElements.GOAL.value]:
            board[player_position[0]][player_position[1]] = GameElements.FLOOR.value 
            player_position = next_player_position

        else:
            print("ERROR")
            assert(0)
        self.redraw_board(board=board, player_position=player_position, box_positions=box_positions)
        targets = self.targets(box_positions=box_positions)
        return self.embed(board, box_dict), self.reward(board, turn=self.turn+1), 1 if targets == 1 or self.turn + 1> self.max_number_of_turns else 0 
    
    # POST: Returns a dictionary that contains the distances between the start and the end positions, where the keys are the end positions and the values the distances
    def bfs(self, start, end, board):
        distance = {}
        reached_goals = set()
        queue = deque([start])
        height = len(board)
        width = max(len(row) for row in board)
        visited = [[False for _ in range(width)] for _ in range(height)]
        visited[start[0]][start[1]] = True
        step = 0
        while queue:
            for _ in range(len(queue)):
                x, y = queue.popleft()
                if [x, y] in end:
                    reached_goals.add((x, y))
                    distance[(x, y)] = step
                    if len(reached_goals) == len(end):
                        return distance
                for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                    new_x, new_y = x + dx, y + dy
                    if 0 <= new_x < height and 0 <= new_y < width and not visited[new_x][new_y]:
                        if board[new_x][new_y] in [GameElements.FLOOR.value, GameElements.GOAL.value, GameElements.BOX.value, GameElements.BOX_ON_GOAL.value, GameElements.PLAYER.value, GameElements.PLAYER_ON_GOAL.value]:
                            queue.append((new_x, new_y))
                            visited[new_x][new_y] = True
            step += 1
        return distance 
    
    def legal_moves(self):
        legal_moves = {"w": True, "a": True, "s": True, "d": True}
        for move in legal_moves:
            next_player_position = self.adjacent_position(self.player_position, move=move)
            next_player_obstacle = self.board[next_player_position[0]][next_player_position[1]]
            if next_player_obstacle == GameElements.WALL.value:
                legal_moves[move] = False
            if next_player_obstacle in [GameElements.BOX.value, GameElements.BOX_ON_GOAL.value]:
                next_box_position = self.adjacent_position(next_player_position, move=move)
                next_box_obstacle = self.board[next_box_position[0]][next_box_position[1]]
                if next_box_obstacle in [GameElements.WALL.value, GameElements.BOX.value, GameElements.BOX_ON_GOAL.value]:
                    legal_moves[move] = False
        return [key for key, value in legal_moves.items() if value is True]       
    
    def targets(self, box_positions):
        return len(set(map(tuple, box_positions)).intersection(set(map(tuple,self.goal_positions))))/len(self.box_positions)
    
    # POST: returns the state of the game
    def state(self):
        return self.embed(self.board, self.box_dict), self.reward(self.board, self.turn), self.end
    
    def reward(self, board, turn):
        if len(self.find_elements([GameElements.BOX_ON_GOAL.value], board)) == len(self.goal_positions) and turn < self.max_number_of_turns:
            return 1
        else:
            return 0
        
    
    def calculate_distance_matrix(self, board, box_dict):
        box_positions = sorted(self.find_elements([GameElements.BOX.value, GameElements.BOX_ON_GOAL.value], board=board))
        goal_positions = self.goal_positions # these don't change
        player_position = self.find_elements([GameElements.PLAYER.value, GameElements.PLAYER_ON_GOAL.value], board=board)[0]
        # distance matrix dist: dim(dist) =  [number_of_boxes + 1, number_of_boxes]
        # the first row contains the distance from the player to each of the boxes
        # for i > 1: dist[i][j] is the distance from the i-1 box to the j-th goal (i < number_of_boxes + 1, j < number_of_boxes)
        dist = torch.zeros(len(self.box_positions) + 1, len(self.box_positions))
        player_distances = self.bfs(start=player_position, end=box_positions, board=board)
        
        for key, value in player_distances.items():
            box_index = box_dict[key]
            dist[0,box_index] = value
       
        for j, goal in enumerate(goal_positions):
            goal_distances = self.bfs(start=goal, end=box_positions, board=board)
            for key, value in goal_distances.items():
                box_index = box_dict[key]
                dist[box_index+1][j] = value
        return dist
    
    # Nodes of the graph include all game elements exept WALLs and BEDROCK
    def embed(self, board, box_dict):
        height = len(board)
        width = len(board[0])
        nodes = []
        dist_mat = self.calculate_distance_matrix(board, box_dict)
        for i in range(height):
            for j in range(width):
                element = board[i][j]
                if element not in [GameElements.WALL.value, GameElements.BEDROCK.value]:
                    if element in [GameElements.PLAYER.value, GameElements.PLAYER_ON_GOAL.value]:
                        tensor = torch.concat((torch.tensor([element]), dist_mat[0,:])).view(1, -1)
                        nodes.append(tensor)  # Append tensor to the list
                    if element in [GameElements.BOX.value, GameElements.BOX_ON_GOAL.value]:
                        index = box_dict[(i,j)]
                        tensor = torch.concat((torch.tensor([element]), dist_mat[index+1,:])).view(1, -1)
                        nodes.append(tensor)  # Append tensor to the list
                    if element == GameElements.GOAL.value:
                        index = self.goal_positions.index([i, j])
                        tensor = torch.concat((torch.tensor([element]), dist_mat[1:, index])).view(1, -1)
                        nodes.append(tensor)  # Append tensor to the list
                    if element == GameElements.FLOOR.value:
                        tensor = torch.zeros((1, len(self.box_positions) + 1))
                        tensor[0,0] = element
                        nodes.append(tensor)
        
        nodes = torch.cat(nodes, dim=0)   
        self.print_board(board)
        return nodes
    
    def construct_edge_list(self, board):
        height = len(board)
        width = len(board[0])
        node_indices = {}
        ind = 0
        edge_list = [[],[]]
        for i in range(height):
            for j in range(width):
                if not board[i][j] in [GameElements.WALL.value, GameElements.BEDROCK.value]:
                    node_indices[(i,j)] = ind
                    ind +=1
        for i in range(height):
            for j in range(width):
                if board[i][j] not in [GameElements.WALL.value, GameElements.BEDROCK.value]:
                    for dx, dy in [(0,1), (1,0), (0,-1), (-1,0)]:
                        x = i + dx
                        y = j + dy
                        if (0 <= x < height) and (0 <= y < width):
                            if board[x][y] not in [GameElements.WALL.value, GameElements.BEDROCK.value]:
                                edge_list[0].append(node_indices[(i,j)])
                                edge_list[1].append(node_indices[(x,y)])

        return torch.tensor(edge_list, dtype=torch.int64).view((2, -1))
                            
if __name__ == "__main__":
    Warehouse = Game(1, disable_prints=False)
    Warehouse.play()