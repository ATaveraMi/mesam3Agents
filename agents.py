from mesa import Agent
import random
from mesa.space import MultiGrid
from map import endList


class BuildingAgent(Agent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.is_building = True

    def step(self):
        pass

class TrafficLightAgent(Agent):
    def __init__(self, unique_id, model, pos, state):
        super().__init__(unique_id, model)
        self.pos = pos
        self.state = state  # Initial state: "red", "green", or "yellow"
        

        self.timer = 5 if state == "green" else 7  # Set initial timer based on initial state

    def step(self):
        pass  

class PersonAgent(Agent):
    def __init__(self, unique_id, model, start_pos):
        super().__init__(unique_id, model)
        self.pos = start_pos  # Current position
        self.target_positions = [(7, 7), (11, 7), (15, 7), (7, 11), (15, 11), (15, 15), (11, 15), (7, 15)]
        self.target_index = self.target_positions.index(start_pos)  # Start at the correct index
        self.is_blocked = False  # Tracks whether the pedestrian is blocked by a wreckless driver

    def get_closest_traffic_light(self):
        """
        Find the closest traffic light to the person's current position.
        """
        closest_light = None
        min_distance = float("inf")
        for agent in self.model.schedule.agents:
            if isinstance(agent, TrafficLightAgent):
                distance = abs(self.pos[0] - agent.pos[0]) + abs(self.pos[1] - agent.pos[1])
                if distance < min_distance:
                    min_distance = distance
                    closest_light = agent
        return closest_light

    def get_next_step(self, target):
        """
        Calculate the next step towards the target position.
        """
        current_x, current_y = self.pos
        target_x, target_y = target

        # Determine step direction
        if current_x < target_x:
            next_x = current_x + 1
        elif current_x > target_x:
            next_x = current_x - 1
        else:
            next_x = current_x

        if current_y < target_y:
            next_y = current_y + 1
        elif current_y > target_y:
            next_y = current_y - 1
        else:
            next_y = current_y

        return next_x, next_y

    def can_move_to(self, position):
        """
        Determines if the pedestrian can move to a position.
        Returns True if there is no CarAgent in the target position.
        """
        cell_contents = self.model.grid.get_cell_list_contents([position])
        for agent in cell_contents:
            if isinstance(agent, CarAgent):
                return False  # Cannot move if there is a car
        return True  # Can move if there are no cars

    def move(self):
        """
        Move one cell at a time towards the next target position if the closest traffic light is red.
        """
        # If blocked by a wreckless driver, do nothing
        if self.is_blocked:
            return

        # Get the closest traffic light
        closest_light = self.get_closest_traffic_light()

        # Check if the traffic light is red
        if closest_light and closest_light.state == "red":
            # Determine the next target position
            target_pos = self.target_positions[self.target_index]

            # Calculate the next step towards the target position
            next_pos = self.get_next_step(target_pos)

            # Move to the calculated next position if possible
            if next_pos != self.pos and self.can_move_to(next_pos):
                self.model.grid.move_agent(self, next_pos)
                self.pos = next_pos

            # Check if the pedestrian has reached the target position
            if self.pos == target_pos:
                # Update to the next target position
                self.target_index = (self.target_index + 1) % len(self.target_positions)

    def step(self):
        # Check if a wreckless driver is in the same cell
        cell_contents = self.model.grid.get_cell_list_contents([self.pos])
        self.is_blocked = any(isinstance(agent, WrecklessAgent) for agent in cell_contents)
        self.move()

class WrecklessAgent(Agent):
    def __init__(self, unique_id, model, starting_pos, agent_type="wreckless"):
        super().__init__(unique_id, model)
        self.starting_pos = starting_pos
        self.agent_type = agent_type
        self.state = "wreckless"
        self.happiness = 100
        self.jammedCounter = 0
        self.last_passed_lights = set()  # Initialize the attribute to track passed streetlights

        # Initialize the current direction based on starting position
        if self.starting_pos[1] == 0:  # Moving up
            self.current_direction = "up"
        elif self.starting_pos[1] == self.model.grid.height - 1:  # Moving down
            self.current_direction = "down"
        elif self.starting_pos[0] == 0:  # Moving right
            self.current_direction = "right"
        elif self.starting_pos[0] == self.model.grid.width - 1:  # Moving left
            self.current_direction = "left"
    def skip_stop_sign(self, semaphore):
        """
        Determines whether the agent should skip the stop sign or stop based on a 60% skip (True) or 40% stop (False).
        """
        # 60% chance to skip (True), 40% chance to stop (False)
        return random.random() < 0.6  # True if skip, False if stop


    def check_semaphore(self):
        """
        Determines if the wreckless agent is at a traffic light and decides whether to stop.
        Returns the semaphore if the agent decides to respect it (50% chance for red/yellow), otherwise None.
        """
        semaphore_positions = {
            (8, 22): (9, 15),
            (9, 22): (9, 15),
            (10, 22): (9, 15),
            (22, 12): (15, 13),
            (22, 13): (15, 13),
            (22, 14): (15, 13),
            (12, 0): (13, 7),
            (13, 0): (13, 7),
            (14, 0): (13, 7),
            (0, 8): (7, 9),
            (0, 9): (7, 9),
            (0, 10): (7, 9),
        }

        controlling_position = semaphore_positions.get(self.starting_pos)
        if not controlling_position:
            return None

        # Get the semaphore at the controlling position
        for agent in self.model.grid.get_cell_list_contents([controlling_position]):
            if isinstance(agent, TrafficLightAgent):
                semaphore = agent

                # If the semaphore is red or yellow, decide whether to stop
                if semaphore.state in ("red", "yellow"):
                    if random.random() < 0.5:  # 50% chance to respect the semaphore
                        return semaphore  # Respect the semaphore
                    else:
                        return None  # Skip the semaphore

                # If the semaphore is green, allow the agent to proceed
                return None

        return None


    def move(self):
        """
        Defines the movement behavior of the wreckless agent, ensuring it moves nonstop
        when there's no vehicle in front or if it has already crossed a streetlight.
        Incorporates trajectory change functionality at defined points and handles interaction with PersonAgent.
        """
        # Check if the agent should change trajectory at the current position
        self.change_trajectory()

        # Define movement based on current direction
        preferred_move = None
        if self.current_direction == "up":
            preferred_move = (self.pos[0], self.pos[1] + 1)
        elif self.current_direction == "down":
            preferred_move = (self.pos[0], self.pos[1] - 1)
        elif self.current_direction == "right":
            preferred_move = (self.pos[0] + 1, self.pos[1])
        elif self.current_direction == "left":
            preferred_move = (self.pos[0] - 1, self.pos[1])

        # Check if preferred_move is within bounds
        if preferred_move and not self.model.grid.out_of_bounds(preferred_move):
            # Check cell contents at preferred position
            cell_contents = self.model.grid.get_cell_list_contents([preferred_move])
            front_vehicle = any(isinstance(agent, CarAgent) for agent in cell_contents)
            person_present = any(isinstance(agent, PersonAgent) for agent in cell_contents)

            # If there's no vehicle in front, proceed to check for streetlight
            if not front_vehicle:
                semaphore = self.check_semaphore()

                # If there's a streetlight and the agent decides to respect it
                if semaphore and semaphore.pos not in self.last_passed_lights:
                    # Stop if the agent respects the semaphore
                    self.jammedCounter += 1
                    self.happiness -= 5
                    return

                # Move to the preferred position
                self.model.grid.move_agent(self, preferred_move)
                self.happiness += 5
                self.jammedCounter = 0

                # Handle interaction with PersonAgent
                if person_present:
                    for agent in cell_contents:
                        if isinstance(agent, PersonAgent):
                            agent.stop_movement()  # Stop the person from moving
                return

            # If blocked by another vehicle, increment jammed counter
            self.jammedCounter += 1
            self.happiness -= 2
        else:
            # If preferred_move is invalid, increment jammed counter
            self.jammedCounter += 1
            self.happiness -= 2


    def change_trajectory(self):
        """
        Decide if the agent should change direction based on its current position.
        Returns the new direction if a turn is made, or None if no turn occurs.
        """
        # Define turning points and probabilities
        turn_points = {
            (9, 11): "right", (10, 11): "right", (11, 11): "right",  # Down to right
            (13, 14): "left", (14, 14): "left", (15, 14): "left",  # Up to left
            (13, 10): "up", (13, 9): "up", (15, 11): "up",  # Right to up
            (10, 13): "right", (10, 14): "right", (15, 14): "right",  # Left to right
        }

        if self.pos in turn_points:
            new_direction = turn_points[self.pos]
            if random.random() < 0.7:  # 70% chance to change direction
                self.current_direction = new_direction
                return new_direction

        # No change in direction
        return None
    def step(self):
        self.move()

class CarAgent(Agent):
    def __init__(self, unique_id, model, starting_pos, agent_type=None):
        super().__init__(unique_id, model)
        self.starting_pos = starting_pos
        self.last_passed_light = None 
        self.state = "happy"
        self.happiness = 1000
        self.passed_light_timer = None
        
        self.jammedCounter = 0
        
        # Asignar un tipo aleatorio si no se proporciona
        if agent_type is None:
            self.agent_type = random.choice(["cooperative", "competitive", "neutral"])  # Aleatorio
        else:
            self.agent_type = agent_type
        
        self.last_negotiation = None
        self.reward_matrix = {
            ("Rendir", "Rendir"): (3, 3),
            ("Rendir", "Avanza"): (2, 4),
            ("Avanza", "Rendir"): (5, 1),
            ("Avanza", "Avanza"): (1, 1)
        }

    def is_rightmost_lane(self):
        """
        Verifica si el coche está en el carril de extrema derecha antes de llegar a una intersección.
        """
        x, y = self.pos
        # Suponiendo que el grid tiene tamaño `size`, el carril de extrema derecha depende de la dirección.
        if self.starting_pos[1] == 0:  # Moviéndose hacia arriba
            return x == (self.model.grid.width - 1)
        elif self.starting_pos[1] == (self.model.grid.height - 1):  # Moviéndose hacia abajo
            return x == 0
        elif self.starting_pos[0] == 0:  # Moviéndose hacia la derecha
            return y == (self.model.grid.height - 1)
        elif self.starting_pos[0] == (self.model.grid.width - 1):  # Moviéndose hacia la izquierda
            return y == 0
        return False

    def negotiate(self, other_agent):
        # Determine the negotiation outcome based on agent types
        if self.agent_type == "competitive" and other_agent.agent_type == "competitive":
            my_action, other_action = "Avanza", "Avanza"
        elif self.agent_type == "cooperative":
            my_action, other_action = "Rendir", "Avanza"
        elif other_agent.agent_type == "cooperative":
            my_action, other_action = "Avanza", "Rendir"
        else:
            my_action, other_action = "Rendir", "Rendir"
            self.state = "angry"
        
        # Determine rewards (for potential future use)
        my_reward, other_reward = self.reward_matrix[(my_action, other_action)]

        # Set the last_negotiation attribute based on the outcome
        if my_action == "Rendir" and other_action == "Rendir":
            self.last_negotiation = "Rendir"
        elif my_action == "Avanza" and other_action == "Avanza":
            self.last_negotiation = "Stalemate"
        else:
            self.last_negotiation = "Avanza" if my_action == "Avanza" else "Rendir"
        
        return my_action, my_reward


    def communicate_with_neighbors(self):
        nearby_agents = self.model.grid.get_neighbors(self.pos, moore=True, include_center=False)
        messages = []
        for agent in nearby_agents:
            if isinstance(agent, CarAgent) and agent != self:
                messages.append({
                    "agent_id": agent.unique_id,
                    "position": agent.pos,
                    "intention": "avanzar" if agent.agent_type == "competitive" else "rendir"
                })
        return messages

    
    def check_semaphore(self):
        """
        Determina si el coche está en una intersección controlada por un semáforo.
        Actualiza last_passed_light y passed_light_timer si pasa el semáforo.
        """
        semaphore_positions = {
            (8, 22): (9, 15),
            (9, 22): (9, 15),
            (10, 22): (9, 15),
            (22, 12): (15, 13),
            (22, 13): (15, 13),
            (22, 14): (15, 13),
            (12, 0): (13, 7),
            (13, 0): (13, 7),
            (14, 0): (13, 7),
            (0, 8): (7, 9),
            (0, 9): (7, 9),
            (0, 10): (7, 9),
        }

        controlling_position = semaphore_positions.get(self.starting_pos)
        if not controlling_position or self.last_passed_light == controlling_position:
            return None  # Ignorar si ya pasó este semáforo

        for agent in self.model.grid.get_cell_list_contents([controlling_position]):
            if isinstance(agent, TrafficLightAgent):
                semaphore = agent
                if self.starting_pos[1] == 0 and self.pos[1] > semaphore.pos[1]:  # Moving up
                    self.last_passed_light = semaphore.pos
                    self.passed_light_timer = 0  # Reiniciar contador
                elif self.starting_pos[1] == self.model.grid.height - 1 and self.pos[1] < semaphore.pos[1]:  # Moving down
                    self.last_passed_light = semaphore.pos
                    self.passed_light_timer = 0
                elif self.starting_pos[0] == 0 and self.pos[0] > semaphore.pos[0]:  # Moving right
                    self.last_passed_light = semaphore.pos
                    self.passed_light_timer = 0
                elif self.starting_pos[0] == self.model.grid.width - 1 and self.pos[0] < semaphore.pos[0]:  # Moving left
                    self.last_passed_light = semaphore.pos
                    self.passed_light_timer = 0
                return semaphore

        return None



    def move(self):
        """
        Defines the movement behavior of the car, respecting traffic light rules and accounting for:
        - Ignoring lights already passed.
        - Negotiating with other cars.
        - Resetting `last_passed_light` after 2 steps.
        """
        # Check if `last_passed_light` should be removed
        if self.last_passed_light is not None and self.passed_light_timer is not None:
            if self.passed_light_timer >= 2:
                self.last_passed_light = None
                self.passed_light_timer = None
            else:
                self.passed_light_timer += 1

        # Determine preferred move
        preferred_move = None
        if self.is_rightmost_lane():
            # Decide right turn if in the rightmost lane
            if self.starting_pos[1] == 0:  # Moving up
                preferred_move = (self.pos[0] + 1, self.pos[1])  # Turn right
            elif self.starting_pos[1] == (self.model.grid.height - 1):  # Moving down
                preferred_move = (self.pos[0] - 1, self.pos[1])  # Turn left
            elif self.starting_pos[0] == 0:  # Moving right
                preferred_move = (self.pos[0], self.pos[1] - 1)  # Turn down
            elif self.starting_pos[0] == (self.model.grid.width - 1):  # Moving left
                preferred_move = (self.pos[0], self.pos[1] + 1)  # Turn up
        else:
            # Move straight if not in the rightmost lane
            if self.starting_pos[1] == 0:  # Bottom of the grid
                preferred_move = (self.pos[0], self.pos[1] + 1)  # Move up
            elif self.starting_pos[1] == self.model.grid.height - 1:  # Top of the grid
                preferred_move = (self.pos[0], self.pos[1] - 1)  # Move down
            elif self.starting_pos[0] == 0:  # Left of the grid
                preferred_move = (self.pos[0] + 1, self.pos[1])  # Move right
            elif self.starting_pos[0] == self.model.grid.width - 1:  # Right of the grid
                preferred_move = (self.pos[0] - 1, self.pos[1])  # Move left

        # Check traffic light rules
        semaphore = self.check_semaphore()
        if semaphore:
            # Update `last_passed_light` if the car has passed the semaphore
            if self.starting_pos[1] == 0 and self.pos[1] > semaphore.pos[1]:  # Moving up
                self.last_passed_light = semaphore.pos
                self.passed_light_timer = 0
            elif self.starting_pos[1] == self.model.grid.height - 1 and self.pos[1] < semaphore.pos[1]:  # Moving down
                self.last_passed_light = semaphore.pos
                self.passed_light_timer = 0
            elif self.starting_pos[0] == 0 and self.pos[0] > semaphore.pos[0]:  # Moving right
                self.last_passed_light = semaphore.pos
                self.passed_light_timer = 0
            elif self.starting_pos[0] == self.model.grid.width - 1 and self.pos[0] < semaphore.pos[0]:  # Moving left
                self.last_passed_light = semaphore.pos
                self.passed_light_timer = 0

            # Stop if the light is red and hasn't been passed
            if semaphore.state == "red":
                self.jammedCounter += 1
                self.happiness -= 5
                return

        # Attempt to move
        if preferred_move:
            x, y = self.model.grid.torus_adj(preferred_move)
            cell_contents = self.model.grid.get_cell_list_contents([(x, y)])
            other_car = next((agent for agent in cell_contents if isinstance(agent, CarAgent)), None)

            # Check if the cell is occupied by another car or building
            if not any(isinstance(obj, CarAgent) or isinstance(obj, BuildingAgent) for obj in cell_contents):
                # Move to the new position
                self.model.grid.move_agent(self, (x, y))
                self.happiness += 5
                self.jammedCounter = 0
                self.state = "happy"
                return

            # Negotiate with another car if present
            if other_car:
                my_action, my_reward = self.negotiate(other_car)
                print(f"Car {self.unique_id} negotiated with Car {other_car.unique_id}: {my_action}")

                if my_action == "Advance" and self.model.grid.is_cell_empty(preferred_move):
                    # Attempt to advance after negotiation
                    self.model.grid.move_agent(self, preferred_move)
                    self.happiness += my_reward
                    self.jammedCounter = 0
                else:
                    # Yield or blocked
                    self.happiness += 1 if my_action == "Yield" else -2
                    self.jammedCounter += 1
                return

        # Increase jammed counter if unable to move
        self.jammedCounter += 1
        self.happiness -= 2
        self.state = "angry" 
        if self.jammedCounter > 5:
            self.state = "angry"


    def step(self):
        self.move()