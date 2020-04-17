def get_solution(data, manager, routing, assignment):

    solution = {}
    solution["vehicleSchedules"] = []

    #get any dimensions
    time_dimension = routing.GetDimensionOrDie('Time')
    cost_dimension = routing.GetDimensionOrDie("Cost")

    solution['dropped_nodes'] = []
    for node in range(routing.Size()):
        if routing.IsStart(node) or routing.IsEnd(node):
            continue
        if assignment.Value(routing.NextVar(node)) == node:
            #dropped_nodes += ' {}'.format(manager.IndexToNode(node))
            solution['dropped_nodes'].append(node)
    print(solution['dropped_nodes'])

    #variables to print
    total_time = 0
    total_cost = 0

	#for each vehicle make a route
    for vehicle_ind in range(data['num_vehicles']):
        #array to store the steps of the path
        vehicle_route = []

        #get the idnex to the start node for the vehicle
        index = routing.Start(vehicle_ind)
        plan_output = 'Route for vehicle {}:\n'.format(vehicle_ind)

        #loop through the route steps
        while not routing.IsEnd(index):
            
            time_var = time_dimension.CumulVar(index)
            cost_var = cost_dimension.CumulVar(index)

            plan_output += '\033[32mNode {0}\033[0m Time({1},{2})  Cost({3})-> '.format(
                    manager.IndexToNode(index),
                    assignment.Min(time_var),
                    assignment.Max(time_var),
                    assignment.Min(cost_var)
                )
            step = {
                "id": str(manager.IndexToNode(index)),
                "solutionTimeWindow": {
                    "start": assignment.Min(time_var),
                    "end": assignment.Max(time_var)
                },
                "cost": assignment.Min(cost_var)
            }

            index = assignment.Value(routing.NextVar(index))
            vehicle_route.append(step)

        time_var = time_dimension.CumulVar(index)
        plan_output += 'Time of the route: {}\n'.format(assignment.Min(time_var))
        plan_output += 'Cost of the route: {}\n'.format(assignment.Min(cost_var))
        
        print(plan_output)

        vehicle_schedule = {
            "id": vehicle_ind,
            "costOfRoute": assignment.Min(cost_var),
            "timeOfRoute": assignment.Min(time_var),
            "routeSteps": vehicle_route,
        }  

        total_time += assignment.Min(time_var)
        total_cost += assignment.Min(cost_var)
        solution["vehicleSchedules"].append(vehicle_schedule)
	
	
    solution["id"] = "Rig Schedule"
    solution["totalTime"] = total_time
    solution["totalCost"] = total_cost

    return solution


def convert_solution(solution):

    converted_solution = {
        "id": solution["id"],
        "totalCost": solution['totalCost'],
        "totalTime": solution['totalTime'],
        "rigSchedules": solution['vehicleSchedules'],
        "wellsNotServices": solution['dropped_nodes']
    }

    return converted_solution