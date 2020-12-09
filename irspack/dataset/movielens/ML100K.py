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
import os
import re
from typing import List, Tuple
from .base import BaseMovieLenstDataLoader

import pandas as pd


class MovieLens100KDataManager(BaseMovieLenstDataLoader):
    DOWNLOAD_URL = "http://files.grouplens.org/datasets/movielens/ml-100k.zip"
    DEFAULT_PATH = os.path.expanduser("~/.ml-100k.zip")
    INTERACTION_PATH = "ml-100k/u.data"

    USER_INFO_PATH = "ml-100k/u.user"
    ITEM_INFO_PATH = "ml-100k/u.item"
    GENRE_PATH = "ml-100k/u.genre"

    def read_user_info(self) -> pd.DataFrame:
        with self._read_as_istream(self.USER_INFO_PATH) as ifs:
            return pd.read_csv(
                ifs,
                sep="|",
                header=None,
                names=["userId", "age", "gender", "occupation", "zipcode"],
            )

    def read_interaction(self) -> pd.DataFrame:
        with self._read_as_istream(self.INTERACTION_PATH) as ifs:
            data = pd.read_csv(
                ifs,
                sep="\t",
                header=None,
                names=["userId", "movieId", "rating", "timestamp"],
            )
            data["timestamp"] = pd.to_datetime(data["timestamp"], unit="s")
            return data

    def _read_genre(self) -> List[str]:
        with self._read_as_istream(self.GENRE_PATH) as ifs:
            items = ifs.read().decode("latin-1").split()
            return [re.sub("\|\d+$", "", i.strip()) for i in items]

    def read_item_info(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        with self._read_as_istream(self.ITEM_INFO_PATH) as ifs:
            df = pd.read_csv(ifs, sep="|", header=None, encoding="latin-1")

        genres = self._read_genre()
        df.columns = [
            "movie_id",
            "title",
            "release_date",
            "video_release_date",
            "URL",
        ] + genres
        movie_ids = df.movie_id.values
        df["release_date"] = pd.to_datetime(df.release_date)
        genre_df = pd.DataFrame(
            [
                dict(movie_id=movie_ids[row], genre=genres[col])
                for row, col in zip(*df[genres].values.nonzero())
            ]
        )
        return df.drop(columns=genres), genre_df
