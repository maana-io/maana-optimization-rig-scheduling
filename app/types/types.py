rig_scheduling_types = """


type Info {
  id: ID!
  name: String!
  description: String
}


type Optimizer {
  id: ID!
  timeLimit: Int!
  firstSolutionStrategy: String!
  localSearch: String!
  penalty: Int!
}

input OptimizerAsInput {
  id: ID!
  timeLimit: Int!
  firstSolutionStrategy: String!
  localSearch: String!
  penalty: Int!
}

type Query {
  
  getOptimalRigSchedule(rigs: [RigAsInput!]!, wells: [WellAsInput!]!, timeMatrix: TimeMatrixAsInput!, optimizer: OptimizerAsInput!): RigWellSchedule!
  CKGErrors: [String]
}

type Rig {
  id: ID!
  startPosition: Int!
  startTimeWindow: TimeWindow!
}

input RigAsInput {
  id: ID!
  startPosition: Int!
  startTimeWindow: TimeWindowAsInput!
}

type RigRoute {
  id: ID!
  costOfRoute: Int!
  timeOfRoute: Int!
  routeSteps: [RigRouteStep!]!
}

type RigRouteStep {
  id: ID!
  solutionTimeWindow: TimeWindow!
  cost: Int!
}

type RigWellSchedule {
  id: ID!
  totalCost: Int!
  totalTime: Int!
  rigSchedules: [RigRoute!]!
  wellsNotServiced: [Int!]!
}

type Row {
  id: ID!
  values: [Value]!
}

input RowAsInput {
  id: ID!
  values: [ValueAsInput!]!
}

scalar Time

type TimeMatrix {
  id: ID!
  rows: [Row]!
}

input TimeMatrixAsInput {
  id: ID!
  rows: [RowAsInput!]!
}

type TimeWindow {
  id: ID!
  start: Int!
  end: Int!
}

input TimeWindowAsInput {
  id: ID!
  start: Int!
  end: Int!
}

type Value {
  id: ID!
  value: Int!
}

input ValueAsInput {
  id: ID!
  value: Int!
}

type Well {
  id: ID!
  arrivalTimeWindow: TimeWindow!
  serviceTime: Int!
  candidateRigs: [Int]
}

input WellAsInput {
  id: ID!
  arrivalTimeWindow: TimeWindowAsInput!
  serviceTime: Int!
  candidateRigs: [Int!]
}


"""