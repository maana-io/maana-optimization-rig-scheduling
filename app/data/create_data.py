def create_data_model(rigs, wells, timeMatrix):
    
    #data object to hold the model
    data = {}

	# number of rigs
    def convert_rigs_to_vehicles(rigs):
        data["start_positions"] = []
        data['max_start_times'] = []
        data['min_start_times'] = []

        for rig in rigs:
            data['start_positions'].append(rig['startPosition'])
            data['max_start_times'].append(rig['startTimeWindow']['end'])
            data['min_start_times'].append(rig['startTimeWindow']['start'])

        data['num_vehicles'] = len(rigs)
        data["ends"] = [0 for _ in range(len(rigs))]


    def convert_wells_to_nodes(wells):
        data['time_windows'] = []
        data['service_times'] = []
        data['candidate_vehicles'] = []
        data['production_loss'] = []
        data['service_times'].append(0)
        data['production_loss'].append(0)
        for well in wells:
            data['time_windows'].append(tuple((well['arrivalTimeWindow']["start"], well['arrivalTimeWindow']['end'],)))
            data["service_times"].append( well["serviceTime"])
            data['candidate_vehicles'].append(well['candidateRigs'])
            #for rig in well['candidateRigs']:
            #    data['candidate_vehicles'].append(rigs.index(rig)) if rig in rigs else -1
            #data['production_loss'].append(node["production_loss"])



    def convert_time_matrix(timeMatrix):

        time_matrix = []
        values = []
        for r in timeMatrix["rows"]:
            for v in r["values"]:
                values.append(v["value"])
            time_matrix.append(values)
            values = []

        new_time_matrix = []
        new_time_matrix.append([0 for _ in range(len(time_matrix) + 1)])
        #adds a column of zeros
        for row in time_matrix:
            new_time_matrix.append([0] + row)


        data['time_matrix'] = new_time_matrix
        print(data['time_matrix'])
        data['num_locations'] = len(data['time_matrix'])

    convert_rigs_to_vehicles(rigs)
    convert_wells_to_nodes(wells)
    convert_time_matrix(timeMatrix)

    return data