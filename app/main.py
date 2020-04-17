from ariadne import ObjectType, QueryType, MutationType, gql, make_executable_schema
from ariadne.asgi import GraphQL
from asgi_lifespan import Lifespan, LifespanMiddleware
from graphqlclient import GraphQLClient

# HTTP request library for access token call
import requests
# .env
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()


#import the schema
from app.types.types import rig_scheduling_types

from app.data.create_data import create_data_model
from app.solution.solution import get_solution, convert_solution

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

from functools import partial


def getAuthToken():
    authProvider = os.getenv('AUTH_PROVIDER')
    authDomain = os.getenv('AUTH_DOMAIN')
    authClientId = os.getenv('AUTH_CLIENT_ID')
    authSecret = os.getenv('AUTH_SECRET')
    authIdentifier = os.getenv('AUTH_IDENTIFIER')

    # Short-circuit for 'no-auth' scenario.
    if(authProvider == ''):
        print('Auth provider not set. Aborting token request...')
        return None

    url = ''
    if authProvider == 'keycloak':
        url = f'{authDomain}/auth/realms/{authIdentifier}/protocol/openid-connect/token'
    else:
        url = f'https://{authDomain}/oauth/token'

    payload = {
        'grant_type': 'client_credentials',
        'client_id': authClientId,
        'client_secret': authSecret,
        'audience': authIdentifier
    }

    headers = {'content-type': 'application/x-www-form-urlencoded'}

    r = requests.post(url, data=payload, headers=headers)
    response_data = r.json()
    print("Finished auth token request...")
    return response_data['access_token']


def getClient():

    graphqlClient = None

    # Build as closure to keep scope clean.

    def buildClient(client=graphqlClient):
        # Cached in regular use cases.
        if (client is None):
            print('Building graphql client...')
            token = getAuthToken()
            if (token is None):
                # Short-circuit for 'no-auth' scenario.
                print('Failed to get access token. Abandoning client setup...')
                return None
            url = os.getenv('MAANA_ENDPOINT_URL')
            client = GraphQLClient(url)
            client.inject_token('Bearer '+token)
        return client
    return buildClient()


# Define types using Schema Definition Language (https://graphql.org/learn/schema/)
# Wrapping string in gql function provides validation and better error traceback
type_defs = gql(rig_scheduling_types)

# Map resolver functions to Query fields using QueryType
query = QueryType()



# Resolvers are simple python functions
#getOptimalRigSchedule(rigs: [RigAsInput], wells: [WellAsInput], timeMatrix: AddTimeWindowInputAsInput): RigWellSchedule
@query.field("getOptimalRigSchedule")
def resolve_get_optimal_rig_schedule(*_, rigs, wells, timeMatrix, optimizer):
    data = create_data_model(rigs, wells, timeMatrix)

    print(data)

    # set up the routing 
    manager = pywrapcp.RoutingIndexManager(len(data['time_matrix']),
                                                data['num_vehicles'],
                                                #data["starts"],
                                                data['start_positions'],
                                                data["ends"])
    # Create Routing Model.
    routing = pywrapcp.RoutingModel(manager)

    ##### evaluators
    def create_time_evaluator(data):
        """Creates callback to get total times between locations."""

        _total_time = {}
        # precompute total time to have time callback in O(1)
        for from_node in range(data['num_locations']):
            _total_time[from_node] = {}
            for to_node in range(data['num_locations']):
                if from_node == to_node:
                    _total_time[from_node][to_node] = 0
                else:
                    _total_time[from_node][to_node] = data['time_matrix'][from_node][to_node] #+ data['service_times'][to_node]

        def time_evaluator(manager, from_node, to_node):
            return _total_time[manager.IndexToNode(from_node)][manager.IndexToNode(to_node)]

        return time_evaluator
    ### need to add proper cost

    def create_cost_evaluator(data):

        #time_dimension = routing.GetDimensionOrDie("Time")
        _costs = {}
        for from_node in range(data['num_locations']):

            
            
            _costs[from_node] = {}
            for to_node in range(data['num_locations']):
                if from_node == to_node:
                    _costs[from_node][to_node] = 0
                else:
                    #time_elapsed = time_dimension.CumulVar(to_node)
                    _costs[from_node][to_node] = data['time_matrix'][from_node][to_node]

                    #_costs[from_node][to_node] = (time_elapsed + data['time_matrix'][from_node][to_node] ) * data["production_loss"][to_node]
                    #_costs[from_node][to_node] = (data['time_matrix'][from_node][to_node]) * ( data['production_loss'][to_node])
                    #print(_costs)
            
        def cost_evaluator(manage, from_node, to_node):
            
            return _costs[manager.IndexToNode(from_node)][manager.IndexToNode(to_node)]

        return cost_evaluator
    ######

    ######## ADD DIMENSIONS
    time_evaluator_index = routing.RegisterTransitCallback(
        partial(create_time_evaluator(data), manager))

    time = 'Time'
    horizon = 120
    routing.AddDimension(
        time_evaluator_index,
        horizon,  # allow waiting time (doesnt affect the solution right now)
        horizon,  # maximum time per vehicle
        False,  #since there maybe a time window that is after 0 start 
        time)

    time_dimension = routing.GetDimensionOrDie(time)

    cost_evaluator_index = routing.RegisterTransitCallback(
        partial(create_cost_evaluator(data), manager))

    cost = "Cost"
    routing.AddDimension(
            cost_evaluator_index,
            0,
            100000,
            False,
            cost
        )
    cost_dimension = routing.GetDimensionOrDie(cost)

    ## SET COST EDGE
    routing.SetArcCostEvaluatorOfAllVehicles(cost_evaluator_index)
    ######## 

    ## ADD TIME WINDOW CONSTRAINT To THE LOCATIONS
    for location_idx, time_window in enumerate(data['time_windows']):
        # dont think this if is needed since we have a dummy start node
        #if location_idx == 0:
        #    continue
        index = manager.NodeToIndex(location_idx)    
        time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])

    # provides a vehicle available start time (end time is fixed)

    for vehicle_id in range(data['num_vehicles']):
        index = routing.Start(vehicle_id)
        time_dimension.CumulVar(index).SetRange(data['min_start_times'][vehicle_id] ,data['max_start_times'][vehicle_id])

    # Instantiate route start and end times to produce feasible times.
    for i in range(data['num_vehicles']):
        routing.AddVariableMinimizedByFinalizer(
            time_dimension.CumulVar(routing.Start(i)))
        routing.AddVariableMinimizedByFinalizer(
            time_dimension.CumulVar(routing.End(i)))

    ################################################
    # this should match wells to rigs that can actaully drill them
    for ind, node in enumerate(data['candidate_vehicles']):
        index = manager.NodeToIndex(ind)
        if node:
            routing.VehicleVar(index).SetValues(node)

    ################################################
    #### penalties ####
    # introduce a penalty for skipping a locati0on
    penalty = optimizer['penalty']
    for node in range(1, len(data['time_matrix'])):
        routing.AddDisjunction([manager.NodeToIndex(node)], penalty)

        ################################################   

    # Setting first solution heuristic (cheapest addition).
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()

    if(optimizer['firstSolutionStrategy'] == "parallel_cheapest_insertion"):
        search_parameters.first_solution_strategy = (routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION)
    elif(optimizer['firstSolutionStrategy'] == "path_cheapest_arc"):
        search_parameters.first_solution_strategy = (routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)

    if(optimizer['localSearch']== "tabu_search"):
        search_parameters.local_search_metaheuristic = (routing_enums_pb2.LocalSearchMetaheuristic.TABU_SEARCH)
    elif(optimizer['localSearch']=="greedy_decesent"):
        search_parameters.local_search_metaheuristic = (routing_enums_pb2.LocalSearchMetaheuristic.GREEDY_DESCENT)

    search_parameters.time_limit.FromSeconds(optimizer['timeLimit'])
    # Solve the problem.
    assignment = routing.SolveWithParameters(search_parameters)


    status_map = {
            0: "ROUTING_NOT_SOLVED",
            1: "ROUTING_SUCCESS",
            2: "ROUTING_FAIL",
            3: "ROUTING_FAIL_TIMEOUT",
            4: "ROUTING_INVALID",
    }

    status = routing.status()

    if assignment:
        #solution = print_solution(data, manager, routing, assignment)
        solution = get_solution(data, manager, routing, assignment)
        solution["status"] = status_map[status]
        print(solution)

        return convert_solution(solution)
        
        
    else:
        print("NO SOLUTION FOUND!!!")
        return None



# Create executable GraphQL schema
schema = make_executable_schema(type_defs, [query])

# --- ASGI app

# Create an ASGI app using the schema, running in debug mode
# Set context with authenticated graphql client.
#ontext_value={'client': getClient()}
app = GraphQL(
    schema, debug=True)

# 'Lifespan' is a standalone ASGI app.
# It implements the lifespan protocol,
# and allows registering lifespan event handlers.
lifespan = Lifespan()


@lifespan.on_event("startup")
async def startup():
    print("Starting up...")
    print("... done!")


@lifespan.on_event("shutdown")
async def shutdown():
    print("Shutting down...")
    print("... done!")

# 'LifespanMiddleware' returns an ASGI app.
# It forwards lifespan requests to 'lifespan',
# and anything else goes to 'app'.
app = LifespanMiddleware(app, lifespan=lifespan)
