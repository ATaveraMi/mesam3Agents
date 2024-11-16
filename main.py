from agents import BuildingAgent, TrafficLightAgent, CarAgent, WrecklessAgent, PersonAgent
from models import IntersectionModel
from mesa.visualization.modules import CanvasGrid, ChartModule
from mesa.visualization.ModularVisualization import ModularServer
import random

def intersectionPortrayal(agent):
    if agent is None:
        return

    portrayal = {"Filled": "true"}

    if isinstance(agent, PersonAgent):
        portrayal["Shape"] = "circle"
        portrayal["r"] = 0.4
        portrayal["Color"] = "#00FF00"  # Green for pedestrians
        portrayal["Layer"] = 4  # Higher layer to ensure visibility
        return portrayal  # Return immediately to prioritize PersonAgent

    if isinstance(agent, BuildingAgent):
        portrayal["Shape"] = "rect"
        portrayal["w"] = 0.8
        portrayal["h"] = 0.8
        portrayal["Color"] = "#808080"  # Grey for buildings
        portrayal["Layer"] = 1

    elif isinstance(agent, TrafficLightAgent):
        portrayal["Shape"] = "rect"
        portrayal["w"] = 0.6
        portrayal["h"] = 0.6
        if agent.state == "green":
            portrayal["Color"] = "green"
        elif agent.state == "red":
            portrayal["Color"] = "red"
        else:
            portrayal["Color"] = "yellow"
        portrayal["Layer"] = 2

    elif isinstance(agent, CarAgent):
        portrayal["Shape"] = "circle"
        portrayal["r"] = 0.5
        portrayal["Color"] = "#0000FF" if agent.state == "happy" else "#FF0000"
        portrayal["Layer"] = 3

    elif isinstance(agent, WrecklessAgent):
        portrayal["Shape"] = "circle"
        portrayal["r"] = 0.5
        portrayal["Color"] = "#FFFF00"  # Yellow for wreckless agents
        portrayal["Layer"] = 3

    return portrayal


# Create the CanvasGrid
grid = CanvasGrid(intersectionPortrayal, 23, 23, 500, 500)

# Create the ChartModule for displaying advances by agent type
advance_chart = ChartModule(
    [
        {"Label": "Cooperative Advances", "Color": "Purple"},
        {"Label": "Competitive Advances", "Color": "Orange"},
        {"Label": "Neutral Advances", "Color": "Gray"}
    ],
    data_collector_name='datacollector'  # Must match the name in IntersectionModel
)

# Set up model parameters for the user interface
model_parameters = {
    "size": 23,
    "num_lights": 4,  # Number of traffic lights
    "num_cars": 20,   # Number of cars
    "num_pedestrians": random.randint(1, 2)  # Randomly decide 1 or 2 pedestrians
}

emotion_chart = ChartModule(
    [
        {"Label": "HappyCars", "Color": "Blue"},
        {"Label": "AngryCars", "Color": "Red"}
    ],
    data_collector_name='datacollector'
)

# Set up the ModularServer to run the simulation with the grid and advance chart
server = ModularServer(
    IntersectionModel,
    [grid, emotion_chart],  # Include both grid and advance chart in the server
    "Modelo de Intersección - Multiagentes",
    model_parameters
)

server.port = 8521  # Default port
server.launch()