import unittest
import sys

import numpy as np

from smac.epm.rf_with_instances import RandomForestWithInstances

if sys.version_info[0] == 2:
    import mock
else:
    from unittest import mock


class TestRFWithInstances(unittest.TestCase):
    def test_predict_wrong_X_dimensions(self):
        rs = np.random.RandomState(1)

        model = RandomForestWithInstances(np.zeros((10,), dtype=np.uint), 10)
        X = rs.rand(10)
        self.assertRaisesRegex(ValueError, "Expected 2d array, got 1d array!",
                               model.predict, X)
        X = rs.rand(10, 10, 10)
        self.assertRaisesRegex(ValueError, "Expected 2d array, got 3d array!",
                               model.predict, X)

        X = rs.rand(10, 5)
        self.assertRaisesRegex(ValueError, "Rows in X should have 11 entries "
                                           "but have 5!",
                               model.predict, X)

    def test_predict(self):
        rs = np.random.RandomState(1)
        X = rs.rand(10, 10)
        Y = rs.rand(10, 1)
        f_map = np.array([[i,0] for i in range(10)], dtype=np.uint)
        model = RandomForestWithInstances(np.zeros((10,), dtype=np.uint), 10)
        model.train(X, f_map, Y[:10])
        X = rs.rand(10, 11)
        m_hat, v_hat = model.predict(X)
        self.assertEqual(m_hat.shape, (10, 1))
        self.assertEqual(v_hat.shape, (10, 1))

    @mock.patch.object(RandomForestWithInstances, '_predict')
    def test_predict_mocked(self, rf_mock):
        """Use mock to count the number of calls to _predict"""
        class SideEffect(object):
            def __init__(self):
                self.counter = 0

            def __call__(self, X):
                self.counter += 1
                # Return mean and variance
                return self.counter, self.counter

        rf_mock.side_effect = SideEffect()

        rs = np.random.RandomState(1)
        X = rs.rand(10, 10)
        Y = rs.rand(10, 1)
        f_map = np.array([[i,0] for i in range(10)], dtype=np.uint)
        model = RandomForestWithInstances(np.zeros((10,), dtype=np.uint), 10)
        model.train(X, f_map, Y[:10])
        X = rs.rand(10, 11)
        m_hat, v_hat = model.predict(X)
        self.assertEqual(m_hat.shape, (10, 1))
        self.assertEqual(v_hat.shape, (10, 1))
        self.assertEqual(rf_mock.call_count, 10)
        for i in range(10):
            self.assertEqual(m_hat[i], i+1)
            self.assertEqual(v_hat[i], i + 1)

    def test__predict(self):
        rs = np.random.RandomState(1)
        X = rs.rand(10, 10)
        Y = rs.rand(10, 1)
        f_map = np.array([[i,0] for i in range(10)], dtype=np.uint)
        model = RandomForestWithInstances(np.zeros((10,), dtype=np.uint), 10)
        model.train(X, f_map, Y[:10])
        x = rs.rand(10)
        m_hat, v_hat = model._predict(x)
        self.assertIsInstance(m_hat, float)
        self.assertIsInstance(v_hat, float)
        self.assertRaisesRegex(ValueError, 'Buffer has wrong number of '
                                           'dimensions \(expected 1, got 2\)',
                               model._predict, X[10:])

    def test_predict_marginalized_over_instances_wrong_X_dimensions(self):
        rs = np.random.RandomState(1)

        model = RandomForestWithInstances(np.zeros((10,), dtype=np.uint), 10,
                                          instance_features=rs.rand(10, 2))
        X = rs.rand(10)
        self.assertRaisesRegex(ValueError, "Expected 2d array, got 1d array!",
                               model.predict_marginalized_over_instances, X)
        X = rs.rand(10, 10, 10)
        self.assertRaisesRegex(ValueError, "Expected 2d array, got 3d array!",
                               model.predict_marginalized_over_instances, X)

        X = rs.rand(10, 5)
        self.assertRaisesRegex(ValueError, "Rows in X should have 8 entries "
                                           "but have 5!",
                               model.predict_marginalized_over_instances, X)

    @mock.patch.object(RandomForestWithInstances, 'predict')
    def test_predict_marginalized_over_instances_no_features(self, rf_mock):
        """The RF should fall back to the regular predict() method."""

        rs = np.random.RandomState(1)
        X = rs.rand(10, 10)
        Y = rs.rand(10, 1)
        f_map = np.array([[i,0] for i in range(10)], dtype=np.uint)
        model = RandomForestWithInstances(np.zeros((10,), dtype=np.uint), 10)
        model.train(X, f_map, Y[:10])
        X = rs.rand(10, 10)
        model.predict(X)
        self.assertEqual(rf_mock.call_count, 1)

    def test_predict_marginalized_over_instances(self):
        rs = np.random.RandomState(1)
        X = rs.rand(20, 10)
        F = rs.rand(10, 5)
        Y = rs.rand(X.shape[1] * F.shape[1], 1)
        f_map = np.array([[i,j] for i in range(X.shape[1]) for j in range(F.shape[1])], dtype=np.uint)
        
        model = RandomForestWithInstances(np.zeros((15,), dtype=np.uint), X.shape[1] * F.shape[1],
                                          instance_features=F)
        model.train(X, f_map, Y)
        means, vars = model.predict_marginalized_over_instances(X)
        self.assertEqual(means.shape, (20, 1))
        self.assertEqual(vars.shape, (20, 1))
