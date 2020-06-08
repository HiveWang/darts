import logging
import unittest

import numpy as np
import pandas as pd

from ..timeseries import TimeSeries


class TimeSeriesTestCase(unittest.TestCase):

    times1 = pd.date_range('20130101', '20130110')
    times2 = pd.date_range('20130201', '20130210')
    dataframe1 = pd.DataFrame({
        0: range(10),
        1: range(5, 15),
        2: range(10, 20)
    }, index=times1)
    dataframe2 = pd.DataFrame({
        0: np.arange(1, 11),
        1: np.arange(1, 11) * 3,
        2: np.arange(1, 11) * 5
    }, index=times1)
    dataframe3 = pd.DataFrame({
        0: np.arange(1, 11),
        1: np.arange(11, 21),
    }, index=times2)
    series1 = TimeSeries(dataframe1)
    series2 = TimeSeries(dataframe2)
    series3 = TimeSeries(dataframe3)

    @classmethod
    def setUpClass(cls):
        logging.disable(logging.CRITICAL)

    def test_creation(self):
        with self.assertRaises(ValueError):
            # Index is dateTimeIndex
            TimeSeries(pd.DataFrame(range(10), range(10)))
        series_test = TimeSeries(self.dataframe1)
        self.assertTrue(series_test.pd_dataframe().equals(self.dataframe1))

        # Series cannot be lower than three without passing frequency as argument to constructor
        with self.assertRaises(ValueError):
            TimeSeries(self.dataframe1.iloc[:2, :])
        TimeSeries(self.dataframe1.iloc[:2, :], 'D')

    def test_eq(self):
        seriesA = TimeSeries(self.dataframe1)
        self.assertTrue(self.series1 == seriesA)
        self.assertFalse(self.series1 != seriesA)

        # with different dates
        dataframeB = self.dataframe1.copy()
        dataframeB.index = pd.date_range('20130102', '20130111')
        seriesB = TimeSeries(dataframeB)
        self.assertFalse(self.series1 == seriesB)

        # with one different value
        dataframeC = self.dataframe1.copy()
        dataframeC.iloc[2, 2] = 0
        seriesC = TimeSeries(dataframeC)
        self.assertFalse(self.series1 == seriesC)

    def test_rescale(self):
        with self.assertRaises(ValueError):
            self.series1.rescale_with_value(1)

        seriesA = self.series2.rescale_with_value(0)
        self.assertTrue(np.all(seriesA.values() == 0).all())

        seriesB = self.series2.rescale_with_value(1)
        self.assertEqual(seriesB, TimeSeries(
            pd.DataFrame({
                0: np.arange(1, 11),
                1: np.arange(1, 11),
                2: np.arange(1, 11)
            }, index=self.dataframe2.index).astype(float)
        ))

    """
    Testing new multivariate methods.
    """

    def test_stack(self):
        with self.assertRaises(ValueError):
            self.series1.stack(self.series3)
        seriesA = self.series1.stack(self.series2)
        dataframeA = pd.concat([self.dataframe1, self.dataframe2], axis=1)
        dataframeA.columns = range(6)
        self.assertTrue((seriesA.pd_dataframe() == dataframeA).all().all())
        self.assertEqual(seriesA.values().shape, (len(self.dataframe1),
                                                  len(self.dataframe1.columns) + len(self.dataframe2.columns)))

    def test_univariate_component(self):
        with self.assertRaises(ValueError):
            self.series1.univariate_component(-1)
        with self.assertRaises(ValueError):
            self.series1.univariate_component(3)
        seriesA = self.series1.univariate_component(1)
        self.assertTrue(seriesA == TimeSeries.from_times_and_values(self.times1, range(5, 15)))
        seriesB = self.series1.univariate_component(0).stack(seriesA).stack(self.series1.univariate_component(2))
        self.assertTrue(self.series1 == seriesB)

    def test_add_datetime_attribute(self):
        seriesA = self.series1.add_datetime_attribute('day')
        self.assertEqual(seriesA.width, self.series1.width + 1)
        self.assertTrue(set(seriesA._series.loc[:, seriesA.width - 1]) == set(range(1, 11)))
        seriesB = self.series1.add_datetime_attribute('day', True)
        self.assertEqual(seriesB.width, self.series1.width + 10)
        self.assertTrue(set(seriesB._series.loc[:, seriesA.width - 1]) == {0, 1})
        seriesC = self.series1.add_datetime_attribute('month', True)
        self.assertEqual(seriesC.width, self.series1.width + 1)

    def test_add_holidays(self):
        times = pd.date_range(start=pd.Timestamp('20201201'), periods=30, freq='D')
        seriesA = TimeSeries.from_times_and_values(times, range(len(times)))

        # testing for christmas and non-holiday in US
        seriesA = seriesA.add_holidays('US')
        last_column = seriesA._series.iloc[:, seriesA.width - 1]
        self.assertEqual(last_column.at[pd.Timestamp('20201225')], 1)
        self.assertEqual(last_column.at[pd.Timestamp('20201210')], 0)
        self.assertEqual(last_column.at[pd.Timestamp('20201226')], 0)

        # testing for christmas and non-holiday in PL
        seriesA = seriesA.add_holidays('PL')
        last_column = seriesA._series.iloc[:, seriesA.width - 1]
        self.assertEqual(last_column.at[pd.Timestamp('20201225')], 1)
        self.assertEqual(last_column.at[pd.Timestamp('20201210')], 0)
        self.assertEqual(last_column.at[pd.Timestamp('20201226')], 1)
        self.assertEqual(seriesA.width, 3)

        # testing hourly time series
        times = pd.date_range(start=pd.Timestamp('20201224'), periods=50, freq='H')
        seriesB = TimeSeries.from_times_and_values(times, range(len(times)))
        seriesB = seriesB.add_holidays('US')
        last_column = seriesB._series.iloc[:, seriesB.width - 1]
        self.assertEqual(last_column.at[pd.Timestamp('2020-12-25 01:00:00')], 1)
        self.assertEqual(last_column.at[pd.Timestamp('2020-12-24 23:00:00')], 0)
