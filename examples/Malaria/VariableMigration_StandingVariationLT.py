"""Three different populations with a variable rate of migration between them
-Each population has a different genetic variation
-Population1: 5 possible alleles, Population2: 3 possible alleles, Population3: 1 possible allele
-Low transmission (contact_rate_host_vector) for all popoulations = 1
-Mutation in vector is given a value of 1 for all populations
-Migration among populations increases with time
-The files for this simulation are saved with LT at the end, which stands for low transmission rate. This is done to set
apart this simulation from another with same parameters but high transmission rate"""

import numpy as np
from opqua.model import Model # This is all you need to import to run models.

my_model = Model() # Make a new model object.

my_model.newSetup('highGV_LT',preset='vector-borne', num_loci=5,possible_alleles="DRSTW",contact_rate_host_vector=1, mutate_in_host=1e-4)
my_model.newSetup('mediumGV_LT',preset='vector-borne', num_loci=5,possible_alleles="BCY",contact_rate_host_vector=1,mutate_in_host=1e-4)
my_model.newSetup('lowGV_LT',preset='vector-borne', num_loci=5,possible_alleles="A",contact_rate_host_vector=1, mutate_in_host=1e-4)
    # Create a new set of parameters called "my_setup" to be used to simulate
    # a population in the model. Use the default parameter set for a
    # vector-borne model.

my_model.newPopulation('population_highGV', 'highGV_LT', num_hosts=30, num_vectors=30)
my_model.newPopulation('population_mediumGV', 'mediumGV_LT', num_hosts=30, num_vectors=30)
my_model.newPopulation('population_lowGV', 'lowGV_LT', num_hosts=30, num_vectors=30)

my_model.addPathogensToHosts( 'population_highGV',{'DRSSW':10})
my_model.addPathogensToHosts( 'population_mediumGV',{'BBCYY':10})
my_model.addPathogensToHosts( 'population_lowGV',{'AAAAA':10})

for i in range(0,200,1):
    migration=0.01*np.sqrt(i)
    my_model.linkPopulations('population_highGV','population_mediumGV',migration)
    my_model.linkPopulations('population_mediumGV','population_highGV',migration)
    my_model.linkPopulations('population_highGV','population_lowGV',migration)
    my_model.linkPopulations('population_lowGV','population_highGV',migration)
    my_model.linkPopulations('population_lowGV','population_mediumGV',migration)
    my_model.linkPopulations('population_mediumGV','population_lowGV',migration)
my_model.run(0,200) # Run the simulation for 200 time units.
data = my_model.saveToDataFrame('VarMigr_StandVarLT.csv')
    # Save the model results to a table.
graph = my_model.compartmentPlot('VarMigrStandVar_HostsLT.png', data)
    # Plot the number of susceptible and infected hosts in the model over time.
graph2 = my_model.compositionPlot('VarMigr_StanVar_GenotypesLT.png',data)
    #Plot the track genotypes across time
graph3= my_model.populationsPlot('VarMigr_StanVar_PopulationLT',data)
    #Track the number of infected per population over time
