
"""Contains class Population."""

import copy as cp
import pandas as pd
import numpy as np
import joblib as jl

from opqua.model import *

class Gillespie(object):
    """Class contains methods for simulating model with Gillespie algorithm.

    Class defines a model's events and methods for changing system state
    according to the possible events and simulating a timecourse using the
    Gillespie algorithm.

    Methods:
    getRates -- returns array containing rates for each event for a given system
        state
    doAction -- carries out an event, modifying system state
    run -- simulates model for a specified length of time
    """

    # Event ID constants:

    MIGRATE_HOST = 0
    MIGRATE_VECTOR = 1
    POPULATION_CONTACT_HOST_HOST = 2
    POPULATION_CONTACT_HOST_VECTOR = 3
    POPULATION_CONTACT_VECTOR_HOST = 4
    CONTACT_HOST_HOST = 5
    CONTACT_HOST_VECTOR = 6
    CONTACT_VECTOR_HOST = 7
    RECOVER_HOST = 8
    RECOVER_VECTOR = 9
    MUTATE_HOST = 10
    MUTATE_VECTOR = 11
    RECOMBINE_HOST = 12
    RECOMBINE_VECTOR = 13
    KILL_HOST = 14
    KILL_VECTOR = 15

    def __init__(self, model):
        """Create a new Gillespie simulation object.

        Arguments:
        model -- the model this simulation belongs to (Model)
        """

        super(Gillespie, self).__init__() # initialize as parent class object

        # Event IDs
        self.evt_IDs = [
            self.MIGRATE_HOST, self.MIGRATE_VECTOR,
            self.POPULATION_CONTACT_HOST_HOST,
            self.POPULATION_CONTACT_HOST_VECTOR,
            self.POPULATION_CONTACT_VECTOR_HOST,
            self.CONTACT_HOST_HOST, self.CONTACT_HOST_VECTOR,
            self.CONTACT_VECTOR_HOST,
            self.RECOVER_HOST, self.RECOVER_VECTOR,
            self.MUTATE_HOST, self.MUTATE_VECTOR,
            self.RECOMBINE_HOST, self.RECOMBINE_VECTOR,
            self.KILL_HOST, self.KILL_VECTOR
            ]
            # event IDs in specific order to be used

        self.model = model

    def getRates(self,population_ids):
        """Wrapper for calculating event rates as per current system state.

        Arguments:
        population_ids -- list with ids for every population in the model
            (list of Strings)

        Returns:
        Matrix with rates as values for events (rows) and populations (columns).
        Populations in order given in argument.
        """

        rates = np.zeros( [ len(self.evt_IDs), len(population_ids) ] )
            # rate array size of event space

        # Contact rates assume scaling area: large populations are equally
        # dense as small ones, so contact is constant with both host and
        # vector populations. If you don't want this to happen, modify each
        # population's base contact rate accordingly.


        for i,id in enumerate(population_ids):
            # First calculate the population's one-sided population contact rate
            self.model.populations[id].total_population_contact_rate_host_host = \
                np.sum([
                    self.model.populations[id].neighbors_contact_hosts[other_id]
                    * ( 1 - self.model.populations[other_id].coefficients_hosts[
                        :, self.model.populations[other_id].POPULATION_CONTACT
                        ].mean() )
                    for j,other_id in enumerate(population_ids)
                    ])

            self.model.populations[id].total_population_contact_rate_host_vector = \
                np.sum([
                    self.model.populations[id].neighbors_contact_hosts[other_id]
                    * ( 1 - self.model.populations[other_id].coefficients_vectors[
                        :, self.model.populations[other_id].POPULATION_CONTACT
                        ].mean() )
                    for j,other_id in enumerate(population_ids)
                    ])

            self.model.populations[id].total_population_contact_rate_vector_host = \
                np.sum([
                    self.model.populations[id].neighbors_contact_vectors[other_id]
                    * ( 1 - self.model.populations[other_id].coefficients_hosts[
                        :, self.model.populations[other_id].POPULATION_CONTACT
                        ].mean() )
                    for j,other_id in enumerate(population_ids)
                    ])

            # Now the actual rates:
            rates[self.MIGRATE_HOST,i] = (
                self.model.populations[id].total_migration_rate_hosts
                * self.model.populations[id].coefficients_hosts[
                    :, self.model.populations[id].MIGRATION
                    ].sum()
                ) # rate per individual

            rates[self.MIGRATE_VECTOR,i] = (
                self.model.populations[id].total_migration_rate_vectors
                * self.model.populations[id].coefficients_vectors[
                    :, self.model.populations[id].MIGRATION
                    ].sum()
                ) # rate per individual

            rates[self.POPULATION_CONTACT_HOST_HOST,i] = (
                np.multiply(
                    1 - self.model.populations[id].coefficients_hosts[
                        :, self.model.populations[id].POPULATION_CONTACT
                        ],
                    self.model.populations[id].coefficients_hosts[
                        :, self.model.populations[id].INFECTED
                        ]
                    ).sum()
                * self.model.populations[id].total_population_contact_rate_host_host
                ) # rate per individual

            rates[self.POPULATION_CONTACT_HOST_VECTOR,i] = (
                np.multiply(
                    1 - self.model.populations[id].coefficients_hosts[
                        :, self.model.populations[id].POPULATION_CONTACT
                        ],
                    self.model.populations[id].coefficients_hosts[
                        :, self.model.populations[id].INFECTED
                        ]
                    ).sum()
                * self.model.populations[id].total_population_contact_rate_host_vector
                ) # rate per individual

            rates[self.POPULATION_CONTACT_VECTOR_HOST,i] = (
                np.multiply(
                    1 - self.model.populations[id].coefficients_vectors[
                        :, self.model.populations[id].POPULATION_CONTACT
                        ],
                    self.model.populations[id].coefficients_vectors[
                        :, self.model.populations[id].INFECTED
                        ]
                    ).sum()
                * self.model.populations[id].total_population_contact_rate_vector_host
                ) # rate per individual

            rates[self.CONTACT_HOST_HOST,i] = (
                self.model.populations[id].contact_rate_host_host
                * np.multiply(
                    1 - self.model.populations[id].coefficients_hosts[
                        :, self.model.populations[id].CONTACT
                        ],
                    self.model.populations[id].coefficients_hosts[
                        :, self.model.populations[id].INFECTED
                        ]
                    ).sum()
                * ( 1 - np.mean( self.model.populations[id].coefficients_hosts[
                    :, self.model.populations[id].CONTACT
                    ] ) )
                ) # rate per individual

            rates[self.CONTACT_HOST_VECTOR,i] = (
                self.model.populations[id].contact_rate_host_vector
                * np.multiply(
                    1 - self.model.populations[id].coefficients_hosts[
                        :, self.model.populations[id].CONTACT
                        ],
                    self.model.populations[id].coefficients_hosts[
                        :, self.model.populations[id].INFECTED
                        ]
                    ).sum()
                * ( 1-np.mean( self.model.populations[id].coefficients_vectors[
                    :, self.model.populations[id].CONTACT
                    ] ) )
                ) # rate per individual

            rates[self.CONTACT_VECTOR_HOST,i] = (
                self.model.populations[id].contact_rate_host_vector
                * np.multiply(
                    1 - self.model.populations[id].coefficients_vectors[
                        :, self.model.populations[id].CONTACT
                        ],
                    self.model.populations[id].coefficients_vectors[
                        :, self.model.populations[id].INFECTED
                        ]
                    ).sum()
                * ( 1 - np.mean( self.model.populations[id].coefficients_hosts[
                    :, self.model.populations[id].CONTACT
                    ]) )
                ) # rate per individual

            rates[self.RECOVER_HOST,i] = (
                self.model.populations[id].recovery_rate_host
                * self.model.populations[id].coefficients_hosts[
                    :, self.model.populations[id].RECOVERY
                    ].sum()
                )

            rates[self.RECOVER_VECTOR,i] = (
                self.model.populations[id].recovery_rate_vector
                * self.model.populations[id].coefficients_vectors[
                    :, self.model.populations[id].RECOVERY
                    ].sum()
                )

            rates[self.MUTATE_HOST,i] = (
                self.model.populations[id].mutate_in_host
                * self.model.populations[id].coefficients_hosts[
                    :, self.model.populations[id].MUTATION
                    ].sum()
                )

            rates[self.MUTATE_VECTOR,i] = (
                self.model.populations[id].mutate_in_vector
                * self.model.populations[id].coefficients_vectors[
                    :, self.model.populations[id].MUTATION
                    ].sum()
                )

            rates[self.RECOMBINE_HOST,i] = (
                self.model.populations[id].recombine_in_host
                * self.model.populations[id].coefficients_hosts[
                    :, self.model.populations[id].RECOMBINATION
                    ].sum()
                )

            rates[self.RECOMBINE_VECTOR,i] = (
                self.model.populations[id].recombine_in_vector
                * self.model.populations[id].coefficients_vectors[
                    :, self.model.populations[id].RECOMBINATION
                    ].sum()
                )

            rates[self.KILL_HOST,i] = (
                self.model.populations[id].death_rate_host
                * self.model.populations[id].coefficients_hosts[
                    :, self.model.populations[id].LETHALITY
                    ].sum()
                )

            rates[self.KILL_VECTOR,i] = (
                self.model.populations[id].death_rate_vector
                * self.model.populations[id].coefficients_vectors[
                    :, self.model.populations[id].LETHALITY
                    ].sum()
                )

        return rates

    def doAction(self,act,pop,rand):

        """Change system state according to act argument passed

        Arguments:
        act -- defines action to be taken, one of the event ID constants (int)
        pop -- population action will happen in (Population)
        rand -- random number used to define event (number 0-1)

        Returns:
        whether or not the model has changed state (Boolean)
        """

        changed = False

        if act == self.MIGRATE_HOST:
            rand = rand * pop.total_migration_rate_hosts
            r_cum = 0
            for neighbor in pop.neighbors_hosts:
                r_cum += pop.neighbors_hosts[neighbor]
                if r_cum > rand:
                    pop.migrate(neighbor,1,0, rand=(
                        ( rand - r_cum + pop.neighbors_hosts[neighbor] )
                        / pop.neighbors_hosts[neighbor] ) )
                    changed = True
                    break

        elif act == self.MIGRATE_VECTOR:
            rand = rand * pop.total_migration_rate_vectors
            r_cum = 0
            for neighbor in pop.neighbors_vectors:
                r_cum += pop.neighbors_vectors[neighbor]
                if r_cum > rand:
                    pop.migrate(neighbor,0,1, rand=(
                        ( rand - r_cum + pop.neighbors_vectors[neighbor] )
                        / pop.neighbors_vectors[neighbor] ) )
                    changed = True
                    break

        elif act == self.POPULATION_CONTACT_HOST_HOST:
            rand = rand * pop.total_population_contact_rate_host_host
            r_cum = 0
            for neighbor in pop.neighbors_contact_hosts:
                r_cum += ( pop.neighbors_contact_hosts[neighbor]
                    * self.model.populations[neighbor].coefficients_hosts[
                        :,self.model.populations[neighbor].POPULATION_CONTACT
                        ].mean() )
                if r_cum > rand:
                    changed = pop.populationContact(
                        target_pop, (
                            ( rand - r_cum + pop.neighbors_contact_hosts[neighbor] )
                            / pop.neighbors_contact_hosts[neighbor] ),
                        host_origin=True, host_target=True
                        )
                    break

        elif act == self.POPULATION_CONTACT_HOST_VECTOR:
            rand = rand * pop.total_population_contact_rate_host_vector
            r_cum = 0
            for neighbor in pop.neighbors_contact_hosts:
                r_cum += ( pop.neighbors_contact_hosts[neighbor]
                    * self.model.populations[neighbor].coefficients_vectors[
                        :,self.model.populations[neighbor].POPULATION_CONTACT
                        ].mean() )
                if r_cum > rand:
                    changed = pop.populationContact(
                        target_pop, (
                            ( rand - r_cum + pop.neighbors_contact_hosts[neighbor] )
                            / pop.neighbors_contact_hosts[neighbor] ),
                        host_origin=True, host_target=False
                        )
                    break

        elif act == self.POPULATION_CONTACT_VECTOR_HOST:
            rand = rand * pop.total_population_contact_rate_vector_host
            r_cum = 0
            for neighbor in pop.neighbors_contact_vectors:
                r_cum += ( pop.neighbors_contact_vectors[neighbor]
                    * self.model.populations[neighbor].coefficients_hosts[
                        :,self.model.populations[neighbor].POPULATION_CONTACT
                        ].mean() )
                if r_cum > rand:
                    changed = pop.populationContact(
                        target_pop, (
                            ( rand - r_cum + pop.neighbors_contact_vectors[neighbor] )
                            / pop.neighbors_contact_vectors[neighbor] ),
                        host_origin=False, host_target=True
                        )
                    break

        elif act == self.CONTACT_HOST_HOST:
            changed = pop.contactHostHost(rand)

        elif act == self.CONTACT_HOST_VECTOR:
            changed = pop.contactHostVector(rand)

        elif act == self.CONTACT_VECTOR_HOST:
            changed = pop.contactVectorHost(rand)

        elif act == self.RECOVER_HOST:
            pop.recoverHost(rand)
            changed = True

        elif act == self.RECOVER_VECTOR:
            pop.recoverVector(rand)
            changed = True

        elif act == self.MUTATE_HOST:
            pop.mutateHost(rand)
            changed = True

        elif act == self.MUTATE_VECTOR:
            pop.mutateVector(rand)
            changed = True

        elif act == self.RECOMBINE_HOST:
            pop.recombineHost(rand)
            changed = True

        elif act == self.RECOMBINE_VECTOR:
            pop.recombineVector(rand)
            changed = True

        elif act == self.KILL_HOST:
            pop.killHost(rand)
            changed = True

        elif act == self.KILL_VECTOR:
            pop.killVector(rand)
            changed = True

        return changed

    def run(self,t0,tf,time_sampling=0,host_sampling=0,vector_sampling=0,
            print_every_n_events=1000):

        """Simulate model for a specified time between two time points.

        Simulates a time series using the Gillespie algorithm.

        Arguments:
        t0 -- initial time point to start simulation at (number)
        tf -- initial time point to end simulation at (number)
        time_sampling -- how many events to skip before saving a snapshot of the
            system state (saves all by default), if <0, saves only final state
            (int, default 0)
        host_sampling -- how many hosts to skip before saving one in a snapshot
            of the system state (saves all by default) (int, default 0)
        vector_sampling -- how many vectors to skip before saving one in a
            snapshot of the system state (saves all by default) (int, default 0)
        print_every_n_events -- number of events a message is printed to console
            (int>0, default 1000)

        Returns:
        dictionary containing model state history, with keys=times and
            values=Model objects with model snapshot at that time point
        """

        # Simulation variables
        t_var = t0 # keeps track of time
        history = { 0: cp.deepcopy(self.model) }
        intervention_tracker = 0
            # keeps track of what the next intervention should be
        self.model.interventions = sorted(
            self.model.interventions, key=lambda i: i.time
            )

        print_counter = 0 # only used to track when to print
        sampling_counter = 0 # used to track when to save a snapshot

        while t_var < tf: # repeat until t reaches end of timecourse
            population_ids = list( self.model.populations.keys() )
            r = self.getRates(population_ids) # get event rates in this state
            r_tot = np.sum(r) # sum of all rates

            # Time handling
            if r_tot > 0:
                dt = np.random.exponential( 1/r_tot ) # time until next event
                t_var += dt # add time step to main timer

                if (intervention_tracker < len(self.model.interventions)
                    and t_var
                    >= self.model.interventions[intervention_tracker].time):
                    # if there are any interventions left and if it is time
                    # to make one,
                    while ( intervention_tracker < len(self.model.interventions)
                        and (t_var
                        >= self.model.interventions[intervention_tracker].time
                        or r_tot == 0) ):
                            # carry out all interventions at this time point,
                            # and additional timepoints if no events will happen
                        self.model.interventions[
                            intervention_tracker
                            ].doIntervention()
                        t_var = self.model.interventions[
                            intervention_tracker
                            ].time
                        intervention_tracker += 1 # advance the tracker

                        # save snapshot at this timepoint
                        sampling_counter = 0
                        history[t_var] = self.model.copyState()

                        # now recalculate rates
                        population_ids = list( self.model.populations.keys() )
                        r = self.getRates(population_ids)
                            # get event rates in this state
                        r_tot = np.sum(r) # sum of all rates

                    if r_tot > 0: # if no more events happening,
                        dt = np.random.exponential( 1/r_tot )
                            # time until next event
                        t_var += dt # add time step to main timer
                    else:
                        t_var = tf # go to end

                # Event handling
                if t_var < tf: # if still within max time
                    u = np.random.random() * r_tot
                        # random uniform number between 0 and total rate
                    r_cum = 0 # cumulative rate
                    for e in range(r.shape[0]): # for every possible event,
                        for p in range(r.shape[1]):
                            # for every possible population,
                            r_cum += r[e,p]
                                # add this event's rate to cumulative rate
                            if u < r_cum:
                                # if random number is under cumulative rate

                                # print every n events
                                print_counter += 1
                                if print_counter == print_every_n_events:
                                    print_counter = 0
                                    print(
                                        'Simulating time: '
                                        + str(t_var) + ', event ID: ' + str(e)
                                        )

                                changed = self.doAction(
                                    e, self.model.populations[
                                        population_ids[p]
                                        ], ( u - r_cum + r[e,p] ) / r[e,p]
                                    ) # do corresponding action,
                                      # feed in renormalized random number
                                if changed and time_sampling >= 0:
                                        # if state changed and saving history,
                                        # saves history at correct intervals
                                    sampling_counter += 1
                                    if sampling_counter > time_sampling:
                                        sampling_counter = 0
                                        history[t_var] = self.model.copyState()

                                break # exit event loop

                        else: # if the inner loop wasn't broken,
                            continue # continue outer loop

                        break # otherwise, break outer loop
            else: # if no events happening,
                if intervention_tracker < len(self.model.interventions):
                        # if still not done with interventions,
                    while (intervention_tracker < len(self.model.interventions)
                        and t_var
                        >= self.model.interventions[intervention_tracker].time):
                            # carry out all interventions at this time point
                        self.model.interventions[
                            intervention_tracker
                            ].doIntervention()
                        t_var = self.model.interventions[
                            intervention_tracker
                            ].time
                        intervention_tracker += 1 # advance the tracker
                else:
                    t_var = tf

        print( 'Simulating time: ' + str(t_var), 'END')
        history[tf] = cp.deepcopy(self.model)
        history[tf].history = None

        return history
