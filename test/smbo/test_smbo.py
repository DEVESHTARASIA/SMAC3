'''
Created on Dec 15, 2015

@author: Aaron Klein
'''
import sys
import unittest

import numpy as np
from ConfigSpace import ConfigurationSpace, Configuration

from smac.runhistory.runhistory import RunHistory
from smac.runhistory.runhistory2epm import RunHistory2EPM4Cost, \
    RunHistory2EPM4LogCost, RunHistory2EPM4EIPS
from smac.smbo.smbo import SMBO, get_types
from smac.scenario.scenario import Scenario
from smac.smbo.acquisition import EI, EIPS
from smac.smbo.local_search import LocalSearch
from smac.utils import test_helpers
from smac.epm.rf_with_instances import RandomForestWithInstances
from smac.epm.uncorrelated_mo_rf_with_instances import \
    UncorrelatedMultiObjectiveRandomForestWithInstances

if sys.version_info[0] == 2:
    import mock
else:
    from unittest import mock


class ConfigurationMock(object):
    def __init__(self, value=None):
        self.value = value

    def get_array(self):
        return [self.value]


class TestSMBO(unittest.TestCase):

    def setUp(self):
        self.scenario = Scenario({'cs': test_helpers.get_branin_config_space()})
        
    def branin(self, x):
        y = (x[:, 1] - (5.1 / (4 * np.pi ** 2)) * x[:, 0] ** 2 + 5 * x[:, 0] / np.pi - 6) ** 2
        y += 10 * (1 - 1 / (8 * np.pi)) * np.cos(x[:, 0]) + 10

        return y[:, np.newaxis]        

    def test_init_only_scenario_runtime(self):
        smbo = SMBO(self.scenario)
        self.assertIsInstance(smbo.model, RandomForestWithInstances)
        np.testing.assert_allclose(smbo.types, smbo.model.types)
        self.assertIsInstance(smbo.rh2EPM, RunHistory2EPM4LogCost)
        self.assertIsInstance(smbo.acquisition_func, EI)

    def test_init_only_scenario_quality(self):
        self.scenario.run_obj = 'quality'
        smbo = SMBO(self.scenario)
        self.assertIsInstance(smbo.model, RandomForestWithInstances)
        np.testing.assert_allclose(smbo.types, smbo.model.types)
        self.assertIsInstance(smbo.rh2EPM, RunHistory2EPM4Cost)
        self.assertIsInstance(smbo.acquisition_func, EI)

    def test_init_EIPS_as_arguments(self):
        for objective in ['runtime', 'quality']:
            self.scenario.run_obj = objective
            types = get_types(self.scenario.cs, None)
            umrfwi = UncorrelatedMultiObjectiveRandomForestWithInstances(
                ['cost', 'runtime'], types)
            eips = EIPS(umrfwi)
            rh2EPM = RunHistory2EPM4EIPS(self.scenario, 2)
            smbo = SMBO(self.scenario, model=umrfwi, acquisition_function=eips,
                        runhistory2epm=rh2EPM)
            self.assertIs(umrfwi, smbo.model)
            self.assertIs(eips, smbo.acquisition_func)
            self.assertIs(rh2EPM, smbo.rh2EPM)

    def test_rng(self):
        smbo = SMBO(self.scenario, rng=None)
        self.assertIsInstance(smbo.rng, np.random.RandomState)
        smbo = SMBO(self.scenario, rng=1)
        rng = np.random.RandomState(1)
        self.assertIsInstance(smbo.rng, np.random.RandomState)
        smbo = SMBO(self.scenario, rng=rng)
        self.assertIs(smbo.rng, rng)
        # ML: I don't understand the following line and it throws an error
        self.assertRaisesRegexp(TypeError,
                                "Unknown type <(class|type) 'str'> for argument "
                                'rng. Only accepts None, int or '
                                'np.random.RandomState',
                                SMBO, self.scenario, rng='BLA')

    def test_select_configurations(self):
        seed = 42
        smbo = SMBO(self.scenario, seed)
        smbo.runhistory = RunHistory()

        X = self.scenario.cs.sample_configuration().get_array()[None, :]
        Y = self.branin(X)
        smbo.model.train(X, Y)
        smbo.acquisition_func.update(model=smbo.model, eta=0.0)

        x = smbo.select_configurations()[0].get_array()
        assert x.shape == (2,)

    def test_select_configurations_2(self):
        def side_effect(X, derivative):
            return np.mean(X, axis=1).reshape((-1, 1))

        smbo = SMBO(self.scenario, 1)
        smbo.runhistory = RunHistory()
        smbo.model = mock.MagicMock()
        smbo.acquisition_func._compute = mock.MagicMock()
        smbo.acquisition_func._compute.side_effect = side_effect
        # local search would call the underlying local search maximizer,
        # which would have to be mocked out. Replacing the method by random
        # search is way easier!
        smbo._get_next_by_local_search = smbo._get_next_by_random_search

        X = smbo.rng.rand(10, 2)
        Y = smbo.rng.rand(10, 1)
        smbo.model.train(X, Y)
        smbo.acquisition_func.update(model=smbo.model, eta=0.0)

        x = smbo.select_configurations()

        self.assertEqual(smbo.model.train.call_count, 1)
        self.assertEqual(smbo.acquisition_func._compute.call_count, 1)
        self.assertEqual(len(x), 2020)
        num_random_search = 0
        for i in range(0, 2020, 2):
            self.assertIsInstance(x[i], Configuration)
            if x[i].origin == 'Random Search':
                num_random_search += 1
        # Since we replace local search with random search, we have to count
        # the occurences of random seacrh instead
        self.assertEqual(num_random_search, 10)
        for i in range(1, 2020, 2):
            self.assertIsInstance(x[i], Configuration)
            self.assertEqual(x[i].origin, 'Random Search')

    @mock.patch('ConfigSpace.util.impute_inactive_values')
    @mock.patch.object(EI, '__call__')
    @mock.patch.object(ConfigurationSpace, 'sample_configuration')
    def test_get_next_by_random_search_sorted(self,
                                              patch_sample,
                                              patch_ei,
                                              patch_impute):
        values = (10, 1, 9, 2, 8, 3, 7, 4, 6, 5)
        patch_sample.return_value = [ConfigurationMock(i) for i in values]
        patch_ei.return_value = np.array(values, dtype=float)
        patch_impute.side_effect = lambda x: x
        smbo = SMBO(self.scenario, 1)
        rval = smbo._get_next_by_random_search(10, True)
        self.assertEqual(len(rval), 10)
        for i in range(10):
            self.assertIsInstance(rval[i][1], ConfigurationMock)
            self.assertEqual(rval[i][1].value, 10 - i)
            self.assertEqual(rval[i][0], 10 - i)
            self.assertEqual(rval[i][1].origin, 'Random Search (sorted)')

        # Check that config.get_array works as desired and imputation is used
        #  in between
        np.testing.assert_allclose(patch_ei.call_args[0][0],
                                   np.array(values, dtype=float)
                                   .reshape((-1, 1)))

    @mock.patch.object(ConfigurationSpace, 'sample_configuration')
    def test_get_next_by_random_search(self, patch):
        def side_effect(size):
            return [ConfigurationMock()] * size
        patch.side_effect = side_effect
        smbo = SMBO(self.scenario, 1)
        rval = smbo._get_next_by_random_search(10, False)
        self.assertEqual(len(rval), 10)
        for i in range(10):
            self.assertIsInstance(rval[i][1], ConfigurationMock)
            self.assertEqual(rval[i][1].origin, 'Random Search')
            self.assertEqual(rval[i][0], 0)

    @mock.patch.object(LocalSearch, 'maximize')
    def test_get_next_by_local_search(self, patch):
        # Without known incumbent
        class SideEffect(object):
            def __init__(self):
                self.call_number = 0

            def __call__(self, *args, **kwargs):
                rval = 9 - self.call_number
                self.call_number += 1
                return (ConfigurationMock(rval), [[rval]])

        patch.side_effect = SideEffect()
        smbo = SMBO(self.scenario, 1)
        rval = smbo._get_next_by_local_search(num_points=9)
        self.assertEqual(len(rval), 9)
        self.assertEqual(patch.call_count, 9)
        for i in range(9):
            self.assertIsInstance(rval[i][1], ConfigurationMock)
            self.assertEqual(rval[i][1].value, 9 - i)
            self.assertEqual(rval[i][0], 9 - i)
            self.assertEqual(rval[i][1].origin, 'Local Search')

        # With known incumbent
        patch.side_effect = SideEffect()
        smbo.incumbent = 'Incumbent'
        rval = smbo._get_next_by_local_search(num_points=10)
        self.assertEqual(len(rval), 10)
        self.assertEqual(patch.call_count, 19)
        # Only the first local search in each iteration starts from the
        # incumbent
        self.assertEqual(patch.call_args_list[9][0][0], 'Incumbent')
        for i in range(10):
            self.assertEqual(rval[i][1].origin, 'Local Search')


if __name__ == "__main__":
    unittest.main()
