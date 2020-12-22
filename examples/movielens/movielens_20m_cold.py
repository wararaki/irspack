import json
import logging
import os
from typing import List, Tuple, Type, Dict, Any

import pandas as pd
from scipy import sparse as sps

from irspack.evaluator import EvaluatorWithColdUser
from irspack.dataset.movielens import (
    MovieLens20MDataManager,
)
from irspack.optimizers import (
    BaseOptimizer,
    DenseSLIMOptimizer,
    RandomWalkWithRestartOptimizer,
    IALSOptimizer,
    MultVAEOptimizer,
    P3alphaOptimizer,
    DenseSLIMOptimizer,
    RP3betaOptimizer,
    SLIMOptimizer,
    TopPopOptimizer,
)
from irspack.split import split

os.environ["OMP_NUM_THREADS"] = "4"
os.environ["RS_THREAD_DEFAULT"] = "8"

if __name__ == "__main__":

    BASE_CUTOFF = 100

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.FileHandler(f"search.log"))
    logger.addHandler(logging.StreamHandler())

    data_manager = MovieLens20MDataManager()
    df_all = data_manager.read_interaction()
    df_all = df_all[df_all.rating >= 4]
    user_cnt = df_all.userId.value_counts()
    user_cnt = user_cnt[user_cnt >= 5]
    df_all = df_all[df_all.userId.isin(user_cnt.index)]

    data_all, _ = split(
        df_all,
        "userId",
        "movieId",
        n_test_user=10000,
        n_val_user=10000,
        heldout_ratio_val=0.2,
        heldout_ratio_test=0.2,
    )

    data_train = data_all["train"]
    data_val = data_all["val"]
    data_test = data_all["test"]

    X_train_val_all: sps.csr_matrix = sps.vstack(
        [data_train.X_all, data_val.X_all], format="csr"
    )
    valid_evaluator = EvaluatorWithColdUser(
        input_interaction=data_val.X_learn,
        ground_truth=data_val.X_predict,
        cutoff=BASE_CUTOFF,
        n_thread=8,
    )
    test_evaluator = EvaluatorWithColdUser(
        input_interaction=data_test.X_learn,
        ground_truth=data_test.X_predict,
        cutoff=BASE_CUTOFF,
        n_thread=8,
    )

    test_results = []
    validation_results = []

    test_configs: List[Tuple[Type[BaseOptimizer], int, Dict[str, Any]]] = [
        # (TopPopOptimizer, 1),
        # (IALSOptimizer, 40),
        (DenseSLIMOptimizer, 20, dict()),
        (P3alphaOptimizer, 30, dict(alpha=1)),
        # (RP3betaOptimizer, 40),
        (
            MultVAEOptimizer,
            1,
            dict(
                dim_z=200, enc_hidden_dims=600, kl_anneal_goal=0.2
            ),  # nothing to tune, use the parameters used in the paper.
        ),
        # (SLIMOptimizer, 40),
    ]
    for optimizer_class, n_trials, config in test_configs:
        recommender_name = optimizer_class.recommender_class.__name__
        optimizer: BaseOptimizer = optimizer_class(
            data_train.X_all,
            valid_evaluator,
            metric="ndcg",
            n_trials=n_trials,
            logger=logger,
            fixed_params=config,
        )
        (best_param, validation_result_df) = optimizer.do_search(timeout=14400)
        validation_result_df["recommender_name"] = recommender_name
        validation_results.append(validation_result_df)
        pd.concat(validation_results).to_csv(f"validation_scores.csv")
        test_recommender = optimizer.recommender_class(
            X_train_val_all, **best_param
        )
        test_recommender.learn()
        test_scores = test_evaluator.get_scores(test_recommender, [20, 50, 100])

        test_results.append(
            dict(name=recommender_name, best_param=best_param, **test_scores)
        )
        with open("test_results.json", "w") as ofs:
            json.dump(test_results, ofs, indent=2)