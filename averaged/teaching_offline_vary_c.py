import numpy as np
import copy
import sys
import os


import teacher
import plot_chain
import sys
sys.path.append('../')
import MDPSolver
import env_chain
import matplotlib.pyplot as plt


class teaaching:
    def __init__(self, M_0, settings_to_run, teachers_to_run, target_pi):
        self.M_0 = M_0
        self.settings_to_run = settings_to_run
        self.teachers_to_run = teachers_to_run
        self.target_pi = target_pi
        self.accumulator = {}

    #enddef

    def offline_attack(self):
        for setting in self.settings_to_run:
            gamma = self.teachers_to_run[0][2]["gamma"]
            R_c, success_prob = setting[0], setting[1]
            M_in = get_M(self.M_0[0], self.M_0[1], R_c, success_prob, gamma=gamma)
            env_in = env_chain.Environment(M_in)
            pool = teacher.generate_pool(M_in[0], M_in[1], M_in[2], M_in[3], M_in[4], self.target_pi)
            for tchr in self.teachers_to_run:
                target_pi = tchr[2]["target_pi"]
                p = tchr[1]
                epsilon = tchr[2]["epsilon"]
                delta = tchr[2]["delta"]
                costr = tchr[2]["costr"]
                costp = tchr[2]["costp"]
                d_0 = tchr[2]["d_0"]
                teacher_type = tchr[0]
                cost_y_axis = tchr[2]["cost_y_axis"]
                teacher_obj = teacher.teacher(env=env_in, target_pi=target_pi, p=p, epsilon=epsilon,
                                              delta=delta,costr=costr, costp=costp, d_0=d_0,
                                              teacher_type=teacher_type, pool=pool) #Pool here

                try:
                    M_out, _, feasible = teacher_obj.get_target_M(M_in)
                except Exception as e:
                    print("====================NOT FEASIBLE=======================")
                    print("==================== Exception --{}".format(e))

                    print("--teacher_type={}--R_c={}--P_success={}".format(teacher_type, R_c, success_prob))
                    input()
                if not feasible:
                    print("====================NOT FEASIBLE=======================")
                    print("--teacher_type={}--R_c={}--P_success={}".format(teacher_type, R_c, success_prob))
                    cost = self.max_cost_value_if_non_feasible(cost_y_axis)
                    self.append_cost_to_accumulator(cost, teacher_type, p, cost_y_axis, success_prob, R_c)
                    continue
                else:
                    print("====================FEASIBLE=======================")
                    print("--teacher_type={}--R_c={}--P_success={}".format(teacher_type, R_c, success_prob))

                env_out = env_chain.Environment(M_out)
                _, pi_T, _ = MDPSolver.averaged_valueIteration(env_out, env_out.reward)
                print(teacher_type)
                print("cost=", teacher_obj.cost(M_in, M_out, cost_y_axis))
                # print("cost=", cost)
                print("Policy for R_T=", pi_T)
                print("Opt_expected_reward on modified = ",
                      MDPSolver.compute_averaged_reward_given_policy(env_out, env_out.reward, pi_T))
                cost = teacher_obj.cost(M_in, M_out, cost_y_axis)
                # cost = cost
                self.append_cost_to_accumulator(cost, teacher_type, p, cost_y_axis, success_prob, R_c)
        return self.accumulator
    #enddef

    def max_cost_value_if_non_feasible(self, cost_y_axis):
        if cost_y_axis == np.inf:
            return 100
        else:
            print("cost_y_axis should be inf")
            exit(0)

    def append_cost_to_accumulator(self, cost, teacher_type, p, cost_y_axis, success_prob, R_c):
        key = "{}_p={}_cost_y_axis={}_success_prob={}".format(teacher_type, p, cost_y_axis, success_prob)
        key_2 = "{}_p={}_cost_y_axis={}_R_c={}".format(teacher_type, p, cost_y_axis, R_c)
        if key in self.accumulator:
            self.accumulator[key].append(cost)
        else:
            self.accumulator[key] = [cost]
        if key_2 in self.accumulator:
            self.accumulator[key_2].append(cost)
        else:
            self.accumulator[key_2] = [cost]
        #enddef


def write_into_file(accumulator, exp_iter, teacher_type="offline_teaching_c"):
    directory = 'results/{}'.format(teacher_type)
    filename = "convergence" + '_' + str(exp_iter) + '.txt'
    if not os.path.isdir(directory):
        os.makedirs(directory)
    filepath = directory + '/' + filename
    print("output file name  ", filepath)
    f = open(filepath, 'w')
    for key in accumulator:
        f.write(key + '\t')
        temp = list(map(str, accumulator[key]))
        for j in temp:
            f.write(j + '\t')
        f.write('\n')
    f.close()
#enddef

def get_M(n_states, n_actions, R_c=-2.5, success_prob=0.9, gamma=1):
    # # n_states = 4
    # # n_actions = 2
    # success_prob = 0.9

    unif_prob = (1 - success_prob) / (n_states - 1)
    R = np.array([[-2.5, -2.5],
                  [0.5, 0.5],
                  [0.5, 0.5],
                  [-0.5, -0.5]])
    R[0,:] = R_c
    P_0 = np.zeros((n_states, n_states, n_actions))
    P_0[:, :, 0] = np.array(
        [[success_prob, unif_prob, unif_prob, unif_prob],
         [success_prob, unif_prob, unif_prob, unif_prob],
         [unif_prob, success_prob, unif_prob, unif_prob],
         [unif_prob, unif_prob, success_prob, unif_prob]]
    )
    P_0[:, :, 1] = np.array(
        [[unif_prob, success_prob, unif_prob, unif_prob],
         [unif_prob, unif_prob, success_prob, unif_prob],
         [unif_prob, unif_prob, unif_prob, success_prob],
         [unif_prob, unif_prob, unif_prob, success_prob]]
    )

    M_0 = (n_states, n_actions, R, P_0, gamma)

    return M_0
#enddef


def accumulator_function(tmp_dict, dict_accumulator):
    for key in tmp_dict:
        if key in dict_accumulator:
            dict_accumulator[key] += np.array(tmp_dict[key])
        else:
            dict_accumulator[key] = np.array(tmp_dict[key])
    return dict_accumulator
#enddef

def calculate_average(dict_accumulator, number_of_iterations):
    for key in dict_accumulator:
        dict_accumulator[key] = dict_accumulator[key]/number_of_iterations
    return dict_accumulator
#enddef



########################################
if __name__ == "__main__":


    number_of_iterations  = 10
    dict_accumulator = {}

    for iter_num in range(1, number_of_iterations+1):
        # ====================
        gamma = 1

        M_0 = get_M(n_states=4, n_actions=2, R_c=-2.5, success_prob=0.9, gamma=gamma)
        target_pi = np.ones(M_0[0], dtype="int")
        d_0 = np.ones(M_0[0]) / M_0[0]
        costr = 3
        costp = 1


        #Settings_to_run = [ (c1, p1), (c2, p2), (c3, p3), …………………]

        params = {
            "n_states":4,
            "n_action":2,
            "target_pi": target_pi,
            "gamma": gamma,
            "epsilon": 0.1,
            "delta": 0.0001,
            "costr": costr,
            "costp": costp,
            "d_0": d_0,
            "cost_y_axis": np.inf
        }

        teachers_to_run = [("general_attack_on_reward", np.inf, params),
                             ("general_attack_on_dynamics", np.inf, params),
                            ("non_target_attack_joint", np.inf, params),
                            ("general_attack_joint", np.inf, params)
                           ]


        settings_to_run_init_1 = []
        p = 0.9
        for c in [-5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5]:
            settings_to_run_init_1.append((c, p))
        print(settings_to_run_init_1)



        settings_to_run_init_2 = []
        c = -2.5
        for p in [0.8, 0.825, 0.85, 0.875, 0.9, 0.925, 0.95, 0.975]:
            p = np.round(p, 2)
            settings_to_run_init_2.append((c, p))
        print(settings_to_run_init_2)

        #=========================================

        settings_to_run_init = settings_to_run_init_1

        #=========================================

        #general_attack_on_reward #non_target_attack_on_reward
        teaaching_obj = teaaching(M_0, settings_to_run_init, teachers_to_run, target_pi) #settings_to_run_init

        acc_dict = teaaching_obj.offline_attack()
        dict_accumulator = accumulator_function(acc_dict, dict_accumulator)

    dict_accumulator = calculate_average(dict_accumulator, number_of_iterations)
    plot_chain.plot_offline_teaching_vary_c(dict_file=dict_accumulator, each_number=1, show_plots=False)

    #write_into_file(acc_dict, exp_iter=iter_num, teacher_type="offline_teaching_vary_c_costr={}_costp={}".format(costr, costp))
    exit(0)

    ####################################################