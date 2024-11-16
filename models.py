from mesa import Model
from mesa.time import SimultaneousActivation
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector
import random
from agents import BuildingAgent, TrafficLightAgent, CarAgent, WrecklessAgent, PersonAgent
from map import optionMap, startList, endList, Semaphores


class IntersectionModel(Model):
    def __init__(self, size, num_lights, num_cars, num_pedestrians):
        self.schedule = SimultaneousActivation(self)
        self.grid = MultiGrid(size, size, torus=True)
        self.num_lights = num_lights
        self.num_cars = num_cars
        self.current_time = 0
        self.current_id = 0
        
        self.num_pedestrians = num_pedestrians
        self.running = True
        self.completedCars = 0
        self.num_cars = num_cars
        self.traffic_lights = []
        self.light_index = 0  # Start cycling from the first traffic light

        # Advance counters by agent type
        self.cooperative_advances = 0
        self.competitive_advances = 0
        self.neutral_advances = 0

        # DataCollector to record advances by agent type
        self.datacollector = DataCollector(
            {
                "HappyCars": lambda m: sum(1 for a in m.schedule.agents if isinstance(a, CarAgent) and a.state == "happy"),
                "AngryCars": lambda m: sum(1 for a in m.schedule.agents if isinstance(a, CarAgent) and a.state == "angry")
            }
        )

        middle_lane = size // 2
        self.create_buildings(size, middle_lane)
        self.create_traffic_lights()
        self.create_car_agents()
        self.create_pedestrians()

    def create_buildings(self, size, middle_lane):
        for x in range(size):
            for y in range(size):
                if not (middle_lane - 3 <= x <= middle_lane + 3 or middle_lane - 3 <= y <= middle_lane + 3):
                    building = BuildingAgent(f"B-{x}-{y}", self)
                    self.schedule.add(building)
                    self.grid.place_agent(building, (x, y))
                elif x == middle_lane or y == middle_lane:
                    if not (middle_lane - 3 <= x <= middle_lane + 3 and middle_lane - 3 <= y <= middle_lane + 3):
                        building = BuildingAgent(f"B-{x}-{y}", self)
                        self.schedule.add(building)
                        self.grid.place_agent(building, (x, y))

    def create_traffic_lights(self):
        for position, _ in Semaphores:
            unique_id = self.next_id()
            traffic_light = TrafficLightAgent(unique_id, self, position, "red")  # Default state is red
            self.schedule.add(traffic_light)
            self.grid.place_agent(traffic_light, position)
            self.traffic_lights.append(traffic_light)

        # Set the first traffic light to green
        if self.traffic_lights:
            self.light_index = 0
            first_light = self.traffic_lights[self.light_index]
            first_light.state = "green"
            first_light.timer = 6  # Green lasts 6 seconds
            print(f"Traffic light at {first_light.pos} initialized to green.")
    def create_pedestrians(self):
        """
        Create pedestrian agents and place them on the grid.
        Allows pedestrians to be placed on top of BuildingAgent but not other PersonAgents.
        """
        start_positions = [(7, 7), (11, 7), (15, 7), (7, 11), (15, 11), (15, 15), (11, 15), (7, 15)]
        
        for i in range(self.num_pedestrians):
            # Randomly select a start position
            pos = random.choice(start_positions)
            cell_contents = self.grid.get_cell_list_contents([pos])

            # Ensure no other PersonAgent is in the cell
            if not any(isinstance(agent, PersonAgent) for agent in cell_contents):
                pedestrian = PersonAgent(f"Person-{i}", self, pos)
                self.schedule.add(pedestrian)
                self.grid.place_agent(pedestrian, pos)
            else:
                print(f"Position {pos} is already occupied by another pedestrian.")






    def create_car_agents(self):
        for _ in range(self.num_cars):
            starting_pos = random.choice(startList)
            unique_id = self.next_id()
            
            # 10% chance for the car to be a wreckless agent
            if random.random() < 0.1:
                c = WrecklessAgent(unique_id, self, starting_pos)
            else:
                agent_type = random.choice(["cooperative", "competitive", "neutral"])
                c = CarAgent(unique_id, self, starting_pos, agent_type)
            
            self.schedule.add(c)
            self.grid.place_agent(c, starting_pos)


    def step(self):
        current_light = self.traffic_lights[self.light_index]

        # Manage the current light's timing
        if current_light.timer > 0:
            current_light.timer -= 1
        else:
            current_light.state = "red"
            self.light_index = (self.light_index + 1) % len(self.traffic_lights)
            next_light = self.traffic_lights[self.light_index]
            next_light.state = "green"
            next_light.timer = 6  # Green lasts 6 seconds

        self.datacollector.collect(self)
        self.schedule.step()



    def get_traffic_light_positions(self, position):
        # Return starting positions associated with each traffic light
        if position == (9, 15):
            return [(8, 22), (9, 22), (10, 22)]
        elif position == (15, 13):
            return [(22, 12), (22, 13), (22, 14)]
        elif position == (13, 7):
            return [(12, 0), (13, 0), (14, 0)]
        elif position == (7, 9):
            return [(0, 8), (0, 9), (0, 10)]
        return []