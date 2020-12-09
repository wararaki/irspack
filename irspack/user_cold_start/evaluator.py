"""
Copyright 2020 BizReach, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

     https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import numpy as np
from typing import Dict, Any
from .._evaluator import EvaluatorCore, Metrics
from ..recommenders.base import InteractionMatrix
from . import base


class UserColdStartEvaluator(object):
    def __init__(
        self, X: InteractionMatrix, profiles: "base.ProfileMatrix", mb_size: int = 1024
    ):
        assert X.shape[0] == profiles.shape[0]

        self.core = EvaluatorCore(X.astype(np.float64))
        self.profiles = profiles
        self.n_users = X.shape[0]
        self.n_items = X.shape[1]
        self.dim_profile = profiles.shape[1]
        self.mb_size = mb_size

    def get_score(
        self, model: "base.UserColdStartRecommenderBase", cutoff=20
    ) -> Dict[str, Any]:
        metric_base = Metrics(self.n_items)
        for start in range(0, self.n_users, self.mb_size):
            end = min(start + 1024, self.n_users)
            score_mb = model.get_score(self.profiles[start:end])
            metric = self.core.get_metrics(score_mb, cutoff, start, 4, False)
            metric_base.merge(metric)
        return metric_base.as_dict()