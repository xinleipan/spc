import numpy as np
import pdb
import copy

def get_act_samps(num_time, num_actions=6, prev_act=0, num_samples=1000, same_step=False):
    acts = []
    num, cnt = 0, 0
    while num < num_samples:
        act = get_act_seq(num_time, num_actions, prev_act, same_step)
        act = list(act)
        if act not in acts:
            acts.append(act)
            cnt = 0
            num += 1
        else:
            cnt +=1
        if cnt >= 100000:
            break
    acts = np.stack(acts).reshape((-1))
    res = np.zeros((num_samples * num_time, num_actions))
    res[np.arange(num_samples * num_time), acts] = 1
    res = res.reshape((num_samples, num_time, num_actions))
    return res, 0

def get_act_with_prob(num_samples, num_time, num_actions=6, prev_act=0, prob=None):
    # get actions according to a specific distribution prob
    # prob is a matrix of size 6 x 6
    acts = []
    num, cnt = 0, 0
    while num < num_samples:
        actions = []
        curr_act = prev_act
        for i in range(num_time):
            curr_act = np.random.choice(num_actions, p=list(prob[curr_act,:]/np.sum(prob[curr_act,:])))
            actions.append(curr_act)
        if actions not in acts:
            acts.append(actions)
            cnt = 0
            num += 1
        else:
            cnt += 1
        if cnt >= 100000:
            break
    acts = np.stack(acts).reshape((-1))
    res = np.zeros((num_samples * num_time, num_actions))
    res[np.arange(num_samples * num_time), acts] = 1
    res = res.reshape((num_samples, num_time, num_actions)) 
    return res

def get_prob_with_act(act_seq, num_actions=6):
    # act_seq: of size num_sample x num_time
    num_sample, num_time = act_seq.shape
    act_seq = np.concatenate([act_seq, np.ones((num_sample,1))*-1], 1)
    act_seq = act_seq.reshape((-1))
    prob = np.ones((num_actions, num_actions))/(num_actions*1.0)
    for prev_act in range(num_actions):
        prev_act_idx = np.where(act_seq[:-1] == prev_act)[0]
        num_prev_act = len(prev_act_idx)
        if num_prev_act > 0:
            for next_act in range(num_actions):
                this_act_seq = act_seq[prev_act_idx+1] 
                next_act_idx = np.where(this_act_seq==next_act)[0]
                num_next_act = len(next_act_idx)
                prob[prev_act, next_act] = num_next_act*1.0/(num_prev_act*1.0)
    prob /= prob.sum(-1).reshape((num_actions, 1))
    return prob
 
def get_act_seq(num_time, num_actions=6, prev_act=0, same_step=False):
    actions = []
    curr_act = prev_act
    if num_actions == 6:
        for i in range(num_time):
            if curr_act in [1,4]:
                p = np.ones(num_actions)/(num_actions*1.0)
            elif curr_act in [0,2,3,5]:
                p = np.zeros(num_actions)
                if same_step == False:
                    p[1] = 0.5
                    p[4] = 0.5
                else:
                    p = np.ones(num_actions)*0.1
                    p[1] = 0.3
                    p[4] = 0.3
            curr_act = np.random.choice(num_actions, p=list(p/p.sum()))
            actions.append(curr_act)
    elif num_actions == 4:
        for i in range(num_time):
            if curr_act in [0,2]:
                p = np.ones(4)/4.0
            elif curr_act in [1,3]:
                p = np.zeros(4)
                if same_step == False:
                    p[0] = 0.5
                    p[2] = 0.5
                else:
                    p[0] = 0.45
                    p[2] = 0.45
                    p[curr_act] = 0.1
            curr_act = np.random.choice(num_actions, p=list(p/p.sum()))
            actions.append(curr_act)
    return np.array(actions)
            
def get_action_sample(num_time, num_step_per_time, num_actions=9):
    # num time: number of prediction time
    # num step per time: how many steps are of the same action
    num_step = int(num_time/num_step_per_time)
    args1 = []
    for i in range(num_step):
        args1.append(np.arange(0,num_actions,1))
    args1 = tuple(args1)
    outs1 = np.meshgrid(*args1)
    args2 = []
    for i in range(num_step):
        args2.append(outs1[i].ravel())
    args2 = tuple(args2)
    points = np.c_[args2]
    res = np.repeat(points, [num_step_per_time], axis=1)
    res = res[:,:num_time]
    res2 = np.zeros((res.shape[0], res.shape[1], num_actions))
    res2 = res2.reshape((-1, num_actions))
    res3 = res.reshape((-1))
    res2[range(res2.shape[0]), res3] = 1
    res2 = res2.reshape((res.shape[0], res.shape[1], num_actions))
    return res2  # [9**num_step, num_time]