#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Runs a simulated experiment on previous TAC-KBP years.
"""

import pdb
import os
import csv
import sys
import logging
from collections import Counter, defaultdict

import numpy as np

from tqdm import tqdm
from kbpo.data import load_queries, load_gold, load_output, Provenance, EvaluationEntry, OutputEntry
from kbpo.util import macro, micro
from kbpo.analysis import k, kn, get_key, project_gold, project_output, compute_entity_scores
from kbpo.counter_utils import normalize
from kbpo.sample_util import sample_with_replacement, sample_without_replacement
from kbpo.evaluation import weighted_score, simple_score, joint_score, compute_weights, construct_proposal_distribution, estimate_n_samples, update_weights, update_proposal_distribution

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def load_data(args):
    Q = load_queries(args.queries)
    gold = load_gold(args.gold, Q)
    outputs = {}

    for fname in tqdm(os.listdir(args.preds), desc="Loading outputs"):
        if not fname.endswith(".txt"): continue
        runid = fname.split(".")[0]
        #logger.info("Loading output for %s", runid)

        with open(os.path.join(args.preds, fname)) as f:
            output = load_output(f, Q)
            if len(output) > 0:
                outputs[runid] = output
    logger.info("Loaded output for %d systems", len(outputs))
    assert "LDC" in outputs
    return Q, gold, outputs

def transform_output(Q, gold, outputs, mode="closed-world"):
    """
    Transform output from the official evaluation files to appropriately
    score output.
    In particular, this function transforms the input to include all
    true entries for a particular relation as a way of handling recall
    problems.
    """
    G, Gr = project_gold(Q, gold, mode)
    # The list of all true items are in Gr.
    Y = [(key, 1.0) for (_, key), value in Gr.items() if value > 0]
    # Uniformly weigh entities.
    U = Counter({x:1./len(xs) for fills in G.values() for eq, xs in fills.items() for x in xs if eq > 0.})

    Rs, Xs, Ps  = [], [], []
    for run_id, output in outputs.items():
        Rs.append(run_id) # Helps keep track of performance.
        O = project_output(Q, Gr, output, mode)
        X = []
        # To handle the problem with missing mentions and its effect on
        # recall, if the system gets one instanec for a fill, it's
        # artificially made to get _all_ of them.
        # We account for its effect on precision by dividing by the
        # number of correct fills.
        P = Counter({})
        for entity, fills in O.items():
            for eq, xs in fills.items():
                if eq == 0: # the incorrect fills; do not augment.
                    X.extend([(x, 0.0) for x in xs])
                    P.update({x: 1. for x in xs})
                else: # Augment keys with things in P.
                    xs_ = G[entity][eq]
                    X.extend([(x, 1.0) for x in xs_])
                    P.update({x: 1./len(xs_) for x in xs_})
        Xs.append(X)
        P = normalize(P)
        Ps.append(normalize(P))

    # Just make sure the counts of objects match up
    gold_count = len(set(x for x, fx in Y if fx == 1.0))
    pool_count = len(set(x for X in Xs for x, fx in X if fx == 1.0))
    assert gold_count == pool_count

    # shuffle the output around so that LDC is the first run (makes
    # things convenient.
    i = Rs.index("LDC")
    Ps.insert(0, Ps.pop(i))
    Xs.insert(0, Xs.pop(i))
    Rs.insert(0, Rs.pop(i))

    return Rs, U, Y, Ps, Xs

def _test_input():
    Q = {'s1': 's1', 's2': 's2', 's3':'s3'}
    gold = [
        EvaluationEntry(1, 's1', 's1','r1', [Provenance('d1',1,2)], 'o0', [], 'C', 'C', 0, 0),
        EvaluationEntry(1, 's1', 's1','r1', [Provenance('d1',1,2)], 'o1', [], 'C', 'C', 1, 1),
        EvaluationEntry(1, 's1', 's1','r1', [Provenance('d2',1,2)], 'o1', [], 'C', 'C', 1, 1),
        EvaluationEntry(1, 's1', 's1','r1', [Provenance('d3',1,2)], 'o1', [], 'C', 'C', 1, 1),
        EvaluationEntry(1, 's1', 's1','r1', [Provenance('d1',1,2)], 'o2', [], 'C', 'C', 2, 2),
        EvaluationEntry(1, 's1', 's1','r1', [Provenance('d2',1,2)], 'o2', [], 'C', 'C', 2, 2),
        EvaluationEntry(1, 's2', 's2','r1', [Provenance('d1',1,2)], 'o0', [], 'C', 'C', 0, 0),
        EvaluationEntry(1, 's2', 's2','r1', [Provenance('d1',1,2)], 'o3', [], 'C', 'C', 3, 3),
        EvaluationEntry(1, 's2', 's2','r1', [Provenance('d2',1,2)], 'o3', [], 'C', 'C', 3, 3),
        ]
    output = [
        OutputEntry('s1', 's1','r1', 'test', [Provenance('d1',1,2)], 'o0', 'type', [], 1.0), # '0'),
        OutputEntry('s1', 's1','r1', 'test', [Provenance('d1',1,2)], 'o1', 'type', [], 1.0), # '1'),
        OutputEntry('s1', 's1','r1', 'test', [Provenance('d1',1,2)], 'o2', 'type', [], 1.0), # '2'),
        OutputEntry('s2', 's2','r1', 'test', [Provenance('d1',1,2)], 'o0', 'type', [], 1.0), # '0'),
        OutputEntry('s2', 's2','r1', 'test', [Provenance('d2',1,2)], 'o3', 'type', [], 1.0), # '3'),
        ]
    return Q, gold, [output]

def test_transform_output():
    Q, gold, outputs = _test_input()
    S, C, T = compute_entity_scores(Q, gold, outputs[0])
    p, r, f1 = micro(S, C, T)
    print("official", p, r, f1)

    U, Y, _, Ps, Xs, = transform_output(Q, gold, {'test': outputs[0]})
    ps, rs, f1s = weighted_score(U, Ps, Y, Xs)
    p_, r_, f1_ = ps[0], rs[0], f1s[0]
    print("weighted", p_, r_, f1_)

    assert np.allclose([p, r, f1], [p_,r_,f1_], 1e-2)

def test_transform_output_sample():
    np.random.seed(42)

    Q, gold, outputs = _test_input()
    U, Y, _, Ps, Xs, = transform_output(Q, gold, {'test':outputs[0]})
    ps, rs, f1s = weighted_score(U, Ps, Y, Xs)
    p, r, f1 = ps[0], rs[0], f1s[0]
    print("weighted", p, r, f1)

    # Draw samples.
    n_samples = 1000
    U_ = normalize(Counter({x: 1.0 for x in U})) # uniform distribution is what we really can sample from.
    Y0 = sample_with_replacement(normalize(U_), n_samples, Y)
    Xhs = [sample_with_replacement(P, n_samples, X) for P, X in zip(Ps, Xs)]

    ps, rs, f1s = simple_score(U, Ps, Y0, Xhs)
    p_, r_, f1_ = ps[0], rs[0], f1s[0]
    print("simple", p_, r_, f1_)
    assert np.allclose([p, r, f1], [p_,r_,f1_], 5e-2)

def teamid(runid):
    """
    SF_UMass_IESL1 -> UMass_IESL
    """
    return runid.split("_", 1)[-1][:-1]

def shuffle(Rs, Ps, Xs, by_team=False):
    """
    """
    if by_team:
        # First compress the list of systems by team id.
        Ts = sorted(set(teamid(r) for r in Rs[1:]))
        np.random.shuffle(Ts)
        Rs_, Ps_, Xs_ = zip(*[(r, p, x) for t in Ts for r, p, x in zip(Rs, Ps, Xs) if teamid(r) == t])
    else:
        ixs = np.arange(len(Rs))
        np.random.shuffle(ixs)
        Rs_, Ps_, Xs_ = zip(*[(Rs[i], Ps[i], Xs[i]) for i in ixs])
    return Rs_, Ps_, Xs_

def create_pool(Rs, Ps, Xs, replace_labels=False, pool_fraction=0.5):
    """
    Set Y to be the union of the output from all the pooled systems.
    Then rescore the outputs from _unpooled systems_.
    """
    # First compress the list of systems by team id.
    Ts = sorted(set(teamid(r) for r in Rs[1:]))
    pool_size = int(len(Ts) * pool_fraction)
    np.random.shuffle(Ts)
    Ts = Ts[:pool_size]
    pool = Rs[0:1] + [R for R in Rs if teamid(R) in Ts]

    assert "LDC" in pool
    Y_ = sorted(set((x,fx) for (R, X) in zip(Rs, Xs) for x, fx in X if R in pool and fx == 1.0))
    Rs_, Ps_, Xs_ = zip(*[(R, P, X) for R, P, X in zip(Rs, Ps, Xs) if R not in pool])
    if replace_labels:
        Yx = set(x for x, _ in Y_)
        Xs_ = [[(x, 1.0 if x in Yx else 0.0) for x, _ in X] for X in Xs_]

    return Rs_, Y_, Ps_, Xs_

def project_Y(Y0, Xs):
    Xs_ = [{x for x, _ in X} for X in Xs]
    ret = [[] for _ in Xs]
    for x, _ in Y0:
        for i, _ in enumerate(Xs):
            ret[i].append((x, x in Xs_[i]))
    return ret

def restrict_top(Rs, Ps, Xs, F1s, n=40):
    ixs = np.argsort(F1s)[:n]
    Rs_ = [Rs[i] for i in ixs]
    Ps_ = [Ps[i] for i in ixs]
    Xs_ = [Xs[i] for i in ixs]
    F1s_ = [F1s[i] for i in ixs]
    return Rs_, Ps_, Xs_, F1s_

def do_simulate(args):
    # Load the data.
    # Handle the LDC -- that shouldn't be part of the output.
    Q, gold, outputs = load_data(args)

    logger.info("Transforming data...")
    Rs, U, Y, Ps, Xs = transform_output(Q, gold, outputs)

    logger.info("Evaluating true scores...")
    # Measure the true precision and recall values on the entire data.
    precisions, recalls, f1s = weighted_score(U, Ps, Y, Xs)
    true_scores = {run_id: [p, r, f1] for run_id, p, r, f1 in zip(Rs, precisions, recalls, f1s)}

    logger.info("Evaluating estimated scores...")
    estimated_scores = {run_id: [] for run_id in Rs}
    # For n epochs:
    for _ in tqdm(range(args.num_epochs)):
        # Evaluate scores based on the chosen elements.
        # When creating the pool,
        Rs_, Y_, Ps_, Xs_ = create_pool(Rs, Ps, Xs, args.mode == "pooled") # Last argument changes truth values of elements.

        if args.mode == "pooled":
            n_samples = len(Y_)
            ps, rs, f1s = weighted_score(U, Ps_, Y_, Xs_)
        else:
            # Draw n_samples from respective distributions
            n_samples = 5000
            per_samples = int(n_samples / (len(Rs_) + 1)) # evenly distributed to estimate precision and recall.
            # duplicate because new interface for scoring allows each "system" to have a different label for a given x (because of entity linking)
            Y0 = sample_with_replacement(normalize({x: 1.0 for x in U}), per_samples, X=Y)
            Y0 = project_Y(Y0, Xs_)
            # This can increase variance because the sets X can be very
            # small.
            Xhs = [sample_with_replacement(P, per_samples, X) for P, X in zip(Ps_, Xs_)]
            if args.mode == "simple":
                ps, rs, f1s = simple_score(U, Ps_, Y0, Xhs)
            elif args.mode == "joint":
                #W = compute_weights(Ps_, Xhs, "heuristic") # To save computation time (else it's cubic in n!).
                W, _ = compute_weights(Ps_, Xhs, "heuristic") # To save computation time (else it's cubic in n!).
                Q = construct_proposal_distribution(W, Ps_)
                #pdb.set_trace()
                ps, rs, f1s = joint_score(U, Ps_, Y0, Xhs, W=W, Q=Q)

        for run_id, p, r, f1 in zip(Rs_, ps, rs, f1s):
            estimated_scores[run_id].append([n_samples, p, r, f1])

    logger.info("Printing output...")
    writer = csv.writer(args.output, delimiter="\t")
    writer.writerow(["run_id",
                     "p", "r", "f1", "n_samples",
                     "delta_p", "delta_r", "delta_f1",
                     "p_lrange", "r_lrange", "f1_lrange",
                     "p_rrange", "r_rrange", "f1_rrange",])
    for run_id in sorted(Rs):
        if run_id == "LDC": continue

        if len(estimated_scores[run_id]) == 0:
            logger.warning("Did not sample any experiments for %s; ignoring", run_id)
            continue
        p, r, f1 = true_scores[run_id]
        metrics = np.array(estimated_scores[run_id])
        n_samples, p_, r_, f1_ = np.mean(metrics, 0)
        _, p_l, r_l, f1_l = np.percentile(metrics, 5, 0)
        _, p_r, r_r, f1_r = np.percentile(metrics, 95, 0)
        writer.writerow([run_id,
                         p, r, f1, n_samples,
                         p - p_, r - r_, f1 - f1_,
                         p_ - p_l, r_ - r_l, f1_ - f1_l,
                         p_r - p_, r_r - r_, f1_r - f1_])

def do_simulate_n(args):
    """
    Run a simulation to predict the number of samples required for
    a certain number of systems.
    """

    # Load the data.
    # Handle the LDC -- that shouldn't be part of the output.
    Q, gold, outputs = load_data(args)

    logger.info("Transforming data...")
    Rs, U, Y, Ps, Xs = transform_output(Q, gold, outputs)

    logger.info("Evaluating true scores...")
    # Measure the true precision and recall values on the entire data.
    precisions, recalls, f1s = weighted_score(U, Ps, Y, Xs)
    true_scores = {run_id: [p, r, f1] for run_id, p, r, f1 in zip(Rs, precisions, recalls, f1s)}

    # Restricting to the top 40.
    F1s = -np.array([true_scores[run_id][-1] for run_id in Rs])
    Rs, Ps, Xs, _ = restrict_top(Rs, Ps, Xs, F1s)

    logger.info("Evaluating estimated scores...")
#    estimated_scores = defaultdict(list)
    trajectories = []

    n_samples = 500
    # For n epochs:
    for _ in tqdm(range(args.num_epochs), desc="Sample trajectory"):
        # Choose a random sequence of systems.
        Rs_, Ps_, Xs_ = shuffle(Rs, Ps, Xs) # Pooled changes truth values of elements.

        Y0 = sample_without_replacement(normalize({x: 1.0 for x in U}), 500, X=Y)
        Y0 = project_Y(Y0, Xs_)
        # Draw n_samples from respective distributions
        Rhs, Phs, Xhs = [], [], []
        N = 0
        trajectory = []

        W_, Z_, Q_ = [], [], []
        for i, (R, P, X) in tqdm(enumerate(zip(Rs_, Ps_, Xs_)), desc="Estimating samples"):
            Rhs.append(R)
            Phs.append(P)

            if args.mode == "simple":
                n_samples_ = n_samples
            elif args.mode == "joint":
                n_samples_ = estimate_n_samples(Phs, Xhs, Ws=W_, Zs=Z_, Qs=Q_, target=n_samples)

            Xh = sample_with_replacement(P, n_samples_, X)
            N += len(Xh)
            Xhs.append(Xh)

            if args.mode == "simple":
                pass
                #ps, rs, f1s = simple_score(U, Phs, Y0, Xhs)
            elif args.mode == "joint":
                W, Z = update_weights(Phs, Xhs, W_, Z_)
                Q = update_proposal_distribution(W, Z, Phs, Q_, Z_)
                #ps, rs, f1s = joint_score(U, Phs, Y0, Xhs, W=W, Q=Q)
                W_, Z_, Q_ = W, Z, Q

            #errs = []
            #for run_id, p_, r_, f1_ in zip(Rs_, ps, rs, f1s):
            #    p, r, f1 = true_scores[run_id]
            #    # Just add all of these into a list for metrics later.
            #    errs.append([p-p_, r-r_, f1-f1_])
            #errs = list(np.mean(errs, axis=0))
            #estimated_scores[i].append([N,] + errs)
            trajectory.append(N)
        trajectories.append(trajectory)
        args.output_trajectory.write(" ".join(map(str, trajectory)) + "\n")

#    logger.info("Printing output...")
#    writer = csv.writer(args.output, delimiter="\t")
#    writer.writerow(["t", "n",
#                     "delta_p", "delta_r", "delta_f1",
#                     "p_lrange", "r_lrange", "f1_lrange",
#                     "p_rrange", "r_rrange", "f1_rrange",])
#    for i in sorted(estimated_scores.keys()):
#        metrics = np.array(estimated_scores[i])
#        n_samples, dp, dr, df1 = np.mean(metrics, 0)
#        _, dp_l, dr_l, df1_l = np.percentile(metrics, 5, 0)
#        _, dp_r, dr_r, df1_r = np.percentile(metrics, 95, 0)
#        writer.writerow([i, n_samples,
#                         dp, dr, df1,
#                         dp_l, dr_l, df1_l,
#                         dp_r, dr_r, df1_r,])
#

if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)

    DD = "data/KBP2015_Cold_Start_Slot-Filling_Evaluation_Results_2016-03-31"
    parser = argparse.ArgumentParser(description='Run a simulated experiment to compare stability of previous year scores with different methodologies')
    parser.add_argument('-g', '--gold', type=argparse.FileType('r'), default=(DD + "/SF_aux_files/batch_00_05_poolc.assessed.fqec"), help="A list of gold entries")
    parser.add_argument('-q', '--queries', type=argparse.FileType('r'), default=(DD + "/SF_aux_files/batch_00_05_queryids.v3.0.txt"), help="A list of queries that were evaluated")
    parser.add_argument('-ps', '--preds', type=str, default=(DD+ "/corrected_runs/"), help="A directory with predicted entries")
    parser.add_argument('-m', '--mode', choices=["pooled", "simple", "joint"], default="pooled", help="How scores should be estimated")
    parser.add_argument('-o', '--output', type=argparse.FileType('w'), default=sys.stdout, help="Outputs a list of results for every system (true, predicted, stdev)")
    parser.add_argument('-n', '--num-epochs', type=int, default=1000, help="Number of epochs to average over")
    parser.set_defaults(func=None)

    subparsers = parser.add_subparsers()
    command_parser = subparsers.add_parser('bias', help='Simulate bias')
    command_parser.set_defaults(func=do_simulate)

    command_parser = subparsers.add_parser('n', help='Simulate n sample')
    command_parser.add_argument('-ot', '--output-trajectory', type=argparse.FileType('w'), default=sys.stdout, help="Outputs a list of trajectories")
    command_parser.set_defaults(func=do_simulate_n)

    ARGS = parser.parse_args()
    if ARGS.func is None:
        parser.print_help()
        sys.exit(1)
    else:
        ARGS.func(ARGS)
