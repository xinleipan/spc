import gym
import numpy as np
import random

class MPCBuffer(object):
    def __init__(self, size, frame_history_len, pred_step, num_actions):
        self.size = size
        self.frame_history_len = frame_history_len
        self.next_idx      = 0
        self.num_in_buffer = 0
        self.pred_step = pred_step # number of prediction steps
        self.num_actions = num_actions

        self.obs      = None
        self.action   = None
        self.done     = None
        self.coll     = None
        self.offroad  = None
        self.speed    = None
        self.angle    = None
        self.pos      = None
        self.ret      = 0

    def sample_n_unique(self, sampling_f, n):
        res = []
        dist = np.arange(self.num_in_buffer-2,)
        dist = np.abs(dist-self.ret)*-1.0
        dist = np.exp(dist)/np.exp(dist).sum()
        while len(res) < n:
            #candidate = sampling_f()
            candidate = np.random.choice(self.num_in_buffer-2, p=dist)
            done = self.sample_done(candidate)
            if candidate not in res and done:
                res.append(candidate)
        return res

    def sample_done(self, idx):
        if idx < 10 or idx >= self.num_in_buffer - self.pred_step-10:
            return False
        else:
            done_list = self.done[idx-self.frame_history_len+1:idx-self.frame_history_len+1+self.pred_step]
            if np.sum(done_list) >= 1.0:
                return False
            else:
                return True

    def can_sample(self, batch_size):
        return batch_size*self.pred_step + 1 <= self.num_in_buffer

    def _encode_sample(self, idxes):
        obs_batch = np.concatenate([np.concatenate([self._encode_observation(idx+ii)[np.newaxis,:] for ii in range(self.pred_step)], 0)[np.newaxis,:] for idx in idxes], 0)
        nx_obs_batch = np.concatenate([np.concatenate([self._encode_observation(idx+1+ii)[np.newaxis,:] for ii in range(self.pred_step)], 0)[np.newaxis,:] for idx in idxes], 0)
        act_batch = np.concatenate([np.concatenate([self.action[idx+ii, :][np.newaxis,:] for ii in range(self.pred_step)],0)[np.newaxis,:] for idx in idxes], 0)
        sp_batch = np.concatenate([np.concatenate([self.speed[idx+ii,:][np.newaxis,:] for ii in range(self.pred_step+1)],0)[np.newaxis,:] for idx in idxes], 0)
        off_batch = np.concatenate([np.concatenate([self.offroad[idx+ii,:][np.newaxis,:] for ii in range(self.pred_step)],0)[np.newaxis,:] for idx in idxes], 0)
        coll_batch = np.concatenate([np.concatenate([self.coll[idx+ii,:][np.newaxis,:] for ii in range(self.pred_step)], 0)[np.newaxis,:] for idx in idxes], 0)
        pos_batch = np.concatenate([np.concatenate([self.pos[idx+ii,:][np.newaxis,:] for ii in range(self.pred_step+1)],0)[np.newaxis,:] for idx in idxes], 0)
        angle_batch = np.concatenate([np.concatenate([self.angle[idx+ii,:][np.newaxis,:] for ii in range(self.pred_step+1)],0)[np.newaxis,:] for idx in idxes], 0)
        dist_batch = sp_batch*(np.cos(angle_batch)-np.abs(np.sin(angle_batch))-((np.abs(pos_batch-2))/9.0)**1.0) 

        return act_batch, coll_batch,sp_batch,off_batch,dist_batch,obs_batch, nx_obs_batch, pos_batch 

    def sample(self, batch_size):
        assert self.can_sample(batch_size)
        idxes = self.sample_n_unique(lambda: random.randint(0, self.num_in_buffer - 2), batch_size)
        return self._encode_sample(idxes)

    def encode_recent_observation(self):
        assert self.num_in_buffer > 0
        return self._encode_observation((self.next_idx - 1) % self.size)

    def _encode_observation(self, idx):
        end_idx   = idx + 1 # make noninclusive
        start_idx = end_idx - self.frame_history_len
        # this checks if we are using low-dimensional observations, such as RAM
        # state, in which case we just directly return the latest RAM.
        if len(self.obs.shape) == 2:
            return self.obs[end_idx-1]
        # if there weren't enough frames ever in the buffer for context
        if start_idx < 0 and self.num_in_buffer != self.size:
            start_idx = 0
        for idx in range(start_idx, end_idx - 1):
            if self.done[idx % self.size]:
                start_idx = idx + 1
        missing_context = self.frame_history_len - (end_idx - start_idx)
        # if zero padding is needed for missing context
        # or we are on the boundry of the buffer
        if start_idx < 0 or missing_context > 0:
            frames = [np.zeros_like(self.obs[0]) for _ in range(missing_context)]
            for idx in range(start_idx, end_idx):
                frames.append(self.obs[idx % self.size])
            return np.concatenate(frames, 0)
        else:
            # this optimization has potential to saves about 30% compute time \o/
            img_h, img_w = self.obs.shape[2], self.obs.shape[3]
            return self.obs[start_idx:end_idx].reshape(-1, img_h, img_w)

    def store_frame(self, frame):
        if len(frame.shape) > 1:
            # transpose image frame into (img_c, img_h, img_w)
            frame = frame.transpose(2, 0, 1)

        if self.obs is None:
            self.obs      = np.empty([self.size] + list(frame.shape), dtype=np.uint8)
            self.action   = np.zeros([self.size] + [self.num_actions],dtype=np.int32)
            self.done     = np.empty([self.size],                     dtype=np.int32)
            self.coll     = np.empty([self.size] + [2], dtype=np.int32)
            self.offroad  = np.empty([self.size] + [2], dtype=np.int32)
            self.speed    = np.empty([self.size, 1],    dtype=np.float32)
            self.angle    = np.empty([self.size, 1],    dtype=np.float32)
            self.pos      = np.empty([self.size, 1],    dtype=np.float32)
        self.obs[self.next_idx] = frame

        ret = self.next_idx
        self.next_idx = (self.next_idx + 1) % self.size
        self.num_in_buffer = min(self.size, self.num_in_buffer + 1)
        self.ret = ret
        return ret

    def store_effect(self, idx, action, done, coll, off, speed, angle, pos):
        self.action[idx, :] = action
        self.done[idx]   = int(done)
        self.coll[idx,int(coll)] = 1
        self.offroad[idx, int(off)] = 1
        self.speed[idx,0] = speed
        self.angle[idx,0] = angle
        self.pos[idx,0] = pos
