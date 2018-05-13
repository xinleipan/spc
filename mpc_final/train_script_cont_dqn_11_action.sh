#!/bin/bash
python3.5 train_torcs.py \
	--continuous \
	--use-seg \
    --normalize \
    --num-total-act 2 \
    --pred-step 15 \
	--use-collision \
	--use-offroad \
	--use-distance \
	--use-seg \
    --use-pos \
    --use-angle \
    --use-speed \
    --use-xyz \
    --use-dqn \
    --use-random-reset \
    --num-dqn-action 11 \
    --sample-with-offroad \
    --sample-with-distance \
    --sample-with-collision \
    --num-same-step 1 \
    --id 1