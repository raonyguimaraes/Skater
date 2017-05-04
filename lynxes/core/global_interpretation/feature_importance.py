"""Partial Dependence class"""
from itertools import cycle
import numpy as np
import pandas as pd

from ...data import DataManager
from .base import BaseGlobalInterpretation
from ...util.plotting import COLORS
from ...util.exceptions import *
from ...model.model import ModelType


def predict_wrapper(data, modelinstance, filter_classes):
    return DataManager(modelinstance.predict(data), feature_names=modelinstance.target_names)[filter_classes]

class FeatureImportance(BaseGlobalInterpretation):
    """Contains methods for feature importance. Subclass of BaseGlobalInterpretation"""

    @staticmethod
    def _build_fresh_metadata_dict():
        return {
            'pdp_cols': {},
            'sd_col': '',
            'val_cols': []
        }


    def feature_importance(self, modelinstance, filter_classes=None):

        """
        Computes feature importance of all features related to a model instance.


        Parameters:
        -----------

        modelinstance: lynxes.model.model.Model subtype
            the machine learning model "prediction" function to explain, such that
            predictions = predict_fn(data).

            :Example:
            >>> from lynxes.model import InMemoryModel
            >>> from lynxes.core.explanations import Interpretation
            >>> from sklearn.ensemble import RandomForestClassier
            >>> rf = RandomForestClassier()
            >>> rf.fit(X,y)


            >>> model = InMemoryModel(rf, examples = X)
            >>> interpreter = Interpretation()
            >>> interpreter.load_data(X)
            >>> interpreter.feature_importance.feature_importance(model)

            Supports classification, multi-class classification, and regression.
        filter_classes: array type
            The classes to run partial dependence on. Default None invokes all classes.
            Only used in classification models.

        """

        if filter_classes:
            assert all([i in modelinstance.target_names for i in filter_classes]), "members of filter classes must be" \
                                                                                  "members of modelinstance.classes." \
                                                                                  "Expected members of: " \
                                                                                  "{0}\n" \
                                                                                  "got: " \
                                                                                  "{1}".format(modelinstance.target_names,
                                                                                               filter_classes)
        def predict_wrapper(predictions, filter_classes):
            if filter_classes:
                return ModelType._filter_outputs(predictions, modelinstance.target_names, filter_classes)
            else:
                return predictions

        importances = {}
        original_predictions = predict_wrapper(modelinstance.predict(self.data_set.data), filter_classes)

        n = original_predictions.shape[0]

        # instead of copying the whole dataset, should we copy a column, change column values,
        # revert column back to copy?
        copy_of_data_set = DataManager(self.data_set.data,
                                       feature_names=self.data_set.feature_ids,
                                       index=self.data_set.index)

        for feature_id in self.data_set.feature_ids:
            # collect perturbations
            samples = self.data_set.generate_column_sample(feature_id, n_samples=n, method='random-choice')
            copy_of_data_set[feature_id] = samples

            # get size of perturbations
            # feature_perturbations = self.data_set[feature_id] - copy_of_data_set[feature_id]

            # predict based on perturbed values
            new_predictions = predict_wrapper(modelinstance.predict(copy_of_data_set.data), filter_classes)

            # evaluated entropy of scaled changes.
            changes_in_predictions = new_predictions - original_predictions
            importance = np.mean(np.std(changes_in_predictions, axis=0))
            importances[feature_id] = importance

            # reset copy
            copy_of_data_set[feature_id] = self.data_set[feature_id]

        importances = pd.Series(importances).sort_values()
        importances = importances / importances.sum()
        return importances


    def plot_feature_importance(self, predict_fn, filter_classes=None, ax=None):
        """Computes feature importance of all features related to a model instance,
        then plots the results.


        Parameters:
        -----------

        modelinstance: lynxes.model.model.Model subtype
            the machine learning model "prediction" function to explain, such that
            predictions = predict_fn(data).

            For instance:
            >>> from lynxes.model import InMemoryModel
            >>> from lynxes.core.explanations import Interpretation
            >>> from sklearn.ensemble import RandomForestClassier
            >>> rf = RandomForestClassier()
            >>> rf.fit(X,y)


            >>> model = InMemoryModel(rf, examples = X)
            >>> interpreter = Interpretation()
            >>> interpreter.load_data(X)
            >>> interpreter.feature_importance.feature_importance(model)

            Supports classification, multi-class classification, and regression.

        filter_classes: array type
            The classes to run partial dependence on. Default None invokes all classes.
            Only used in classification models.

        ax: matplotlib.axes._subplots.AxesSubplot
            existing subplot on which to plot feature importance. If none is provided,
            one will be created.
            """
        try:
            global pyplot
            from matplotlib import pyplot
        except ImportError:
            raise (MatplotlibUnavailableError("Matplotlib is required but unavailable on your system."))
        except RuntimeError:
            raise (MatplotlibDisplayError("Matplotlib unable to open display"))

        importances = self.feature_importance(predict_fn, filter_classes=filter_classes)

        if ax is None:
            f, ax = pyplot.subplots(1)
        else:
            f = ax.figure

        colors = cycle(COLORS)
        color = next(colors)
        importances.sort_values().plot(kind='barh', ax=ax, color=color)
        return f, ax
